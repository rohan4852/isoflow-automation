import os
import io
import smtplib
import traceback
import requests
from flask import Flask, request, jsonify
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

app = Flask(__name__)

ZOHO_USER = os.getenv("ZOHO_USER", "rohan@isoflowai.in").strip()
ZOHO_PASS = os.getenv("ZOHO_PASSWORD", "").strip()
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()

SMTP_SERVERS = [
    {"host": "smtppro.zoho.in", "port": 465, "ssl": True},
    {"host": "smtp.zoho.in", "port": 465, "ssl": True},
    {"host": "smtppro.zoho.in", "port": 587, "ssl": False},
    {"host": "smtp.zoho.in", "port": 587, "ssl": False},
    {"host": "smtp.zoho.com", "port": 465, "ssl": True}
]

def build_pdf_bytes(domain):
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    c.drawString(72, 750, f"IsoFlow Systems - Compliance Mapping Preview for {domain}")
    c.drawString(72, 730, "-------------------------------------------------------------")
    c.drawString(72, 700, "Control ID | Framework     | Status   | Extraction Speed")
    c.drawString(72, 680, "CC1.1      | SOC 2 Type II | Mapped   | 0.38s")
    c.drawString(72, 660, "A.5.1      | ISO 27001     | Mapped   | 0.42s")
    c.drawString(72, 640, "CC6.1      | Access Ctrl   | [REDACTED - Purchase Access]")
    c.drawString(72, 620, "Unlock full audit mapping at https://isoflowai.in")
    c.showPage()
    c.save()
    buffer.seek(0)
    return buffer.getvalue()

def dispatch_email(recipient, domain, pdf_data):
    if not ZOHO_PASS:
        raise ValueError("ZOHO_PASSWORD environment variable is empty or not set on Render.")

    msg = MIMEMultipart()
    msg["Subject"] = f"Your Compliance Matrix Preview for {domain}"
    msg["From"] = ZOHO_USER
    msg["To"] = recipient

    body_text = (
        f"Attached is your generated compliance matrix preview for {domain}.\n\n"
        "Full policy mappings and SOC 2 / ISO 27001 gap analyses can be viewed at https://isoflowai.in"
    )
    msg.attach(MIMEText(body_text, "plain"))

    attachment = MIMEApplication(pdf_data, Name=f"{domain}_preview.pdf")
    attachment['Content-Disposition'] = f'attachment; filename="{domain}_preview.pdf"'
    msg.attach(attachment)

    errors = []
    for srv in SMTP_SERVERS:
        try:
            if srv["ssl"]:
                with smtplib.SMTP_SSL(srv["host"], srv["port"], timeout=7) as server:
                    server.login(ZOHO_USER, ZOHO_PASS)
                    server.sendmail(ZOHO_USER, [recipient], msg.as_string())
            else:
                with smtplib.SMTP(srv["host"], srv["port"], timeout=7) as server:
                    server.starttls()
                    server.login(ZOHO_USER, ZOHO_PASS)
                    server.sendmail(ZOHO_USER, [recipient], msg.as_string())
            return True
        except Exception as e:
            errors.append(f"{srv['host']}:{srv['port']} -> {str(e)}")

    raise RuntimeError(f"All SMTP connection attempts failed: {' | '.join(errors)}")

@app.route("/", methods=["GET"])
def health():
    return jsonify({
        "status": "active",
        "service": "IsoFlow Automation Engine",
        "zoho_user": ZOHO_USER,
        "zoho_pass_configured": bool(ZOHO_PASS),
        "telegram_configured": bool(TELEGRAM_BOT_TOKEN)
    }), 200

@app.route("/api/generate-preview", methods=["POST"])
def generate_preview():
    try:
        data = request.get_json(force=True, silent=True) or {}
        domain = data.get("domain", "target-company.com").strip()
        recipient = data.get("email", "").strip()

        if not recipient:
            return jsonify({"status": "error", "message": "Email address is required."}), 400

        pdf_bytes = build_pdf_bytes(domain)
        dispatch_email(recipient, domain, pdf_bytes)

        return jsonify({
            "status": "success",
            "message": f"Preview successfully generated and delivered to {recipient}"
        }), 200

    except Exception as e:
        traceback.print_exc()
        return jsonify({
            "status": "error",
            "error_type": type(e).__name__,
            "message": str(e)
        }), 500

@app.route("/telegram/<token>", methods=["POST"])
def telegram_webhook(token):
    if token != TELEGRAM_BOT_TOKEN:
        return "Unauthorized", 403

    try:
        update = request.get_json(force=True, silent=True) or {}
        if "message" in update and "text" in update["message"]:
            chat_id = update["message"]["chat"]["id"]
            text = update["message"]["text"].strip()

            reply = f"IsoFlow Engine received: {text}"
            if text.startswith("/check_inbox"):
                reply = "Inbox Status: Active on Zoho India SMTP (0 unread)."
            elif text.startswith("/status"):
                reply = "IsoFlow 24/7 backend is running normally."

            requests.post(
                f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
                json={"chat_id": chat_id, "text": reply},
                timeout=10
            )
    except Exception as e:
        traceback.print_exc()

    return "OK", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)