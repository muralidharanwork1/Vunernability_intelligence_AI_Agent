"""
fetcher.py — Pulls vulnerabilities from FREE public sources.
No API key needed for any of these.
"""

import requests
import feedparser
from datetime import datetime, timedelta, timezone


# ── Source 1: NIST NVD REST API (Official US Gov CVE database) ─────────────
def fetch_nvd_cves(days_back: int = 1) -> list[str]:
    """Fetch CVEs published in the last N days from NIST NVD."""
    now = datetime.now(timezone.utc)
    start = now - timedelta(days=days_back)
    fmt = "%Y-%m-%dT%H:%M:%S.000"

    url = "https://services.nvd.nist.gov/rest/json/cves/2.0"
    params = {
        "pubStartDate": start.strftime(fmt),
        "pubEndDate": now.strftime(fmt),
        "resultsPerPage": 10,
    }

    try:
        resp = requests.get(url, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        results = []
        for item in data.get("vulnerabilities", []):
            cve = item["cve"]
            cve_id = cve["id"]
            desc = cve["descriptions"][0]["value"][:250]
            severity = "N/A"
            try:
                severity = cve["metrics"]["cvssMetricV31"][0]["cvssData"]["baseSeverity"]
            except (KeyError, IndexError):
                pass
            results.append(f"[{cve_id}] Severity: {severity} — {desc}")
        return results
    except Exception as e:
        print(f"  ⚠️  NVD API error: {e}")
        return []


# ── Source 2: Exploit-DB RSS Feed ──────────────────────────────────────────
def fetch_exploitdb() -> list[str]:
    """Fetch latest exploits from Exploit-DB RSS."""
    try:
        feed = feedparser.parse("https://www.exploit-db.com/rss.xml")
        return [f"[ExploitDB] {e.title}" for e in feed.entries[:5]]
    except Exception as e:
        print(f"  ⚠️  ExploitDB error: {e}")
        return []


# ── Source 3: CISA Known Exploited Vulnerabilities (KEV) ───────────────────
def fetch_cisa_kev() -> list[str]:
    """Fetch CISA's actively exploited vulnerability catalog."""
    try:
        url = "https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json"
        resp = requests.get(url, timeout=15)
        data = resp.json()
        # Get 5 most recently added
        vulns = sorted(
            data.get("vulnerabilities", []),
            key=lambda x: x.get("dateAdded", ""),
            reverse=True
        )[:5]
        return [
            f"[CISA-KEV] {v['cveID']} — {v['vulnerabilityName']}: {v['shortDescription'][:150]}"
            for v in vulns
        ]
    except Exception as e:
        print(f"  ⚠️  CISA KEV error: {e}")
        return []


# ── Combined Fetch ──────────────────────────────────────────────────────────
def fetch_vulnerabilities() -> list[str]:
    """Aggregate from all sources and return combined list."""
    print("  → Fetching from NIST NVD...")
    nvd = fetch_nvd_cves(days_back=1)

    print("  → Fetching from CISA KEV...")
    cisa = fetch_cisa_kev()

    print("  → Fetching from Exploit-DB...")
    edb = fetch_exploitdb()

    combined = nvd + cisa + edb
    print(f"  ✅ Total fetched: {len(combined)} vulnerabilities")
    return combined
