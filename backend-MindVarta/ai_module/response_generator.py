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
    Fix spacing issues in AI-generated text.
    Handles:
    1. Words with spaces in the middle: "Im do ing" → "I'm doing"
    2. Missing spaces between words: "companionand" → "companion and"
    3. Extra spaces in contractions: "I m" → "I'm", "yo u" → "you"
    """
    if not text:
        return text
    
    # Fix broken contractions and common words first
    # Common contractions that get split
    contractions = {
        r'\bI m\b': "I'm",
        r'\byo u\b': "you",
        r'\byo ur\b': "your",
        r'\bthe y\b': "they",
        r'\bwe re\b': "we're",
        r'\bhe s\b': "he's",
        r'\bshe s\b': "she's",
        r'\bit s\b': "it's",
        r'\btha t\b': "that",
        r'\bwha t\b': "what",
        r'\bcan t\b': "can't",
        r'\bdon t\b': "don't",
        r'\bwon t\b': "won't",
        r'\bId\b': "I'd",
        r'\bIll\b': "I'll",
        r'\bIve\b': "I've",
        r'\byou re\b': "you're",
        r'\byou ve\b': "you've",
        r'\byou ll\b': "you'll",
        r'\byou d\b': "you'd",
        r'\btha nk\b': "thank",
        r'\bth ink\b': "think",
        r'\bth is\b': "this",
        r'\bth at\b': "that",
        r'\bth ere\b': "there",
        r'\bth ey\b': "they",
        r'\bth eir\b': "their",
        r'\bwi th\b': "with",
        r'\babo ut\b': "about",
        r'\bsometh ing\b': "something",
        r'\banyo ne\b': "anyone",
        r'\banywh ere\b': "anywhere",
        r'\banyth ing\b': "anything",
        r'\beveryo ne\b': "everyone",
        r'\bsomeo ne\b': "someone",
        r'\brel ated\b': "related",
        r'\bsh are\b': "share",
        r'\bfe el\b': "feel",
        r'\bfe eling\b': "feeling",
        r'\bfeel ings\b': "feelings",
        r'\bdo ing\b': "doing",
        r'\bask ing\b': "asking",
        r'\blist en\b': "listen",
        r'\bsupp ort\b': "support",
        r'\bquest ions\b': "questions",
        r'\btop ics\b': "topics",
        r'\bdisc uss\b': "discuss",
        r'\bment al\b': "mental",
        r'\bhe alth\b': "health",
        r'\bcompani on\b': "companion",
        r'\bdesign ed\b': "designed",
        r'\bprov ide\b': "provide",
        r'\bjudg ment\b': "judgment",
        r'\bsp ace\b': "space",
        r'\btho ughts\b': "thoughts",
        r'\bspecif ic\b': "specific",
        r'\bissu es\b': "issues",
        r'\bconc erns\b': "concerns",
        r'\bPerh aps\b': "Perhaps",
        r'\brelat ionships\b': "relationships",
        r'\bsimpl y\b': "simply",
        r'\bwe ll\b': "well",
        r'\bbe ing\b': "being",
        r'\bwellth ank\b': "well thank",
        r'\btalk abo\b': "talk abo",
        r'\bNam aste\b': "Namaste",
    }
    
    for pattern, replacement in contractions.items():
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
    
    # Fix words that are incorrectly joined (no space)
    # Pattern: lowercase letter followed immediately by uppercase letter
    text = re.sub(r'([a-z])([A-Z])', r'\1 \2', text)
    
    # Fix common word endings directly followed by common starting words
    # e.g., "companionand" → "companion and", "friendbut" → "friend but"
    common_words = r'(and|but|the|is|are|was|were|in|to|of|or|for|with|by|from|as|be|an|at|if|that|this|it|Im|Id|Ill)'
    text = re.sub(rf'([a-z])({common_words})\b', r'\1 \2', text, flags=re.IGNORECASE)
    
    # Fix "Im" specifically (very common)
    text = re.sub(r'\bIm\b', "I'm", text)
    text = re.sub(r'\bId\b', "I'd", text)
    text = re.sub(r'\bIll\b', "I'll", text)
    text = re.sub(r'\bIve\b', "I've", text)
    
    # Clean up any multiple spaces that might have been created
    text = re.sub(r'\s+', ' ', text)
    
    return text.strip()
    
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
