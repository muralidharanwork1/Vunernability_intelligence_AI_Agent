# 🔐 Vulnerability Intelligence Agent

An autonomous AI agent built with **SimplerLLM + Gemini Free API** that:
- 🔍 Searches NIST NVD, CISA KEV, and Exploit-DB for new CVEs daily
- 🧠 Analyzes and summarizes them using Gemini LLM
- 📧 Emails you a clean, actionable digest every morning
- ☁️ Runs free on GitHub Actions (no server needed)

---

## 🏗️ Architecture

```
[GitHub Actions Scheduler]
         ↓
   [fetcher.py]  ←── NIST NVD API (free)
         |       ←── CISA KEV Feed (free)
         |       ←── Exploit-DB RSS (free)
         ↓
   [agent.py]   ←── SimplerLLM + Gemini Flash (free)
         ↓
  [emailer.py]  ──→ Gmail SMTP (free)
         ↓
    📧 Your Inbox
```

---

## ⚡ Quick Start (Local)

```bash
# 1. Clone the repo
git clone https://github.com/YOUR_USERNAME/vuln-agent
cd vuln-agent

# 2. Install dependencies
pip install -r requirements.txt

# 3. Set up environment
cp .env.example .env
# Edit .env and add your keys

# 4. Test run immediately
RUN_NOW=true python agent.py
```

---

## 🔑 Free API Keys Setup

### Gemini (LLM) — 1500 requests/day free
1. Go to [aistudio.google.com](https://aistudio.google.com)
2. Click **"Get API Key"**
3. Copy key → paste in `.env` as `GEMINI_API_KEY`

### Gmail App Password (Email alerts) — free
1. Enable **2FA** on your Google account
2. Go to **Google Account → Security → App Passwords**
3. Generate password for "Mail"
4. Paste in `.env` as `GMAIL_APP_PASSWORD`

---

## ☁️ GitHub Actions Deployment (Free, Global)

1. Push this repo to GitHub
2. Go to **Settings → Secrets and Variables → Actions**
3. Add these secrets:
   - `GEMINI_API_KEY`
   - `GMAIL_ADDRESS`
   - `GMAIL_APP_PASSWORD`
   - `ALERT_EMAIL`
4. The agent runs automatically Mon–Fri at 8 AM UTC

**Manual trigger:** Go to Actions tab → "Daily Vulnerability Digest" → "Run workflow"

---

## 📁 Project Structure

```
vuln-agent/
├── agent.py          # Main orchestrator
├── fetcher.py        # CVE data from 3 free sources
├── emailer.py        # Gmail SMTP alert sender
├── prompts.py        # LLM prompt templates
├── requirements.txt
├── .env.example      # Template — copy to .env
└── .github/
    └── workflows/
        └── run_agent.yml  # GitHub Actions schedule
```

---

## 🛠️ Tech Stack

| Component | Tool | Cost |
|-----------|------|------|
| LLM Framework | SimplerLLM | Free |
| AI Model | Google Gemini 1.5 Flash | Free (1500/day) |
| CVE Source 1 | NIST NVD REST API | Free |
| CVE Source 2 | CISA KEV Feed | Free |
| CVE Source 3 | Exploit-DB RSS | Free |
| Email | Gmail SMTP | Free |
| Hosting | GitHub Actions | Free (2000 min/month) |

**Total cost: $0**

---

## 🔄 Swap LLM Provider (SimplerLLM advantage)

```python
# In agent.py — change just this one line:

# Gemini (default)
llm = LLM.create(provider=LLMProvider.GEMINI, model_name="gemini-1.5-flash", ...)

# Groq (faster, 14,400 free req/day)
llm = LLM.create(provider=LLMProvider.GROQ, model_name="llama3-8b-8192", ...)

# OpenAI
llm = LLM.create(provider=LLMProvider.OPENAI, model_name="gpt-4o-mini", ...)
```

---


