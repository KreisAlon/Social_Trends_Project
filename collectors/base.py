from abc import ABC, abstractmethod
import sqlite3
import math
import statistics
import os
from textblob import TextBlob
from langdetect import detect, LangDetectException
from config import KEYWORDS

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "trends_project.db")


class BaseCollector(ABC):
    """
    Abstract Base Class for all data collectors.
    Implements core logic, filtering, and statistical normalization.
    """

    def __init__(self, platform_name):
        self.platform_name = platform_name
        self.stats_config = {
            'min_stdev': 1.0,
            'damping_factor': 1.0,
            'sigmoid_shift': 0.5,
            'log_base': 10
        }

    @staticmethod
    def extract_keywords(text):
        found = []
        if not text: return found
        text_lower = text.lower()
        for k in KEYWORDS:
            if k in text_lower:
                found.append(k)
        return list(set(found))

    @staticmethod
    def analyze_sentiment(text):
        if not text: return 0.0
        try:
            analysis = TextBlob(text)
            return analysis.sentiment.polarity
        except Exception:
            return 0.0

    def is_quality_content(self, post):
        """
        STRICT Quality Filter.
        """
        # 1. Reject empty keyword posts
        if not post.get('keywords'):
            return False

        # 2. Reject negative scores
        if post.get('raw_score', 0) < 0:
            return False

        # 3. Reject Spam (Too many hashtags)
        if post.get('title', '').count('#') > 5:
            return False

        # 4. STRICT Language Validation
        # If we are not 100% sure it is English, we drop it.
        text_to_check = (post['title'] + " " + post.get('content', ''))[:500]

        if len(text_to_check) > 20:
            try:
                lang = detect(text_to_check)
                if lang != 'en':
                    return False
            except LangDetectException:
                # STRICT MODE: If detection fails, assume it's garbage/foreign and drop it.
                return False

        return True

    def recalculate_platform_stats(self):
        """
        Recalculates the statistical mean and standard deviation for the platform.
        Applies Logarithmic (Log10) scaling to platforms with extreme outliers (e.g., GitHub)
        to prevent them from dominating the global trend ranking.
        """
        import math
        import sqlite3
        import numpy as np

        with sqlite3.connect("trends_project.db") as conn:
            cursor = conn.cursor()

            # Step 1: Fetch all raw scores for this specific platform
            cursor.execute('SELECT id, raw_score FROM unified_posts WHERE source_platform = ?', (self.platform_name,))
            rows = cursor.fetchall()

            if not rows:
                return

            # Step 2: Apply Log10 scaling ONLY for GitHub to compress astronomical star counts
            # (e.g., 100,000 stars becomes ~5.0, making it comparable to other platforms)
            processed_scores = []
            for row in rows:
                score = row[1]
                if self.platform_name == "GitHub":
                    score = math.log10(score + 1) if score > 0 else 0
                processed_scores.append(score)

            # Step 3: Calculate Statistical Mean and Standard Deviation
            mean = np.mean(processed_scores)
            std_dev = np.std(processed_scores)

            # Avoid division by zero if all scores are identical
            if std_dev == 0:
                std_dev = 1.0

            print(f"   -> {self.platform_name} Stats: Mean={mean:.2f}, StdDev={std_dev:.2f}")

            # Step 4: Calculate Z-Score and apply Sigmoid function for the final Trend Score (0-100)
            damp = self.stats_config.get('damping_factor', 1.0)

            for row, scaled_score in zip(rows, processed_scores):
                post_id = row[0]

                # Z-Score measures how many standard deviations the score is from the mean
                z_score = (scaled_score - mean) / (std_dev * damp)

                # Sigmoid function normalizes the score to a beautiful 0 to 100 scale
                trend_score = (1 / (1 + math.exp(-z_score))) * 100

                # Step 5: Update the database with the normalized score
                cursor.execute('UPDATE unified_posts SET trend_score = ? WHERE id = ?', (trend_score, post_id))

            conn.commit()
            conn.close()

    @abstractmethod
    async def collect(self, client):
        pass