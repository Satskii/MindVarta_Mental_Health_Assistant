"""
All DB read/write operations.
Falls back to in-memory store if DB is unavailable.
"""
import uuid
from database.connection import get_connection, release_connection

HISTORY_LIMIT = 20

# In-memory fallback
_fallback: dict = {}
_db_available = True


def _use_fallback() -> bool:
    return not _db_available


def set_db_available(state: bool):
    global _db_available
    _db_available = state


# ── Users ─────────────────────────────────────────────────────────────────────

def create_user(name: str, email: str, password_hash: str) -> dict:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO users (name, email, password_hash)
                   VALUES (%s, %s, %s)
                   RETURNING id, name, email, created_at""",
                (name, email, password_hash)
            )
            row = cur.fetchone()
        conn.commit()
    finally:
        release_connection(conn)
    return {"id": str(row[0]), "name": row[1], "email": row[2], "created_at": str(row[3])}


def get_user_by_email(email: str) -> dict | None:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, name, email, password_hash FROM users WHERE email = %s",
                (email,)
            )
            row = cur.fetchone()
    finally:
        release_connection(conn)
    if not row:
        return None
    return {"id": str(row[0]), "name": row[1], "email": row[2], "password_hash": row[3]}


def get_user_by_id(user_id: str) -> dict | None:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, name, email FROM users WHERE id = %s",
                (user_id,)
            )
            row = cur.fetchone()
    finally:
        release_connection(conn)
    if not row:
        return None
    return {"id": str(row[0]), "name": row[1], "email": row[2]}


# ── Auth Sessions ─────────────────────────────────────────────────────────────

def create_auth_session(user_id: str, token: str, language: str = "english",
                        ip_address: str = None, device_info: str = None) -> str:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO sessions (user_id, session_token, language, ip_address, device_info)
                   VALUES (%s, %s, %s, %s, %s)
                   RETURNING session_id""",
                (user_id, token, language, ip_address, device_info)
            )
            sid = str(cur.fetchone()[0])
        conn.commit()
    finally:
        release_connection(conn)
    return sid


def get_auth_session_by_token(token: str) -> dict | None:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT session_id, user_id, language, expires_at
                   FROM sessions
                   WHERE session_token = %s AND expires_at > NOW()""",
                (token,)
            )
            row = cur.fetchone()
    finally:
        release_connection(conn)
    if not row:
        return None
    return {
        "session_id": str(row[0]),
        "user_id": str(row[1]),
        "language": row[2],
        "expires_at": str(row[3]),
    }


def delete_auth_session(token: str):
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM sessions WHERE session_token = %s", (token,))
        conn.commit()
    finally:
        release_connection(conn)


def update_session_language(session_id: str, language: str):
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE sessions SET language = %s WHERE session_id = %s",
                (language, session_id)
            )
        conn.commit()
    finally:
        release_connection(conn)


# ── Conversations ─────────────────────────────────────────────────────────────

def create_conversation(user_id: str, session_id: str, title: str = "New Conversation", language: str = "english") -> str:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO conversations (user_id, session_id, language, title)
                   VALUES (%s, %s, %s, %s) RETURNING conv_id""",
                (user_id, session_id, language, title)
            )
            conv_id = str(cur.fetchone()[0])
        conn.commit()
    finally:
        release_connection(conn)
    return conv_id


def get_conversation(conv_id: str) -> dict | None:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT conv_id, user_id, language, title, msg_count, memory FROM conversations WHERE conv_id = %s",
                (conv_id,)
            )
            row = cur.fetchone()
    finally:
        release_connection(conn)
    if not row:
        return None
    return {
        "conv_id": str(row[0]), "user_id": str(row[1]), "language": row[2],
        "title": row[3], "count": row[4], "memory": row[5],
    }


