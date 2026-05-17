import os
import uuid
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, UploadFile, File, Form, Header, Depends, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional

from ai_module.response_generator import generate_response
from ai_module.config import FREE_CHAT_LIMIT
from stt_module.transcriber import transcribe_audio
from tts_module.synthesizer import synthesize_speech
from database.init_db import init_db
from database.connection import close_pool
from database import repository as db
from auth.utils import hash_password, verify_password, generate_token
from auth.dependencies import get_current_user, COOKIE_NAME
from auth.email import send_reset_email

COOKIE_MAX_AGE = 60 * 60 * 24 * 7  # 7 days
SUPPORTED_LANGUAGES = {"english", "hindi", "bengali", "en", "hi", "bn"}


# ── Language detection ────────────────────────────────────────────────────────
#
# Replaced the old Unicode-only detect_language() function with an import from
# ai_module/language_detector.py — which uses a Unicode fast path AND a lightweight
# LLM call as fallback. This correctly handles romanized Bengali ("ami khub kharap
# achi") and romanized Hindi ("mujhe bahut bura lag raha hai") which the old
# Unicode-only version classified as "english".
#
from ai_module.language_detector import detect_language
# ─────────────────────────────────────────────────────────────────────────────



# ── Lifespan ──────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Validate required environment variables on startup
    missing = []
    if not os.getenv("GROQ_API_KEY"):
        missing.append("GROQ_API_KEY")
    if missing:
        print("\n" + "="*60)
        print("  MISSING ENVIRONMENT VARIABLES:")
        for var in missing:
            print(f"    - {var}")
        print("\n  Copy backend-MindVarta/.env.example to backend-MindVarta/.env")
        print("  and fill in your credentials before starting the server.")
        print("="*60 + "\n")
        raise RuntimeError(f"Missing required env vars: {', '.join(missing)}")

    try:
        init_db()
        print("[DB] Connected successfully.")
    except Exception as e:
        print(f"[DB WARNING] Could not connect: {e}")
        print("[DB WARNING] Running with in-memory fallback.")
    yield
    close_pool()


app = FastAPI(title="MindVarta API", lifespan=lifespan)
@app.get("/")
async def home():
    return {"message": "Backend is running successfully"}

# In development allow all localhost origins dynamically
def is_allowed_origin(origin: str) -> bool:
    return origin.startswith("http://localhost") or origin.startswith("http://127.0.0.1")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:5174",
        "http://localhost:3000",
        "http://localhost:4173",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Pydantic models ───────────────────────────────────────────────────────────

class SignUpRequest(BaseModel):
    name: str
    email: str
    password: str

class SignInRequest(BaseModel):
    email: str
    password: str

class ChatRequest(BaseModel):
    message: str
    language: Optional[str] = "english"
    conv_id: Optional[str] = None

class SpeakRequest(BaseModel):
    text: str
    language: Optional[str] = "english"

class ForgotPasswordRequest(BaseModel):
    email: str

class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str

class MoodLogRequest(BaseModel):
    mood_score: int
    mood_label: Optional[str] = None
    note: Optional[str] = None


# ── Security Helpers ──────────────────────────────────────────────────────────

def verify_conversation_ownership(conv_id: str, user_id: str) -> dict:
    """
    Verifies that a conversation belongs to the current user.
    Raises 403 if user is not the owner, 404 if conversation doesn't exist.
    
    Args:
        conv_id: Conversation ID to verify
        user_id: Current user's ID
    
    Returns:
        dict: The conversation object if ownership is verified
    
    Raises:
        HTTPException: 404 if not found, 403 if not owner
    """
    if not conv_id:
        raise HTTPException(status_code=400, detail="Conversation ID is required")
    
    conv = db.get_conversation(conv_id)
    
    if not conv:
        print(f"[SECURITY] Attempt to access non-existent conversation {conv_id} by user {user_id}")
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    if str(conv["user_id"]) != str(user_id):
        print(f"[SECURITY] UNAUTHORIZED ACCESS: User {user_id} tried to access conv {conv_id} (owner: {conv['user_id']})")
        raise HTTPException(status_code=403, detail="Access denied")
    
    return conv


# ── Auth routes ───────────────────────────────────────────────────────────────

