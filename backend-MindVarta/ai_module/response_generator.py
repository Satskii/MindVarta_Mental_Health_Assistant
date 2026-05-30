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


# ─────────────────────────────────────────────────────────────
# CRISIS LEVEL CLASSIFIER
# ─────────────────────────────────────────────────────────────

def classify_crisis_level(user_input: str) -> str:
    """
    Lightweight pattern-based crisis level estimation.

    Returns: "high" | "medium" | "none"

    This is conversational guidance only — not a medical assessment.
    """

    text = user_input.lower()

    high_risk = [
        r"\bi will kill myself\b",
        r"\bi want to die\b",
        r"\bi('m| am) going to (commit suicide|end my life)\b",
        r"\bend my life\b",
        r"\bi don.t want to live\b",
        r"\bhate katchi\b",
        r"\bblade diye kat\w*\b",
        r"\bbleeding\b",
        r"\bi will die in \d+\b",
        r"\btook (pills|tablets|overdose)\b",
        r"\bjust cut\b",
    ]

    medium_risk = [
        r"\bsuicid\w*\b",
        r"\bself.?harm\b",
        r"\bhurt myself\b",
        r"\bcut myself\b",
        r"\bnothing matters\b",
        r"\bbetter off without me\b",
        r"\bjeena nahi chah\w*\b",
        r"\bmar jaana chah\w*\b",
        r"\bsuicide korte chacchi\b",
        r"\bmare jabo\b",
    ]

    for pattern in high_risk:
        if re.search(pattern, text):
            return "high"

    for pattern in medium_risk:
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
    crisis_level    = classify_crisis_level(user_input)

    if possible_crisis:
        print(
            f"[CRISIS] Level={crisis_level} | "
            f"Active={prompt_manager.detect_active_harm(user_input)} | "
            f"Input={user_input[:80]!r}"
        )

    # ── Build messages ────────────────────────────────────────
    client = OpenAI(api_key=GROQ_API_KEY, base_url=BASE_URL)

    messages = prompt_manager.build_prompt(
        user_input=user_input,
        conversation_history=conversation_history,
        language=language,
        memory_summary=memory_summary,
        possible_crisis=possible_crisis,
    )

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
        max_tokens=MAX_TOKENS
    )

    raw_output = completion.choices[0].message.content.strip()

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
