import sqlite3
import json
import numpy as np
from datetime import datetime
from sentence_transformers import SentenceTransformer


class DatabaseManager:
    def __init__(self, db_path="trends_project.db"):
        self.db_path = db_path

        # Initialize the NLP model for semantic embeddings
        # 'all-MiniLM-L6-v2' is a fast and accurate model for sentence similarity
        print("🧠 Loading NLP Model for semantic analysis...")
        self.nlp_model = SentenceTransformer('all-MiniLM-L6-v2')
        print("✅ NLP Model Loaded Successfully!")

        self._init_db()

    def _init_db(self):
        """Initializes the database schema with support for semantic embeddings."""
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
                    embedding TEXT, -- Stores the high-dimensional vector as a JSON string
                    UNIQUE(source_platform, external_id)
                )
            ''')
            conn.commit()

    def save_posts(self, posts):
        """Processes and saves posts with calculated semantic embeddings."""
        if not posts:
            return 0

        added_count = 0
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            collected_at = datetime.now().isoformat()

            for post in posts:
                try:
                    # Generate semantic embedding based on Title and Content combined
                    text_to_embed = f"{post.get('title', '')}. {post.get('content', '')}"

                    # Compute the vector (384 dimensions for this model)
                    embedding_vector = self.nlp_model.encode(text_to_embed)

                    # Convert numpy array to JSON string for SQLite storage
                    embedding_json = json.dumps(embedding_vector.tolist())

                    cursor.execute('''
                        INSERT OR IGNORE INTO unified_posts (
                            source_platform, external_id, title, content, 
                            author, url, raw_score, trend_score, 
                            published_at, collected_at, embedding
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
                        embedding_json
                    ))
                    if cursor.rowcount > 0:
                        added_count += 1
                except Exception as e:
                    print(f"Error saving post {post.get('external_id')}: {e}")

            conn.commit()
        return added_count

    def get_all_posts(self):
        """Retrieves all posts from the database."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM unified_posts ORDER BY trend_score DESC')
            return [dict(row) for row in cursor.fetchall()]