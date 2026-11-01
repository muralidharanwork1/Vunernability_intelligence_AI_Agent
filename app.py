"""
app.py — Autonomous Vulnerability Intelligence Agent.
- Runs every hour automatically via background scheduler
- Single-click manual trigger
- Supports Groq or Gemini (controlled by LLM_PROVIDER in .env)
- Optional email alerts (controlled by EMAIL_ALERT_ENABLED in .env)
"""

import io
import os
import time
import threading
import contextlib
from datetime import datetime, timedelta

import gradio as gr
import schedule
from dotenv import load_dotenv

from fetcher import fetch_vulnerabilities
from emailer import send_email_alert
from prompts import VULN_PROMPT

load_dotenv()


# ── Global agent state (shared between scheduler thread and UI) ───────────────

_state = {
    "status":       "⏳  Agent initializing — first run starting...",
    "digest":       "",
    "email_status": "",
    "last_run":     "Never",
    "next_run":     "—",
    "running":      False,
}
_lock = threading.Lock()


def _set(**kwargs):
    with _lock:
        _state.update(kwargs)


def _get():
    with _lock:
        return dict(_state)


# ── LLM router — picks Groq or Gemini from LLM_PROVIDER env ──────────────────

def _call_llm(prompt: str) -> str:
    provider = os.getenv("LLM_PROVIDER", "groq").lower()

    if provider == "gemini":
        from SimplerLLM.language.llm import LLM, LLMProvider
        api_key = os.getenv("GEMINI_API_KEY", "")
        if not api_key:
            raise ValueError("GEMINI_API_KEY not set. Add it in Settings or .env")
        llm = LLM.create(
            provider=LLMProvider.GEMINI,
            model_name="gemini-1.5-flash",
            api_key=api_key,
        )
        resp = llm.generate_response(model="gemini-1.5-flash", prompt=prompt, max_tokens=800)
        return resp.generated_text

    else:  # groq (default)
        from groq import Groq
        api_key = os.getenv("GROQ_API_KEY", "")
        if not api_key:
            raise ValueError("GROQ_API_KEY not set. Add it in Settings or .env")
        client = Groq(api_key=api_key)
        resp = client.chat.completions.create(
            model="openai/gpt-oss-120b",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=4000,
        )
        return resp.choices[0].message.content


# ── Core agent pipeline ───────────────────────────────────────────────────────

def run_agent_job():
    """Full pipeline: fetch vulnerabilities → AI analysis → optional email."""
    if _get()["running"]:
        return  # prevent overlapping runs

    provider = os.getenv("LLM_PROVIDER", "groq").upper()
    _set(running=True, status=f"📡  [{provider}] Fetching vulnerabilities from NVD · CISA · Exploit-DB...")

    try:
        # Step 1: Fetch
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            vulns = fetch_vulnerabilities()

        if not vulns:
            _set(status="⚠️  No vulnerabilities fetched — check network.", running=False)
            return

        nvd_count   = sum(1 for v in vulns if "[CVE-"     in v and "[CISA" not in v and "[Exploit" not in v)
        cisa_count  = sum(1 for v in vulns if "[CISA-KEV]" in v)
        edb_count   = sum(1 for v in vulns if "[ExploitDB]" in v)

        _set(status=(
            f"🧠  [{provider}] Analyzing {len(vulns)} vulnerabilities "
            f"({nvd_count} NVD · {cisa_count} CISA · {edb_count} ExploitDB)..."
        ))

        # Step 2: AI Analysis
        vuln_text = "\n".join(f"- {v}" for v in vulns[:10])
        prompt    = VULN_PROMPT.format(vulnerabilities=vuln_text)
        digest    = _call_llm(prompt)

        now_str  = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        next_str = (datetime.now() + timedelta(hours=1)).strftime("%H:%M:%S")

        # Step 3: Email (if enabled)
        email_msg = ""
        if os.getenv("EMAIL_ALERT_ENABLED", "false").lower() == "true":
            _set(status="📧  Sending email alert...")
            eb = io.StringIO()
            with contextlib.redirect_stdout(eb):
                send_email_alert(
                    subject=f"🔐 Vulnerability Digest — {now_str}",
                    body=digest,
                )
            email_msg = eb.getvalue().strip() or "✅  Email sent."
        else:
            email_msg = "📭  Email alerts off  (set EMAIL_ALERT_ENABLED=true in Settings to enable)"

        _set(
            running=False,
            digest=digest,
            email_status=email_msg,
            last_run=now_str,
            next_run=next_str,
            status=(
                f"✅  Done  |  Provider: {provider}  |  "
                f"Vulns: {len(vulns)}  |  Last run: {now_str}  |  Next: ~{next_str}"
            ),
        )

    except Exception as exc:
        _set(running=False, status=f"❌  Agent error: {exc}")


# ── Background scheduler (runs every hour, also fires immediately on start) ───

def _scheduler_loop():
    run_agent_job()
    schedule.every(1).hours.do(run_agent_job)
    while True:
        schedule.run_pending()
        time.sleep(30)


threading.Thread(target=_scheduler_loop, daemon=True).start()


# ── Settings helpers ──────────────────────────────────────────────────────────

