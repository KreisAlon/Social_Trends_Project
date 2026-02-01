from datetime import datetime
from config import KEYWORDS, TEXT_PREVIEW_LENGTH
from .base import BaseCollector


def _is_english(text):
    """
    Fast ASCII-based heuristic to filter out non-English titles
    before invoking the heavy NLP model.
    """
    try:
        text.encode('utf-8').decode('ascii')
        return True
    except UnicodeDecodeError:
        return False


class HackerNewsCollector(BaseCollector):
    """
    Collector for YCombinator's Hacker News.
    Targets high-quality technical discussions and industry news.
    """

    def __init__(self):
        super().__init__("Hacker News")

        # --- Statistical Tuning ---
        # HN uses a weighted voting algorithm. Scores can be high but not as inflated as GitHub stars.
        self.stats_config.update({
            'min_stdev': 0.8,
            'damping_factor': 1.2,  # Slight damping to normalize against GitHub
            'sigmoid_shift': 0.5
        })

    def is_quality_content(self, post):
        # Filter: Ignore items with very low traction as they are likely noise.
        # Since we fetch 'Top Stories', most items should pass this.
        if post['raw_score'] < 5:
            return False
        return super().is_quality_content(post)

    async def collect(self, client):
        print(f"--- {self.platform_name}: Querying Top Stories... ---")
        posts = []
        try:
            # API Strategy: 'topstories' returns IDs of the current front page.
            # This ensures high relevance compared to 'newstories'.
            resp = await client.get('https://hacker-news.firebaseio.com/v0/topstories.json')
            ids = resp.json()[:80]  # Processing the top 80 items

            for sid in ids:
                item_resp = await client.get(f'https://hacker-news.firebaseio.com/v0/item/{sid}.json')
                data = item_resp.json()

                if data and data.get('type') == 'story':
                    title = data.get('title', '')

                    # Pre-filter non-English titles
                    if not _is_english(title):
                        continue

                    text = data.get('text', '') or ''
                    # Combine title and intro for keyword extraction context
                    combined_text = (title + " " + text[:TEXT_PREVIEW_LENGTH]).lower()

                    found_keys = self.extract_keywords(combined_text)
                    if found_keys:
                        raw_score = data.get('score', 0)

                        # NLP Sentiment Analysis
                        sentiment = self.analyze_sentiment(title + " " + text)

                        post = {
                            'source_platform': self.platform_name,
                            'external_id': str(data.get('id')),
                            'title': title,
                            'content': text,
                            'author': data.get('by', ''),
                            'published_at': datetime.fromtimestamp(data.get('time', 0)),
                            'raw_score': raw_score,
                            'sentiment': sentiment,
                            'url': data.get('url', f"https://news.ycombinator.com/item?id={data.get('id')}"),
                            'keywords': found_keys
                        }

                        if self.is_quality_content(post):
                            posts.append(post)
                            print(f"   [HN] Ingested: {title[:30]}...")

        except Exception as e:
            print(f"Connection Error {self.platform_name}: {e}")
        return posts