import os, smtplib, requests
from email.mime.text import MIMEText

ZOHO_USER = "rohan@isoflowai.in"
ZOHO_PASS = os.getenv("ZOHO_PASSWORD")
OPENROUTER_KEY = os.getenv("OPENROUTER_API_KEY")

TARGETS = [
    {"company": "Tailscale", "domain": "tailscale.com", "email": "security@tailscale.com"},
    {"company": "Supabase", "domain": "supabase.com", "email": "security@supabase.com"},
]

def generate_pitch(company_name, domain):
    prompt = f"Write a 3-sentence high-ticket B2B cold email to the CTO of {company_name} ({domain}). Pitch IsoFlow Systems (isoflowai.in), an engine that maps 90+ page policy PDFs to deterministic SOC 2 Type II and ISO 27001 matrices in under 12 seconds. Keep it strictly blunt, no fluff, ending with a low-friction call to review a sample mapping."
    headers = {
        "Authorization": f"Bearer {OPENROUTER_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "meta-llama/llama-3.3-70b-instruct:free",
        "messages": [{"role": "user", "content": prompt}]
    }
    res = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=payload, timeout=30)
    return res.json()["choices"][0]["message"]["content"].strip()

def send_mail(to_addr, body):
    msg = MIMEText(body, "plain")
    msg["Subject"] = "Automating your SOC 2 / ISO 27001 mapping bottleneck"
    msg["From"] = ZOHO_USER
    msg["To"] = to_addr
    with smtplib.SMTP_SSL("smtp.zoho.com", 465) as server:
        server.login(ZOHO_USER, ZOHO_PASS)
        server.sendmail(ZOHO_USER, [to_addr], msg.as_string())

if __name__ == "__main__":
    for target in TARGETS[:5]:
        try:
            pitch = generate_pitch(target["company"], target["domain"])
            send_mail(target["email"], pitch)
            print(f"Dispatched email to {target['email']}")
        except Exception as e:
            print(f"Error for {target['email']}: {e}")
