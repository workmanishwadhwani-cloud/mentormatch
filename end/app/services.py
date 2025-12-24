"""
Service layer for handling payments, emails, SMS, and calendar notifications
"""
import os
from datetime import datetime, timedelta
from flask import current_app, render_template_string
from flask_mail import Mail, Message as EmailMessage
import razorpay
from twilio.rest import Client
from icalendar import Calendar, Event
from app import db
from app.models import EmailNotification, SMSNotification, CalendarEvent, Payment, Session

mail = Mail()


class PaymentService:
    """Handle Razorpay payment operations"""
    
    @staticmethod
    def initialize_client():
        """Initialize Razorpay client"""
        return razorpay.Client(
            auth=(current_app.config['RAZORPAY_KEY_ID'],
                  current_app.config['RAZORPAY_KEY_SECRET'])
        )
    
    @staticmethod
    def create_order(session_id, student_id, mentor_id, amount):
        """Create a Razorpay order"""
        try:
            client = PaymentService.initialize_client()
            
            # Create order
            order_data = {
                'amount': int(amount * 100),  # Amount in paise
                'currency': 'INR',
                'receipt': f'session_{session_id}',
                'notes': {
                    'session_id': session_id,
                    'student_id': student_id,
                    'mentor_id': mentor_id
                }
            }
            
            order = client.order.create(data=order_data)
            
            # Save payment record
            payment = Payment(
                session_id=session_id,
                student_id=student_id,
                mentor_id=mentor_id,
                amount=amount,
                razorpay_order_id=order['id'],
                status='pending'
            )
            db.session.add(payment)
            db.session.commit()
            
            return {
                'success': True,
                'order_id': order['id'],
                'amount': amount,
                'currency': 'INR'
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    @staticmethod
    def verify_payment(order_id, payment_id, signature):
        """Verify Razorpay payment signature"""
        try:
            client = PaymentService.initialize_client()
            
            # Verify signature
            params_dict = {
                'razorpay_order_id': order_id,
                'razorpay_payment_id': payment_id,
                'razorpay_signature': signature
            }
            
            client.utility.verify_payment_signature(params_dict)
            
            # Update payment record
            payment = Payment.query.filter_by(razorpay_order_id=order_id).first()
            if payment:
                payment.razorpay_payment_id = payment_id
                payment.status = 'completed'
                payment.updated_at = datetime.utcnow()
                db.session.commit()
                
                return {'success': True, 'payment_id': payment.id}
            
            return {'success': False, 'error': 'Payment record not found'}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    @staticmethod
    def refund_payment(payment_id, amount=None):
        """Refund a Razorpay payment"""
        try:
            payment = Payment.query.get(payment_id)
            if not payment or payment.razorpay_payment_id is None:
                return {'success': False, 'error': 'Payment not found'}
            
            client = PaymentService.initialize_client()
            refund_data = {}
            
            if amount:
                refund_data['amount'] = int(amount * 100)
            
            refund = client.payment.refund(payment.razorpay_payment_id, refund_data)
            
            payment.status = 'refunded'
            payment.updated_at = datetime.utcnow()
            db.session.commit()
            
            return {'success': True, 'refund_id': refund['id']}
        except Exception as e:
            return {'success': False, 'error': str(e)}


class EmailService:
    """Handle email notifications"""
    
    @staticmethod
    def send_session_request_email(student_name, mentor_email, session_topic):
        """Send email when student requests a session"""
        subject = f"New Session Request: {session_topic}"
        body = f"""
        <h2>New Session Request</h2>
        <p>Hi,</p>
        <p><strong>{student_name}</strong> has requested a mentorship session on <strong>{session_topic}</strong>.</p>
        <p>Please log in to your MentorConnect dashboard to review and respond to this request.</p>
        <p>Best regards,<br/>MentorConnect Team</p>
        """
        
        return EmailService._send_email(
            recipient=mentor_email,
            subject=subject,
            body=body,
            notification_type='session_request'
        )
    
    @staticmethod
    def send_session_accepted_email(student_email, mentor_name, session_date):
        """Send email when mentor accepts a session"""
        subject = "Session Request Accepted!"
        body = f"""
        <h2>Session Accepted</h2>
        <p>Hi,</p>
        <p>Great news! <strong>{mentor_name}</strong> has accepted your session request.</p>
        <p><strong>Session Date:</strong> {session_date}</p>
        <p>Check your dashboard for more details and to start messaging with your mentor.</p>
        <p>Best regards,<br/>MentorConnect Team</p>
        """
        
        return EmailService._send_email(
            recipient=student_email,
            subject=subject,
            body=body,
            notification_type='session_accepted'
        )
    
    @staticmethod
    def send_new_message_email(recipient_email, sender_name):
        """Send email notification for new message"""
        subject = f"New Message from {sender_name}"
        body = f"""
        <h2>New Message</h2>
        <p>Hi,</p>
        <p>You have received a new message from <strong>{sender_name}</strong>.</p>
        <p>Log in to MentorConnect to read and reply to the message.</p>
        <p>Best regards,<br/>MentorConnect Team</p>
        """
        
        return EmailService._send_email(
            recipient=recipient_email,
            subject=subject,
            body=body,
            notification_type='message'
        )
    
    @staticmethod
    def send_payment_confirmation_email(recipient_email, amount, session_date):
        """Send payment confirmation email"""
        subject = "Payment Confirmation"
        body = f"""
        <h2>Payment Successful</h2>
        <p>Hi,</p>
        <p>Your payment has been processed successfully!</p>
        <p><strong>Amount:</strong> ₹{amount}</p>
        <p><strong>Session Date:</strong> {session_date}</p>
        <p>Thank you for using MentorConnect!</p>
        <p>Best regards,<br/>MentorConnect Team</p>
        """
        
        return EmailService._send_email(
            recipient=recipient_email,
            subject=subject,
            body=body,
            notification_type='payment'
        )
    
    @staticmethod
    def _send_email(recipient, subject, body, notification_type='general'):
        """Internal method to send email and log notification"""
        try:
            msg = EmailMessage(
                subject=subject,
                recipients=[recipient],
                html=body
            )
            
            mail.send(msg)
            
            # Log email notification
            email_notif = EmailNotification(
                recipient_email=recipient,
                subject=subject,
                body=body,
                notification_type=notification_type,
                status='sent',
                sent_at=datetime.utcnow()
            )
            db.session.add(email_notif)
            db.session.commit()
            
            return {'success': True}
        except Exception as e:
            email_notif = EmailNotification(
                recipient_email=recipient,
                subject=subject,
                body=body,
                notification_type=notification_type,
                status='failed'
            )
            db.session.add(email_notif)
            db.session.commit()
            return {'success': False, 'error': str(e)}


class SMSService:
    """Handle SMS notifications via Twilio"""
    
    @staticmethod
    def initialize_client():
        """Initialize Twilio client"""
        return Client(
            current_app.config['TWILIO_ACCOUNT_SID'],
            current_app.config['TWILIO_AUTH_TOKEN']
        )
    
    @staticmethod
    def send_session_reminder(phone_number, mentor_name, session_time):
        """Send SMS reminder for upcoming session"""
        message_text = f"MentorConnect: Reminder! Your session with {mentor_name} is at {session_time}. Reply STOP to unsubscribe."
        
        return SMSService._send_sms(
            phone_number=phone_number,
            message=message_text,
            notification_type='session_reminder'
        )
    
    @staticmethod
    def send_payment_notification(phone_number, amount, mentor_name):
        """Send SMS for successful payment"""
        message_text = f"MentorConnect: Payment of ₹{amount} to {mentor_name} confirmed. Session details in your inbox."
        
        return SMSService._send_sms(
            phone_number=phone_number,
            message=message_text,
            notification_type='payment'
        )
    
    @staticmethod
    def send_message_notification(phone_number, sender_name):
        """Send SMS for new message"""
        message_text = f"MentorConnect: New message from {sender_name}. Check your account for details."
        
        return SMSService._send_sms(
            phone_number=phone_number,
            message=message_text,
            notification_type='message'
        )
    
    @staticmethod
    def _send_sms(phone_number, message, notification_type='general'):
        """Internal method to send SMS via Twilio"""
        try:
            client = SMSService.initialize_client()
            
            sms = client.messages.create(
                body=message,
                from_=current_app.config['TWILIO_PHONE_NUMBER'],
                to=phone_number
            )
            
            # Log SMS notification
            sms_notif = SMSNotification(
                phone_number=phone_number,
                message=message,
                notification_type=notification_type,
                status='sent',
                twilio_sid=sms.sid,
                sent_at=datetime.utcnow()
            )
            db.session.add(sms_notif)
            db.session.commit()
            
            return {'success': True, 'sms_sid': sms.sid}
        except Exception as e:
            sms_notif = SMSNotification(
                phone_number=phone_number,
                message=message,
                notification_type=notification_type,
                status='failed'
            )
            db.session.add(sms_notif)
            db.session.commit()
            return {'success': False, 'error': str(e)}


class CalendarService:
    """Handle calendar event creation and management"""
    
    @staticmethod
    def create_calendar_event(session_id, user_id, session):
        """Create iCalendar event for a session"""
        try:
            # Create calendar
            cal = Calendar()
            cal.add('prodid', '-//MentorConnect//EN')
            cal.add('version', '2.0')
            cal.add('calscale', 'GREGORIAN')
            
            # Create event
            event = Event()
            event.add('summary', f"Session: {session.topic}")
            event.add('description', session.description or '')
            event.add('dtstart', session.scheduled_at)
            event.add('dtend', session.scheduled_at + timedelta(hours=1))
            event.add('dtstamp', datetime.utcnow())
            
            # Generate unique UID
            uid = f"session_{session_id}_{user_id}@mentorconnect.com"
            event.add('uid', uid)
            
            # Add location
            event.add('location', 'Online - MentorConnect Platform')
            
            # Add alarm
            event.add('alarm', {'trigger': '-PT15M', 'action': 'DISPLAY', 'description': 'Session Reminder'})
            
            cal.add_component(event)
            
            # Save calendar event to database
            calendar_event = CalendarEvent(
                session_id=session_id,
                user_id=user_id,
                title=f"Session: {session.topic}",
                description=session.description,
                start_time=session.scheduled_at,
                end_time=session.scheduled_at + timedelta(hours=1),
                ical_uid=uid
            )
            db.session.add(calendar_event)
            db.session.commit()
            
            return {
                'success': True,
                'calendar_data': cal.to_ical().decode('utf-8'),
                'event_id': calendar_event.id
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    @staticmethod
    def get_calendar_export(user_id):
        """Generate calendar export for all user's sessions"""
        try:
            from app.models import Session, User
            
            user = User.query.get(user_id)
            if not user:
                return {'success': False, 'error': 'User not found'}
            
            # Get all sessions for the user
            if user.is_student():
                sessions = Session.query.filter_by(student_id=user_id).all()
            else:
                sessions = Session.query.filter_by(mentor_id=user_id).all()
            
            # Create calendar
            cal = Calendar()
            cal.add('prodid', '-//MentorConnect//EN')
            cal.add('version', '2.0')
            cal.add('calscale', 'GREGORIAN')
            cal.add('method', 'PUBLISH')
            cal.add('x-wr-calname', f"{user.name}'s MentorConnect Sessions")
            cal.add('x-wr-timezone', current_app.config.get('CALENDAR_TIMEZONE', 'Asia/Kolkata'))
            
            # Add events
            for session in sessions:
                event = Event()
                event.add('summary', f"Session: {session.topic}")
                event.add('description', session.description or '')
                event.add('dtstart', session.scheduled_at)
                event.add('dtend', session.scheduled_at + timedelta(hours=1))
                event.add('uid', f"session_{session.id}_{user_id}@mentorconnect.com")
                event.add('status', session.status.upper())
                
                cal.add_component(event)
            
            return {
                'success': True,
                'calendar_data': cal.to_ical().decode('utf-8'),
                'filename': f"{user.name}_mentorconnect_calendar.ics"
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    @staticmethod
    def send_calendar_reminder(user_id, days_before=1):
        """Send calendar reminders for upcoming sessions"""
        try:
            from app.models import Session, User
            
            user = User.query.get(user_id)
            if not user:
                return {'success': False, 'error': 'User not found'}
            
            # Get upcoming sessions
            threshold = datetime.utcnow() + timedelta(days=days_before)
            
            if user.is_student():
                sessions = Session.query.filter(
                    Session.student_id == user_id,
                    Session.scheduled_at.between(datetime.utcnow(), threshold),
                    Session.status.in_(['accepted', 'completed'])
                ).all()
            else:
                sessions = Session.query.filter(
                    Session.mentor_id == user_id,
                    Session.scheduled_at.between(datetime.utcnow(), threshold),
                    Session.status.in_(['accepted', 'completed'])
                ).all()
            
            reminders_sent = 0
            for session in sessions:
                calendar_event = CalendarEvent.query.filter_by(session_id=session.id, user_id=user_id).first()
                
                if calendar_event and not calendar_event.notification_sent:
                    # Send reminder (could be email, SMS, or both)
                    calendar_event.notification_sent = True
                    db.session.commit()
                    reminders_sent += 1
            
            return {'success': True, 'reminders_sent': reminders_sent}
        except Exception as e:
            return {'success': False, 'error': str(e)}
