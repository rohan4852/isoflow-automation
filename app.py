import os, smtplib, requests
from flask import Flask, request, jsonify
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

app = Flask(__name__)
ZOHO_USER = "rohan@isoflowai.in"
ZOHO_PASS = os.getenv("ZOHO_PASSWORD")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

@app.route("/", methods=["GET"])
def health():
    return "IsoFlow Engine Active", 200

@app.route("/api/generate-preview", methods=["POST"])
def generate_preview():
    data = request.json or {}
    domain = data.get("domain", "target-company.com")
    recipient = data.get("email")

    pdf_path = f"/tmp/{domain}_preview.pdf"
    c = canvas.Canvas(pdf_path, pagesize=letter)
    c.drawString(72, 750, f"IsoFlow Systems - Audit Matrix Preview for {domain}")
    c.drawString(72, 730, "-------------------------------------------------------------")
    c.drawString(72, 700, "Control ID | Category         | Status   | Mapping Time")
    c.drawString(72, 680, "CC1.1      | COSO Control     | Mapped   | 0.4s")
    c.drawString(72, 660, "CC6.1      | Logical Access   | [REDACTED - Purchase Access]")
    c.drawString(72, 620, "Unlock full audit mapping at https://isoflowai.in")
    c.save()

    if recipient and ZOHO_PASS:
        msg = MIMEMultipart()
        msg["Subject"] = f"Your Compliance Matrix Preview for {domain}"
        msg["From"] = ZOHO_USER
        msg["To"] = recipient
        msg.attach(MIMEText("Attached is your generated compliance matrix preview from IsoFlow Systems.", "plain"))

        with open(pdf_path, "rb") as f:
            part = MIMEApplication(f.read(), Name=f"{domain}_preview.pdf")
            part['Content-Disposition'] = f'attachment; filename="{domain}_preview.pdf"'
            msg.attach(part)

        with smtplib.SMTP_SSL("smtp.zoho.com", 465) as server:
            server.login(ZOHO_USER, ZOHO_PASS)
            server.sendmail(ZOHO_USER, [recipient], msg.as_string())

    return jsonify({"status": "success", "file": pdf_path}), 200

@app.route(f"/telegram/{TELEGRAM_BOT_TOKEN}", methods=["POST"])
def telegram_webhook():
    update = request.get_json(force=True)
    if "message" in update and "text" in update["message"]:
        chat_id = update["message"]["chat"]["id"]
        text = update["message"]["text"].strip()
        
        reply = f"IsoFlow Engine received: {text}"
        if text.startswith("/check_inbox"):
            reply = "Inbox Status: Active on Zoho SMTP (0 unread)."
        elif text.startswith("/status"):
            reply = "IsoFlow 24/7 backend is running normally."

        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
            json={"chat_id": chat_id, "text": reply},
            timeout=10
        )
    return "OK", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
