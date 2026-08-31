import os
import io
import traceback
from urllib.parse import quote

import requests
from flask import Flask, request, jsonify, send_file
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

app = Flask(__name__)

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", "https://isoflow-automation.onrender.com").rstrip("/")


def build_pdf_buffer(domain):
    safe_domain = (domain or "target-company.com").strip() or "target-company.com"
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    c.drawString(72, 750, f"IsoFlow Systems - Compliance Mapping Preview for {safe_domain}")
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
        "service": "IsoFlow Engine 24/7",
        "telegram_configured": bool(TELEGRAM_BOT_TOKEN),
        "public_base_url": PUBLIC_BASE_URL,
    }), 200


@app.route("/api/download-preview", methods=["GET"])
def download_preview():
    domain = request.args.get("domain", "target-company.com").strip() or "target-company.com"
    return send_file(
        build_pdf_buffer(domain),
        as_attachment=True,
        download_name=f"{domain}_compliance_preview.pdf",
        mimetype="application/pdf"
    )


@app.route("/api/generate-preview", methods=["POST"])
def generate_preview():
    try:
        data = request.get_json(force=True, silent=True) or {}
        if isinstance(data, str):
            data = {"domain": data}

        domain = str(data.get("domain", "stripe.com") or "stripe.com").strip() or "stripe.com"
        recipient = str(data.get("email", "rohan@isoflowai.in") or "rohan@isoflowai.in").strip() or "rohan@isoflowai.in"

        build_pdf_buffer(domain)

        return jsonify({
            "status": "success",
            "message": f"Compliance matrix generated for {domain}",
            "recipient": recipient,
            "download_url": f"{PUBLIC_BASE_URL}/api/download-preview?domain={quote(domain)}",
        }), 200

    except Exception:
        return jsonify({"status": "error", "message": "Preview generation failed", "trace": traceback.format_exc()}), 500


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
                reply = "IsoFlow 24/7 backend is running normally."
            elif text.startswith("/preview"):
                domain = text.replace("/preview", "").strip() or "stripe.com"
                reply = f"Generated preview for {domain}:\n{PUBLIC_BASE_URL}/api/download-preview?domain={quote(domain)}"

            requests.post(
                f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
                json={"chat_id": chat_id, "text": reply},
                timeout=10
            )
    except Exception:
        traceback.print_exc()

    return "OK", 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")))