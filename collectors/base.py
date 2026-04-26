from abc import ABC, abstractmethod
import sqlite3
import math
import os
import re
import html  # Added for unescaping HTML entitiesֿ
import numpy as np
from textblob import TextBlob
from langdetect import detect, detect_langs, LangDetectException
from config import AI_FILTER_KEYWORDS
from keybert import KeyBERT

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "trends_project.db")

print("🧠 Loading NLP Model (KeyBERT) for dynamic entity extraction...")
kw_model = KeyBERT(model='all-MiniLM-L6-v2')


class BaseCollector(ABC):
    def __init__(self, platform_name):
        self.platform_name = platform_name
        self.stats_config = {
            'min_stdev': 1.0,
            'damping_factor': 1.0,
            'sigmoid_shift': 0.5,
            'log_base': 10
        }

    @staticmethod
    def clean_text(text):
        """Sanitizes text and converts HTML entities back to plain text."""
        if not text: return ""
        # 1. Convert entities like &amp; to &
        clean = html.unescape(text)
        # 2. Remove HTML tags
        clean = re.sub(r'<[^>]+>', ' ', clean)
        # 3. Remove URLs
        clean = re.sub(r'http[s]?://\S+', '', clean)
        clean = re.sub(r'www\.\S+', '', clean)
        # 4. Normalize spaces
        clean = re.sub(r'\s+', ' ', clean)
        return clean.strip()

    @staticmethod
    def is_ai_relevant(text):
        if not text: return False
        return any(keyword in text.lower() for keyword in AI_FILTER_KEYWORDS)

    @staticmethod
    def extract_keywords(text):
        if not text: return []
        try:
            extracted = kw_model.extract_keywords(text, keyphrase_ngram_range=(1, 2), stop_words='english', top_n=5)
            return [phrase.lower() for phrase, score in extracted if score > 0.35]
        except Exception as e:
            print(f"Extraction error: {e}")
            return []

    @staticmethod
    def analyze_sentiment(text):
        if not text or not isinstance(text, str): return 0.0
        try:
            return TextBlob(text).sentiment.polarity
        except:
            return 0.0

    def is_quality_content(self, post):
        """Final gatekeeper with language and relevance check."""
        post['title'] = self.clean_text(post.get('title', ''))
        post['content'] = self.clean_text(post.get('content', ''))
        full_text = f"{post['title']} {post['content']}"

        if not self.is_ai_relevant(full_text): return False

        # Enhanced language detection
        text_to_check = full_text[:500]
        if len(text_to_check) > 25:
            try:
                langs = detect_langs(text_to_check)
                if langs[0].lang != 'en' or langs[0].prob < 0.85: return False
            except LangDetectException:
                return False

        post['keywords'] = self.extract_keywords(full_text)
        return bool(post.get('keywords'))

    def recalculate_platform_stats(self):
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT id, raw_score FROM unified_posts WHERE source_platform = ?', (self.platform_name,))
            rows = cursor.fetchall()
            if not rows: return
            processed_scores = [math.log10(r[1] + 1) if r[1] > 0 else 0 for r in rows]
            mean, std_dev = np.mean(processed_scores), np.std(processed_scores) or 1.0
            damp, shift = self.stats_config.get('damping_factor', 1.0), self.stats_config.get('sigmoid_shift', 0.5)
            for row, scaled_score in zip(rows, processed_scores):
                z_score = ((scaled_score - mean) / (std_dev * damp)) + shift
                trend_score = (1 / (1 + math.exp(-z_score))) * 100
                cursor.execute('UPDATE unified_posts SET trend_score = ? WHERE id = ?', (trend_score, row[0]))
            conn.commit()

    @abstractmethod
    async def collect(self, client):
        pass