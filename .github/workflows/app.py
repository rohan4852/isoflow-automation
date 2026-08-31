import os
import io
import traceback
import requests
from flask import Flask, request, jsonify, send_file
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

app = Flask(__name__)

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()

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
    return buffer

@app.route("/", methods=["GET"])
def health():
    return jsonify({
        "status": "active",
        "service": "IsoFlow Automation Engine",
        "telegram_configured": bool(TELEGRAM_BOT_TOKEN)
    }), 200

# Download PDF directly over HTTPS (bypasses all email port blocks)
@app.route("/api/download-preview", methods=["GET"])
def download_preview():
    domain = request.args.get("domain", "target-company.com").strip()
    pdf_buffer = build_pdf_bytes(domain)
    return send_file(
        pdf_buffer,
        as_attachment=True,
        download_name=f"{domain}_compliance_preview.pdf",
        mimetype="application/pdf"
    )

# Lead-magnet endpoint returning preview status & direct download link
@app.route("/api/generate-preview", methods=["POST"])
def generate_preview():
    try:
        data = request.get_json(force=True, silent=True) or {}
        domain = data.get("domain", "stripe.com").strip()
        recipient = data.get("email", "rohan@isoflowai.in").strip()

        # Generate in-memory preview
        _ = build_pdf_bytes(domain)

        return jsonify({
            "status": "success",
            "message": f"Compliance matrix generated for {domain}",
            "recipient": recipient,
            "download_url": f"https://isoflow-automation.onrender.com/api/download-preview?domain={domain}"
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
                reply = "IsoFlow 24/7 backend is running normally on Render."
            elif text.startswith("/preview"):
                domain = text.replace("/preview", "").strip() or "stripe.com"
                reply = f"Generated preview for {domain}: https://isoflow-automation.onrender.com/api/download-preview?domain={domain}"

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