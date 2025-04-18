from flask import Flask, render_template, request, session, redirect, url_for, jsonify
from flask_sqlalchemy import SQLAlchemy
import requests
from base64 import b64encode
from datetime import datetime
import os
from dotenv import load_dotenv
import uuid
import secrets

# ─── Setup ─────────────────────────────────────────────────────────────────────
app = Flask(__name__, template_folder='templates', static_folder='static')
app.secret_key = secrets.token_hex(16)
load_dotenv()

# Database Configuration
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL") 
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)

# Daraja (sandbox) endpoints & credentials
STK_PUSH_URL       = "https://sandbox.safaricom.co.ke/mpesa/stkpush/v1/processrequest"
CONSUMER_KEY       = os.getenv('CONSUMER_KEY')
CONSUMER_SECRET    = os.getenv('CONSUMER_SECRET')
BUSINESS_SHORTCODE = os.getenv('BUSINESS_SHORTCODE')
PASSKEY            = os.getenv('PASSKEY')

# Your public domain
BASE_URL    = os.getenv('BASE_URL') 
CALLBACK_ROUTE = "/mpesa_callback"
CALLBACK_URL   = f"{BASE_URL}{CALLBACK_ROUTE}"


# ─── Models ─────────────────────────────────────────────────────────────────────
class Payment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    checkout_id = db.Column(db.String(50), unique=True, nullable=False)
    status = db.Column(db.String(20), default="pending")  # pending, success, failed
    amount = db.Column(db.Float, nullable=True)


# ─── Application Context to Create Database ─────────────────────────────────────
# with app.app_context():
#     db.create_all()

# ─── User‑driven flow ─────────────────────────────────────────────────────────────
@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        session["name"]  = request.form["name"]
        session["phone"] = request.form["phone"]
        return redirect(url_for("message"))
    return render_template("index.html")

@app.route("/message", methods=["GET", "POST"])
def message():
    if request.method == "POST":
        session["note"] = request.form["note"]
        return redirect(url_for("gift"))
    return render_template("message.html")

@app.route("/gift")
def gift():
    # pull from session
    note = session.get("note", "")
    phone = session.get("phone", "")

    # your hidden backend WhatsApp number
    giftee_whatsapp_to = os.getenv("GIFTEE_WHATSAPP_TO")

    return render_template(
        "gift.html",
        note=note,
        phone=phone,
        giftee_whatsapp_to=giftee_whatsapp_to
    )


# ─── Kick off STK Push ────────────────────────────────────────────────────────────
@app.route("/process_payment", methods=["POST"])
def process_payment():
    amount = request.form["amount"]
    raw_phone = request.form.get("phone", "")
    phone = "254" + raw_phone.lstrip("0")

    # 1. Get OAuth token
    basic_auth = b64encode(f"{CONSUMER_KEY}:{CONSUMER_SECRET}".encode()).decode()
    token_r = requests.get(
        "https://sandbox.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials",
        headers={"Authorization": f"Basic {basic_auth}"}
    )
    access_token = token_r.json().get("access_token")

    # 2. Build payload
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    password = b64encode(f"{BUSINESS_SHORTCODE}{PASSKEY}{timestamp}".encode()).decode()

    payload = {
        "BusinessShortCode": BUSINESS_SHORTCODE,
        "Password": password,
        "Timestamp": timestamp,
        "TransactionType": "CustomerPayBillOnline",
        "Amount": str(int(amount)),
        "PartyA": phone,
        "PartyB": BUSINESS_SHORTCODE,
        "PhoneNumber": phone,
        "CallBackURL": CALLBACK_URL,
        "AccountReference": str(uuid.uuid4()),
        "TransactionDesc": "Birthday Gift"
    }

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    resp = requests.post(STK_PUSH_URL, json=payload, headers=headers)
    data = resp.json()

    if data.get("ResponseCode") == "0":
        checkout_id = data["CheckoutRequestID"]
        # Store in DB
        payment = Payment(checkout_id=checkout_id, status="pending")
        db.session.add(payment)
        db.session.commit()

        return render_template("pending.html", checkout_id=checkout_id)
    else:
        return redirect(url_for("error"))


# ─── Polling endpoint ────────────────────────────────────────────────────────────
@app.route("/payment_status/<checkout_id>")
def payment_status(checkout_id):
    payment = Payment.query.filter_by(checkout_id=checkout_id).first()
    if not payment:
        return jsonify(status="unknown"), 404
    return jsonify(status=payment.status, amount=payment.amount)


# ─── Safaricom webhook ───────────────────────────────────────────────────────────
@app.route(CALLBACK_ROUTE, methods=["POST"])
def mpesa_callback():
    data = request.get_json()
    stk = data["Body"]["stkCallback"]
    checkout_id = stk["CheckoutRequestID"]

    payment = Payment.query.filter_by(checkout_id=checkout_id).first()
    if not payment:
        return "", 404

    if stk["ResultCode"] == 0:
        amount = next(item["Value"] for item in stk["CallbackMetadata"]["Item"] if item["Name"] == "Amount")
        payment.status = "success"
        payment.amount = amount
    else:
        payment.status = "failed"

    db.session.commit()
    return "", 200


# ─── Final pages ─────────────────────────────────────────────────────────────────
@app.route("/success")
def success():
    return render_template("success.html", amount=request.args.get("amount"))

@app.route("/error")
def error():
    return render_template("error.html")


# ─── Run the app ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    app.run(debug=True)