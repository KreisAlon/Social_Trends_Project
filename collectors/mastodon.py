from datetime import datetime
from config import KEYWORDS
from .base import BaseCollector
from bs4 import BeautifulSoup


class MastodonCollector(BaseCollector):
    """
    Collector for Mastodon (decentralized social network).
    Focuses on #AI hashtags to gauge community sentiment.
    """

    def __init__(self):
        super().__init__("Mastodon")

        # --- Statistical Tuning ---
        self.stats_config.update({
            'min_stdev': 0.5,
            'damping_factor': 1.5,
            'sigmoid_shift': 0.5
        })

    def is_quality_content(self, post):
        """
        Strict filtering logic.
        """
        raw_score = post.get('raw_score', 0)
        content_len = len(post.get('content', ''))

        # STRICT FILTER: No engagement = No entry.
        if raw_score <= 0:
            return False

        # Extremely short posts provide little semantic value.
        if content_len < 30:
            return False

        return super().is_quality_content(post)

    async def collect(self, client):
        print(f"--- {self.platform_name}: Ingesting timeline... ---")
        posts = []
        url = "https://mastodon.social/api/v1/timelines/tag/AI?limit=40"

        try:
            resp = await client.get(url)
            if resp.status_code == 200:
                items = resp.json()
                for item in items:
                    if item.get('language') and item.get('language') != 'en':
                        continue

                    # Clean HTML tags immediately to get raw text
                    raw_html = item.get('content', '')
                    clean_text = BeautifulSoup(raw_html, "html.parser").get_text()

                    content_lower = clean_text.lower()
                    found_keys = self.extract_keywords(content_lower)

                    if found_keys:
                        raw_score = item.get('favourites_count', 0)

                        # Optimization: Pre-filter before NLP analysis to save CPU
                        if raw_score <= 0:
                            continue

                        username = item.get('account', {}).get('username', 'Unknown')
                        sentiment = self.analyze_sentiment(clean_text)

                        display_title = clean_text.replace('\n', ' ')
                        post = {
                            'source_platform': self.platform_name,
                            'external_id': str(item.get('id')),
                            'title': display_title,
                            'content': clean_text,
                            'author': username,
                            'published_at': item.get('created_at', datetime.now()),
                            'raw_score': raw_score,
                            'sentiment': sentiment,
                            'url': item.get('url', ''),
                            'keywords': found_keys
                        }

                        if self.is_quality_content(post):
                            posts.append(post)
                            print(f"   [Mastodon] Found: {display_title[:40]}... ({raw_score} likes)")

        except Exception as e:
            print(f"Error fetching from {self.platform_name}: {e}")

        return posts