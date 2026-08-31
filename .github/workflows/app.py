import os
import io
import base64
import traceback
import requests
from flask import Flask, request, jsonify, send_file
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

app = Flask(__name__)

BASE_URL = os.getenv("PUBLIC_BASE_URL", "https://isoflow-automation.onrender.com").rstrip("/")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
RESEND_API_KEY = os.getenv("RESEND_API_KEY", "").strip()

def build_pdf_bytes(domain):
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    c.drawString(72, 750, f"IsoFlow Systems - Compliance Mapping Preview for {domain}")
    c.drawString(72, 730, "-------------------------------------------------------------")
    c.drawString(72, 700, "Control ID | Framework     | Status   | Extraction Speed")
    c.drawString(72, 680, "CC1.1      | SOC 2 Type II | Mapped   | 0.38s")
    c.drawString(72, 660, "A.5.1      | ISO 27001     | Mapped   | 0.42s")
    c.drawString(72, 640, "CC6.1      | Access Ctrl   | [REDACTED - Purchase Access]")
    c.drawString(72, 600, "Unlock full audit mapping at https://isoflowai.in")
    c.showPage()
    c.save()
    buffer.seek(0)
    return buffer.getvalue()

def send_via_resend(recipient, domain, pdf_bytes):
    if not RESEND_API_KEY:
        return False, "RESEND_API_KEY not configured."

    pdf_base64 = base64.b64encode(pdf_bytes).decode("utf-8")
    
    headers = {
        "Authorization": f"Bearer {RESEND_API_KEY}",
        "Content-Type": "application/json"
    }
    
    # If using Resend default onboarding without domain verification yet: 'onboarding@resend.dev'
    # Once domain verified in Resend: 'rohan@isoflowai.in'
    from_address = os.getenv("RESEND_FROM_EMAIL", "IsoFlow Systems <onboarding@resend.dev>")

    payload = {
        "from": from_address,
        "to": [recipient],
        "subject": f"Your Compliance Matrix Preview for {domain}",
        "html": f"<p>Attached is your compliance preview for <strong>{domain}</strong>.</p><p>Explore full mapping at <a href='https://isoflowai.in'>isoflowai.in</a></p>",
        "attachments": [
            {
                "filename": f"{domain}_preview.pdf",
                "content": pdf_base64
            }
        ]
    }

    resp = requests.post("https://api.resend.com/emails", json=payload, headers=headers, timeout=10)
    if resp.status_code in [200, 201]:
        return True, "Delivered"
    return False, f"Resend error: {resp.status_code} - {resp.text}"

@app.route("/", methods=["GET"])
def health():
    return jsonify({
        "status": "active",
        "service": "IsoFlow Automation Engine",
        "resend_configured": bool(RESEND_API_KEY),
        "telegram_configured": bool(TELEGRAM_BOT_TOKEN)
    }), 200

@app.route("/api/download-preview", methods=["GET"])
def download_preview():
    domain = request.args.get("domain", "target-company.com").strip()
    pdf_bytes = build_pdf_bytes(domain)
    return send_file(
        io.BytesIO(pdf_bytes),
        as_attachment=True,
        download_name=f"{domain}_compliance_preview.pdf",
        mimetype="application/pdf"
    )

@app.route("/api/generate-preview", methods=["POST"])
def generate_preview():
    try:
        data = request.get_json(force=True, silent=True) or {}
        domain = data.get("domain", "stripe.com").strip()
        recipient = data.get("email", "rohan@isoflowai.in").strip()

        pdf_bytes = build_pdf_bytes(domain)
        email_sent, email_msg = send_via_resend(recipient, domain, pdf_bytes)

        return jsonify({
            "status": "success",
            "message": f"Compliance matrix generated for {domain}",
            "recipient": recipient,
            "email_status": "sent" if email_sent else "failed",
            "email_detail": email_msg,
            "download_url": f"{BASE_URL}/api/download-preview?domain={domain}"
        }), 200

    except Exception as e:
        return jsonify({"status": "error", "message": str(e), "trace": traceback.format_exc()}), 500

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
            if text.startswith("/status"):
                reply = "IsoFlow 24/7 backend is running normally on Render (Resend HTTPS Active)."
            elif text.startswith("/preview"):
                domain = text.replace("/preview", "").strip() or "stripe.com"
                reply = f"Generated preview for {domain}:\n{BASE_URL}/api/download-preview?domain={domain}"

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