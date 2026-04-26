import httpx
from collectors.base import BaseCollector
from config import MAX_POSTS_PER_PLATFORM


class DevToCollector(BaseCollector):
    """
    Collector for Dev.to articles.
    Uses 'Deep Fetching' to get the full article body instead of truncated descriptions.
    """

    def __init__(self):
        super().__init__("Dev.to")
        self.api_url = "https://dev.to/api/articles"

    async def fetch_full_content(self, client, article_id):
        """Fetches the full markdown body of an article for better NLP context."""
        url = f"https://dev.to/api/articles/{article_id}"
        try:
            resp = await client.get(url)
            if resp.status_code == 200:
                data = resp.json()
                return data.get('body_markdown', '') or data.get('description', '')
        except:
            return ""
        return ""

    async def collect(self, client: httpx.AsyncClient):
        print(f"--- {self.platform_name}: Performing Deep Fetch for Articles... ---")
        posts = []
        try:
            params = {"tag": "ai", "per_page": MAX_POSTS_PER_PLATFORM}
            response = await client.get(self.api_url, params=params)
            if response.status_code != 200: return []

            articles = response.json()[:MAX_POSTS_PER_PLATFORM]

            for art in articles:
                # DEEP FETCH: Get the full content instead of the truncated 'description'
                full_content = await self.fetch_full_content(client, art['id'])

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
                if self.is_quality_content(post):
                    posts.append(post)
            return posts
        except Exception as e:
            print(f"Error Dev.to: {e}")
            return []