import httpx
from datetime import datetime
from config import KEYWORDS
from .base import BaseCollector


class DevToCollector(BaseCollector):
    def __init__(self):
        super().__init__("Dev.to")

        # --- Statistical Tuning ---
        self.stats_config.update({
            'min_stdev': 0.8,
            'damping_factor': 1.2,
            'sigmoid_shift': 0.8
        })

    async def fetch_full_article(self, client, article_id):
        """
        Fetches the full markdown body of a dev.to article to provide
        rich content for the semantic embedding model.
        """
        url = f"https://dev.to/api/articles/{article_id}"
        try:
            resp = await client.get(url)
            if resp.status_code == 200:
                data = resp.json()
                # Return the full markdown, or fallback to description
                return data.get('body_markdown', '') or data.get('description', '')
        except Exception:
            return ""
        return ""

    async def collect(self, client: httpx.AsyncClient):
        print(f"--- {self.platform_name}: Scanning for high-quality articles... ---")
        posts = []
        url = "https://dev.to/api/articles?tag=ai&top=1"

        try:
            resp = await client.get(url)
            if resp.status_code == 200:
                items = resp.json()
                for item in items:
                    raw_score = item.get('public_reactions_count', 0)

                    # STRICT FILTER: Completely ignore posts with 0 engagement
                    if raw_score <= 0:
                        continue

                    title = item.get('title', '')
                    article_id = item.get('id')

                    # Fetch the full text for deep NLP analysis
                    full_text = await self.fetch_full_article(client, article_id)
                    # Take up to 2000 characters to keep the DB optimized
                    clean_content = full_text[:2000]

                    found_keys = self.extract_keywords((title + " " + clean_content).lower())
                    if found_keys:
                        sentiment = self.analyze_sentiment(title + " " + clean_content)

                        post = {
                            'source_platform': self.platform_name,
                            'external_id': str(article_id),
                            'title': title,
                            'content': clean_content,
                            'author': item.get('user', {}).get('username', ''),
                            'published_at': item.get('published_at', datetime.now().isoformat()),
                            'raw_score': raw_score,
                            'sentiment': sentiment,
                            'url': item.get('url', ''),
                            'keywords': found_keys
                        }

                        if self.is_quality_content(post):
                            posts.append(post)
                            # NO TRUNCATION - Print the full title
                            print(f"   [Dev.to] Ingested Full Article: {title}")
        except Exception as e:
            print(f"Error {self.platform_name}: {e}")
        return posts