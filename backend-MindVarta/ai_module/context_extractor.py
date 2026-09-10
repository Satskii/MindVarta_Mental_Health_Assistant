"""
Detailed Context Extractor - Extracts specific, actionable information from conversations.
Instead of generic summaries, captures:
- Key details about user's situation (problems, challenges, achievements)
- Personal information (background, interests, relationships)
- Emotional context (how they're feeling, past struggles)
- Specific goals or concerns mentioned
- Any advice given and user's response
"""

import json
from openai import OpenAI
from ai_module.config import GROQ_API_KEY, BASE_URL

client = OpenAI(
    api_key=GROQ_API_KEY,
    base_url=BASE_URL,
)

EXTRACTION_PROMPT = """
You are an expert at extracting important context from conversations.
Analyze the conversation and extract SPECIFIC, DETAILED information the user shared.

Extract and return ONLY valid JSON with this structure:
{
  "personal_info": {
    "name": "user's name if mentioned",
    "background": "education level, field of study, current role",
    "relationships": "family, friends, relationships mentioned",
    "location": "city/state if mentioned"
  },
  "current_situation": {
    "challenges": ["specific problem 1", "specific problem 2"],
    "achievements": ["what they succeeded at", "positive things they mentioned"],
    "responsibilities": "what they're responsible for (work, studies, family)"
  },
  "emotional_context": {
    "primary_feelings": ["stressed", "anxious", "overwhelmed", etc],
    "past_struggles": ["previous challenges they mentioned"],
    "coping_mechanisms": ["how they usually handle stress"]
  },
  "specific_concerns": [
    "exact worry 1 as mentioned by user",
    "exact worry 2 as mentioned by user"
  ],
  "goals_and_interests": {
    "short_term_goals": ["goal 1", "goal 2"],
    "long_term_goals": ["career goal", "life goal"],
    "interests": ["hobby 1", "hobby 2"]
  },
  "health_indicators": {
    "sleep_quality": "mentioned sleep status",
    "stress_level": "1-10 if mentioned",
    "physical_activity": "mentioned exercise/activity",
    "substance_use": "any mention of alcohol, drugs, caffeine"
  },
  "advice_given_and_response": {
    "suggestions_made": ["suggestion 1"],
    "user_response": "did they agree, reject, or modify the advice?"
  }
}

RULES:
- Extract ONLY information explicitly mentioned, don't infer or make assumptions
- If something wasn't mentioned, set it to null or empty string
- Be specific: "exam stress in biology" not just "exam stress"
- Keep exact phrases the user used where possible
- Return ONLY the JSON, no other text
"""

def extract_detailed_context(conversation_history: list, language: str = "english") -> dict:
    """
    Analyzes a conversation and extracts detailed, structured context.
    Falls back to basic context generation if extraction fails or returns empty.
    
    Args:
        conversation_history: List of message dicts with 'role' and 'content'
        language: Language of conversation
    
    Returns:
        dict: Structured context with personal info, situation, emotions, etc.
    """
    
    if not conversation_history:
        return {}
    
    # Format conversation for analysis
    conv_text = "\n".join([
        f"{msg['role'].upper()}: {msg['content']}"
        for msg in conversation_history
    ])
    
    try:
        completion = client.chat.completions.create(
            model="openai/gpt-oss-120b",
            messages=[
                {
                    "role": "system",
                    "content": EXTRACTION_PROMPT
                },
                {
                    "role": "user",
                    "content": f"Extract detailed context from this conversation:\n\n{conv_text}"
                }
            ],
            temperature=0.3,  # Low temperature for consistent extraction
            max_tokens=2000,
        )
        
        response_text = completion.choices[0].message.content.strip()
        
        # Clean up any markdown code fences
        if "```" in response_text:
            response_text = response_text.split("```")[1]
            if response_text.startswith("json"):
                response_text = response_text[4:]
            response_text = response_text.strip()
        
        # Parse JSON
        extracted = json.loads(response_text)
        
        # Ensure we have at least some fields (not all empty)
        if extracted and any(v for v in extracted.values() if v):
            print(f"[DEBUG] Successfully extracted detailed context from {len(conversation_history)} messages")
            return extracted
        else:
            print(f"[DEBUG] Extracted context was empty, generating fallback")
            return _generate_fallback_context(conversation_history)
        
    except json.JSONDecodeError as e:
        print(f"[WARN] Failed to parse extracted context: {e}, using fallback")
        return _generate_fallback_context(conversation_history)
    except Exception as e:
        print(f"[WARN] Context extraction failed: {e}, using fallback")
        return _generate_fallback_context(conversation_history)


