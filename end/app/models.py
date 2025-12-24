from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from app import db, login


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), nullable=False)
    email = db.Column(db.String(120), unique=True, index=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    role = db.Column(db.String(20), default='student', index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    student_profile = db.relationship('StudentProfile', backref='user', uselist=False, cascade='all, delete-orphan')
    mentor_profile = db.relationship('MentorProfile', backref='user', uselist=False, cascade='all, delete-orphan')

    sent_messages = db.relationship('Message', foreign_keys='Message.sender_id', backref='sender', lazy='dynamic')
    received_messages = db.relationship('Message', foreign_keys='Message.receiver_id', backref='receiver', lazy='dynamic')

    notifications = db.relationship('Notification', backref='user', lazy='dynamic', cascade='all, delete-orphan')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def is_student(self):
        return self.role == 'student'

    def is_mentor(self):
        return self.role == 'mentor'

    def is_admin(self):
        return self.role == 'admin'


@login.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


class StudentProfile(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    academic_year = db.Column(db.String(64))
    course = db.Column(db.String(128))
    interests = db.Column(db.Text)
    goals = db.Column(db.Text)


class MentorProfile(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    title = db.Column(db.String(128))
    skills = db.Column(db.String(256))
    years_of_experience = db.Column(db.Integer)
    hourly_rate = db.Column(db.Float)
    profile_pic = db.Column(db.String(256))

    availabilities = db.relationship('Availability', backref='mentor', lazy='dynamic')
    reviews = db.relationship('Review', backref='mentor', lazy='dynamic',
                              primaryjoin="MentorProfile.user_id==Review.mentor_id",
                              foreign_keys='Review.mentor_id')


class Availability(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    mentor_id = db.Column(db.Integer, db.ForeignKey('mentor_profile.id'))
    day_of_week = db.Column(db.Integer)  # 0=Mon ..6=Sun
    start_time = db.Column(db.Time)
    end_time = db.Column(db.Time)


class Session(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('user.id'), index=True)
    mentor_id = db.Column(db.Integer, db.ForeignKey('user.id'), index=True)
    topic = db.Column(db.String(256))
    description = db.Column(db.Text)
    scheduled_at = db.Column(db.DateTime, index=True)
    status = db.Column(db.String(32), default='requested', index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'), index=True)
    receiver_id = db.Column(db.Integer, db.ForeignKey('user.id'), index=True)
    session_id = db.Column(db.Integer, db.ForeignKey('session.id'), nullable=True)
    content = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    
    __table_args__ = (
        db.Index('idx_message_conversation', 'sender_id', 'receiver_id', 'created_at'),
    )


class Review(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey('session.id'), index=True)
    student_id = db.Column(db.Integer, db.ForeignKey('user.id'), index=True)
    mentor_id = db.Column(db.Integer, db.ForeignKey('user.id'), index=True)
    rating = db.Column(db.Integer)
    comment = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)


class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), index=True)
    message = db.Column(db.String(256))
    is_read = db.Column(db.Boolean, default=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)


class Payment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey('session.id'), index=True)
    student_id = db.Column(db.Integer, db.ForeignKey('user.id'), index=True)
    mentor_id = db.Column(db.Integer, db.ForeignKey('user.id'), index=True)
    amount = db.Column(db.Float, nullable=False)
    currency = db.Column(db.String(3), default='INR')
    razorpay_order_id = db.Column(db.String(128), unique=True, index=True)
    razorpay_payment_id = db.Column(db.String(128), unique=True, index=True)
    status = db.Column(db.String(32), default='pending', index=True)  # pending, completed, failed, refunded
    payment_method = db.Column(db.String(64))  # card, netbanking, upi
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    student = db.relationship('User', foreign_keys=[student_id])
    mentor = db.relationship('User', foreign_keys=[mentor_id])
    session = db.relationship('Session', backref='payment')


class EmailNotification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), index=True)
    recipient_email = db.Column(db.String(120), nullable=False)
    subject = db.Column(db.String(256), nullable=False)
    body = db.Column(db.Text)
    notification_type = db.Column(db.String(64))  # session_request, message, payment, review
    status = db.Column(db.String(32), default='pending', index=True)  # pending, sent, failed
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    sent_at = db.Column(db.DateTime)
    
    user = db.relationship('User', backref='email_notifications')


class SMSNotification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), index=True)
    phone_number = db.Column(db.String(20), nullable=False)
    message = db.Column(db.String(160), nullable=False)
    notification_type = db.Column(db.String(64))  # session_update, payment, reminder
    status = db.Column(db.String(32), default='pending', index=True)  # pending, sent, failed
    twilio_sid = db.Column(db.String(128))
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    sent_at = db.Column(db.DateTime)
    
    user = db.relationship('User', backref='sms_notifications')


class CalendarEvent(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey('session.id'), index=True, unique=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), index=True)
    title = db.Column(db.String(256), nullable=False)
    description = db.Column(db.Text)
    start_time = db.Column(db.DateTime, index=True)
    end_time = db.Column(db.DateTime, index=True)
    location = db.Column(db.String(256))
    ical_uid = db.Column(db.String(256), unique=True)
    notification_sent = db.Column(db.Boolean, default=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    
    session = db.relationship('Session', backref='calendar_event')
    user = db.relationship('User', backref='calendar_events')
