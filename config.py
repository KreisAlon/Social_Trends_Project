# config.py

# רשימת מילות המפתח המורחבת - המערכת תחפש מילים אלו גם בכותרת וגם בתוכן
KEYWORDS = [
    # מושגי בסיס
    'genai', 'generative ai', 'artificial intelligence', 'machine learning',

    # מודלים פופולריים וחדשים
    'gpt', 'llm', 'transformer', 'diffusion', 'llama', 'mistral',
    'claude', 'gemini', 'copilot', 'stable diffusion',
    'deepseek', 'grok', 'dalle', 'midjourney',

    # חברות מרכזיות
    'openai', 'anthropic', 'huggingface', 'nvidia',

    # טכנולוגיות וכלים
    'rag', 'lora', 'fine-tuning', 'agents', 'langchain', 'vector db'
]

# כמה תווים לקרוא מתוך גוף הטקסט (כדי לא להעמיס על המערכת)
TEXT_PREVIEW_LENGTH = 1000