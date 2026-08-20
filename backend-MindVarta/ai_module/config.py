import os
from dotenv import load_dotenv

load_dotenv()

# Groq — free tier with fast inference
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
# Use openai/gpt-oss-120b (the model that works with reasoning_effort)
AI_MODEL = os.getenv("AI_MODEL", "openai/gpt-oss-120b")
BASE_URL = "https://api.groq.com/openai/v1"

# Temperature: 0.7 for more natural, conversational responses
TEMPERATURE = 0.7

# Aggressively reduced to ensure complete, properly-spaced responses
MAX_TOKENS = 250

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
