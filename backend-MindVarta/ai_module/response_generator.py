import json
import re

from openai import OpenAI

from ai_module.config import (
    GROQ_API_KEY,
    AI_MODEL,
    TEMPERATURE,
    MAX_TOKENS,
    BASE_URL
)

from ai_module.prompts.language_prompts import PromptManagerV3

prompt_manager = PromptManagerV3()

MAX_PROMPT_TOKENS = 2600
MAX_RESPONSE_TOKENS = 300
MAX_HISTORY_MESSAGES = 4
MAX_MEMORY_CHARS = 350


def estimate_text_tokens(text: str) -> int:
    """Rough token estimate used to keep Groq requests under the free-tier TPM cap."""
    text = text or ""
    words = len(re.findall(r"\w+|[^\w\s]", text))
    chars = len(text)
    return max(1, int(chars / 4 + words * 0.6))


def estimate_prompt_tokens(messages: list) -> int:
    return sum(estimate_text_tokens(msg.get("content", "")) for msg in messages)


def trim_prompt_for_budget(messages: list, max_tokens: int = MAX_PROMPT_TOKENS) -> list:
    """Trim the prompt to fit the Groq free-tier token budget without changing the user question."""
    trimmed = [dict(msg) for msg in messages]

    def over_budget(items):
        return estimate_prompt_tokens(items) > max_tokens

    # Drop memory/context system blocks first, since they are the easiest to cut.
    for idx, msg in enumerate(trimmed):
        if msg.get("role") == "system" and "What you already know about this person" in msg.get("content", ""):
            trimmed[idx]["content"] = ""
            break

    # Keep only the newest conversation turns.
    while over_budget(trimmed) and len(trimmed) > 4:
        for idx in range(1, len(trimmed) - 1):
            if trimmed[idx].get("role") in {"user", "assistant"}:
                del trimmed[idx]
                break
        else:
            break

    # Shrink long content aggressively.
    previous_tokens = estimate_prompt_tokens(trimmed)
    for _ in range(8):
        if not over_budget(trimmed):
            break
        previous_tokens = estimate_prompt_tokens(trimmed)
        for msg in trimmed:
            content = msg.get("content", "") or ""
            if len(content) > 120:
                msg["content"] = content[:120]
                break
        if estimate_prompt_tokens(trimmed) >= previous_tokens:
            break

    # As a last resort, strip all non-essential system text and keep only the user question.
    if over_budget(trimmed):
        trimmed = [msg for msg in trimmed if msg.get("role") == "user"]
        if not trimmed:
            trimmed = [{"role": "user", "content": "Please reply briefly."}]

    return trimmed


# ─────────────────────────────────────────────────────────────
# FIX MISSING SPACES
# ─────────────────────────────────────────────────────────────

