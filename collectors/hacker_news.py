from datetime import datetime
from config import KEYWORDS, TEXT_PREVIEW_LENGTH
from .base import BaseCollector


def _is_english(text):
    try:
        text.encode('utf-8').decode('ascii')
        return True
    except:
        return False


class HackerNewsCollector(BaseCollector):
    def __init__(self):
        super().__init__("Hacker News")
        self.stats_config.update({
            'min_stdev': 0.8,
            'damping_factor': 1.2,  # Slight damping for HN
            'sigmoid_shift': 0.5
        })

    def is_quality_content(self, post):
        if post['raw_score'] < 3: return False
        return super().is_quality_content(post)

    async def collect(self, client):
        print(f"--- {self.platform_name}: Scanning... ---")
        posts = []
        try:
            resp = await client.get('https://hacker-news.firebaseio.com/v0/newstories.json')
            ids = resp.json()[:60]

            for sid in ids:
                item_resp = await client.get(f'https://hacker-news.firebaseio.com/v0/item/{sid}.json')
                data = item_resp.json()

                if data and data.get('type') == 'story':
                    title = data.get('title', '')
                    if not _is_english(title): continue

                    text = data.get('text', '') or ''
                    combined = (title + " " + text[:TEXT_PREVIEW_LENGTH]).lower()

                    found_keys = self.extract_keywords(combined)
                    if found_keys:
                        raw_score = data.get('score', 0)
                        post = {
                            'source_platform': self.platform_name,
                            'external_id': str(data.get('id')),
                            'title': title,
                            'content': text,
                            'author': data.get('by', ''),
                            'published_at': datetime.fromtimestamp(data.get('time', 0)),
                            'raw_score': raw_score,
                            'url': data.get('url', ''),
                            'keywords': found_keys
                        }
                        post['sentiment'] = self.analyze_sentiment(post['title'] + " " + post['content'])

                        if self.is_quality_content(post):
                            posts.append(post)
                            print(f"   [HN] Found: {title[:30]}...")
        except Exception as e:
            print(f"Error {self.platform_name}: {e}")
        return posts