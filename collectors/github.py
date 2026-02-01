from datetime import datetime
from config import KEYWORDS
from .base import BaseCollector


class GitHubCollector(BaseCollector):
    def __init__(self):
        super().__init__("GitHub")

        # --- Statistical Tuning (Boosting) ---
        # GitHub repos have massive star counts (Mean > 1000).
        # Standard deviation is naturally high, making it hard to get a high Z-Score.
        # Solution:
        # 1. Low 'damping_factor' (0.5) acts as a multiplier, boosting the score.
        # 2. Low 'sigmoid_shift' (0.2) lowers the threshold for trending status.
        self.stats_config.update({
            'min_stdev': 1.0,
            'damping_factor': 0.5,  # Boost factor: rewards deviations more generously
            'sigmoid_shift': 0.2  # Lower threshold to help GitHub repos compete
        })

    def is_quality_content(self, post):
        # Filter out empty repositories with 0 stars
        if post['raw_score'] < 1:
            return False
        return super().is_quality_content(post)

    async def collect(self, client):
        print(f"--- {self.platform_name}: Searching repos... ---")
        posts = []
        # Searching for repositories pushed recently with AI topics
        url = "https://api.github.com/search/repositories?q=topic:ai+pushed:>2024-01-01&sort=stars&order=desc&per_page=15"

        try:
            resp = await client.get(url)
            if resp.status_code == 200:
                items = resp.json().get('items', [])
                for item in items:
                    name = item.get('name', '').lower()
                    desc = (item.get('description') or '').lower()

                    found_keys = self.extract_keywords(name + " " + desc)
                    if found_keys:
                        raw_score = item.get('stargazers_count', 0)

                        # --- SENTIMENT ---
                        sentiment = self.analyze_sentiment(name + " " + desc)

                        post = {
                            'source_platform': self.platform_name,
                            'external_id': str(item.get('id')),
                            'title': item.get('name', ''),
                            'content': item.get('description', ''),
                            'author': item.get('owner', {}).get('login', ''),
                            'published_at': item.get('created_at', datetime.now()),
                            'raw_score': raw_score,
                            'sentiment': sentiment,  # Added
                            'url': item.get('html_url', ''),
                            'keywords': found_keys
                        }

                        if self.is_quality_content(post):
                            posts.append(post)
                            print(f"   [{self.platform_name}] Found: {item.get('name')}")
        except Exception as e:
            print(f"Error {self.platform_name}: {e}")
        return posts