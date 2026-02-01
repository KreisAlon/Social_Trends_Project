from datetime import datetime
from config import KEYWORDS, TEXT_PREVIEW_LENGTH
from .base import BaseCollector


def _is_english(text):
    """Simple ASCII check as a first line of defense before NLP."""
    try:
        text.encode('utf-8').decode('ascii')
        return True
    except UnicodeDecodeError:
        return False


class HackerNewsCollector(BaseCollector):
    def __init__(self):
        super().__init__("Hacker News")

        # --- Statistical Tuning ---
        # Hacker News is text-heavy and critical.
        # We apply slight damping to balance it against GitHub's massive numbers.
        self.stats_config.update({
            'min_stdev': 0.8,
            'damping_factor': 1.2,
            'sigmoid_shift': 0.5
        })

    def is_quality_content(self, post):
        # HN posts with very low points are usually ignored
        if post['raw_score'] < 3:
            return False
        return super().is_quality_content(post)

    async def collect(self, client):
        print(f"--- {self.platform_name}: Scanning... ---")
        posts = []
        try:
            # Fetch top new stories
            resp = await client.get('https://hacker-news.firebaseio.com/v0/newstories.json')
            ids = resp.json()[:60]  # Scan top 60 items

            for sid in ids:
                item_resp = await client.get(f'https://hacker-news.firebaseio.com/v0/item/{sid}.json')
                data = item_resp.json()

                if data and data.get('type') == 'story':
                    title = data.get('title', '')

                    # Fast filter for non-English titles
                    if not _is_english(title):
                        continue

                    text = data.get('text', '') or ''
                    combined_text = (title + " " + text[:TEXT_PREVIEW_LENGTH]).lower()

                    found_keys = self.extract_keywords(combined_text)
                    if found_keys:
                        raw_score = data.get('score', 0)

                        # --- SENTIMENT ANALYSIS ---
                        # Calculating sentiment score (-1.0 to 1.0)
                        sentiment_score = self.analyze_sentiment(title + " " + text)

                        post = {
                            'source_platform': self.platform_name,
                            'external_id': str(data.get('id')),
                            'title': title,
                            'content': text,
                            'author': data.get('by', ''),
                            'published_at': datetime.fromtimestamp(data.get('time', 0)),
                            'raw_score': raw_score,
                            'sentiment': sentiment_score,  # Saving sentiment
                            'url': data.get('url', ''),
                            'keywords': found_keys
                        }

                        if self.is_quality_content(post):
                            posts.append(post)
                            print(f"   [HN] Found: {title[:30]}...")

        except Exception as e:
            print(f"Error {self.platform_name}: {e}")
        return posts