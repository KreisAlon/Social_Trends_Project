import sqlite3
import os

# --- Path Configuration ---
# We determine the database path relative to this file to ensure consistency
# regardless of where the script is run from.
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CURRENT_DIR)
DB_PATH = os.path.join(PROJECT_ROOT, "trends_project.db")


class TrendManager:
    """
    Database Abstraction Layer (DAL).
    Handles all SQLite operations: connection, table creation, insertion, and retrieval.
    """

    def __init__(self):
        self.db_path = DB_PATH
        self._init_db()

    def _init_db(self):
        """
        Initializes the database schema.
        Creates the 'unified_posts' table if it does not exist.
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Create the main table with a unique constraint on (source_platform, external_id)
        # to prevent duplicates.
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
                trend_score REAL DEFAULT 0.0,
                sentiment REAL DEFAULT 0.0,
                url TEXT,
                found_keywords TEXT,
                UNIQUE(source_platform, external_id)
            )
        ''')
        conn.commit()
        conn.close()
        print("[Manager] Database Ready.")

    def save_posts(self, posts):
        """
        Batch inserts or updates posts in the database.

        Args:
            posts (list): A list of dictionaries containing post data.
        """
        if not posts:
            return

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        for post in posts:
            # Convert keyword list to string for storage
            keywords_str = ",".join(post.get('keywords', []))

            # Use INSERT OR IGNORE to skip duplicates efficiently.
            # In a production environment, we might use UPSERT (ON CONFLICT UPDATE)
            # to update scores of existing posts.
            cursor.execute('''
                INSERT OR IGNORE INTO unified_posts 
                (source_platform, external_id, title, content, author, published_at, raw_score, sentiment, url, found_keywords)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                post['source_platform'],
                post['external_id'],
                post['title'],
                post['content'],
                post['author'],
                post['published_at'],
                post['raw_score'],
                post['sentiment'],
                post['url'],
                keywords_str
            ))

            # If the post exists, we update its raw_score and sentiment to keep it fresh
            cursor.execute('''
                UPDATE unified_posts 
                SET raw_score = ?, sentiment = ?
                WHERE source_platform = ? AND external_id = ?
            ''', (
                post['raw_score'],
                post['sentiment'],
                post['source_platform'],
                post['external_id']
            ))

        conn.commit()
        conn.close()
        # print(f"[Manager] Saved/Updated {len(posts)} items.")

    def get_top_trends(self, limit=15):
        """
        Retrieves the top trending posts sorted by the calculated Trend Score.

        Args:
            limit (int): Number of posts to return.

        Returns:
            list: List of sqlite3.Row objects (access columns by name).
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # Allows accessing columns by name (row['title'])
        cursor = conn.cursor()

        cursor.execute('''
            SELECT * FROM unified_posts 
            ORDER BY trend_score DESC 
            LIMIT ?
        ''', (limit,))

        rows = cursor.fetchall()
        conn.close()
        return rows