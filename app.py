from flask import Flask, render_template, request, session, redirect, url_for, jsonify
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

# Daraja (sandbox) endpoints & credentials
STK_PUSH_URL       = "https://sandbox.safaricom.co.ke/mpesa/stkpush/v1/processrequest"
CONSUMER_KEY       = os.getenv('CONSUMER_KEY')
CONSUMER_SECRET    = os.getenv('CONSUMER_SECRET')
BUSINESS_SHORTCODE = os.getenv('BUSINESS_SHORTCODE')
PASSKEY            = os.getenv('PASSKEY')


BASE_URL = os.getenv('BASE_URL')  
CALLBACK_ROUTE = "/mpesa_callback"
CALLBACK_URL = f"{BASE_URL}{CALLBACK_ROUTE}"


# ─── Routes for user flow ───────────────────────────────────────────────────────
@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        session["name"] = request.form["name"]
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
    return render_template("gift.html")


# ─── STK Push initiation ────────────────────────────────────────────────────────
@app.route("/process_payment", methods=["POST"])
def process_payment():
    # Gather form data
    amount = request.form["amount"]
    raw_phone = request.form.get("phone", "")
    phone = "254" + raw_phone.lstrip("0")  # ensure in 2547XXXXXXXX format

    # 1. Get OAuth token
    basic_auth = b64encode(f"{CONSUMER_KEY}:{CONSUMER_SECRET}".encode()).decode()
    token_resp = requests.get(
        "https://sandbox.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials",
        headers={"Authorization": f"Basic {basic_auth}"}
    )
    access_token = token_resp.json().get("access_token")

    # 2. Build STK Push payload
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

    print("M-Pesa Response Status:", resp.status_code)
    print("M-Pesa Response Content:", resp.text)

    if data.get("ResponseCode") == "0":
        session["CheckoutRequestID"] = data["CheckoutRequestID"]
        return render_template("pending.html")
    else:
        return redirect(url_for("error"))


# ─── Callback webhook (no redirects!) ──────────────────────────────────────────
@app.route(CALLBACK_ROUTE, methods=["POST"])
def mpesa_callback():
    """
    This endpoint MUST return HTTP 200 OK immediately.
    Safaricom will POST the transaction result here.
    """
    callback_data = request.get_json()
    # TODO: persist callback_data to your database or process as needed
    print("MPESA CALLBACK RECEIVED:", callback_data)

    # Always ACK with 200, empty body
    return "", 200


# ─── Success & error pages (for user‐driven flow) ──────────────────────────────
@app.route("/success")
def success():
    amt = request.args.get("amount")
    return render_template("success.html", amount=amt)


@app.route("/error")
def error():
    return render_template("error.html")


# ─── Run ───────────────────────────────────────────────────────────────────────
# if __name__ == "__main__":
#     app.run(debug=True)
