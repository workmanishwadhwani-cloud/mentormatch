"""
Forms for payment and notification preferences
"""
from flask_wtf import FlaskForm
from wtforms import StringField, IntegerField, SelectField, BooleanField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Length, Email, Optional, NumberRange


class PaymentForm(FlaskForm):
    """Form for payment processing"""
    amount = IntegerField('Amount (₹)', validators=[DataRequired(), NumberRange(min=100)])
    payment_method = SelectField(
        'Payment Method',
        choices=[('card', 'Credit/Debit Card'), ('netbanking', 'Net Banking'), ('upi', 'UPI')],
        validators=[DataRequired()]
    )
    submit = SubmitField('Proceed to Payment')


class NotificationPreferencesForm(FlaskForm):
    """Form for user notification preferences"""
    email_notifications = BooleanField('Receive Email Notifications')
    sms_notifications = BooleanField('Receive SMS Notifications')
    phone_number = StringField('Phone Number', validators=[Optional(), Length(min=10, max=20)])
    email_on_session_request = BooleanField('Email when I receive session requests')
    email_on_message = BooleanField('Email when I receive messages')
    email_on_payment = BooleanField('Email payment confirmations')
    sms_on_reminder = BooleanField('SMS session reminders')
    sms_on_payment = BooleanField('SMS payment notifications')
    submit = SubmitField('Save Preferences')


class CalendarExportForm(FlaskForm):
    """Form for calendar export options"""
    format = SelectField(
        'Calendar Format',
        choices=[('ics', 'iCalendar (.ics)'), ('google', 'Google Calendar'), ('outlook', 'Outlook Calendar')],
        validators=[DataRequired()]
    )
    include_past_sessions = BooleanField('Include past sessions')
    submit = SubmitField('Export Calendar')
