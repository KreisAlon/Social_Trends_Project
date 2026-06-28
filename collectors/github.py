import base64
import httpx
import asyncio
from collectors.base import BaseCollector
from config import MAX_POSTS_PER_PLATFORM

async def fetch_readme(client, owner, repo):
    """
    Fetches and decodes the README.md for a given repository.
    Includes a timeout to prevent hanging on unresponsive servers or massive files.
    """
    url = f"https://api.github.com/repos/{owner}/{repo}/readme"
    try:
        headers = {'Accept': 'application/vnd.github.v3+json'}
        # Added a 5.0 second timeout for external safety
        response = await client.get(url, headers=headers, timeout=5.0)
        
        if response.status_code == 200:
            content_b64 = response.json().get('content', '')
            # Decode Base64 and limit to 800 characters for optimal keyword extraction
            return base64.b64decode(content_b64).decode('utf-8', errors='ignore')[:800]
    except Exception:
        return ""
    return ""

class GitHubCollector(BaseCollector):
    """
    Collector for GitHub repositories.
    Implements concurrent fetching for README files to avoid sequential blocking.
    """
    def __init__(self):
        super().__init__("GitHub")
        self.base_url = "https://api.github.com/search/repositories"

    async def process_repo(self, client, item):
        """
        Helper function to process a single repository concurrently.
        Fetches the README, normalizes the data, and runs quality checks.
        """
        try:
            repo_name = item['name']
            
            # Execute the concurrent deep fetch for the README content
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

            # Pass through the semantic gatekeeper to extract keywords
            if self.is_quality_content(post):
                return post
                
        except Exception as e:
            print(f"Error processing GitHub repo {item.get('name')}: {e}")
            
        return None

    async def collect(self, client: httpx.AsyncClient):
        """Main entry point. Fetches top repositories and dispatches concurrent tasks."""
        print(f"--- {self.platform_name}: Searching for trending AI repos concurrently... ---")
        try:
            params = {
                "q": "AI OR LLM OR GPT OR 'Machine Learning' stars:>500",
                "sort": "updated",
                "per_page": MAX_POSTS_PER_PLATFORM
            }
            headers = {'Accept': 'application/vnd.github.v3+json'}
            
            response = await client.get(self.base_url, params=params, headers=headers)
            if response.status_code != 200: 
                return []

            items = response.json().get('items', [])[:MAX_POSTS_PER_PLATFORM]

            # Concurrency implementation: Dispatch a task to fetch the README for each repo
            tasks = [self.process_repo(client, item) for item in items]
            results = await asyncio.gather(*tasks)

            # Filter out invalid or failed repositories
            return [post for post in results if post is not None]
            
        except Exception as e:
            print(f"Critical Error in GitHub Collector orchestration: {e}")
            return []