def _generate_fallback_context(conversation_history: list) -> dict:
    """
    Generate basic context from conversation when LLM extraction fails.
    Ensures we always have SOME context to work with.
    """
    if not conversation_history or len(conversation_history) < 2:
        return {}
    
    # Find user messages (skip system messages)
    user_messages = [msg['content'] for msg in conversation_history if msg.get('role') == 'user']
    assistant_messages = [msg['content'] for msg in conversation_history if msg.get('role') == 'assistant']
    
    if not user_messages:
        return {}
    
    # Build basic context from what we can extract
    context = {
        "personal_info": {},
        "current_situation": {
            "challenges": [],
            "achievements": [],
            "responsibilities": ""
        },
        "emotional_context": {
            "primary_feelings": [],
            "past_struggles": [],
            "coping_mechanisms": []
        },
        "specific_concerns": [],
        "goals_and_interests": {
            "short_term_goals": [],
            "long_term_goals": [],
            "interests": []
        },
        "health_indicators": {},
        "advice_given_and_response": {}
    }
    
    # Extract keywords from first user message that might indicate concerns
    first_message = user_messages[0].lower()
    
    # Simple keyword detection for emotions
    emotion_keywords = {
        'stressed': 'stressed',
        'anxious': 'anxious',
        'overwhelmed': 'overwhelmed',
        'sad': 'sad',
        'worried': 'worried',
        'tired': 'tired',
        'confused': 'confused',
        'frustrated': 'frustrated',
    }
    
    for keyword, label in emotion_keywords.items():
        if keyword in first_message:
            context["emotional_context"]["primary_feelings"].append(label)
    
    # If we extracted at least one emotion, keep the context
    if context["emotional_context"]["primary_feelings"]:
        print(f"[DEBUG] Generated fallback context with detected emotions")
        return context
    
    # If still empty, return minimal context
    return {}



def merge_contexts(old_context: dict | str, new_context: dict) -> dict:
    """
    Merges old and new context, preserving previous details and adding new ones.
    
    Args:
        old_context: Previous context (dict or JSON string)
        new_context: Newly extracted context (dict)
    
    Returns:
        dict: Merged context
    """
    
    # Parse old context if it's a string
    if isinstance(old_context, str):
        try:
            old = json.loads(old_context)
        except:
            old = {}
    else:
        old = old_context or {}
    
    # If no old context, return new
    if not old:
        return new_context
    
    merged = {}
    
    # Merge personal_info (new info overrides old)
    if "personal_info" in old or "personal_info" in new_context:
        merged["personal_info"] = {**old.get("personal_info", {}), **new_context.get("personal_info", {})}
    
    # Merge challenges and achievements (append new, don't duplicate)
    if "current_situation" in old or "current_situation" in new_context:
        old_sit = old.get("current_situation", {})
        new_sit = new_context.get("current_situation", {})
        merged["current_situation"] = {
            "challenges": list(set((old_sit.get("challenges") or []) + (new_sit.get("challenges") or []))),
            "achievements": list(set((old_sit.get("achievements") or []) + (new_sit.get("achievements") or []))),
            "responsibilities": new_sit.get("responsibilities") or old_sit.get("responsibilities", "")
        }
    
    # Merge emotional context
    if "emotional_context" in old or "emotional_context" in new_context:
        old_em = old.get("emotional_context", {})
        new_em = new_context.get("emotional_context", {})
        merged["emotional_context"] = {
            "primary_feelings": list(set((old_em.get("primary_feelings") or []) + (new_em.get("primary_feelings") or []))),
            "past_struggles": list(set((old_em.get("past_struggles") or []) + (new_em.get("past_struggles") or []))),
            "coping_mechanisms": list(set((old_em.get("coping_mechanisms") or []) + (new_em.get("coping_mechanisms") or [])))
        }
    
    # Merge specific concerns
    if "specific_concerns" in old or "specific_concerns" in new_context:
        merged["specific_concerns"] = list(set(
            (old.get("specific_concerns") or []) + (new_context.get("specific_concerns") or [])
        ))
    
    # Merge goals
    if "goals_and_interests" in old or "goals_and_interests" in new_context:
        old_goals = old.get("goals_and_interests", {})
        new_goals = new_context.get("goals_and_interests", {})
        merged["goals_and_interests"] = {
            "short_term_goals": list(set((old_goals.get("short_term_goals") or []) + (new_goals.get("short_term_goals") or []))),
            "long_term_goals": list(set((old_goals.get("long_term_goals") or []) + (new_goals.get("long_term_goals") or []))),
            "interests": list(set((old_goals.get("interests") or []) + (new_goals.get("interests") or [])))
        }
    
    # Update health indicators
    if "health_indicators" in new_context:
        merged["health_indicators"] = new_context["health_indicators"]
    elif "health_indicators" in old:
        merged["health_indicators"] = old["health_indicators"]
    
    # Latest advice
    if "advice_given_and_response" in new_context:
        merged["advice_given_and_response"] = new_context["advice_given_and_response"]
    elif "advice_given_and_response" in old:
        merged["advice_given_and_response"] = old["advice_given_and_response"]
    
    return merged