def fix_missing_spaces(text: str) -> str:
    """
    Fix spacing issues in AI-generated text using multiple strategies.
    Handles:
    1. Words with spaces in the middle: "f or" → "for"
    2. Missing spaces between words: "wellthank" → "well thank"
    3. Broken contractions: "I m" → "I'm", "youre" → "you're"
    """
    if not text:
        return text
    
    # Step 1: Fix words that have incorrect spaces in the middle
    # Pattern: single letter + space + rest of word
    broken_words = {
        r'\bf or\b': 'for',
        r'\bt o\b': 'to',
        r'\ba t\b': 'at',
        r'\bi n\b': 'in',
        r'\bo f\b': 'of',
        r'\bo n\b': 'on',
        r'\bi s\b': 'is',
        r'\ba s\b': 'as',
        r'\bb y\b': 'by',
        r'\bI m\b': "I'm",
        r'\bI d\b': "I'd",
        r'\bI ll\b': "I'll",
        r'\bI ve\b': "I've",
        r'\bc an\b': 'can',
        r'\bc ant\b': "can't",
        r'\bd o\b': 'do',
        r'\bd ont\b': "don't",
        r'\bw ill\b': 'will',
        r'\bw ont\b': "won't",
        r'\bw ith\b': 'with',
        r'\bt hat\b': 'that',
        r'\bt his\b': 'this',
        r'\bt hey\b': 'they',
        r'\bt heir\b': 'their',
        r'\bt here\b': 'there',
        r'\bw hat\b': 'what',
        r'\bw hen\b': 'when',
        r'\bw here\b': 'where',
        r'\bw hy\b': 'why',
        r'\bh ow\b': 'how',
        r'\bh ave\b': 'have',
        r'\bh ad\b': 'had',
        r'\bs o\b': 'so',
        r'\bm y\b': 'my',
        r'\bm e\b': 'me',
        r'\by ou\b': 'you',
        r'\by our\b': 'your',
        r'\bh e\b': 'he',
        r'\bh er\b': 'her',
        r'\bh is\b': 'his',
        r'\bs he\b': 'she',
        r'\bi t\b': 'it',
        r'\bw e\b': 'we',
        r'\bo ur\b': 'our',
        r'\bsh are\b': 'share',
        r'\bsh aring\b': 'sharing',
        r'\bf eel\b': 'feel',
        r'\bf eeling\b': 'feeling',
        r'\bf eelings\b': 'feelings',
    }
    
    for pattern, replacement in broken_words.items():
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
    
    # Step 2: Fix contractions that are missing apostrophes
    contractions = {
        r'\bIm\b': "I'm",
        r'\bId\b': "I'd",
        r'\bIll\b': "I'll",
        r'\bIve\b': "I've",
        r'\byoure\b': "you're",
        r'\byoull\b': "you'll",
        r'\byouve\b': "you've",
        r'\byoud\b': "you'd",
        r'\btheyre\b': "they're",
        r'\btheyll\b': "they'll",
        r'\btheyve\b': "they've",
        r'\btheyd\b': "they'd",
        r'\bwere\b': "we're",
        r'\bwell\b': "we'll",
        r'\bweve\b': "we've",
        r'\bwed\b': "we'd",
        r'\bhes\b': "he's",
        r'\bhell\b': "he'll",
        r'\bhed\b': "he'd",
        r'\bshes\b': "she's",
        r'\bshe ll\b': "she'll",
        r'\bshed\b': "she'd",
        r'\bits\b': "it's",
        r'\bitll\b': "it'll",
        r'\bthats\b': "that's",
        r'\btheres\b': "there's",
        r'\bwhats\b': "what's",
        r'\bwheres\b': "where's",
        r'\bwhos\b': "who's",
        r'\bhows\b': "how's",
        r'\bwhos\b': "who's",
        r'\bcant\b': "can't",
        r'\bwont\b': "won't",
        r'\bdont\b': "don't",
        r'\bdoesnt\b': "doesn't",
        r'\bdidnt\b': "didn't",
        r'\bhasnt\b': "hasn't",
        r'\bhavent\b': "haven't",
        r'\bhadnt\b': "hadn't",
        r'\bisnt\b': "isn't",
        r'\barent\b': "aren't",
        r'\bwasnt\b': "wasn't",
        r'\bwerent\b': "weren't",
        r'\bcouldnt\b': "couldn't",
        r'\bwouldnt\b': "wouldn't",
        r'\bshouldnt\b': "shouldn't",
    }
    
    for pattern, replacement in contractions.items():
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
    
    # Step 3: Fix common word combinations that are missing spaces
    # Pattern: word ending + word beginning (e.g., "wellthank" → "well thank")
    common_joins = {
        r'\b(well)(thank)\b': r'\1 \2',
        r'\b(you)(so)\b': r'\1 \2',
        r'\b(you)(how)\b': r'\1 \2',
        r'\b(you)(what)\b': r'\1 \2',
        r'\b(you)(where)\b': r'\1 \2',
        r'\b(you)(when)\b': r'\1 \2',
        r'\b(and)(I)\b': r'\1 \2',
        r'\b(and)(you)\b': r'\1 \2',
        r'\b(and)(the)\b': r'\1 \2',
        r'\b(or)(you)\b': r'\1 \2',
        r'\b(or)(I)\b': r'\1 \2',
        r'\b(but)(I)\b': r'\1 \2',
        r'\b(but)(you)\b': r'\1 \2',
        r'\b(so)(I)\b': r'\1 \2',
        r'\b(so)(you)\b': r'\1 \2',
        r'\b(if)(you)\b': r'\1 \2',
        r'\b(if)(I)\b': r'\1 \2',
    }
    
    for pattern, replacement in common_joins.items():
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
    
    # Step 4: Generic pattern - lowercase letter followed immediately by another word
    # This catches patterns like "youso", "wellthank", etc.
    # Look for [word ending with lowercase][word starting with lowercase]
    text = re.sub(r'([a-z]{3,})([a-z]{2,})\b', lambda m: 
                  m.group(1) + ' ' + m.group(2) if is_likely_two_words(m.group(1), m.group(2)) else m.group(0), 
                  text)
    
    # Step 5: Fix "youhows" specifically (you + how's)
    text = re.sub(r'\byouhows\b', "you how's", text, flags=re.IGNORECASE)
    text = re.sub(r'\byouhow\b', 'you how', text, flags=re.IGNORECASE)
    
    # Step 6: Clean up multiple spaces
    text = re.sub(r'\s+', ' ', text)
    
    return text.strip()


