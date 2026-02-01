from abc import ABC, abstractmethod
import sqlite3
import math
import statistics
import os
from textblob import TextBlob
from langdetect import detect, LangDetectException
from config import KEYWORDS

# Set base path for database access
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "trends_project.db")


class BaseCollector(ABC):
    """
    Abstract Base Class for all data collectors.
    Implements core logic, filtering, and statistical normalization.
    """

    def __init__(self, platform_name):
        self.platform_name = platform_name

        # --- Statistical Configuration ---
        self.stats_config = {
            'min_stdev': 1.0,
            'damping_factor': 1.0,
            'sigmoid_shift': 0.5,
            'log_base': 10
        }

    @staticmethod
    def extract_keywords(text):
        """
        Scans the input text for keywords defined in `config.py`.
        """
        found = []
        if not text:
            return found
        text_lower = text.lower()
        for k in KEYWORDS:
            if k in text_lower:
                found.append(k)
        return list(set(found))

    @staticmethod
    def analyze_sentiment(text):
        """
        Analyzes the text polarity using NLP (TextBlob).
        Returns a float between -1.0 (Negative) and 1.0 (Positive).
        """
        if not text:
            return 0.0
        try:
            analysis = TextBlob(text)
            return analysis.sentiment.polarity
        except Exception:  # pylint: disable=broad-except
            # We catch generic exceptions here to ensure the data collection
            # cycle never crashes due to an NLP library error.
            return 0.0

    def is_quality_content(self, post):
        """
        Core Quality Filter: Keywords, Score, Spam, and Language.
        """
        # 1. Keyword Check
        if not post.get('keywords'):
            return False

        # 2. Basic Validity Check
        if post.get('raw_score', 0) < 0:
            return False

        # 3. Basic Spam Filter (Too many hashtags)
        if post.get('title', '').count('#') > 5:
            return False

        # 4. Language Validation (NLP)
        text_to_check = (post['title'] + " " + post.get('content', ''))[:500]

        if len(text_to_check) > 20:
            try:
                lang = detect(text_to_check)
                if lang != 'en':
                    return False
            except LangDetectException:
                pass

        return True

    def recalculate_platform_stats(self):
        """
        The Core Algorithm: Decentralized Statistical Normalization (Z-Score).
        """
        print(f"[{self.platform_name}] Running statistical normalization...")

        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("SELECT id, raw_score FROM unified_posts WHERE source_platform = ?", (self.platform_name,))
        rows = cursor.fetchall()

        if not rows:
            conn.close()
            return

        raw_scores = [r['raw_score'] for r in rows]

        # Step 1: Log Transformation
        log_scores = [math.log(s + 1, self.stats_config['log_base']) for s in raw_scores]

        # Step 2: Calculate Distribution
        if len(log_scores) > 1:
            mean = statistics.mean(log_scores)
            stdev = statistics.stdev(log_scores)
        else:
            mean, stdev = log_scores[0], 1.0

        if stdev < self.stats_config['min_stdev']:
            stdev = self.stats_config['min_stdev']

        print(f"   -> {self.platform_name} Stats: Mean={mean:.2f}, StdDev={stdev:.2f} "
              f"(Config: Damp={self.stats_config['damping_factor']})")

        # Step 3: Update Scores
        for i, row in enumerate(rows):
            z_score = (log_scores[i] - mean) / stdev
            damped_z = z_score / self.stats_config['damping_factor']
            norm_score = 100.0 / (1 + math.exp(-1.0 * (damped_z - self.stats_config['sigmoid_shift'])))
            final_score = max(0.0, min(99.9, norm_score))

            cursor.execute("UPDATE unified_posts SET trend_score = ? WHERE id = ?",
                           (round(final_score, 1), row['id']))

        conn.commit()
        conn.close()

    @abstractmethod
    async def collect(self, client):
        """Abstract method for data collection."""
        pass