def format_context_for_llm(context: dict | str) -> str:
    """
    Formats extracted context into a readable prompt for the LLM.
    Ensures SOMETHING is returned even if context is sparse.
    
    Args:
        context: Structured context dict or JSON string
    
    Returns:
        str: Formatted context prompt
    """
    
    if isinstance(context, str):
        try:
            ctx = json.loads(context)
        except:
            return ""
    else:
        ctx = context
    
    if not ctx:
        return ""
    
    lines = []
    
    # Personal info - only add section if we have content
    if ctx.get("personal_info"):
        pi = ctx["personal_info"]
        if any(v for v in pi.values() if v):  # Only add section if has content
            lines.append("ABOUT THIS USER:")
            if pi.get("background"):
                lines.append(f"  - Background: {pi['background']}")
            if pi.get("relationships"):
                lines.append(f"  - Relationships: {pi['relationships']}")
            if pi.get("location"):
                lines.append(f"  - Location: {pi['location']}")
    
    # Current situation - only add section if we have content
    if ctx.get("current_situation"):
        cs = ctx["current_situation"]
        has_content = any([cs.get("challenges"), cs.get("achievements"), cs.get("responsibilities")])
        if has_content:
            lines.append("\nCURRENT SITUATION:")
            if cs.get("challenges"):
                lines.append(f"  Challenges: {', '.join(cs['challenges'])}")
            if cs.get("achievements"):
                lines.append(f"  Recent wins: {', '.join(cs['achievements'])}")
            if cs.get("responsibilities"):
                lines.append(f"  Responsibilities: {cs['responsibilities']}")
    
    # Emotions - only add section if we have content
    if ctx.get("emotional_context"):
        em = ctx["emotional_context"]
        has_content = any([em.get("primary_feelings"), em.get("coping_mechanisms")])
        if has_content:
            lines.append("\nEMOTIONAL CONTEXT:")
            if em.get("primary_feelings"):
                lines.append(f"  Currently feeling: {', '.join(em['primary_feelings'])}")
            if em.get("coping_mechanisms"):
                lines.append(f"  Usually copes with: {', '.join(em['coping_mechanisms'])}")
    
    # Concerns - only add section if we have content
    if ctx.get("specific_concerns"):
        concerns = ctx["specific_concerns"]
        if concerns:
            lines.append("\nSPECIFIC CONCERNS:")
            for concern in concerns[:5]:  # Max 5
                if concern:
                    lines.append(f"  - {concern}")
    
    # Goals - only add section if we have content
    if ctx.get("goals_and_interests"):
        gi = ctx["goals_and_interests"]
        has_content = any([gi.get("short_term_goals"), gi.get("long_term_goals"), gi.get("interests")])
        if has_content:
            lines.append("\nGOALS & INTERESTS:")
            if gi.get("short_term_goals"):
                lines.append(f"  Short-term: {', '.join(gi['short_term_goals'])}")
            if gi.get("long_term_goals"):
                lines.append(f"  Long-term: {', '.join(gi['long_term_goals'])}")
            if gi.get("interests"):
                lines.append(f"  Interests: {', '.join(gi['interests'])}")
    
    # Health - only add section if we have content
    if ctx.get("health_indicators"):
        hi = ctx["health_indicators"]
        if any(hi.values()):
            lines.append("\nHEALTH:")
            for key, value in hi.items():
                if value:
                    lines.append(f"  - {key}: {value}")
    
    result = "\n".join(lines) if lines else ""
    if result:
        print(f"[DEBUG] Formatted detailed context ({len(result)} chars) for LLM")
    else:
        print(f"[DEBUG] No content to format from detailed context")
    return result

