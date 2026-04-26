import base64
import httpx
from collectors.base import BaseCollector
from config import MAX_POSTS_PER_PLATFORM


async def fetch_readme(client, owner, repo):
    url = f"https://api.github.com/repos/{owner}/{repo}/readme"
    try:
        headers = {'Accept': 'application/vnd.github.v3+json'}
        response = await client.get(url, headers=headers)
        if response.status_code == 200:
            content_b64 = response.json().get('content', '')
            return base64.b64decode(content_b64).decode('utf-8', errors='ignore')[:800]
    except Exception:
        return ""
    return ""


class GitHubCollector(BaseCollector):
    def __init__(self):
        super().__init__("GitHub")
        self.base_url = "https://api.github.com/search/repositories"

    async def collect(self, client: httpx.AsyncClient):
        print(f"--- {self.platform_name}: Searching for trending AI repos... ---")
        posts = []
        params = {
            "q": "AI OR LLM OR GPT OR 'Machine Learning' stars:>500",
            "sort": "updated",
            "per_page": MAX_POSTS_PER_PLATFORM
        }

        try:
            headers = {'Accept': 'application/vnd.github.v3+json'}
            response = await client.get(self.base_url, params=params, headers=headers)
            if response.status_code != 200: return []

            items = response.json().get('items', [])[:MAX_POSTS_PER_PLATFORM]

            for item in items:
                repo_name = item['name']
                readme = await fetch_readme(client, item['owner']['login'], repo_name)
                content = f"Project: {repo_name}. Description: {item.get('description', '')}. Details: {readme}"

                post = {
                    'source_platform': self.platform_name,
                    'external_id': str(item['id']),
                    'title': repo_name,
                    'content': content,
                    'author': item['owner']['login'],
                    'url': item['html_url'],
                    'raw_score': item['stargazers_count'],
                    'sentiment': self.analyze_sentiment(content),
                    'published_at': item['updated_at']
                }

                # is_quality_content handles cleaning and keyword extraction
                if self.is_quality_content(post):
                    posts.append(post)
            return posts
        except Exception as e:
            print(f"Error GitHub: {e}")
            return []