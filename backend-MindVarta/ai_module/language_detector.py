"""
language_detector.py

LLM-based language detector for Saathi.

Handles:
  - Bengali / Hindi written in English (Roman) letters
  - Mixed scripts (Hinglish, Benglish)
  - Unicode Bengali / Hindi
  - Plain English

Returns: "english" | "hindi" | "bengali"
"""

import re
from openai import OpenAI
from ai_module.config import GROQ_API_KEY, BASE_URL

_client = None

# Common English words — if the message is mostly these, it's English.
# Keeps a broad list so short messages like "you remember i cut my hand?" are caught.
_ENGLISH_STOPWORDS = {
    "i", "you", "he", "she", "we", "they", "it", "me", "him", "her", "us", "them",
    "my", "your", "his", "its", "our", "their", "this", "that", "these", "those",
    "am", "is", "are", "was", "were", "be", "been", "being", "have", "has", "had",
    "do", "does", "did", "will", "would", "could", "should", "may", "might", "must",
    "can", "shall", "not", "and", "or", "but", "if", "in", "on", "at", "to", "for",
    "of", "with", "by", "from", "up", "about", "into", "than", "then", "so", "yet",
    "a", "an", "the", "no", "nor", "as", "just", "very", "too", "also",
    # Common verbs / nouns that appear in emotional English messages
    "remember", "know", "think", "feel", "said", "say", "go", "going", "come",
    "want", "need", "like", "love", "hate", "help", "talk", "tell", "ask",
    "what", "when", "where", "who", "how", "why", "which", "there", "here",
    "cut", "hand", "head", "heart", "mind", "time", "day", "night", "life",
    "good", "bad", "okay", "fine", "right", "wrong", "really", "still", "again",
    "get", "got", "let", "look", "back", "now", "even", "never", "always",
    "please", "sorry", "thank", "yes", "no", "yeah", "ok", "oh", "well",
}


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(api_key=GROQ_API_KEY, base_url=BASE_URL)
    return _client


_DETECTION_PROMPT = """
You are a language classifier. Your job is to decide whether a message is written in English, Hindi (Romanised or Devanagari), or Bengali (Romanised or Bengali script).

CRITICAL RULE — English first:
If the message uses standard English words and grammar — even if the topic is emotional or personal — return "english".
Do NOT classify a message as Bengali or Hindi just because it contains common words like "cut", "hand", "remember", "feel", etc.

Bengali signals (Romanised): ami, amar, tumi, tomake, achi, achhi, ki, keno, bhalo, kharap, mon, chacchi, jabo, hobe, lagche, bolo, bol, thakbo, nei, ebar, ektu, shob, kichhu, jani, janina
Hindi signals (Romanised): main, mujhe, hoon, hai, tha, yaar, kya, nahi, thik, bahut, acha, bol, kar, raha, gaya, laga, chahiye, karo, bata, pata

If the message contains NONE of these signals and reads like normal English → return "english".

Return ONLY one word, nothing else:
english
hindi
bengali
"""


def _is_plain_english(text: str) -> bool:
    """
    Returns True if the text is almost certainly plain English.
    Checks two things:
      1. All characters are ASCII (no Devanagari / Bengali Unicode)
      2. Most tokens are known English words
    This avoids an unnecessary LLM call and prevents misclassification
    of short English phrases (e.g. "you remember i cut my hand?").
    """
    # Must be pure ASCII (no foreign script characters)
    try:
        text.encode("ascii")
    except UnicodeEncodeError:
        return False  # Contains non-ASCII → needs LLM or Unicode path

    # Tokenise: lowercase alphabetic words only
    words = re.findall(r"[a-z]+", text.lower())
    if not words:
        return True  # Empty / punctuation-only → treat as English

    # If ≥60 % of words are in the English stopword list, it's English.
    # 60 % is intentionally permissive — short sentences have low overlap.
    english_count = sum(1 for w in words if w in _ENGLISH_STOPWORDS)
    ratio = english_count / len(words)

    # Also flag known Romanised Bengali/Hindi markers — if ANY appear, skip fast path
    romani_markers = {
        # Bengali
        "ami", "amar", "tumi", "tomake", "achi", "achhi", "ki", "keno",
        "bhalo", "kharap", "mon", "chacchi", "jabo", "hobe", "lagche",
        "bolo", "bol", "thakbo", "nei", "ebar", "ektu", "shob", "kichhu",
        "janina",
        # Hindi
        "mujhe", "hoon", "yaar", "nahi", "thik", "bahut", "acha",
        "raha", "gaya", "laga", "chahiye", "karo", "bata", "pata",
    }
    for w in words:
        if w in romani_markers:
            return False  # Definitely not plain English

    return ratio >= 0.60


def detect_language(text: str) -> str:
    """
    Detects the primary language of a user message.

    Strategy:
      1. Empty input           → "english"
      2. Unicode fast path     → clear Devanagari / Bengali script → no LLM call
      3. ASCII English fast path → plain English words → no LLM call   ← NEW
      4. LLM classification    → Romanised Hindi / Bengali / ambiguous
      5. Any API failure       → falls back to "english"

    Args:
        text: Raw user message

    Returns:
        "english" | "hindi" | "bengali"
    """

    if not text or not text.strip():
        return "english"

    # ── 1. Unicode fast path ─────────────────────────────────────────────────
    devanagari = sum(1 for ch in text if "\u0900" <= ch <= "\u097F")
    bengali_uc  = sum(1 for ch in text if "\u0980" <= ch <= "\u09FF")
    total       = len(text.replace(" ", "")) or 1

    if devanagari / total >= 0.20:
        print(f"[LangDetect] Unicode → hindi   | '{text[:60]}'")
        return "hindi"

    if bengali_uc / total >= 0.20:
        print(f"[LangDetect] Unicode → bengali | '{text[:60]}'")
        return "bengali"

    # ── 2. ASCII English fast path ───────────────────────────────────────────
    # If the message is pure ASCII and mostly common English words,
    # return "english" immediately — no LLM call, no misclassification.
    if _is_plain_english(text):
        print(f"[LangDetect] ASCII   → english | '{text[:60]}'")
        return "english"

    # ── 3. LLM path — Romanised Hindi / Bengali ──────────────────────────────
    try:
        client = _get_client()

        completion = client.chat.completions.create(
            model="openai/gpt-oss-120b",
            temperature=0,
            max_tokens=5,
            messages=[
                {"role": "system", "content": _DETECTION_PROMPT},
                {"role": "user",   "content": text},
            ]
        )

        result = (
            completion.choices[0]
            .message.content
            .strip()
            .lower()
        )

        if result not in ("english", "hindi", "bengali"):
            print(f"[LangDetect] Unexpected LLM output '{result}' → defaulting to english")
            return "english"

        print(f"[LangDetect] LLM     → {result} | '{text[:60]}'")
        return result

    except Exception as e:
        print(f"[LangDetect] LLM call failed: {e} → defaulting to english")
        return "english"