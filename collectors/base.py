from abc import ABC, abstractmethod
import sqlite3
import math
import statistics
import os
from config import KEYWORDS
from textblob import TextBlob

# Set base path for database access
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "trends_project.db")


class BaseCollector(ABC):
    """
    Abstract Base Class.
    Implements the core logic for collection, filtering, keyword extraction,
    and configurable statistical normalization.
    """

    def __init__(self, platform_name):
        self.platform_name = platform_name

        # --- Statistical Configuration ---
        # Default values. Children override these in __init__.
        self.stats_config = {
            'min_stdev': 1.0,  # Prevents infinite scores on low variance
            'damping_factor': 1.0,  # Divides the Z-Score (Higher = harder to rank up)
            'sigmoid_shift': 0.5,  # Shifts the center (Higher = needs more "exceptionalism")
            'log_base': 10  # Logarithm base
        }

    @staticmethod
    def extract_keywords(text):
        """Extracts keywords from text based on config.KEYWORDS."""
        found = []
        if not text: return found
        text_lower = text.lower()
        for k in KEYWORDS:
            if k in text_lower:
                found.append(k)
        return list(set(found))

    @abstractmethod
    async def collect(self, client):
        """Must be implemented by child classes."""
        pass

    def is_quality_content(self, post):
        """Base quality check."""
        if post.get('title', '').count('#') > 5:
            return False
        return True

    def analyze_sentiment(self, text):
        """
        Returns a sentiment score between -1.0 (Negative) and 1.0 (Positive).
        """
        if not text:
            return 0.0
        analysis = TextBlob(text)
        return analysis.sentiment.polarity

    def recalculate_platform_stats(self):
        """
        Runs the Log-Normal Z-Score algorithm specific to this platform's data.
        Uses self.stats_config to apply platform-specific tuning.
        """
        print(f"[{self.platform_name}] Running statistical normalization...")

        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # 1. Fetch raw scores for THIS platform only
        cursor.execute("SELECT id, raw_score FROM unified_posts WHERE source_platform = ?", (self.platform_name,))
        rows = cursor.fetchall()

        if not rows:
            conn.close()
            return

        raw_scores = [r['raw_score'] for r in rows]

        # 2. Log Transformation
        # Using log to handle the huge variance in social metrics (Power Law)
        log_scores = [math.log(s + 1, self.stats_config['log_base']) for s in raw_scores]

        # 3. Calculate Distribution
        if len(log_scores) > 1:
            mean = statistics.mean(log_scores)
            stdev = statistics.stdev(log_scores)
        else:
            mean, stdev = log_scores[0], 1.0

        # Enforce Minimum Standard Deviation
        if stdev < self.stats_config['min_stdev']:
            stdev = self.stats_config['min_stdev']

        print(f"   -> {self.platform_name} Stats: Mean={mean:.2f}, StdDev={stdev:.2f} "
              f"(Config: Damp={self.stats_config['damping_factor']})")

        # 4. Update Scores
        for i, row in enumerate(rows):
            # Z-Score Calculation
            z_score = (log_scores[i] - mean) / stdev

            # Apply Damping
            damped_z = z_score / self.stats_config['damping_factor']

            # Sigmoid Transformation (0 to 100)
            norm_score = 100.0 / (1 + math.exp(-1.0 * (damped_z - self.stats_config['sigmoid_shift'])))

            final_score = max(0.0, min(99.9, norm_score))

            cursor.execute("UPDATE unified_posts SET trend_score = ? WHERE id = ?",
                           (round(final_score, 1), row['id']))

        conn.commit()
        conn.close()