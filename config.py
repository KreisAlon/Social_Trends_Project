# config.py

# --- Noise Filtering Keywords (The Gatekeeper) ---
# Used strictly to verify if a post is generally related to the AI domain before ingestion.
AI_FILTER_KEYWORDS = [
    'ai', 'ml', 'machine learning', 'llm', 'gpt', 'neural', 'deep learning',
    'nlp', 'transformer', 'pytorch', 'tensorflow', 'openai', 'claude',
    'diffusion', 'agent', 'automation', 'data science', 'vector', 'deepseek'
]

# --- Content Processing Settings ---
# Determines the amount of text extracted for semantic analysis.
TEXT_PREVIEW_LENGTH = 1500

# --- Collector Configuration ---
COLLECTORS_CONFIG = {
    'per_page': 50,
    'max_items': 100
}

MAX_POSTS_PER_PLATFORM = 50