def is_likely_two_words(word1: str, word2: str) -> bool:
    """
    Heuristic to determine if two concatenated strings are likely two separate words.
    Returns True if they should be split with a space.
    """
    # Common word endings that often get joined
    common_endings = ['well', 'you', 'and', 'but', 'or', 'so', 'if', 'the', 'my', 'your', 'his', 'her', 'their', 'our']
    # Common word beginnings that often get joined
    common_beginnings = ['thank', 'how', 'what', 'where', 'when', 'why', 'who', 'can', 'so', 'to', 'for', 'and', 'but', 'or']
    
    word1_lower = word1.lower()
    word2_lower = word2.lower()
    
    # Check if word1 is a common ending and word2 is a common beginning
    if word1_lower in common_endings or word2_lower in common_beginnings:
        return True
    
    # If both words are reasonably long (3+ chars each), likely separate words
    if len(word1) >= 3 and len(word2) >= 3:
        return True
    
    return False
    
    # Pattern 3: Fix doubled words accidentally joined (rare but possible)
    # e.g., "veryvery" shouldn't occur, but if it does, we won't fix it to avoid false positives
    
    # Clean up any multiple spaces that might have been created
    text = re.sub(r'\s+', ' ', text)
    
    return text.strip()


# ─────────────────────────────────────────────────────────────
# RESPONSE EXTRACTION
# ─────────────────────────────────────────────────────────────

def extract_response_and_summary(raw_text: str) -> tuple:
    """
    Extracts actual_response and summarize_context from model output.

    Handles:
      1. Valid JSON
      2. Markdown-wrapped JSON (```json ... ```)
      3. Partial / broken model outputs via regex fallback
      4. Multi-language responses (Bengali, Hindi, English, etc.)
      5. Text before/after JSON (cleans it up)
    """

    cleaned = raw_text.strip()

    # Strip markdown code fences if present
    if "```" in cleaned:
        parts = cleaned.split("```")
        if len(parts) > 1:
            cleaned = parts[1]
        cleaned = cleaned.replace("json", "", 1).strip()

    # Attempt clean JSON parse
    try:
        parsed = json.loads(cleaned)

        actual_response   = parsed.get("actual_response",   "").strip()
        summarize_context = parsed.get("summarize_context", "").strip()

        if actual_response:
            actual_response = fix_missing_spaces(actual_response)
            if not summarize_context:
                summarize_context = generate_fallback_summary(actual_response)
            return actual_response, summarize_context

    except Exception:
        pass

    # If JSON parse failed, try to extract JSON from within the text
    # Look for JSON object pattern
    json_match = re.search(r'\{[^{}]*"actual_response"[^{}]*\}', cleaned, re.DOTALL)
    if json_match:
        try:
            parsed = json.loads(json_match.group(0))
            actual_response = parsed.get("actual_response", "").strip()
            summarize_context = parsed.get("summarize_context", "").strip()
            if actual_response:
                actual_response = fix_missing_spaces(actual_response)
                if not summarize_context:
                    summarize_context = generate_fallback_summary(actual_response)
                return actual_response, summarize_context
        except Exception:
            pass

    # Regex fallback - handle both quoted and unquoted values
    # Try different regex patterns to extract actual_response
    patterns = [
        r'"actual_response"\s*:\s*"((?:\\.|[^"\\])*?)"\s*(?:,|\})',  # Standard with comma or closing brace
        r'"actual_response"\s*:\s*"((?:\\.|[^"\\])*?)"',              # Without comma/brace
    ]
    
    actual_response = None
    for pattern in patterns:
        actual_match = re.search(pattern, cleaned, re.DOTALL)
        if actual_match:
            actual_response = actual_match.group(1).strip()
            break
    
    # If still no match, look for the response between "actual_response": and "summarize_context" or }
    if not actual_response:
        match = re.search(
            r'"actual_response"\s*:\s*["\']([^"\']*)["\'][,\s}]',
            cleaned,
            re.DOTALL
        )
        if match:
            actual_response = match.group(1).strip()
    
    summary_match = re.search(
        r'"summarize_context"\s*:\s*"((?:\\.|[^"\\])*?)"',
        cleaned,
        re.DOTALL
    )

    if actual_response:
        # Unescape JSON-encoded characters
        actual_response = actual_response.replace('\\n', '\n')
        actual_response = actual_response.replace('\\\"', '"')
        actual_response = actual_response.replace('\\"', '"')
        actual_response = actual_response.replace('\\\\', '\\')
    else:
        # If regex extraction also fails, try to find content before any JSON-like structure
        # Remove anything that looks like JSON metadata from the response
        actual_response = re.sub(
            r'[{}\[\]"\':]|\s*,\s*|actual_response|summarize_context',
            '',
            cleaned
        ).strip()
        
        # If that resulted in empty or very short string, try a different approach
        if len(actual_response) < 10:
            # Look for the first substantial text block
            lines = cleaned.split('\n')
            for line in lines:
                line = line.strip()
                if line and not line.startswith('{') and not line.startswith('"') and len(line) > 5:
                    actual_response = line
                    break
            
            # If still empty, use whatever is left
            if not actual_response:
                actual_response = cleaned.strip()

    summarize_context = ""
    if summary_match:
        summarize_context = summary_match.group(1).strip()
        # Unescape as well
        summarize_context = summarize_context.replace('\\n', '\n')
        summarize_context = summarize_context.replace('\\\"', '"')
    
    if not summarize_context:
        summarize_context = generate_fallback_summary(actual_response)

    # Fix missing spaces in the response before returning
    actual_response = fix_missing_spaces(actual_response)
    return actual_response, summarize_context