@app.post("/auth/signup")
async def signup(body: SignUpRequest, request: Request, response: Response):
    if not body.name.strip():
        raise HTTPException(status_code=400, detail="Name is required")
    if len(body.password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")

    existing = db.get_user_by_email(body.email)
    if existing:
        raise HTTPException(status_code=409, detail="Email already registered")

    pw_hash = hash_password(body.password)
    user = db.create_user(body.name.strip(), body.email, pw_hash)

    token = generate_token()
    ip = request.client.host if request.client else None
    ua = request.headers.get("user-agent", "")[:255]
    sid = db.create_auth_session(user["id"], token, "english", ip, ua)

    response.set_cookie(
        key=COOKIE_NAME, value=token,
        httponly=True, samesite="lax",
        max_age=COOKIE_MAX_AGE, secure=False,  # set secure=True in production
    )
    return {"message": "Account created", "user": {"id": user["id"], "name": user["name"], "email": user["email"]}}


@app.post("/auth/signin")
async def signin(body: SignInRequest, request: Request, response: Response):
    user = db.get_user_by_email(body.email)
    if not user or not verify_password(body.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    token = generate_token()
    ip = request.client.host if request.client else None
    ua = request.headers.get("user-agent", "")[:255]
    db.create_auth_session(user["id"], token, "english", ip, ua)

    response.set_cookie(
        key=COOKIE_NAME, value=token,
        httponly=True, samesite="lax",
        max_age=COOKIE_MAX_AGE, secure=False,
    )
    return {"message": "Signed in", "user": {"id": user["id"], "name": user["name"], "email": user["email"]}}


@app.post("/auth/forgot-password")
async def forgot_password(body: ForgotPasswordRequest):
    # Always return 200 to avoid email enumeration
    user = db.get_user_by_email(body.email.strip().lower())
    if user:
        token = generate_token()
        db.create_reset_token(user["id"], token)
        try:
            send_reset_email(user["email"], token, user["name"])
        except Exception as e:
            print(f"[EMAIL ERROR] {e}")
            raise HTTPException(status_code=500, detail="Failed to send reset email. Check SMTP settings.")
    return {"message": "If that email is registered, a reset link has been sent."}


@app.post("/auth/reset-password")
async def reset_password(body: ResetPasswordRequest):
    if len(body.new_password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")

    record = db.get_valid_reset_token(body.token)
    if not record:
        raise HTTPException(status_code=400, detail="Reset link is invalid or has expired")

    pw_hash = hash_password(body.new_password)
    db.update_user_password(record["user_id"], pw_hash)
    db.consume_reset_token(body.token)
    return {"message": "Password reset successfully. You can now sign in."}


@app.post("/auth/signout")
async def signout(request: Request, response: Response):
    token = request.cookies.get(COOKIE_NAME)
    if token:
        session = db.get_auth_session_by_token(token)
        if session:
            print(f"[SECURITY] User {session['user_id']} signed out at {token[:20]}...")
            db.delete_auth_session(token)
        else:
            print(f"[SECURITY] Signout attempt with invalid token")
    response.delete_cookie(COOKIE_NAME)
    return {"message": "Signed out"}


@app.get("/auth/me")
async def me(current_user: dict = Depends(get_current_user)):
    return {"user": {k: v for k, v in current_user.items() if k not in ("password_hash",)}}


# ── Conversation routes ───────────────────────────────────────────────────────

@app.get("/conversations")
async def list_conversations(current_user: dict = Depends(get_current_user)):
    convs = db.get_user_conversations(current_user["id"])
    return {"conversations": convs}


@app.post("/conversations")
async def new_conversation(current_user: dict = Depends(get_current_user)):
    from datetime import datetime
    title = f"Session on {datetime.now().strftime('%b %d')}"
    conv_id = db.create_conversation(current_user["id"], current_user["session_id"], title)
    return {"conv_id": conv_id, "title": title}


@app.delete("/conversations/{conv_id}")
async def delete_conversation(conv_id: str, current_user: dict = Depends(get_current_user)):
    # Verify ownership before deleting
    verify_conversation_ownership(conv_id, current_user["id"])
    db.delete_conversation(conv_id)
    print(f"[INFO] User {current_user['id']} deleted conversation {conv_id}")
    return {"message": "Deleted"}


@app.get("/conversations/{conv_id}/messages")
async def get_conversation_messages(conv_id: str, current_user: dict = Depends(get_current_user)):
    # Verify ownership of conversation
    verify_conversation_ownership(conv_id, current_user["id"])
    messages = db.get_recent_history(conv_id)
    return {"messages": messages}


# ── Chat ──────────────────────────────────────────────────────────────────────

@app.post("/chat")
async def chat(body: ChatRequest, current_user: dict = Depends(get_current_user)):
    user_input = body.message.strip()
    if not user_input:
        raise HTTPException(status_code=400, detail="No message provided")

    # ── AUTO-DETECT LANGUAGE FROM THE MESSAGE TEXT ──
    # Previously language came from body.language (a static frontend value).
    # Now we detect from the actual message text so romanized Bengali/Hindi
    # ("ami khub kharap achi", "mujhe bura lag raha hai") are correctly identified.
    language = detect_language(user_input)
    print(f"[LANG] Detected language: '{language}' from message: {user_input[:60]!r}")

    # Get or create conversation
    conv_id = body.conv_id
    if conv_id:
        # SECURITY: Verify ownership of existing conversation
        # This will raise 403 if user doesn't own the conversation
        conv = verify_conversation_ownership(conv_id, current_user["id"])
        
        # If language has changed from the conversation's language, start a new conversation
        if conv.get("language") != language:
            from datetime import datetime
            title = f"Session on {datetime.now().strftime('%b %d')}"
            conv_id = db.create_conversation(current_user["id"], current_user["session_id"], title, language)
            conv = db.get_conversation(conv_id)
            print(f"[INFO] Language changed from {conv.get('language')} to {language}. User {current_user['id']} created new conversation {conv_id}")
    else:
        # Create new conversation
        from datetime import datetime
        title = f"Session on {datetime.now().strftime('%b %d')}"
        conv_id = db.create_conversation(current_user["id"], current_user["session_id"], title, language)
        conv = db.get_conversation(conv_id)
        print(f"[INFO] User {current_user['id']} created new conversation {conv_id}")

    if conv["count"] >= FREE_CHAT_LIMIT:
        raise HTTPException(
            status_code=429,
            detail={
                "error": "free_limit_reached",
                "message": f"You've reached the free limit of {FREE_CHAT_LIMIT} messages. Please start a new conversation.",
                "conv_id": conv_id,
            }
        )

    history = db.get_recent_history(conv_id)

    # Build memory: current conversation memory + summaries from previous sessions
    memory = conv["memory"]
    if not memory:
        prior_context = db.get_user_context_summary(current_user["id"], exclude_conv_id=conv_id)
        if prior_context:
            memory = prior_context
            print(f"[INFO] Loaded prior context ({len(memory)} chars) for user {current_user['id']}")
        else:
            print(f"[INFO] No prior context for user {current_user['id']} (first conversation)")

    try:
        result = generate_response(
            user_input=user_input,
            conversation_history=history,
            language=language,
            memory_summary=memory,
        )
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        print(f"[ERROR] generate_response failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to get a response. Please try again.")

    bot_reply = result["actual_response"]
    new_summary = result.get("summarize_context", "").strip() or conv["memory"]
    new_count = conv["count"] + 1

    db.save_message(conv_id, "user", user_input)
    db.save_message(conv_id, "assistant", bot_reply)
    db.update_conversation(conv_id, new_summary, new_count)

    # Always save a summary for cross-session context
    summary_to_save = new_summary or bot_reply[:200] or user_input[:100]
    if summary_to_save:
        db.save_summary(conv_id, summary_to_save)

    # Sync language on auth session
    if language != current_user.get("language"):
        db.update_session_language(current_user["session_id"], language)

    return {
        "response": bot_reply,
        "conv_id": conv_id,
        "language": language,
        "messages_used": new_count,
        "messages_remaining": FREE_CHAT_LIMIT - new_count,
    }


# ── TTS / STT ─────────────────────────────────────────────────────────────────

@app.post("/speak")
async def speak(body: SpeakRequest, current_user: dict = Depends(get_current_user)):
    text = body.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="No text provided")
    try:
        audio_bytes = synthesize_speech(text, body.language or "english")
    except Exception as e:
        print(f"[ERROR] TTS failed: {e}")
        raise HTTPException(status_code=500, detail="Speech synthesis failed.")
    from fastapi.responses import Response as FResponse
    return FResponse(content=audio_bytes, media_type="audio/mpeg")


@app.post("/transcribe")
async def transcribe(
    audio: UploadFile = File(...),
    language: str = Form(default="english"),
    current_user: dict = Depends(get_current_user),
):
    user_id = current_user.get("id", "unknown")
    lang = language.strip().lower()
    
    try:
        # Log incoming request
        print(f"[STT] /transcribe called by user {user_id}")
        print(f"[STT] Audio file: {audio.filename}, Content-Type: {audio.content_type}, Language: {lang}")
        
        # Get file size
        audio_content = await audio.read()
        file_size = len(audio_content)
        print(f"[STT] Audio size: {file_size} bytes")
        
        # Reset file pointer for transcriber
        await audio.seek(0)
        
        # Transcribe
        transcript = await transcribe_audio(audio, lang)
        
        if not transcript or not transcript.strip():
            print(f"[STT] Empty transcription from audio ({file_size} bytes)")
            return {"transcript": ""}
        
        print(f"[STT] Transcription success ({file_size} bytes -> {len(transcript)} chars): {transcript[:100]}...")
        return {"transcript": transcript}
        
    except Exception as e:
        print(f"[STT] Transcription failed for user {user_id}: {type(e).__name__}: {e}")
        import traceback
        print(f"[STT] Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Transcription failed: {str(e)}")


# ── Mood Logs ─────────────────────────────────────────────────────────────────

@app.post("/mood")
async def log_mood(body: MoodLogRequest, current_user: dict = Depends(get_current_user)):
    if not (1 <= body.mood_score <= 10):
        raise HTTPException(status_code=400, detail="mood_score must be between 1 and 10")
    db.log_mood(current_user["id"], body.mood_score, body.mood_label, body.note)
    return {"message": "Mood logged"}


@app.get("/mood")
async def get_mood_logs(current_user: dict = Depends(get_current_user)):
    logs = db.get_mood_logs(current_user["id"])
    return {"mood_logs": logs}


# ── Health ────────────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "ok"}


# ── Server Startup ────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)