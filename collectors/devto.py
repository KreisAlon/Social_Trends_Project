import httpx
import asyncio
from collectors.base import BaseCollector
from config import MAX_POSTS_PER_PLATFORM

class DevToCollector(BaseCollector):
    """
    Collector for Dev.to articles.
    
    Architecture Note:
    This collector uses 'Deep Fetching' to retrieve the full markdown body of articles
    rather than relying on truncated API descriptions. To prevent network I/O bottlenecks,
    it implements concurrent fetching using asyncio.gather().
    """

    def __init__(self):
        super().__init__("Dev.to")
        self.api_url = "https://dev.to/api/articles"

    async def fetch_full_content(self, client, article_id):
        """
        Retrieves the complete markdown content for a specific article.
        
        Args:
            client (httpx.AsyncClient): The shared async HTTP client.
            article_id (int): The unique identifier of the Dev.to article.
            
        Returns:
            str: The full markdown body, or fallback description if the body is unavailable.
        """
        url = f"https://dev.to/api/articles/{article_id}"
        try:
            resp = await client.get(url)
            if resp.status_code == 200:
                data = resp.json()
                # Prefer the full markdown body for deep semantic analysis
                return data.get('body_markdown', '') or data.get('description', '')
        except Exception as e:
            # Silent fail for individual requests to prevent breaking the entire batch
            return ""
        return ""

    async def process_article(self, client, art):
        """
        Pipeline for processing a single article: fetching content, normalizing schema, 
        and validating quality. Designed to be run concurrently.
        """
        try:
            # 1. Execute the deep fetch
            full_content = await self.fetch_full_content(client, art['id'])

            # 2. Map external data to our internal Unified Schema
            post = {
                'source_platform': self.platform_name,
                'external_id': str(art['id']),
                'title': art.get('title', ''),
                'content': full_content if full_content else art.get('description', ''),
                'author': art.get('user', {}).get('username', 'unknown'),
                'url': art.get('url', ''),
                'raw_score': art.get('public_reactions_count', 0),
                'sentiment': self.analyze_sentiment(full_content),
                'published_at': art.get('published_at', '')
            }
            
            # 3. Pass through the semantic gatekeeper (base.py)
            if self.is_quality_content(post):
                return post
        except Exception as e:
            print(f"Error processing Dev.to article {art.get('id')}: {e}")
        
        # Return None if the article fails validation or encounters an error
        return None

    async def collect(self, client: httpx.AsyncClient):
        """Main entry point for the collector. Orchestrates the concurrent fetching."""
        print(f"--- {self.platform_name}: Performing Concurrent Deep Fetch... ---")
        try:
            params = {"tag": "ai", "per_page": MAX_POSTS_PER_PLATFORM}
            response = await client.get(self.api_url, params=params)
            
            if response.status_code != 200: 
                return []

            articles = response.json()[:MAX_POSTS_PER_PLATFORM]

            # Concurrency implementation: Create a list of async tasks for all articles
            tasks = [self.process_article(client, art) for art in articles]
            
            # Execute all tasks simultaneously. This reduces execution time from 
            # O(N) linear time to O(1) network latency time.
            results = await asyncio.gather(*tasks)

            # Filter out None values (articles that failed quality checks or network errors)
            return [post for post in results if post is not None]
            
        except Exception as e:
            print(f"Critical Error in Dev.to Collector orchestration: {e}")
            return []