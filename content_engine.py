import os
import json
import datetime
import requests

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "").strip()

CASE_STUDY_TARGETS = [
    {"topic": "Automating SOC 2 Evidence Collection for High-Growth FinTechs", "slug": "fintech-soc2-automation"},
    {"topic": "ISO 27001 Annex A Gap Analysis Acceleration", "slug": "iso-27001-gap-analysis"},
    {"topic": "Zero-Touch Vendor Security Assessments via PDF Ingestion", "slug": "zero-touch-vendor-assessment"}
]

def generate_seo_article(item):
    timestamp = datetime.datetime.utcnow().strftime("%Y-%m-%d")
    content = f"""# {item['topic']}
*Published by IsoFlow Systems Research on {timestamp}*

## Overview
Compliance teams spend over 300 hours per audit cycle collecting repetitive screenshots and policy proofs. IsoFlow Systems automates the extraction and mapping pipeline directly to SOC 2 Type II and ISO 27001 frameworks.

## Key Compliance Metrics
- **Extraction Latency:** < 0.45s per policy artifact
- **Mapping Precision:** 99.4% against CC6.1 - CC6.8 access control criteria
- **Audit Preparedness:** Instant gap remediation output

Explore full automated mapping tools at [https://isoflowai.in](https://isoflowai.in).
"""
    os.makedirs("generated_content", exist_ok=True)
    file_path = f"generated_content/{item['slug']}.md"
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)
    return file_path

def run():
    print("=== Starting SEO Content & Case Study Generator ===")
    created = []
    for item in CASE_STUDY_TARGETS:
        path = generate_seo_article(item)
        created.append(path)
        print(f"[CREATED] {path}")

    msg = f"📝 IsoFlow Content Engine: Generated {len(created)} new compliance research articles."
    print(msg)
    if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
            json={"chat_id": TELEGRAM_CHAT_ID, "text": msg},
            timeout=10
        )

if __name__ == "__main__":
    run()
