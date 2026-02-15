from datetime import datetime, timedelta
from .base import BaseCollector


class GitHubCollector(BaseCollector):
    """
    Collector for GitHub Repositories.
    Uses the Search API to find trending AI repositories from the last 30 days.
    """

    def __init__(self):
        super().__init__("GitHub")
        # GitHub stars are valuable, so we dampen them less than likes
        self.stats_config.update({
            'damping_factor': 1.5,
            'log_base': 10
        })

    async def collect(self, client):
        print(f"--- {self.platform_name}: Searching for trending repos... ---")
        posts = []

        # We look for repos created or updated in the last 3 months to ensure relevance
        date_since = (datetime.now() - timedelta(days=90)).strftime('%Y-%m-%d')

        # Search queries focused on current hot topics
        queries = [
            f"topic:ai created:>{date_since} sort:stars",
            f"topic:llm created:>{date_since} sort:stars",
            f"topic:agent created:>{date_since} sort:stars"
        ]

        for query in queries:
            url = f"https://api.github.com/search/repositories?q={query}&per_page=15"

            try:
                resp = await client.get(url)
                if resp.status_code == 200:
                    items = resp.json().get('items', [])

                    for item in items:
                        # Skip if no description
                        description = item.get('description', '') or ''

                        # Combine title and description for keyword extraction
                        full_text = f"{item['name']} {description}"
                        found_keys = self.extract_keywords(full_text)

                        if found_keys:
                            # Normalize stars as the raw score
                            stars = item.get('stargazers_count', 0)

                            post = {
                                'source_platform': self.platform_name,
                                'external_id': str(item['id']),
                                'title': item['name'],
                                'content': description,
                                'author': item['owner']['login'],
                                'published_at': item.get('created_at', datetime.now()),
                                'raw_score': stars,
                                'sentiment': self.analyze_sentiment(description),
                                'url': item.get('html_url', ''),
                                'keywords': found_keys
                            }

                            # Additional filter: Must have at least 50 stars to be considered "Trending"
                            if stars > 50:
                                posts.append(post)
                                print(f"   [GitHub] Found: {post['title']} (⭐ {stars})")

            except Exception as e:
                print(f"Error fetching from GitHub: {e}")

        # Remove duplicates from multiple queries
        unique_posts = {p['external_id']: p for p in posts}.values()
        return list(unique_posts)