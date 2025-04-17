from flask import Flask, render_template, request, session, redirect, url_for, jsonify
import requests
from base64 import b64encode
from datetime import datetime
import os
from dotenv import load_dotenv
import uuid
import secrets

app = Flask(__name__)
app.secret_key = secrets.token_hex(16)  
load_dotenv()


# Daraja (sandbox) endpoints & credentials
STK_PUSH_URL     = "https://sandbox.safaricom.co.ke/mpesa/stkpush/v1/processrequest"
CALLBACK_ROUTE   = "/mpesa_callback"
CONSUMER_KEY = os.getenv('CONSUMER_KEY')
CONSUMER_SECRET = os.getenv('CONSUMER_SECRET')
BUSINESS_SHORTCODE = os.getenv('BUSINESS_SHORTCODE')
PASSKEY = os.getenv('PASSKEY')


@app.route("/", methods=["GET","POST"])
def index():
    if request.method == "POST":
        session["name"] = request.form["name"]
        session["phone"] = request.form["phone"]
        return redirect(url_for("message"))
    return render_template("index.html")

@app.route("/message", methods=["GET","POST"])
def message():
    if request.method == "POST":
        session["note"] = request.form["note"]
        return redirect(url_for("gift"))
    return render_template("message.html")

@app.route("/gift")
def gift():
    return render_template("gift.html")

@app.route("/process_payment", methods=["POST"])
def process_payment():
    amount = request.form["amount"]
    phone  = "254" + request.form.get('phone', '')[1:]

    # if not all([amount, phone]):
    #     return redirect(url_for('payment_response', success=False))

    # Validate amount
    # if not amount.isdigit() or int(amount) < 1:
    #     return redirect(url_for('payment_response', success=False))
    
    # Get access token
    auth = b64encode(f"{CONSUMER_KEY}:{CONSUMER_SECRET}".encode()).decode()
    headers = {'Authorization': f'Basic {auth}'}
    token_response = requests.get('https://sandbox.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials', headers=headers)
    access_token = token_response.json().get('access_token')

    # Initiate STK push
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
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
        "CallBackURL": url_for("mpesa_callback", _external=True),
        "AccountReference": str(uuid.uuid4()),
        "TransactionDesc": "Birthday Gift"
    }

    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
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

@app.route(CALLBACK_ROUTE, methods=["POST"])
def mpesa_callback():
    data = request.get_json()
    stk = data["Body"]["stkCallback"]
    if stk["ResultCode"] == 0:
        # Success
        amt = next(item["Value"] for item in stk["CallbackMetadata"]["Item"] if item["Name"]=="Amount")
        return redirect(url_for("success", amount=amt))
    return redirect(url_for("error"))

@app.route("/success")
def success():
    return render_template("success.html", amount=request.args.get("amount"))

@app.route("/error")
def error():
    return render_template("error.html")

if __name__ == "__main__":
    app.run(debug=True)
