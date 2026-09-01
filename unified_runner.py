import threading
import time
import requests
import os
import outreach_engine
import content_engine

PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", "https://isoflow-automation.onrender.com").rstrip("/")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "").strip()

def run_health_check():
    print(f"[{time.strftime('%X')}] Running Health Audit Task...")
    try:
        r = requests.get(f"{PUBLIC_BASE_URL}/", timeout=10)
        print(f"[HEALTH CHECK] Render responded: {r.status_code}")
    except Exception as e:
        print(f"[HEALTH ALERT] Render unreachable: {e}")

def run_task(name, func):
    print(f"[{time.strftime('%X')}] Starting {name}...")
    try:
        func()
        print(f"[{time.strftime('%X')}] Finished {name}.")
    except Exception as e:
        print(f"[ERROR in {name}]: {e}")

def run_all():
    threads = [
        threading.Thread(target=run_task, args=("Outreach Engine", outreach_engine.run)),
        threading.Thread(target=run_task, args=("Content Engine", content_engine.run)),
        threading.Thread(target=run_health_check),
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    print(f"[{time.strftime('%X')}] All parallel tasks completed.")

if __name__ == "__main__":
    run_all()