# ─────────────────────────────────────────────────────────────
# FALLBACK SUMMARY
# ─────────────────────────────────────────────────────────────

def generate_fallback_summary(response_text: str) -> str:
    """
    Generates a basic memory summary when the model fails to provide one.
    """
    if not response_text:
        return ""

    sentences = re.split(r"(?<=[.!?])\s+", response_text.strip())
    if sentences:
        return sentences[0][:200]

    return response_text[:200]


def looks_incomplete(text: str) -> bool:
    """Heuristics for partially generated or cut-off replies, supporting multiple languages."""
    text = (text or "").strip()
    if not text:
        return False

    # JSON-style output that ends without a balanced object is usually incomplete.
    if '"actual_response"' in text and text.count('{') != text.count('}'):
        return True

    # Detect text that ends without proper sentence-ending markers.
    # Works across languages: English (. ! ?), Hindi/Bengali (।), Arabic (؟), Chinese (。)
    sentence_endings = r'[.!?।؟。\u0964\u0965]'
    natural_ending = re.search(sentence_endings + r'["\')\]]*\s*$', text)
    
    # If response is long but doesn't end with punctuation, likely cut off.
    if len(text) > 100 and not natural_ending:
        return True

    # If text ends with ellipsis but seems to continue further (common truncation)
    if text.endswith('...') and len(text) > 120:
        return True

    # Detect response that ends abruptly mid-phrase (no space before potential cut)
    if len(text) > 80 and re.search(r'[a-zA-Z0-9\u0980-\u09FF\u0900-\u097F]\s*$', text):
        # Word ending with no punctuation
        last_few_chars = text[-30:].split()
        if last_few_chars and len(last_few_chars[-1]) < 5:
            # Very short last word often means truncation
            return True

    return False


def continue_partial_response(client, messages: list, partial_text: str, max_tokens: int = 220) -> str:
    """Ask the model to continue a cut-off reply instead of starting over."""
    continuation_prompt = (
        "The previous response was cut off mid-sentence. "
        "Continue ONLY from where it stopped. "
        "Do NOT repeat the beginning or any earlier content. "
        "Use the same language as the original response. "
        "Complete the thought naturally."
    )
    try:
        # Use a simplified system prompt for continuation to save tokens
        continuation_messages = [
            {"role": "system", "content": "You are continuing an unfinished response. Add only the missing part."},
            {"role": "user", "content": f"{continuation_prompt}\n\nCut-off text:\n{partial_text[-800:]}"},
        ]
        continuation = client.chat.completions.create(
            model=AI_MODEL,
            messages=continuation_messages,
            temperature=0.7,
            max_tokens=max_tokens,
        )
        next_chunk = continuation.choices[0].message.content.strip()
        if next_chunk and next_chunk.lower() != "i cannot continue this.":
            return next_chunk
        return ""
    except Exception as exc:
        print(f"[WARN] Continuation fallback failed: {exc}")
        return ""