def save_settings(provider, groq_key, gemini_key, email_enabled,
                  resend_key, alert_email):
    env_path = os.path.join(os.path.dirname(__file__), ".env")
    lines = [
        f"LLM_PROVIDER={provider.lower()}",
        f"GROQ_API_KEY={groq_key.strip()}",
        f"GEMINI_API_KEY={gemini_key.strip()}",
        f"EMAIL_ALERT_ENABLED={'true' if email_enabled else 'false'}",
        f"RESEND_API_KEY={resend_key.strip()}",
        f"ALERT_EMAIL={alert_email.strip()}",
    ]
    with open(env_path, "w") as f:
        f.write("\n".join(lines) + "\n")
    for k, v in zip(
        ["LLM_PROVIDER", "GROQ_API_KEY", "GEMINI_API_KEY", "EMAIL_ALERT_ENABLED",
         "RESEND_API_KEY", "ALERT_EMAIL"],
        [provider.lower(), groq_key.strip(), gemini_key.strip(),
         "true" if email_enabled else "false",
         resend_key.strip(), alert_email.strip()],
    ):
        os.environ[k] = v
    return "✅  Settings saved to .env"


# ── UI ────────────────────────────────────────────────────────────────────────

CSS = """
.status-box textarea { font-family: monospace; font-size: 13px; }
.digest-box textarea { font-family: monospace; font-size: 13px; white-space: pre-wrap; line-height: 1.6; }
.email-box  textarea { font-family: monospace; font-size: 12px; color: #6b7280; }
h1 { color: #3b82f6 !important; }
"""

with gr.Blocks(
    title="Vulnerability Intelligence Agent",
    theme=gr.themes.Soft(primary_hue="blue", neutral_hue="slate"),
    css=CSS,
) as demo:

    gr.Markdown(
        "# 🔐 Vulnerability Intelligence Agent\n"
        "Autonomous hourly security digest · Sources: **NIST NVD** · **CISA KEV** · **Exploit-DB** · "
        "Providers: **Groq** / **Gemini**"
    )

    with gr.Tabs():

        # ── Tab 1: Agent Dashboard ────────────────────────────────────────────
        with gr.Tab("🤖 Agent"):
            run_btn    = gr.Button("🚀 Run Agent Now", variant="primary")
            status_box = gr.Textbox(label="Agent Status",     interactive=False, elem_classes="status-box")
            digest_box = gr.Textbox(label="AI Security Digest", lines=28, interactive=False, elem_classes="digest-box")
            email_box  = gr.Textbox(label="Email Status",     interactive=False, elem_classes="email-box")

        # ── Tab 2: Settings ───────────────────────────────────────────────────
        with gr.Tab("⚙️ Settings"):

            gr.Markdown("### LLM Provider")
            gr.Markdown(
                "**Groq** — free, fast (get key at [console.groq.com](https://console.groq.com))  \n"
                "**Gemini** — free tier (get key at [aistudio.google.com](https://aistudio.google.com))"
            )
            provider_in   = gr.Radio(
                choices=["groq", "gemini"],
                label="Active Provider",
                value=os.getenv("LLM_PROVIDER", "groq"),
            )
            groq_key_in   = gr.Textbox(label="Groq API Key",   placeholder="gsk_...",  type="password", value=os.getenv("GROQ_API_KEY", ""))
            gemini_key_in = gr.Textbox(label="Gemini API Key", placeholder="AIza...", type="password", value=os.getenv("GEMINI_API_KEY", ""))

            gr.Markdown("### Email Alerts  (via Resend — works on any network)")
            gr.Markdown("Get a free Resend key at [resend.com](https://resend.com) → API Keys")
            email_toggle_in = gr.Checkbox(
                label="Enable Email Alerts  (EMAIL_ALERT_ENABLED)",
                value=os.getenv("EMAIL_ALERT_ENABLED", "false").lower() == "true",
            )
            resend_key_in  = gr.Textbox(label="Resend API Key",  placeholder="re_...",                 type="password", value=os.getenv("RESEND_API_KEY", ""))
            alert_email_in = gr.Textbox(label="Alert Recipient", placeholder="recipient@example.com",               value=os.getenv("ALERT_EMAIL", ""))

            save_btn    = gr.Button("💾 Save Settings", variant="primary")
            save_status = gr.Textbox(label="", interactive=False)

    # ── Polling timer — refreshes UI from shared state every 5 seconds ────────
    timer = gr.Timer(5)

    def _poll():
        s = _get()
        return s["status"], s["digest"], s["email_status"]

    timer.tick(fn=_poll, outputs=[status_box, digest_box, email_box])

    # ── Manual run button ─────────────────────────────────────────────────────
    def _trigger():
        if _get()["running"]:
            return "⏳  Agent is already running — please wait..."
        threading.Thread(target=run_agent_job, daemon=True).start()
        return "🚀  Agent triggered — fetching data..."

    run_btn.click(fn=_trigger, outputs=[status_box])

    # ── Save settings ─────────────────────────────────────────────────────────
    save_btn.click(
        fn=save_settings,
        inputs=[provider_in, groq_key_in, gemini_key_in, email_toggle_in,
                resend_key_in, alert_email_in],
        outputs=[save_status],
    )


if __name__ == "__main__":
    demo.launch(inbrowser=True)
