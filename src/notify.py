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


def format_job_message(job, match_result) -> str:
    strengths = ", ".join(match_result.get("key_strengths", [])[:3]) or "N/A"
    return (
        f"🎯 *New High-Match Job!*\n\n"
        f"*{job['title']}* @ {job['company']}\n"
        f"📍 {job.get('location', 'N/A')}\n"
        f"✅ Match Score: {match_result['match_score']}/100\n"
        f"📄 Use resume: {match_result['resume_label']}\n"
        f"💪 Strengths: {strengths}\n\n"
        f"🔗 {job['url']}"
    )


def notify_job(job, match_result):
    message = format_job_message(job, match_result)
    return send_whatsapp(message)
