"""
Sends WhatsApp notifications via CallMeBot.
"""

import urllib.parse
import requests
import config

CALLMEBOT_URL = "https://api.callmebot.com/whatsapp.php"


def send_whatsapp(message: str) -> bool:
    if not config.CALLMEBOT_PHONE or not config.CALLMEBOT_APIKEY:
        print("[notify] CallMeBot credentials missing, skipping send")
        return False

    params = {
        "phone": config.CALLMEBOT_PHONE,
        "text": message,
        "apikey": config.CALLMEBOT_APIKEY,
    }
    url = f"{CALLMEBOT_URL}?{urllib.parse.urlencode(params)}"

    try:
        resp = requests.get(url, timeout=20)
        print(f"[notify] status={resp.status_code} body={resp.text[:200]}")
        return resp.status_code == 200
    except Exception as e:
        print(f"[notify] failed to send: {e}")
        return False


def _format_age(posted_at):
    if not posted_at:
        return None
    from datetime import datetime, timezone
    age = datetime.now(timezone.utc) - posted_at
    hours = age.total_seconds() / 3600
    if hours < 1:
        return f"{int(age.total_seconds() / 60)}m ago"
    return f"{int(hours)}h ago"


def format_job_message(job, match_result) -> str:
    strengths = ", ".join(match_result.get("key_strengths", [])[:3]) or "N/A"
    age_str = _format_age(job.get("posted_at"))
    age_line = f"🕐 Posted: {age_str}\n" if age_str else ""
    return (
        f"🎯 *New High-Match Job!*\n\n"
        f"*{job['title']}* @ {job['company']}\n"
        f"📍 {job.get('location', 'N/A')}\n"
        f"{age_line}"
        f"✅ Match Score: {match_result['match_score']}/100\n"
        f"📄 Use resume: {match_result['resume_label']}\n"
        f"💪 Strengths: {strengths}\n\n"
        f"🔗 {job['url']}"
    )


def notify_job(job, match_result):
    message = format_job_message(job, match_result)
    return send_whatsapp(message)
