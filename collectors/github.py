import base64
import httpx
from collectors.base import BaseCollector


class GitHubCollector(BaseCollector):
    def __init__(self, config):
        super().__init__(config, "GitHub")
        self.base_url = "https://api.github.com/search/repositories"

    async def fetch_readme(self, client, owner, repo):
        """
        Fetches the README.md content for a given repository to extract deeper semantic context.
        Returns the first 1500 characters to optimize DB storage while maintaining context.
        """
        url = f"https://api.github.com/repos/{owner}/{repo}/readme"
        try:
            response = await client.get(url)
            if response.status_code == 200:
                content_b64 = response.json().get('content', '')
                # Decode Base64 content from GitHub API
                readme_text = base64.b64decode(content_b64).decode('utf-8', errors='ignore')
                return readme_text[:1500]
        except Exception:
            return ""
        return ""

    async def collect(self, client: httpx.AsyncClient):
        # Querying for high-impact AI/ML repositories
        query = "topic:ai OR topic:machine-learning OR topic:llm"
        params = {
            "q": query,
            "sort": "stars",
            "order": "desc",
            "per_page": self.config.get('per_page', 30)
        }

        try:
            response = await client.get(self.base_url, params=params)
            response.raise_for_status()
            data = response.json()

            posts = []
            for item in data.get('items', []):
                owner = item['owner']['login']
                repo_name = item['name']

                # Fetch deeper content (README) asynchronously
                readme_content = await self.fetch_readme(client, owner, repo_name)

                # Merge description and README for rich semantic analysis
                description = item.get('description', '') or ''
                full_content = f"{description}\n\n{readme_content}".strip()

                post = {
                    'source_platform': self.platform_name,
                    'external_id': str(item['id']),
                    'title': repo_name,
                    'content': full_content,
                    'author': owner,
                    'url': item['html_url'],
                    'raw_score': item['stargazers_count'],
                    'published_at': item['updated_at']
                }

                # Filter out low-quality or irrelevant repositories
                if self.is_quality_content(post):
                    posts.append(post)

            return posts
        except Exception as e:
            print(f"Error collecting from GitHub: {e}")
            return []