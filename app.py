import os
import io
import smtplib
import traceback
from urllib.parse import quote

import requests
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from flask import Flask, request, jsonify, send_file
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

app = Flask(__name__)

ZOHO_USER = os.getenv("ZOHO_USER", "rohan@isoflowai.in").strip()
ZOHO_PASS = os.getenv("ZOHO_PASSWORD", "").strip()
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
        "service": "IsoFlow Automation Engine",
        "zoho_user": ZOHO_USER,
        "zoho_pass_configured": bool(ZOHO_PASS),
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


@app.route("/api/test-zoho", methods=["GET"])
def test_zoho():
    if not ZOHO_USER or not ZOHO_PASS:
        return jsonify({
            "zoho_user": ZOHO_USER,
            "password_length": len(ZOHO_PASS),
            "diagnostics": {"status": "not_configured", "message": "ZOHO_USER / ZOHO_PASSWORD are not set."}
        }), 200

    results = {}
    servers = [
        ("smtppro.zoho.in", 465, True),
        ("smtp.zoho.in", 465, True),
        ("smtppro.zoho.in", 587, False),
        ("smtp.zoho.in", 587, False),
        ("smtp.zoho.com", 465, True)
    ]

    for host, port, ssl_mode in servers:
        key = f"{host}:{port} (SSL: {ssl_mode})"
        try:
            if ssl_mode:
                server = smtplib.SMTP_SSL(host, port, timeout=5)
            else:
                server = smtplib.SMTP(host, port, timeout=5)
                server.starttls()

            server.login(ZOHO_USER, ZOHO_PASS)
            server.quit()
            results[key] = "SUCCESS: Authentication passed"
        except Exception as e:
            results[key] = f"FAILED: {type(e).__name__} - {str(e)}"

    return jsonify({
        "zoho_user": ZOHO_USER,
        "password_length": len(ZOHO_PASS),
        "diagnostics": results
    }), 200


@app.route("/api/generate-preview", methods=["POST"])
def generate_preview():
    try:
        data = request.get_json(force=True, silent=True) or {}
        if isinstance(data, str):
            data = {"domain": data}

        domain = str(data.get("domain", "stripe.com") or "stripe.com").strip() or "stripe.com"
        recipient = str(data.get("email", ZOHO_USER or "rohan@isoflowai.in") or "rohan@isoflowai.in").strip() or "rohan@isoflowai.in"

        build_pdf_buffer(domain)

        response = {
            "status": "success",
            "message": f"Compliance matrix generated for {domain}",
            "recipient": recipient,
            "download_url": f"{PUBLIC_BASE_URL}/api/download-preview?domain={quote(domain)}",
        }

        if ZOHO_USER and ZOHO_PASS:
            pdf_buffer = build_pdf_buffer(domain)
            pdf_data = pdf_buffer.getvalue()
            msg = MIMEMultipart()
            msg["Subject"] = f"Your Compliance Matrix Preview for {domain}"
            msg["From"] = ZOHO_USER
            msg["To"] = recipient
            msg.attach(MIMEText(f"Attached is your generated compliance matrix preview for {domain}.", "plain"))

            part = MIMEApplication(pdf_data, Name=f"{domain}_preview.pdf")
            part['Content-Disposition'] = f'attachment; filename="{domain}_preview.pdf"'
            msg.attach(part)

            sent = False
            last_error = ""
            for host, port, use_ssl in [("smtppro.zoho.in", 465, True), ("smtp.zoho.in", 465, True), ("smtp.zoho.in", 587, False)]:
                try:
                    if use_ssl:
                        with smtplib.SMTP_SSL(host, port, timeout=6) as server:
                            server.login(ZOHO_USER, ZOHO_PASS)
                            server.sendmail(ZOHO_USER, [recipient], msg.as_string())
                    else:
                        with smtplib.SMTP(host, port, timeout=6) as server:
                            server.starttls()
                            server.login(ZOHO_USER, ZOHO_PASS)
                            server.sendmail(ZOHO_USER, [recipient], msg.as_string())
                    sent = True
                    break
                except Exception as exc:
                    last_error = f"{host}:{port} -> {exc}"

            if sent:
                response["email_status"] = "delivered"
                response["message"] = f"Compliance matrix generated and emailed to {recipient}"
            else:
                response["email_status"] = "failed"
                response["smtp_error"] = last_error
                response["message"] = f"Compliance matrix generated for {domain}; email delivery failed."
        else:
            response["email_status"] = "not_configured"
            response["message"] = f"Compliance matrix generated for {domain}"

        return jsonify(response), 200

    except Exception as exc:
        return jsonify({
            "status": "error",
            "message": "Preview generation failed",
            "details": str(exc),
            "trace": traceback.format_exc(),
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