# ─────────────────────────────────────────────────────────────
# CRISIS LEVEL CLASSIFIER
# ─────────────────────────────────────────────────────────────

def classify_crisis_level(user_input: str, language: str = "english") -> str:
    """
    Multilingual pattern-based crisis level estimation.
    Supports: English, Hindi (Devanagari & Romanized), Bengali (Bengali script & Romanized)

    Returns: "high" | "medium" | "none"

    This is conversational guidance only — not a medical assessment.
    """

    text = user_input.lower()
    
    # ─── HIGH RISK PATTERNS ───────────────────────────────────────
    high_risk_patterns = [
        # English
        r"\bi will kill myself\b",
        r"\bi want to die\b",
        r"\bi('m| am) going to (commit suicide|end my life)\b",
        r"\bend my life\b",
        r"\bi don.t want to live\b",
        r"\bbleeding\b",
        r"\bi will die in \d+\b",
        r"\btook (pills|tablets|overdose)\b",
        r"\bjust cut\b",
        
        # Romanized Hindi
        r"\bkaat\s+liya\b",
        r"\bgoli\s+kha\s+li\b",
        r"\bdawa\s+kha\s+li\b",
        r"\babhi\s+kat\s+raha\b",
        r"\babhi\s+kat\s+rahi\b",
        
        # Romanized Bengali
        r"\bhate\s+katchi\b",
        r"\bblade\s+diye\s+kat\w*\b",
        r"\bekhon\s+(katchi|katchhi|blade)\b",
        
        # Hindi Devanagari (native script)
        r"मरना\s+चाहता",
        r"मरना\s+चाहती",
        r"खून\s+आ\s+रहा",
        r"काट\s+लिया",
        r"गोली\s+खा\s+ली",
        r"दवा\s+खा\s+ली",
        r"अभी\s+काट\s+रहा",
        r"अभी\s+काट\s+रही",
        r"अभी\s+(ख़ून|खून|कट|काट)",
        
        # Bengali script (native)
        r"হাতে\s+কাটছি",
        r"রক্ত\s+পড়ছে",
        r"এখন\s+কাটছি",
        r"ব্লেড\s+দিয়ে",
        r"মরে\s+যেতে\s+চাই",
    ]
    
    # ─── MEDIUM RISK PATTERNS ──────────────────────────────────────
    medium_risk_patterns = [
        # English
        r"\bsuicid\w*\b",
        r"\bself.?harm\b",
        r"\bhurt myself\b",
        r"\bcut myself\b",
        r"\bnothing matters\b",
        r"\bbetter off without me\b",
        r"\bi don.t want to be here\b",
        
        # Romanized Hindi
        r"\bmar\s+ja(na|oon|au)\b",
        r"\bmar\s+jaana\s+chah\w*\b",
        r"\bjeena\s+nahi\s+chah\w*\b",
        r"\bkhatam\s+kar\s+l\w*\b",
        r"\bjaan\s+de\s+d\w*\b",
        r"\bkud\s+ko\s+(hurt|nuksaan)\b",
        r"\bnahi\s+rehna\s+chahta\b",
        r"\bnahi\s+rehna\s+chahti\b",
        
        # Romanized Bengali
        r"\bmare\s+ja(bo|te\s+chai|chi)\b",
        r"\bnijeke\s+khatam\b",
        r"\bbachte\s+chai\s+na\b",
        r"\bjibon\s+shesh\b",
        r"\bnijer\s+khoti\b",
        r"\bbachte\s+ichhe\s+(nei|nai|na)\b",
        
        # Hindi Devanagari
        r"जीना\s+नहीं\s+चाहता",
        r"जीना\s+नहीं\s+चाहती",
        r"खुद\s+को\s+नुकसान",
        r"जिंदगी\s+खत्म",
        r"नहीं\s+रहना\s+चाहता",
        r"नहीं\s+रहना\s+चाहती",
        r"सब\s+खत्म\s+कर",
        
        # Bengali script
        r"আর\s+বাঁচতে\s+চাই\s+না",
        r"জীবন\s+শেষ\s+করতে\s+চাই",
        r"নিজেকে\s+মেরে",
        r"বাঁচতে\s+ইচ্ছে\s+করছে\s+না",
        r"জীবনের\s+মানে\s+নেই",
        r"আর\s+থাকতে\s+চাই\s+না",
        r"মরে\s+যাই",
    ]
    
    # Check high risk patterns first
    for pattern in high_risk_patterns:
        if re.search(pattern, text):
            return "high"
    
    # Then medium risk
    for pattern in medium_risk_patterns:
        if re.search(pattern, text):
            return "medium"

    return "none"


