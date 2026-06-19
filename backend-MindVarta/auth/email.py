import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

load_dotenv()

SMTP_HOST     = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT     = int(os.getenv("SMTP_PORT", 587))
SMTP_USER     = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
FRONTEND_URL  = os.getenv("FRONTEND_URL", "http://localhost:5173").rstrip("/")

# SendGrid API for production (when SMTP is blocked)
SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY", "")
USE_SENDGRID = os.getenv("USE_SENDGRID", "false").lower() == "true"


def send_reset_email_smtp(to_email: str, reset_token: str, user_name: str):
    """Traditional SMTP email sending (works locally, blocked on Render free tier)"""
    reset_link = f"{FRONTEND_URL}/reset-password?token={reset_token}"

    msg = MIMEMultipart("alternative")
    msg["Subject"] = "Reset your MindVarta password"
    msg["From"]    = f"MindVarta <{SMTP_USER}>"
    msg["To"]      = to_email

    text = f"""Hi {user_name},

You requested a password reset for your MindVarta account.

Click the link below to reset your password (valid for 1 hour):
{reset_link}

If you didn't request this, you can safely ignore this email.

— The MindVarta Team
"""

    html = f"""
<div style="font-family:sans-serif;max-width:480px;margin:0 auto;padding:32px 24px;background:#f8fafc;border-radius:12px;">
  <h2 style="color:#1a6fd4;margin-bottom:8px;">MindVarta</h2>
  <p style="color:#374151;">Hi <strong>{user_name}</strong>,</p>
  <p style="color:#374151;">You requested a password reset. Click the button below — the link is valid for <strong>1 hour</strong>.</p>
  <a href="{reset_link}"
     style="display:inline-block;margin:20px 0;padding:12px 28px;background:#1a6fd4;color:#fff;
            border-radius:50px;text-decoration:none;font-weight:700;font-size:15px;">
    Reset Password
  </a>
  <p style="color:#6b7280;font-size:13px;">If you didn't request this, you can safely ignore this email.</p>
  <hr style="border:none;border-top:1px solid #e5e7eb;margin:24px 0;">
  <p style="color:#9ca3af;font-size:12px;">— The MindVarta Team</p>
</div>
"""

    msg.attach(MIMEText(text, "plain"))
    msg.attach(MIMEText(html, "html"))

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
        server.ehlo()
        server.starttls()
        server.login(SMTP_USER, SMTP_PASSWORD)
        server.sendmail(SMTP_USER, to_email, msg.as_string())


def send_reset_email_sendgrid(to_email: str, reset_token: str, user_name: str):
    """SendGrid API email sending (works on Render free tier)"""
    import requests
    
    reset_link = f"{FRONTEND_URL}/reset-password?token={reset_token}"
    
    html_content = f"""
<div style="font-family:sans-serif;max-width:480px;margin:0 auto;padding:32px 24px;background:#f8fafc;border-radius:12px;">
  <h2 style="color:#1a6fd4;margin-bottom:8px;">MindVarta</h2>
  <p style="color:#374151;">Hi <strong>{user_name}</strong>,</p>
  <p style="color:#374151;">You requested a password reset. Click the button below — the link is valid for <strong>1 hour</strong>.</p>
  <a href="{reset_link}"
     style="display:inline-block;margin:20px 0;padding:12px 28px;background:#1a6fd4;color:#fff;
            border-radius:50px;text-decoration:none;font-weight:700;font-size:15px;">
    Reset Password
  </a>
  <p style="color:#6b7280;font-size:13px;">If you didn't request this, you can safely ignore this email.</p>
  <hr style="border:none;border-top:1px solid #e5e7eb;margin:24px 0;">
  <p style="color:#9ca3af;font-size:12px;">— The MindVarta Team</p>
</div>
"""
    
    text_content = f"""Hi {user_name},

You requested a password reset for your MindVarta account.

Click the link below to reset your password (valid for 1 hour):
{reset_link}

If you didn't request this, you can safely ignore this email.

— The MindVarta Team
"""
    
    payload = {
        "personalizations": [{
            "to": [{"email": to_email}],
            "subject": "Reset your MindVarta password"
        }],
        "from": {
            "email": SMTP_USER,
            "name": "MindVarta"
        },
        "content": [
            {
                "type": "text/plain",
                "value": text_content
            },
            {
                "type": "text/html",
                "value": html_content
            }
        ]
    }
    
    headers = {
        "Authorization": f"Bearer {SENDGRID_API_KEY}",
        "Content-Type": "application/json"
    }
    
    response = requests.post(
        "https://api.sendgrid.com/v3/mail/send",
        json=payload,
        headers=headers
    )
    
    if response.status_code not in [200, 202]:
        raise Exception(f"SendGrid API error: {response.status_code} - {response.text}")


def send_reset_email(to_email: str, reset_token: str, user_name: str):
    """
    Main email sending function that chooses the appropriate method.
    Uses SendGrid API in production (Render), SMTP locally.
    """
    try:
        if USE_SENDGRID and SENDGRID_API_KEY:
            print(f"[EMAIL] Sending via SendGrid to {to_email}")
            send_reset_email_sendgrid(to_email, reset_token, user_name)
        else:
            print(f"[EMAIL] Sending via SMTP to {to_email}")
            send_reset_email_smtp(to_email, reset_token, user_name)
    except Exception as e:
        print(f"[EMAIL ERROR] {e}")
        raise

