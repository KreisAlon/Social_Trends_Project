import httpx
import asyncio
from bs4 import BeautifulSoup
from collectors.base import BaseCollector
from config import MAX_POSTS_PER_PLATFORM

class HackerNewsCollector(BaseCollector):
    """
    Collector for Hacker News (Y Combinator).
    
    Architecture Note:
    Hacker News API only provides links to external websites. This collector acts as a 
    mini web-crawler, visiting each external link concurrently to scrape the actual 
    readable text for our NLP engine.
    """

    def __init__(self):
        super().__init__("Hacker News")
        self.top_stories_url = "https://hacker-news.firebaseio.com/v0/topstories.json"
        self.item_url = "https://hacker-news.firebaseio.com/v0/item/{}.json"

    async def scrape_external_link(self, client, url):
        """
        Crawls an external website and extracts clean, readable text.
        
        Args:
            client (httpx.AsyncClient): The shared async HTTP client.
            url (str): The external target URL.
            
        Returns:
            str: Sanitized text content, stripped of HTML structure.
        """
        # Skip self-referential HN discussion pages (they lack external article content)
        if not url or "news.ycombinator.com" in url: 
            return ""
            
        try:
            # Strict timeout of 5.0 seconds to prevent slow external servers 
            # from degrading our system's overall performance.
            resp = await client.get(url, timeout=5.0)
            
            if resp.status_code == 200:
                # Parse the raw HTML into a DOM tree
                soup = BeautifulSoup(resp.text, 'html.parser')
                
                # Strip out functional/visual elements that pollute NLP analysis
                for s in soup(["script", "style", "nav", "footer", "header"]): 
                    s.decompose()
                    
                # Extract pure text and truncate to 2000 characters to save memory
                return soup.get_text(separator=' ')[:2000]
        except Exception:
            # External scraping is volatile; fail silently if a website blocks us
            return ""
        return ""

    async def process_story(self, client, sid):
        """
        Pipeline for processing a single HN story: resolving the ID to a URL,
        crawling the target, and normalizing the extracted data.
        """
        try:
            # Step 1: Resolve the Story ID to get the metadata
            item_res = await client.get(self.item_url.format(sid))
            
            if item_res.status_code == 200:
                item = item_res.json()
                if not item: 
                    return None
                    
                url = item.get('url', '')

                # Step 2: Trigger the external crawler
                external_text = await self.scrape_external_link(client, url)
                
                # Fallback to the HN title/text if the external crawl fails
                content = external_text if external_text else item.get('text', item.get('title'))

                # Step 3: Map to Unified Schema
                post = {
                    'source_platform': self.platform_name,
                    'external_id': str(sid),
                    'title': item.get('title', ''),
                    'content': content,
                    'author': item.get('by', 'unknown'),
                    'url': url if url else f"https://news.ycombinator.com/item?id={sid}",
                    'raw_score': item.get('score', 0),
                    'sentiment': self.analyze_sentiment(content),
                    'published_at': item.get('time', '')
                }
                
                # Step 4: Quality Check
                if self.is_quality_content(post):
                    return post
                    
        except Exception:
            # Ignore individual story failures to maintain batch integrity
            pass 
            
        return None

    async def collect(self, client: httpx.AsyncClient):
        """Main entry point. Fetches top IDs and dispatches concurrent crawlers."""
        print(f"--- {self.platform_name}: Crawling External Stories Concurrently... ---")
        try:
            # Fetch the current top trending story IDs
            response = await client.get(self.top_stories_url)
            if response.status_code != 200: 
                return []

            story_ids = response.json()[:MAX_POSTS_PER_PLATFORM]

            # Concurrency implementation: Dispatch a crawler task for each story ID
            tasks = [self.process_story(client, sid) for sid in story_ids]
            
            # Wait for all concurrent crawlers to return their payloads
            results = await asyncio.gather(*tasks)

            # Clean out the None values returned by failed/rejected stories
            return [post for post in results if post is not None]
            
        except Exception as e:
            print(f"Critical Error in Hacker News Collector orchestration: {e}")
            return []