# ─────────────────────────────────────────────────────────────
# MAIN RESPONSE GENERATOR
# ─────────────────────────────────────────────────────────────

def generate_response(
    user_input: str,
    conversation_history: list,
    language: str = "english",
    memory_summary: str = ""
) -> dict:
    """
    Main response generation function.

    Returns:
        {
            "actual_response": str,
            "summarize_context": str
        }
    """

    if not GROQ_API_KEY:
        raise ValueError(
            "GROQ_API_KEY is not set. "
            "Please configure it in .env"
        )

    # ── Crisis detection ──────────────────────────────────────
    possible_crisis = prompt_manager.detect_possible_crisis(user_input)
    crisis_level    = classify_crisis_level(user_input, language)

    if possible_crisis:
        print(
            f"[CRISIS] Level={crisis_level} | "
            f"Active={prompt_manager.detect_active_harm(user_input)} | "
            f"Input={user_input[:80]!r}"
        )

    # ── Build messages ────────────────────────────────────────
    client = OpenAI(api_key=GROQ_API_KEY, base_url=BASE_URL)

    safe_history = conversation_history[-MAX_HISTORY_MESSAGES:] if len(conversation_history) > MAX_HISTORY_MESSAGES else conversation_history
    safe_memory = (memory_summary or "")[:MAX_MEMORY_CHARS].strip()

    messages = prompt_manager.build_prompt(
        user_input=user_input,
        conversation_history=safe_history,
        language=language,
        memory_summary=safe_memory,
        possible_crisis=possible_crisis,
    )
    messages = trim_prompt_for_budget(messages)

    estimated_prompt_tokens = estimate_prompt_tokens(messages)
    if estimated_prompt_tokens > MAX_PROMPT_TOKENS:
        print(f"[WARN] Prompt still oversized after trimming: {estimated_prompt_tokens} tokens")

    # ── Extra high-crisis reinforcement ───────────────────────
    # build_prompt already injects the main crisis guidance.
    # This adds a second reinforcement layer for confirmed high-risk messages.
    if crisis_level == "high":
        messages.append({
            "role": "system",
            "content": (
                "This person may be in immediate danger. "
                "Your absolute priority is keeping them talking and feeling less alone. "
                "Do NOT say 'I cannot continue'. Do NOT go silent. "
                "Stay present. Stay human. Stay warm."
            )
        })

    # ── LLM call ─────────────────────────────────────────────
    completion = client.chat.completions.create(
        model=AI_MODEL,
        messages=messages,
        temperature=TEMPERATURE,
        max_tokens=min(MAX_TOKENS, MAX_RESPONSE_TOKENS)
    )

    raw_output = completion.choices[0].message.content.strip()

    # If the reply looks cut off, ask the model to continue from the last sentence.
    if looks_incomplete(raw_output):
        print(f"[CONTINUATION] Response looks incomplete ({len(raw_output)} chars). Asking model to continue...")
        continuation = continue_partial_response(client, messages, raw_output)
        if continuation:
            print(f"[CONTINUATION] Got {len(continuation)} chars of continuation. Stitching together...")
            raw_output = f"{raw_output} {continuation}".strip()
        else:
            print(f"[CONTINUATION] No continuation returned, using partial response.")
    else:
        print(f"[RESPONSE] Complete response ({len(raw_output)} chars) received.")

    # ── Extract response ──────────────────────────────────────
    actual_response, summarize_context = extract_response_and_summary(raw_output)

    # ── Emergency fallback ────────────────────────────────────
    if not actual_response:
        print(f"[WARN] Extraction failed. Raw output: {raw_output[:200]!r}")
        actual_response   = "I'm still here with you. Can you say that again?"
        summarize_context = "Response extraction fallback triggered"

    return {
        "actual_response":   actual_response,
        "summarize_context": summarize_context,
        "crisis_detected": possible_crisis,
        "crisis_level": crisis_level,
    }
