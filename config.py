# config.py

# --- Semantic Analysis Keywords ---
# These keywords help guide the initial discovery phase.
# The system will look for these terms in titles and descriptions across all platforms.
KEYWORDS = [
    # Core Concepts
    'genai', 'generative ai', 'artificial intelligence', 'machine learning',

    # Popular & Emerging Models
    'gpt', 'llm', 'transformer', 'diffusion', 'llama', 'mistral',
    'claude', 'gemini', 'copilot', 'stable diffusion',
    'deepseek', 'grok', 'dalle', 'midjourney',

    # Key Industry Players
    'openai', 'anthropic', 'huggingface', 'nvidia',

    # Technologies & Architecture
    'rag', 'lora', 'fine-tuning', 'agents', 'langchain', 'vector db'
]

# --- Content Processing Settings ---
# Determines the amount of text extracted for semantic analysis.
# Increasing this value provides more 'meat' for the Vector Embeddings model.
TEXT_PREVIEW_LENGTH = 1500

# --- Collector Configuration ---
# Global settings for data fetchers.
# 'per_page' defines how many items to request per platform.
# 'max_items' sets the upper limit for the total items processed per platform.
COLLECTORS_CONFIG = {
    'per_page': 50,    # Increased from 15 to 50 for a richer vector space
    'max_items': 100   # Sufficient volume for meaningful cluster analysis
}