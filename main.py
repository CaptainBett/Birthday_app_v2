from flask import Flask, render_template, request, session, redirect, url_for, jsonify
import requests
from base64 import b64encode
from datetime import datetime
import os
from dotenv import load_dotenv
import json
import secrets

app = Flask(__name__)
app.secret_key = secrets.token_hex(16)  
# Load environment variables from .env file
load_dotenv()

# M-Pesa Daraja Credentials
CONSUMER_KEY = os.getenv('CONSUMER_KEY')
CONSUMER_SECRET = os.getenv('CONSUMER_SECRET')
MPESA_SHORTCODE = os.getenv('MPESA_SHORTCODE')
PASSKEY = os.getenv('PASSKEY')

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/message', methods=['POST'])
def message():
    session['name'] = request.form['name']
    session['phone'] = request.form['phone']
    return render_template('message.html', name=session['name'])

@app.route('/process_gift', methods=['POST'])
def process_gift():
    if 'yes' in request.form:
        return redirect(url_for('payment'))
    return redirect(url_for('no_gift'))

@app.route('/payment')
def payment():
    return render_template('payment.html', phone=session.get('phone', ''))

@app.route('/process_payment', methods=['POST'])
def process_payment():
    # M-Pesa API Integration
    amount = request.form['amount']
    phone = "254" + session.get('phone', '')[1:]

    if not all([amount, phone]):
        return redirect(url_for('payment_response', success=False))

    # Validate amount
    if not amount.isdigit() or int(amount) < 1:
        return redirect(url_for('payment_response', success=False))
    
    # Get access token
    auth = b64encode(f"{CONSUMER_KEY}:{CONSUMER_SECRET}".encode()).decode()
    headers = {'Authorization': f'Basic {auth}'}
    token_response = requests.get('https://sandbox.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials', headers=headers)
    access_token = token_response.json().get('access_token')
    
    # Initiate STK push
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    password = b64encode(f"{MPESA_SHORTCODE}{PASSKEY}{timestamp}".encode()).decode()
    
    payload = {
        "BusinessShortCode": MPESA_SHORTCODE,
        "Password": password,
        "Timestamp": timestamp,
        "TransactionType": "CustomerPayBillOnline",
        "Amount": str(int(amount)),
        "PartyA": phone,
        "PartyB": MPESA_SHORTCODE,
        "PhoneNumber": phone,
        "CallBackURL": "https://postman-echo.com/post",
        "AccountReference": "Birthday Gift",
        "TransactionDesc": "Birthday Celebration"
    }
    
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }

    try:
        response = requests.post(
            'https://sandbox.safaricom.co.ke/mpesa/stkpush/v1/processrequest',
            headers=headers,
            json=payload
        )
        response_data = response.json()
        # Store transaction ID in session
        session['checkout_request_id'] = response_data['CheckoutRequestID']

        print("M-Pesa Response Status:", response.status_code)
        print("M-Pesa Response Content:", response.text)
        
        # Check both status code and API response code
        if response.status_code == 200 and response_data.get('ResponseCode') == '0':
            return redirect(url_for('payment_response', success=True))
        return redirect(url_for('payment_response', success=False))
        
    except Exception as e:
        app.logger.error(f"Payment Error: {str(e)}")
        app.logger.error(f"Amount: {amount}")
        return redirect(url_for('payment_response', success=False))


@app.route('/callback', methods=['POST'])
def callback():
    data = request.get_json()
    if data.get('Body', {}).get('stkCallback', {}).get('ResultCode') == 0:
        # Successful payment logic
        return render_template('payment_success.html')
    else:
        # Failed payment logic
        print("Payment failed:", data)
    return jsonify({'ResultCode': 0, 'ResultDesc': 'Accepted'})


@app.route('/no_gift')
def no_gift():
    return render_template('no_gift.html')

@app.route('/payment_response')
def payment_response():
    success = request.args.get('success', False)
    return render_template('payment_response.html', success=success)

if __name__ == '__main__':
    app.run(ssl_context='adhoc', debug=True)