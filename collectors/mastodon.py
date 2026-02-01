from datetime import datetime
from config import KEYWORDS
from .base import BaseCollector


class MastodonCollector(BaseCollector):
    def __init__(self):
        super().__init__("Mastodon")
        # --- Mastodon Specific Tuning ---
        # High damping because small numbers (1-5 likes) create huge variance.
        self.stats_config.update({
            'min_stdev': 0.5,  # Enforce strict minimum variance
            'damping_factor': 1.5,  # Strong damping to prevent 99.9 scores easily
            'sigmoid_shift': 0.5  # Require score to be clearly above average
        })

    def is_quality_content(self, post):
        # Strict filtering for Mastodon noise
        if post['raw_score'] == 0 and len(post.get('content', '')) < 50:
            return False
        return super().is_quality_content(post)

    async def collect(self, client):
        print(f"--- {self.platform_name}: Scanning feed... ---")
        posts = []
        url = "https://mastodon.social/api/v1/timelines/tag/AI?limit=40"

        try:
            resp = await client.get(url)
            if resp.status_code == 200:
                items = resp.json()
                for item in items:
                    if item.get('language') != 'en': continue
                    content_raw = item.get('content', '').lower()

                    found_keys = self.extract_keywords(content_raw)
                    if found_keys:
                        raw_score = item.get('favourites_count', 0)
                        username = item.get('account', {}).get('username', 'Unknown')

                        post = {
                            'source_platform': self.platform_name,
                            'external_id': str(item.get('id')),
                            'title': f"Toot by @{username}",
                            'content': item.get('content', ''),
                            'author': username,
                            'published_at': item.get('created_at', datetime.now()),
                            'raw_score': raw_score,
                            'url': item.get('url', ''),
                            'keywords': found_keys
                        }
                        post['sentiment'] = self.analyze_sentiment(post['title'] + " " + post['content'])

                        if self.is_quality_content(post):
                            posts.append(post)
        except Exception as e:
            print(f"Error {self.platform_name}: {e}")
        return posts