"""
emailer.py — Sends email alerts via Resend API (HTTPS, works on any network).
Uses requests directly with SSL verify=False to handle corporate SSL inspection.
"""

import os
import re
import requests
import urllib3
from datetime import datetime

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

RESEND_API_URL = "https://api.resend.com/emails"

_SEVERITY_COLOR = {
    "CRITICAL": "#dc2626",
    "HIGH":     "#ea580c",
    "MEDIUM":   "#d97706",
    "LOW":      "#16a34a",
}

_SEVERITY_BG = {
    "CRITICAL": "#fef2f2",
    "HIGH":     "#fff7ed",
    "MEDIUM":   "#fffbeb",
    "LOW":      "#f0fdf4",
}


def _severity_badge(line: str) -> str:
    for sev, color in _SEVERITY_COLOR.items():
        if sev in line.upper():
            return (
                f'<span style="background:{color};color:#fff;padding:2px 8px;'
                f'border-radius:4px;font-size:11px;font-weight:bold;">{sev}</span>'
            )
    return ""


def build_html_email(body: str) -> str:
    date_str = datetime.now().strftime("%B %d, %Y  %H:%M")
    lines    = body.split("\n")
    html_lines = []

    for raw in lines:
        line = raw.strip()

        if line.startswith("📊 DAILY SUMMARY"):
            html_lines.append(
                '<div style="background:#1e3a5f;color:#fff;padding:12px 16px;'
                'border-radius:6px;margin:16px 0 8px;font-weight:bold;font-size:15px;">'
                f'{line}</div>'
            )

        elif line.startswith("🔴"):
            sev_badge = _severity_badge(line)
            html_lines.append(
                f'<div style="margin-top:18px;padding:10px 14px;background:#f8fafc;'
                f'border-left:4px solid #1e3a5f;border-radius:4px;font-weight:bold;">'
                f'{line} {sev_badge}</div>'
            )

        elif line.startswith("💥 Impact:"):
            content = line[len("💥 Impact:"):].strip()
            html_lines.append(
                f'<div style="margin:6px 0 2px;">'
                f'<span style="font-weight:600;color:#dc2626;">💥 Impact:</span> {content}</div>'
            )

        elif line.startswith("🛠️ Remediation:"):
            content = line[len("🛠️ Remediation:"):].strip()
            html_lines.append(
                f'<div style="margin:4px 0 10px;">'
                f'<span style="font-weight:600;color:#16a34a;">🛠️ Remediation:</span> {content}</div>'
            )

        elif line == "---":
            html_lines.append('<hr style="border:none;border-top:1px solid #e5e7eb;margin:12px 0;">')

        elif line == "":
            html_lines.append("<br>")

        else:
            html_lines.append(f'<div style="margin:2px 0;color:#374151;">{line}</div>')

    body_html = "\n".join(html_lines)

    return f"""
    <html>
    <body style="font-family: Arial, sans-serif; max-width: 720px; margin: auto; padding: 24px; background:#f3f4f6;">

      <div style="background:#1a1a2e;color:white;padding:20px 24px;border-radius:8px 8px 0 0;">
        <h2 style="margin:0;">🔐 Vulnerability Intelligence Digest</h2>
        <p style="margin:4px 0 0;color:#94a3b8;font-size:13px;">Generated {date_str} · Auto-run by AI Agent</p>
      </div>

      <div style="background:#ffffff;padding:20px 24px;border-radius:0 0 8px 8px;border:1px solid #e5e7eb;">
        {body_html}
      </div>

      <div style="padding:12px;text-align:center;color:#9ca3af;font-size:11px;">
        Sources: NIST NVD · CISA KEV · Exploit-DB &nbsp;|&nbsp; Powered by Groq / Gemini
      </div>

    </body>
    </html>
    """


def send_email_alert(subject: str, body: str):
    api_key   = os.getenv("RESEND_API_KEY", "")
    recipient = os.getenv("ALERT_EMAIL", "")

    if not api_key:
        print("  ⚠️  RESEND_API_KEY not set in .env — skipping email.")
        return
    if not recipient:
        print("  ⚠️  ALERT_EMAIL not set in .env — skipping email.")
        return

    try:
        resp = requests.post(
            RESEND_API_URL,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "from":    "Vuln Agent <onboarding@resend.dev>",
                "to":      [recipient],
                "subject": subject,
                "html":    build_html_email(body),
                "text":    body,
            },
            timeout=20,
            verify=False,
        )
        resp.raise_for_status()
        email_id = resp.json().get("id", "unknown")
        print(f"  ✅ Email sent to {recipient}  (id: {email_id})")
    except requests.HTTPError as e:
        print(f"  ❌ Resend API error {e.response.status_code}: {e.response.text}")
    except Exception as e:
        print(f"  ❌ Email error: {e}")
