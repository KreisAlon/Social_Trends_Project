import sqlite3
import json
import os
from datetime import datetime

class TrendManager:
    """
    Manages the SQLite database for trends.
    Uses dynamic entities (keywords) for semantic linking instead of heavy embeddings.
    """

    def __init__(self, db_path="trends_project.db"):
        self.db_path = db_path
        print("⚡ Initializing Lightweight Database Manager...")
        self._init_db()

    def _init_db(self):
        """Initializes the schema with support for dynamic keywords (entities)."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS unified_posts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source_platform TEXT,
                    external_id TEXT,
                    title TEXT,
                    content TEXT,
                    author TEXT,
                    url TEXT,
                    raw_score REAL,
                    trend_score REAL,
                    published_at TEXT,
                    collected_at TEXT,
                    keywords TEXT,      -- Stores extracted dynamic entities as JSON
                    UNIQUE(source_platform, external_id)
                )
            ''')
            conn.commit()

    def save_posts(self, posts):
        """Processes a list of posts and saves them to the DB using only keywords."""
        if not posts:
            return 0

        added_count = 0
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            collected_at = datetime.now().isoformat()

            for post in posts:
                try:
                    # Convert the keywords (entities) list to a JSON string for storage
                    keywords_json = json.dumps(post.get('keywords', []))

                    cursor.execute('''
                        INSERT OR IGNORE INTO unified_posts (
                            source_platform, external_id, title, content, 
                            author, url, raw_score, trend_score, 
                            published_at, collected_at, keywords
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        post['source_platform'],
                        post['external_id'],
                        post['title'],
                        post['content'],
                        post['author'],
                        post['url'],
                        post['raw_score'],
                        post.get('trend_score', 0),
                        post['published_at'],
                        collected_at,
                        keywords_json
                    ))
                    if cursor.rowcount > 0:
                        added_count += 1
                except Exception as e:
                    print(f"Error saving post {post.get('external_id')}: {e}")

            conn.commit()
        return added_count

    def get_all_posts(self):
        """Retrieves all posts sorted by their calculated trend intensity."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM unified_posts ORDER BY trend_score DESC')
            return [dict(row) for row in cursor.fetchall()]

    def get_db_stats(self):
        """Queries the database to provide a quick summary."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT source_platform, COUNT(*), AVG(trend_score) 
                FROM unified_posts 
                GROUP BY source_platform
            ''')
            stats = cursor.fetchall()
            print("\n📊 --- Database Health Summary ---")
            if not stats:
                print("No data found in the database yet.")
            for platform, count, avg_score in stats:
                print(f"📍 {platform}: {count} posts | Avg Trend Score: {avg_score:.2f}")
            print("----------------------------------\n")