def get_user_conversations(user_id: str) -> list[dict]:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT conv_id, title, msg_count, created_at, updated_at
                   FROM conversations WHERE user_id = %s
                   ORDER BY updated_at DESC""",
                (user_id,)
            )
            rows = cur.fetchall()
    finally:
        release_connection(conn)
    return [
        {"conv_id": str(r[0]), "title": r[1], "msg_count": r[2],
         "created_at": r[3].isoformat() if r[3] else None, "updated_at": r[4].isoformat() if r[4] else None}
        for r in rows
    ]


def update_conversation(conv_id: str, memory: str, msg_count: int, title: str = None, language: str = None):
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            if title and language:
                cur.execute(
                    "UPDATE conversations SET memory=%s, msg_count=%s, title=%s, language=%s WHERE conv_id=%s",
                    (memory, msg_count, title, language, conv_id)
                )
            elif title:
                cur.execute(
                    "UPDATE conversations SET memory=%s, msg_count=%s, title=%s WHERE conv_id=%s",
                    (memory, msg_count, title, conv_id)
                )
            elif language:
                cur.execute(
                    "UPDATE conversations SET memory=%s, msg_count=%s, language=%s WHERE conv_id=%s",
                    (memory, msg_count, language, conv_id)
                )
            else:
                cur.execute(
                    "UPDATE conversations SET memory=%s, msg_count=%s WHERE conv_id=%s",
                    (memory, msg_count, conv_id)
                )
        conn.commit()
    finally:
        release_connection(conn)


def delete_conversation(conv_id: str):
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM conversations WHERE conv_id = %s", (conv_id,))
        conn.commit()
    finally:
        release_connection(conn)


# ── Messages ──────────────────────────────────────────────────────────────────

def save_message(conv_id: str, role: str, content: str, tokens_used: int = None):
    if _use_fallback():
        if conv_id in _fallback:
            _fallback[conv_id]["history"].append({"role": role, "content": content})
        return
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO messages (conversation_id, role, content, tokens_used) VALUES (%s, %s, %s, %s)",
                (conv_id, role, content, tokens_used)
            )
        conn.commit()
    finally:
        release_connection(conn)


def get_recent_history(conv_id: str) -> list[dict]:
    if _use_fallback():
        return _fallback.get(conv_id, {}).get("history", [])[-HISTORY_LIMIT:]
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT role, content FROM messages
                   WHERE conversation_id = %s
                   ORDER BY created_at DESC LIMIT %s""",
                (conv_id, HISTORY_LIMIT)
            )
            rows = cur.fetchall()
    finally:
        release_connection(conn)
    return [{"role": r[0], "content": r[1]} for r in reversed(rows)]


# ── Conversation Summaries ────────────────────────────────────────────────────

def save_summary(conv_id: str, summary: str):
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO conversation_summaries (conversation_id, summary) VALUES (%s, %s)",
                (conv_id, summary)
            )
        conn.commit()
    finally:
        release_connection(conn)


def get_user_context_summary(user_id: str, exclude_conv_id: str = None) -> str:
    """
    Return the latest *rolling memory* for each of the user's recent previous
    conversations.  ``conversation_summaries`` is an audit trail (one row is
    written per reply), so querying its latest three rows can return three
    versions of the same conversation and omit every other session.

    The ``conversations.memory`` column is the canonical latest summary for a
    conversation.  Reading it here gives cross-session retrieval one useful
    context block per conversation.
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT c.memory
                   FROM conversations c
                   WHERE c.user_id = %s
                     AND c.memory <> ''
                     AND (%s IS NULL OR c.conv_id != %s)
                   ORDER BY c.updated_at DESC
                   LIMIT 3""",
                (user_id, exclude_conv_id, exclude_conv_id)
            )
            rows = cur.fetchall()
    finally:
        release_connection(conn)
    if not rows:
        print(f"[DEBUG] No context summaries found for user {user_id}")
        return ""
    
    result = " | ".join(r[0] for r in rows if r[0])
    print(f"[DEBUG] Retrieved context summary ({len(result)} chars) for user {user_id}")
    return result


# ── Detailed Context ──────────────────────────────────────────────────────────

def save_detailed_context(user_id: str, context_data: dict | str, conversation_id: str = None):
    """
    Saves detailed user context extracted from a conversation.
    
    Args:
        user_id: User ID
        context_data: Structured context dict or JSON string
        conversation_id: Associated conversation ID (optional)
    """
    import json
    
    if isinstance(context_data, dict):
        context_json = json.dumps(context_data)
    else:
        context_json = context_data
    
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO user_detailed_contexts (user_id, conversation_id, context_data)
                   VALUES (%s, %s, %s)
                   RETURNING context_id""",
                (user_id, conversation_id, context_json)
            )
            context_id = str(cur.fetchone()[0])
        conn.commit()
        print(f"[DEBUG] Saved detailed context {context_id} for user {user_id}")
    except Exception as e:
        print(f"[ERROR] Failed to save detailed context for user {user_id}: {e}")
        raise
    finally:
        release_connection(conn)
    return context_id


def get_user_detailed_context(user_id: str, exclude_conv_id: str = None) -> dict:
    """
    Retrieves and merges detailed context from the user's last few conversations.
    This provides rich, specific information for the LLM.
    
    Args:
        user_id: User ID
        exclude_conv_id: Conversation to exclude (current conversation)
    
    Returns:
        dict: Merged detailed context from previous conversations
    """
    import json
    
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT context_data
                   FROM user_detailed_contexts
                   WHERE user_id = %s
                     AND (%s IS NULL OR conversation_id != %s)
                   ORDER BY created_at DESC
                   LIMIT 5""",
                (user_id, exclude_conv_id, exclude_conv_id)
            )
            rows = cur.fetchall()
    finally:
        release_connection(conn)
    
    if not rows:
        print(f"[DEBUG] No detailed context found for user {user_id}")
        return {}
    
    print(f"[DEBUG] Retrieved {len(rows)} detailed context records for user {user_id}")
    
    # Parse and merge contexts (most recent first)
    merged = {}
    for row in rows:
        try:
            ctx = json.loads(row[0]) if isinstance(row[0], str) else row[0]
            if not merged:
                merged = ctx
            else:
                # Import here to avoid circular imports
                from ai_module.context_extractor import merge_contexts
                merged = merge_contexts(merged, ctx)
        except Exception as e:
            print(f"[WARN] Failed to parse detailed context: {e}")
            pass
    
    return merged


