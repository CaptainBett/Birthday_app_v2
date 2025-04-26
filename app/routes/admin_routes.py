from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user

from app.forms import AdminLoginForm, EventForm
from app.models import db, Admin, Message, User, Contribution, Event
from datetime import datetime

admin_bp = Blueprint('admin_panel', __name__)

@admin_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('admin_panel.dashboard'))
    
    form = AdminLoginForm()
    if form.validate_on_submit():
        admin = Admin.query.filter_by(username=form.username.data).first()
        if admin and admin.check_password(form.password.data):
            login_user(admin)
            next_page = request.args.get('next')
            return redirect(next_page or url_for('admin_panel.dashboard'))
        else:
            flash('Invalid username or password', 'danger')
    
    return render_template('admin/login.html', form=form)

@admin_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out', 'info')
    return redirect(url_for('admin_panel.login'))

@admin_bp.route('/dashboard')
@login_required
def dashboard():
    users_count = User.query.count()
    messages_count = Message.query.count()
    contributions_count = Contribution.query.count()
    total_amount = db.session.query(db.func.sum(Contribution.amount)).filter_by(status='completed').scalar() or 0
    
    recent_users = User.query.order_by(User.created_at.desc()).limit(5).all()
    recent_messages = Message.query.order_by(Message.created_at.desc()).limit(5).all()
    recent_contributions = Contribution.query.order_by(Contribution.created_at.desc()).limit(5).all()
    
    return render_template('admin/dashboard.html',
                          users_count=users_count,
                          messages_count=messages_count,
                          contributions_count=contributions_count,
                          total_amount=total_amount,
                          recent_users=recent_users,
                          recent_messages=recent_messages,
                          recent_contributions=recent_contributions)

@admin_bp.route('/messages')
@login_required
def messages():
    page = request.args.get('page', 1, type=int)
    messages = Message.query.join(User).order_by(Message.created_at.desc())\
        .paginate(page=page, per_page=10, error_out=False)
    return render_template('admin/messages.html', messages=messages)

@admin_bp.route('/contributions')
@login_required
def contributions():
    page = request.args.get('page', 1, type=int)
    contributions = Contribution.query.join(User).order_by(Contribution.created_at.desc())\
        .paginate(page=page, per_page=10, error_out=False)
    
    # Calculate total amount from completed contributions
    total_amount = db.session.query(db.func.sum(Contribution.amount)).filter_by(status='completed').scalar() or 0
    
    # Calculate average contribution amount
    completed_count = Contribution.query.filter_by(status='completed').count()
    average_amount = total_amount / completed_count if completed_count > 0 else 0
    
    return render_template('admin/contributions.html', 
                          contributions=contributions,
                          total_amount=total_amount,
                          average_amount=average_amount)

@admin_bp.route('/users')
@login_required
def users():
    page = request.args.get('page', 1, type=int)
    users = User.query.order_by(User.created_at.desc())\
        .paginate(page=page, per_page=10, error_out=False)
    return render_template('admin/users.html', users=users)

@admin_bp.route('/events', methods=['GET', 'POST'])
@login_required
def events():
    form = EventForm()
    if form.validate_on_submit():
        try:
            event_date = datetime.strptime(form.event_date.data, '%Y-%m-%d')
            event = Event(
                title=form.title.data,
                description=form.description.data,
                event_date=event_date
            )
            db.session.add(event)
            db.session.commit()
            flash('Event created successfully!', 'success')
            return redirect(url_for('admin_panel.events'))
        except ValueError:
            flash('Invalid date format. Please use YYYY-MM-DD', 'danger')
    
    page = request.args.get('page', 1, type=int)
    events = Event.query.order_by(Event.event_date.desc())\
        .paginate(page=page, per_page=10, error_out=False)
    
    return render_template('admin/events.html', events=events, form=form)

@admin_bp.route('/events/<int:event_id>/delete', methods=['POST'])
@login_required
def delete_event(event_id):
    event = Event.query.get_or_404(event_id)
    db.session.delete(event)
    db.session.commit()
    flash('Event deleted successfully!', 'success')
    return redirect(url_for('admin_panel.events'))