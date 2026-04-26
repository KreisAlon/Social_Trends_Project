import httpx
import textwrap
from collectors.base import BaseCollector
from config import MAX_POSTS_PER_PLATFORM


class MastodonCollector(BaseCollector):
    def __init__(self):
        super().__init__("Mastodon")
        self.api_url = "https://mastodon.social/api/v1/timelines/tag/ai"

    async def collect(self, client: httpx.AsyncClient):
        print(f"--- {self.platform_name}: Ingesting Toots... ---")
        posts = []
        try:
            params = {"limit": MAX_POSTS_PER_PLATFORM}
            response = await client.get(self.api_url, params=params)
            if response.status_code != 200: return []

            items = response.json()[:MAX_POSTS_PER_PLATFORM]

            for item in items:
                clean_content = self.clean_text(item.get('content', ''))

                # --- FILTER REPLIES ---
                # Skip if the post is a personal conversation starting with @
                if clean_content.startswith('@'): continue

                title = textwrap.shorten(clean_content, width=80, placeholder="...")
                raw_score = (item.get('replies_count', 0) +
                             item.get('reblogs_count', 0) +
                             item.get('favourites_count', 0))

                post = {
                    'source_platform': self.platform_name,
                    'external_id': str(item['id']),
                    'title': title,
                    'content': clean_content,
                    'author': item.get('account', {}).get('username', 'unknown'),
                    'url': item.get('url', ''),
                    'raw_score': raw_score,
                    'sentiment': self.analyze_sentiment(clean_content),
                    'published_at': item.get('created_at', '')
                }

                if self.is_quality_content(post):
                    posts.append(post)
            return posts
        except Exception as e:
            print(f"Error in Mastodon: {e}")
            return []