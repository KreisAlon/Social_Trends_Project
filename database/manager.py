import sqlite3
import os
import asyncio
import httpx

from collectors.github import GitHubCollector
from collectors.hacker_news import HackerNewsCollector
from collectors.mastodon import MastodonCollector
from collectors.devto import DevToCollector

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "trends_project.db")


class TrendManager:
    """
    Orchestrator Class.
    Initializes DB and runs the collection cycle.
    """

    def __init__(self):
        self.collectors = [
            GitHubCollector(),
            HackerNewsCollector(),
            MastodonCollector(),
            DevToCollector()
        ]
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''
                    CREATE TABLE IF NOT EXISTS unified_posts (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        source_platform TEXT,
                        external_id TEXT,
                        title TEXT,
                        content TEXT,
                        author TEXT,
                        published_at TIMESTAMP,
                        raw_score INTEGER,      
                        trend_score REAL, 
                        sentiment REAL,  
                        url TEXT,
                        found_keywords TEXT,
                        UNIQUE(source_platform, external_id)
                    )
                ''')
        conn.commit()
        conn.close()
        print(f"[Manager] Database Ready.")

    async def run_collection_cycle(self):
        print("\n>>> Starting Data Collection Cycle...")

        async with httpx.AsyncClient(headers={'User-Agent': 'TrendAnalyzer/Bot'}) as client:
            # 1. Collect
            tasks = [collector.collect(client) for collector in self.collectors]
            results = await asyncio.gather(*tasks)

            all_posts = []
            for res in results:
                all_posts.extend(res)

        # 2. Save
        new_count = self._save_data(all_posts)

        # 3. Normalize (Delegated to each platform)
        print(f">>> Triggering decentralized normalization...")
        for collector in self.collectors:
            collector.recalculate_platform_stats()

        print(f">>> Cycle Complete. {new_count} new items.")

    def _save_data(self, posts):
        """Internal method to save posts to DB"""
        if not posts: return 0
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        count = 0
        for post in posts:
            try:
                keywords_str = ",".join(post.get('keywords', []))

                # שינוי: הוספנו את sentiment לשאילתה
                cursor.execute('''
                    INSERT OR IGNORE INTO unified_posts 
                    (source_platform, external_id, title, content, author, published_at, raw_score, trend_score, sentiment, url, found_keywords)
                    VALUES (?, ?, ?, ?, ?, ?, ?, 0, ?, ?, ?)
                ''', (post['source_platform'], post['external_id'], post['title'], post['content'],
                      post['author'], post['published_at'], post['raw_score'], post.get('sentiment', 0), post['url'],
                      keywords_str))

                if cursor.rowcount == 0:
                    # שינוי: מעדכנים גם סנטימנט אם הפוסט קיים
                    cursor.execute('''
                        UPDATE unified_posts SET raw_score=?, found_keywords=?, sentiment=?
                        WHERE source_platform=? AND external_id=?
                     ''', (post['raw_score'], keywords_str, post.get('sentiment', 0), post['source_platform'],
                           post['external_id']))

                if cursor.rowcount > 0: count += 1
            except Exception as e:
                print(f"[DB Error] {e}")
        conn.commit()
        conn.close()
        return count