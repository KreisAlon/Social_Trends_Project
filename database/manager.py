import sqlite3
import json
import numpy as np
import os
import logging
import warnings
from datetime import datetime

# =================================================================
# THE NUCLEAR OPTION: Ultimate Silence Block
# This MUST be defined before importing SentenceTransformer to work
# =================================================================
# 1. Disable HuggingFace Hub progress bars completely
os.environ["HF_HUB_DISABLE_PROGRESS_BARS"] = "1"

# 2. Force HuggingFace Hub and Transformers to only show critical errors
os.environ["HF_HUB_VERBOSITY"] = "error"
os.environ["TRANSFORMERS_VERBOSITY"] = "error"

# 3. Suppress specific UserWarnings from huggingface_hub regarding authentication
warnings.filterwarnings("ignore", category=UserWarning, module="huggingface_hub.*")

# 4. Disable parallelism warnings from tokenizers during encoding
os.environ["TOKENIZERS_PARALLELISM"] = "false"
# =================================================================

from sentence_transformers import SentenceTransformer


class TrendManager:
    """
    Manages the SQLite database and semantic vector generation for trends.
    Includes data health monitoring and noise suppression for AI models.
    """

    def __init__(self, db_path="trends_project.db"):
        self.db_path = db_path

        # Initialize the Sentence-Transformer model
        # This model transforms text into 384-dimensional semantic vectors.
        print("🧠 Loading NLP Model for semantic analysis...")
        self.nlp_model = SentenceTransformer('all-MiniLM-L6-v2')
        print("✅ NLP Model Loaded Successfully!")

        self._init_db()

    def _init_db(self):
        """Initializes the schema with support for scores and semantic embeddings."""
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
                    embedding TEXT, -- High-dimensional vector stored as JSON
                    UNIQUE(source_platform, external_id)
                )
            ''')
            conn.commit()

    def save_posts(self, posts):
        """Processes a list of posts, generates embeddings, and saves them to the DB."""
        if not posts:
            return 0

        added_count = 0
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            collected_at = datetime.now().isoformat()

            for post in posts:
                try:
                    # Create a rich text representation for embedding
                    text_to_embed = f"{post.get('title', '')}. {post.get('content', '')}"

                    # Generate semantic vector
                    embedding_vector = self.nlp_model.encode(text_to_embed)

                    # Convert the vector to a JSON string for storage
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
        """Retrieves all posts sorted by their calculated trend intensity."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM unified_posts ORDER BY trend_score DESC')
            return [dict(row) for row in cursor.fetchall()]

    def get_db_stats(self):
        """
        Queries the database to provide a quick summary of ingested posts per platform.
        Used for debugging and monitoring data health.
        """
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