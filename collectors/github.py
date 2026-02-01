from datetime import datetime
from config import KEYWORDS
from .base import BaseCollector


class GitHubCollector(BaseCollector):
    def __init__(self):
        super().__init__("GitHub")
        # GitHub usually has high variance naturally, so less damping needed.
        self.stats_config.update({
            'min_stdev': 1.0,
            'damping_factor': 1.0,
            'sigmoid_shift': 0.5
        })

    def is_quality_content(self, post):
        if post['raw_score'] < 1:
            return False
        return super().is_quality_content(post)

    async def collect(self, client):
        print(f"--- {self.platform_name}: Searching repos... ---")
        posts = []
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

                        post = {
                            'source_platform': self.platform_name,
                            'external_id': str(item.get('id')),
                            'title': item.get('name', ''),
                            'content': item.get('description', ''),
                            'author': item.get('owner', {}).get('login', ''),
                            'published_at': item.get('created_at', datetime.now()),
                            'raw_score': raw_score,
                            'url': item.get('html_url', ''),
                            'keywords': found_keys
                        }
                        post['sentiment'] = self.analyze_sentiment(post['title'] + " " + post['content'])
                        if self.is_quality_content(post):
                            posts.append(post)
                            print(f"   [{self.platform_name}] Found: {item.get('name')}")
        except Exception as e:
            print(f"Error {self.platform_name}: {e}")
        return posts