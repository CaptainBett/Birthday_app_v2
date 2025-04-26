from flask_wtf import FlaskForm
from wtforms import StringField, TelField, TextAreaField, IntegerField, SubmitField, PasswordField
from wtforms.validators import DataRequired, NumberRange, Length

class UserForm(FlaskForm):
    name = StringField(
        'Full Name',
        validators=[
            DataRequired(message="Please enter your full name."),
            Length(min=3, max=100, message="Name must be between 3 and 100 characters.")
        ],
        render_kw={'placeholder': 'Your Name'}
    )
    phone = TelField(
        'Phone Number',
        validators=[
            DataRequired(message="A phone number is required."),
            Length(min=2, max=15, message="Phone must be 10–15 digits.")
        ],
        render_kw={'placeholder': 'Phone Number'}
    )
    submit = SubmitField('🎉 Join the Celebration')


class MessageForm(FlaskForm):
    content = TextAreaField(
        'Leave me a note…',
        validators=[
            DataRequired(message="Please leave a message."),
            Length(
                min=10,
                max=500,
                message="Message must be at least 10 characters."
            )
        ],
        render_kw={'placeholder': 'Your message…'}
    )
    submit = SubmitField('Send Message')


class ContributionForm(FlaskForm):
    amount = IntegerField('Gift Amount:', validators=[
        DataRequired(),
        NumberRange(min=1, message='Minimum contribution is KES 20')
    ],render_kw={
            'placeholder': 'KES 500',
        })
    phone = TelField('Phone Number:',validators=[DataRequired(), Length(min=10, max=15)])
    submit = SubmitField('🎁 Buy Me a Gift')

class AdminLoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')

class EventForm(FlaskForm):
    title = StringField('Event Title', validators=[DataRequired(), Length(max=100)])
    description = TextAreaField('Description', validators=[Length(max=500)])
    event_date = StringField('Event Date (YYYY-MM-DD)', validators=[DataRequired()])
    submit = SubmitField('Save Event')