from datetime import datetime
from config import KEYWORDS
from .base import BaseCollector


class MastodonCollector(BaseCollector):
    """
    Collector for Mastodon (decentralized social network).
    Focuses on #AI hashtags to gauge community sentiment.
    """

    def __init__(self):
        super().__init__("Mastodon")

        # --- Statistical Tuning ---
        # Mastodon typically exhibits lower engagement metrics compared to Twitter/X.
        # We apply high damping to prevent low-interaction posts from artificially inflating the trend score.
        self.stats_config.update({
            'min_stdev': 0.5,  # Handling low variance distributions
            'damping_factor': 1.5,  # Aggressive damping for outliers
            'sigmoid_shift': 0.5  # Higher threshold for "trending" status
        })

    def is_quality_content(self, post):
        """
        Advanced filtering logic to distinguish between 'New Content' and 'Spam'.
        """
        raw_score = post.get('raw_score', 0)
        content_len = len(post.get('content', ''))

        # Heuristic 1: The "New Post" Dilemma.
        # If engagement is zero, the content must be substantial (>60 chars) to pass.
        if raw_score <= 0:
            if content_len < 60:
                return False  # Discard low-effort / short spam

        # Heuristic 2: Length validation
        # Extremely short posts (even with likes) provide little semantic value.
        if content_len < 20:
            return False

        # Defer to the BaseCollector's NLP and language checks.
        return super().is_quality_content(post)

    async def collect(self, client):
        print(f"--- {self.platform_name}: Ingesting timeline... ---")
        posts = []
        # Target specific high-traffic tags
        url = "https://mastodon.social/api/v1/timelines/tag/AI?limit=40"

        try:
            resp = await client.get(url)
            if resp.status_code == 200:
                items = resp.json()
                for item in items:
                    # Metadata Filtering: Explicit language tags
                    if item.get('language') and item.get('language') != 'en':
                        continue

                    content_raw = item.get('content', '').lower()
                    found_keys = self.extract_keywords(content_raw)

                    if found_keys:
                        raw_score = item.get('favourites_count', 0)
                        username = item.get('account', {}).get('username', 'Unknown')

                        # Apply Sentiment Analysis (NLP)
                        sentiment = self.analyze_sentiment(content_raw)

                        post = {
                            'source_platform': self.platform_name,
                            'external_id': str(item.get('id')),
                            'title': f"Toot by @{username}",
                            'content': item.get('content', ''),
                            'author': username,
                            'published_at': item.get('created_at', datetime.now()),
                            'raw_score': raw_score,
                            'sentiment': sentiment,
                            'url': item.get('url', ''),
                            'keywords': found_keys
                        }

                        if self.is_quality_content(post):
                            posts.append(post)
                            # --- THIS WAS MISSING ---
                            print(f"   [Mastodon] Found: {post['title']} ({raw_score} likes)")

        except Exception as e:
            print(f"Error fetching from {self.platform_name}: {e}")

        return posts