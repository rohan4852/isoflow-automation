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

@app.route("/", methods=["GET"])
def health():
    return jsonify({
        "status": "active",
        "service": "IsoFlow Automation Engine",
        "zoho_user": ZOHO_USER,
        "zoho_pass_configured": bool(ZOHO_PASS),
        "telegram_configured": bool(TELEGRAM_BOT_TOKEN)
    }), 200

# DIAGNOSTIC ROUTE: Explicitly tests SMTP connection to reveal root cause
@app.route("/api/test-zoho", methods=["GET"])
def test_zoho():
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
        domain = data.get("domain", "stripe.com").strip()
        recipient = data.get("email", ZOHO_USER).strip()

        # 1. Build PDF in memory
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
        pdf_data = buffer.getvalue()

        # 2. Email payload
        msg = MIMEMultipart()
        msg["Subject"] = f"Your Compliance Matrix Preview for {domain}"
        msg["From"] = ZOHO_USER
        msg["To"] = recipient
        msg.attach(MIMEText(f"Attached is your generated compliance matrix preview for {domain}.", "plain"))

        part = MIMEApplication(pdf_data, Name=f"{domain}_preview.pdf")
        part['Content-Disposition'] = f'attachment; filename="{domain}_preview.pdf"'
        msg.attach(part)

        # 3. Direct dispatch via standard Zoho India SMTP
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
            except Exception as e:
                last_error = f"{host}:{port} -> {str(e)}"

        if not sent:
            return jsonify({"status": "error", "error": last_error}), 500

        return jsonify({"status": "success", "message": f"Delivered to {recipient}"}), 200

    except Exception as e:
        return jsonify({"status": "error", "message": str(e), "trace": traceback.format_exc()}), 500

@app.route("/telegram/<token>", methods=["POST"])
def telegram_webhook(token):
    if token != TELEGRAM_BOT_TOKEN:
        return "Unauthorized", 403
    return "OK", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