def update_detailed_context(user_id: str, context_data: dict | str, conversation_id: str = None) -> str:
    """
    Updates the latest detailed context for a user by merging with existing context.
    Ensures context is saved for ALL users on every message.
    """
    import json
    
    # Parse new context
    if isinstance(context_data, dict):
        new_ctx = context_data
    else:
        try:
            new_ctx = json.loads(context_data)
        except:
            print(f"[WARN] Invalid context data for user {user_id}")
            new_ctx = {}
    
    if not new_ctx:
        print(f"[DEBUG] No new context to save for user {user_id}")
        return None
    
    # Get existing context
    try:
        existing = get_user_detailed_context(user_id, exclude_conv_id=None)
    except Exception as e:
        print(f"[WARN] Could not retrieve existing context for user {user_id}: {e}")
        existing = {}
    
    # Merge contexts
    if existing:
        try:
            from ai_module.context_extractor import merge_contexts
            merged = merge_contexts(existing, new_ctx)
            print(f"[DEBUG] Merged context with existing for user {user_id}")
        except Exception as e:
            print(f"[WARN] Context merge failed for user {user_id}: {e}")
            merged = new_ctx
    else:
        merged = new_ctx
    
    # Save merged context
    try:
        return save_detailed_context(user_id, merged, conversation_id)
    except Exception as e:
        print(f"[ERROR] Failed to update detailed context for user {user_id}: {e}")
        # Don't raise, let chat continue
        return None


# ── Password Reset Tokens ─────────────────────────────────────────────────────

def create_reset_token(user_id: str, token: str):
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            # Invalidate any existing unused tokens for this user
            cur.execute(
                "UPDATE password_reset_tokens SET used=TRUE WHERE user_id=%s AND used=FALSE",
                (user_id,)
            )
            cur.execute(
                "INSERT INTO password_reset_tokens (user_id, token) VALUES (%s, %s)",
                (user_id, token)
            )
        conn.commit()
    finally:
        release_connection(conn)


def get_valid_reset_token(token: str) -> dict | None:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT user_id FROM password_reset_tokens
                   WHERE token = %s AND used = FALSE AND expires_at > NOW()""",
                (token,)
            )
            row = cur.fetchone()
    finally:
        release_connection(conn)
    if not row:
        return None
    return {"user_id": str(row[0])}


def consume_reset_token(token: str):
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE password_reset_tokens SET used=TRUE WHERE token=%s",
                (token,)
            )
        conn.commit()
    finally:
        release_connection(conn)


def update_user_password(user_id: str, password_hash: str):
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE users SET password_hash=%s WHERE id=%s",
                (password_hash, user_id)
            )
        conn.commit()
    finally:
        release_connection(conn)


# ── Mood Logs ─────────────────────────────────────────────────────────────────

def log_mood(user_id: str, mood_score: int, mood_label: str = None, note: str = None):
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO mood_logs (user_id, mood_score, mood_label, note) VALUES (%s, %s, %s, %s)",
                (user_id, mood_score, mood_label, note)
            )
        conn.commit()
    finally:
        release_connection(conn)


def get_mood_logs(user_id: str) -> list[dict]:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT id, mood_score, mood_label, note, logged_at
                   FROM mood_logs WHERE user_id = %s ORDER BY logged_at DESC""",
                (user_id,)
            )
            rows = cur.fetchall()
    finally:
        release_connection(conn)
    return [
        {"id": str(r[0]), "mood_score": r[1], "mood_label": r[2],
         "note": r[3], "logged_at": str(r[4])}
        for r in rows
    ]


# ── Fallback helpers (used when DB is down) ───────────────────────────────────

def create_session_fallback(language: str = "english") -> str:
    sid = str(uuid.uuid4())
    _fallback[sid] = {"session_id": sid, "language": language, "memory": "", "count": 0, "history": []}
    return sid


def get_session_fallback(sid: str) -> dict | None:
    sess = _fallback.get(sid)
    if not sess:
        return None
    return {k: v for k, v in sess.items() if k != "history"}
