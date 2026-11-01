"""
Vulnerability Intelligence Agent
Uses SimplerLLM + Gemini Free API to search CVEs and email a daily digest.
"""

import os
import schedule
import time
from dotenv import load_dotenv
from SimplerLLM.language.llm import LLM, LLMProvider
from fetcher import fetch_vulnerabilities
from emailer import send_email_alert
from prompts import VULN_PROMPT

load_dotenv()

# ── LLM Setup ─────────────────────────────────────────────────────────────────
# Swap provider here freely: GEMINI / GROQ / OPENAI
llm = LLM.create(
    provider=LLMProvider.GEMINI,
    model_name="gemini-1.5-flash",
    api_key=os.getenv("GEMINI_API_KEY")
)

def run_agent():
    print("\n🔍 [Agent] Fetching latest vulnerabilities...")
    vulns = fetch_vulnerabilities()

    if not vulns:
        print("⚠️  No vulnerabilities fetched. Check your network.")
        return

    # Build the prompt with fetched data
    vuln_text = "\n".join([f"- {v}" for v in vulns[:8]])
    prompt = VULN_PROMPT.format(vulnerabilities=vuln_text)

    print("🧠 [Agent] Analyzing with Gemini LLM...")
    response = llm.generate_response(
        model="gemini-1.5-flash",
        prompt=prompt,
        max_tokens=800
    )

    summary = response.generated_text

    print("\n" + "="*60)
    print("📋 VULNERABILITY DIGEST")
    print("="*60)
    print(summary)
    print("="*60 + "\n")

    # Send email alert
    print("📧 [Agent] Sending email alert...")
    send_email_alert(subject="🔐 Daily Vulnerability Digest", body=summary)
    print("✅ [Agent] Done! Email sent.\n")

if __name__ == "__main__":
    print("🤖 Vulnerability Agent Starting...")
    print("📅 Scheduled: runs every day at 08:00 AM")
    print("   (Press Ctrl+C to stop | run once now? → set RUN_NOW=true in .env)\n")

    # Run immediately if RUN_NOW=true
    if os.getenv("RUN_NOW", "false").lower() == "true":
        run_agent()

    # Daily schedule
    schedule.every().day.at("08:00").do(run_agent)

    while True:
        schedule.run_pending()
        time.sleep(30)
