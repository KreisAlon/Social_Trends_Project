import base64
import httpx
from collectors.base import BaseCollector
from config import KEYWORDS


async def fetch_readme(client, owner, repo):
    """
    Fetches the README.md content for a given repository.
    This provides the 'meat' for our vector embedding model.
    """
    url = f"https://api.github.com/repos/{owner}/{repo}/readme"
    try:
        # GitHub API requires specific headers for better compatibility
        headers = {'Accept': 'application/vnd.github.v3+json'}
        response = await client.get(url, headers=headers)
        if response.status_code == 200:
            content_b64 = response.json().get('content', '')
            # Decode base64 content and ignore decoding errors
            readme_text = base64.b64decode(content_b64).decode('utf-8', errors='ignore')
            return readme_text[:1500]  # Limiting to 1500 chars for DB optimization
    except Exception:
        return ""
    return ""


class GitHubCollector(BaseCollector):
    """
    Collector for GitHub.
    Searches for trending repositories related to AI and LLMs
    and fetches their README content for semantic analysis.
    """

    def __init__(self):
        super().__init__("GitHub")
        self.base_url = "https://api.github.com/search/repositories"

    async def collect(self, client: httpx.AsyncClient):
        print(f"--- {self.platform_name}: Searching for trending AI repos... ---")
        posts = []

        # BROADER SEARCH STRATEGY:
        # Searching keywords in name/description and filtering for active repos with stars
        search_query = "AI OR LLM OR GPT OR 'Machine Learning' OR DeepSeek stars:>500"
        params = {
            "q": search_query,
            "sort": "updated",  # Get recently updated projects
            "order": "desc",
            "per_page": 20
        }

        try:
            # Note: GitHub API is strict about User-Agent and Headers
            headers = {'Accept': 'application/vnd.github.v3+json'}
            response = await client.get(self.base_url, params=params, headers=headers)

            if response.status_code != 200:
                print(f"   [GitHub] API Error: {response.status_code}")
                return []

            data = response.json()
            for item in data.get('items', []):
                owner = item['owner']['login']
                repo_name = item['name']
                description = item.get('description', '') or ""

                # Step 1: Fetch the actual README content
                readme_content = await fetch_readme(client, owner, repo_name)

                # Combine metadata for semantic keyword matching
                full_context = f"{repo_name} {description} {readme_content}"

                # Step 2: Use the BaseCollector's keyword extraction
                found_keys = self.extract_keywords(full_context.lower())

                if found_keys:
                    post = {
                        'source_platform': self.platform_name,
                        'external_id': str(item['id']),
                        'title': repo_name,
                        'content': f"{description}\n\n{readme_content}",
                        'author': owner,
                        'url': item['html_url'],
                        'raw_score': item['stargazers_count'],
                        'sentiment': self.analyze_sentiment(full_context),
                        'published_at': item['updated_at'],
                        'keywords': found_keys
                    }

                    # Step 3: Final quality check
                    if self.is_quality_content(post):
                        posts.append(post)
                        print(f"   [GitHub] Ingested Repo: {repo_name} ({post['raw_score']} stars)")

            return posts
        except Exception as e:
            print(f"Error collecting from GitHub: {e}")
            return []