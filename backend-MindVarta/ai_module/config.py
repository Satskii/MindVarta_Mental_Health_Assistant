import os
from dotenv import load_dotenv

load_dotenv()

# Groq — free tier with fast inference
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
AI_MODEL = "llama-3.1-8b-instant"
BASE_URL = "https://api.groq.com/openai/v1"

# Temperature: 0.7 for more consistent and reliable outputs
TEMPERATURE = 0.7

MAX_TOKENS = 512

# Free chat limit per session
FREE_CHAT_LIMIT = 10

# Shared language map used across ai_module, stt_module, and tts_module
LANGUAGE_MAP = {
    "english": "en",
    "hindi":   "hi",
    "bengali": "bn",
    "en":      "en",
    "hi":      "hi",
    "bn":      "bn",
}
