from datetime import datetime
from config import KEYWORDS
from .base import BaseCollector


class MastodonCollector(BaseCollector):
    def __init__(self):
        super().__init__("Mastodon")

        # --- Statistical Tuning (Aggressive Damping) ---
        # Problem: Mastodon has very low average engagement (Mean ~= 0.1).
        # Result: A post with 3 likes could trigger a massive Z-Score (e.g., +10 SD).
        # Solution:
        # 1. High 'damping_factor' (3.0) reduces the Z-Score impact.
        # 2. High 'sigmoid_shift' (1.0) shifts the center, requiring stronger evidence to trend.
        self.stats_config.update({
            'min_stdev': 0.5,  # Prevent division by near-zero variance
            'damping_factor': 3.0,  # Strongly dampen outliers to prevent false positives
            'sigmoid_shift': 1.0  # Require significantly above-average performance
        })

    def is_quality_content(self, post):
        # Strict filtering for micro-blogging noise
        if post['raw_score'] == 0 and len(post.get('content', '')) < 50:
            return False
        return super().is_quality_content(post)

    async def collect(self, client):
        print(f"--- {self.platform_name}: Scanning feed... ---")
        posts = []
        # Searching for the specific hashtag
        url = "https://mastodon.social/api/v1/timelines/tag/AI?limit=40"

        try:
            resp = await client.get(url)
            if resp.status_code == 200:
                items = resp.json()
                for item in items:
                    # Filter: Only process content explicitly marked as English
                    if item.get('language') != 'en':
                        continue

                    content_raw = item.get('content', '').lower()
                    found_keys = self.extract_keywords(content_raw)

                    if found_keys:
                        raw_score = item.get('favourites_count', 0)
                        username = item.get('account', {}).get('username', 'Unknown')

                        # --- SENTIMENT ---
                        sentiment = self.analyze_sentiment(content_raw)

                        post = {
                            'source_platform': self.platform_name,
                            'external_id': str(item.get('id')),
                            'title': f"Toot by @{username}",
                            'content': item.get('content', ''),
                            'author': username,
                            'published_at': item.get('created_at', datetime.now()),
                            'raw_score': raw_score,
                            'sentiment': sentiment,  # Added
                            'url': item.get('url', ''),
                            'keywords': found_keys
                        }

                        if self.is_quality_content(post):
                            posts.append(post)
        except Exception as e:
            print(f"Error {self.platform_name}: {e}")
        return posts