import httpx
from datetime import datetime
from config import KEYWORDS
from .base import BaseCollector
from bs4 import BeautifulSoup


class HackerNewsCollector(BaseCollector):
    def __init__(self):
        super().__init__("Hacker News")
        self.stats_config.update({'min_stdev': 0.8, 'damping_factor': 1.2, 'sigmoid_shift': 0.8})

    async def fetch_link_content(self, client, url):
        """Extracts text content from the shared external link."""
        if not url or "news.ycombinator.com" in url: return ""
        try:
            resp = await client.get(url, timeout=10.0)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, 'html.parser')
                # Remove script and style elements
                for script in soup(["script", "style"]): script.decompose()
                text = soup.get_text(separator=' ')
                return " ".join(text.split())[:2000]  # Limit to 2000 chars
        except:
            return ""
        return ""

    async def collect(self, client: httpx.AsyncClient):
        print(f"--- {self.platform_name}: Querying Top Stories & Extracting Links... ---")
        posts = []
        try:
            top_resp = await client.get("https://hacker-news.firebaseio.com/v0/topstories.json")
            top_ids = top_resp.json()[:30]  # Focus on top 30 for quality

            for story_id in top_ids:
                item_resp = await client.get(f"https://hacker-news.firebaseio.com/v0/item/{story_id}.json")
                item = item_resp.json()
                if not item or item.get('type') != 'story': continue

                title = item.get('title', '')
                url = item.get('url', '')

                # Fetch full content from the link instead of relying on empty 'text' field
                link_content = await self.fetch_link_content(client, url)
                full_context = f"{title}. {link_content}"

                found_keys = self.extract_keywords(full_context.lower())
                if found_keys:
                    post = {
                        'source_platform': self.platform_name,
                        'external_id': str(item['id']),
                        'title': title,
                        'content': link_content if link_content else title,
                        'author': item.get('by', 'unknown'),
                        'published_at': datetime.fromtimestamp(item.get('time', 0)).isoformat(),
                        'raw_score': item.get('score', 0),
                        'sentiment': self.analyze_sentiment(full_context),
                        'url': url if url else f"https://news.ycombinator.com/item?id={story_id}",
                        'keywords': found_keys
                    }
                    if self.is_quality_content(post):
                        posts.append(post)
                        print(f"   [HN] Ingested with Full Link Content: {title}")
        except Exception as e:
            print(f"Error HN: {e}")
        return posts