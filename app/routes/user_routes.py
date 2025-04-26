from flask import Blueprint, render_template, redirect, url_for, flash, session, request, current_app, jsonify
from app.forms import UserForm, MessageForm, ContributionForm
from app.models import db, User, Message, Contribution
import requests
from base64 import b64encode
from datetime import datetime
import uuid

user_bp = Blueprint('user', __name__)

@user_bp.route('/', methods=['GET', 'POST'])
def landing_page():
    form = UserForm()
    if form.validate_on_submit():
        # Check if user exists, otherwise create new
        user = User.query.filter_by(phone=form.phone.data).first()
        if not user:
            user = User(
                name=form.name.data,
                phone=form.phone.data
            )
            db.session.add(user)
            db.session.commit()
        
        # Store user_id in session
        session['user_id'] = user.id
        return redirect(url_for('user.message_page'))
    
    return render_template('landing.html', form=form)

@user_bp.route('/message', methods=['GET', 'POST'])
def message_page():
    if 'user_id' not in session:
        flash('Please register first.', 'warning')
        return redirect(url_for('user.landing_page'))
    
        # Get user with error handling
    user = User.query.get(session['user_id'])
    if not user:
        flash('User not found. Please register again.', 'error')
        return redirect(url_for('user.landing_page'))
    
    form = MessageForm()
    user = User.query.get(session['user_id'])
    print(user.name)
    
    if form.validate_on_submit():
        message = Message(
            content=form.content.data,
            user_id=user.id
        )
        db.session.add(message)
        db.session.commit()
        flash('Your message has been sent successfully!', 'success')
        return redirect(url_for('user.contribute'))
    
    return render_template('message.html', form=form, user=user, name=user.name)


@user_bp.route('/contribute', methods=['GET', 'POST'])
def contribute():
    if 'user_id' not in session:
        flash('Please register first.', 'warning')
        return redirect(url_for('user.landing_page'))

    form = ContributionForm()
    user = User.query.get(session['user_id'])

    form.phone.data = user.phone

    if form.validate_on_submit():
        amount = form.amount.data
        raw_phone = form.phone.data  
        phone = "254" + raw_phone.lstrip("0")

        # Step 1: Get OAuth token
        consumer_key = current_app.config['MPESA_CONSUMER_KEY']
        consumer_secret = current_app.config['MPESA_CONSUMER_SECRET']
        basic_auth = b64encode(f"{consumer_key}:{consumer_secret}".encode()).decode()

        token_url = f"{current_app.config['MPESA_API_URL']}/oauth/v1/generate?grant_type=client_credentials"
        token_r = requests.get(token_url, headers={"Authorization": f"Basic {basic_auth}"})
        access_token = token_r.json().get("access_token")

        # Step 2: Build STK push payload
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        shortcode = current_app.config['MPESA_SHORTCODE']
        passkey = current_app.config['MPESA_PASSKEY']
        password = b64encode(f"{shortcode}{passkey}{timestamp}".encode()).decode()

        base_url = current_app.config.get('BASE_URL', '').strip().rstrip('/')
        if not base_url:
            current_app.logger.error("BASE_URL is not configured")
            return redirect(url_for('user.payment_failed'))
        
        if not base_url.startswith(('http://', 'https://')):
            current_app.logger.error("Invalid BASE_URL configuration")
            return redirect(url_for('user.payment_failed'))
        
        current_app.logger.debug(f"Loaded BASE_URL: {base_url}")

        
        callback_url = f"{base_url}/mpesa_callback"


        payload = {
            "BusinessShortCode": shortcode,
            "Password": password,
            "Timestamp": timestamp,
            "TransactionType": "CustomerPayBillOnline",
            "Amount": str(int(amount)),
            "PartyA": phone,
            "PartyB": shortcode,
            "PhoneNumber": phone,
            "CallBackURL": callback_url,
            "AccountReference": "Chochette's birthday",
            "TransactionDesc": "User Contribution"
        }

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }

        response = requests.post(
            f"{current_app.config['MPESA_API_URL']}/mpesa/stkpush/v1/processrequest",
            json=payload,
            headers=headers
        )
        data = response.json()

        if data.get("ResponseCode") == "0":
            # Create a contribution 
            checkout_id = data.get("CheckoutRequestID")
            contribution = Contribution(
                amount=amount,
                transaction_id=checkout_id,
                status='pending',
                user_id=user.id
            )
            db.session.add(contribution)
            db.session.commit()

      
            return redirect(url_for('user.payment_pending', checkout_id=checkout_id))
        else:
            # Handle error:
            error_message = data.get("errorMessage") or data.get("errorDescription") or "Unknown error"
            print("MPESA Error:", error_message)
            return redirect(url_for('user.payment_failed'))

    return render_template('contribute.html', form=form, user=user)

@user_bp.route('/payment_pending/<checkout_id>', methods=['GET'])
def payment_pending(checkout_id):
    contribution = Contribution.query.filter_by(transaction_id=checkout_id).first()
    if not contribution:
        flash('Contribution not found.', 'danger')
        return redirect(url_for('user.contribute'))
    
    return render_template('payment_pending.html', contribution=contribution)

@user_bp.route('/payment_failed', methods=['GET'])
def payment_failed():
    return render_template('payment_error.html')


@user_bp.route("/mpesa_callback", methods=["POST"])
def mpesa_callback():
    data = request.get_json(force=True)
    stk = data.get("Body", {}).get("stkCallback", {})
    checkout_id = stk.get("CheckoutRequestID")
    if not checkout_id:
        return "", 400

    record = Contribution.query.filter_by(transaction_id=checkout_id).first()

    if not record:
        # unknown transaction
        return "", 404

    # Success?
    if stk.get("ResultCode") == 0:
        # extract amount
        items = stk.get("CallbackMetadata", {}).get("Item", [])
        amount = next((it["Value"] for it in items if it["Name"] == "Amount"), None)
        record.status = "success"
        if amount is not None:
            record.amount = amount
    else:
        record.status = "failed"

    db.session.commit()
    return "", 200

@user_bp.route("/contribution_status/<checkout_id>")
def contribution_status(checkout_id):
    contribution = Contribution.query.filter_by(transaction_id=checkout_id).first()
    if not contribution:
        return jsonify(status="unknown"), 404
    return jsonify(status=contribution.status, amount=contribution.amount)


@user_bp.route('/payment_success/<checkout_id>')
def payment_success(checkout_id):
    contribution = Contribution.query.filter_by(transaction_id=checkout_id).first()
    if not contribution:
        flash('Contribution not found.', 'danger')
        return redirect(url_for('user.contribute'))
    
    return render_template('thank_you.html', 
                         user=contribution.contributor,
                         amount=contribution.amount)