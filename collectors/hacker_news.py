import httpx
from bs4 import BeautifulSoup
from collectors.base import BaseCollector
from config import MAX_POSTS_PER_PLATFORM


class HackerNewsCollector(BaseCollector):
    """
    Collector for Hacker News.
    Crawls external links to provide rich semantic content for NLP analysis.
    """

    def __init__(self):
        super().__init__("Hacker News")
        self.top_stories_url = "https://hacker-news.firebaseio.com/v0/topstories.json"
        self.item_url = "https://hacker-news.firebaseio.com/v0/item/{}.json"

    async def scrape_external_link(self, client, url):
        """Extracts readable text from external websites shared on HN."""
        if not url or "news.ycombinator.com" in url: return ""
        try:
            resp = await client.get(url, timeout=10.0)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, 'html.parser')
                # Remove non-text elements
                for s in soup(["script", "style", "nav", "footer"]): s.decompose()
                return soup.get_text(separator=' ')[:2000]  # Limit to 2000 chars
        except:
            return ""
        return ""

    async def collect(self, client: httpx.AsyncClient):
        print(f"--- {self.platform_name}: Crawling External Stories... ---")
        posts = []
        try:
            response = await client.get(self.top_stories_url)
            if response.status_code != 200: return []

            story_ids = response.json()[:MAX_POSTS_PER_PLATFORM]

            for sid in story_ids:
                item_res = await client.get(self.item_url.format(sid))
                if item_res.status_code == 200:
                    item = item_res.json()
                    url = item.get('url', '')

                    # CRAWL: Go get the actual content from the article link
                    external_text = await self.scrape_external_link(client, url)
                    content = external_text if external_text else item.get('text', item.get('title'))

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
                    if self.is_quality_content(post):
                        posts.append(post)
            return posts
        except Exception as e:
            print(f"Error HN: {e}")
            return []