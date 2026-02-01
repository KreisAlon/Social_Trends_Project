from datetime import datetime
from config import KEYWORDS
from .base import BaseCollector


class DevToCollector(BaseCollector):
    def __init__(self):
        super().__init__("Dev.to")
        self.stats_config.update({
            'min_stdev': 0.8,
            'damping_factor': 1.1,
            'sigmoid_shift': 0.5
        })

    async def collect(self, client):
        print(f"--- {self.platform_name}: Scanning... ---")
        posts = []
        url = "https://dev.to/api/articles?tag=ai&top=1"

        try:
            resp = await client.get(url)
            if resp.status_code == 200:
                items = resp.json()
                for item in items:
                    title = item.get('title', '').lower()
                    desc = (item.get('description') or '').lower()

                    found_keys = self.extract_keywords(title + " " + desc)
                    if found_keys:
                        raw_score = item.get('public_reactions_count', 0)
                        post = {
                            'source_platform': self.platform_name,
                            'external_id': str(item.get('id')),
                            'title': item.get('title', ''),
                            'content': item.get('description', ''),
                            'author': item.get('user', {}).get('username', ''),
                            'published_at': item.get('published_at', datetime.now().isoformat()),
                            'raw_score': raw_score,
                            'url': item.get('url', ''),
                            'keywords': found_keys
                        }
                        post['sentiment'] = self.analyze_sentiment(post['title'] + " " + post['content'])

                        if self.is_quality_content(post):
                            posts.append(post)
                            print(f"   [Dev.to] Found: {item.get('title')[:30]}...")
        except Exception as e:
            print(f"Error {self.platform_name}: {e}")
        return posts