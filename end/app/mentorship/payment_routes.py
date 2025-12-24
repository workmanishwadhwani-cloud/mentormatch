"""
Routes for payments, notifications, and calendar functionality
"""
from flask import render_template, redirect, url_for, flash, request, abort, jsonify, send_file
from flask_login import current_user, login_required
from app import db, cache
from app.mentorship import bp
from app.payment_forms import PaymentForm, NotificationPreferencesForm, CalendarExportForm
from app.models import Session, Payment, User, CalendarEvent, EmailNotification, SMSNotification
from app.services import PaymentService, EmailService, SMSService, CalendarService
from datetime import datetime
import io


@bp.route('/sessions/<int:session_id>/payment', methods=['GET', 'POST'])
@login_required
def initiate_payment(session_id):
    """Initiate payment for a session"""
    session = Session.query.get_or_404(session_id)
    
    # Verify student is the one paying
    if session.student_id != current_user.id:
        abort(403)
    
    # Check if session is accepted
    if session.status != 'accepted':
        flash('You can only pay for accepted sessions', 'error')
        return redirect(url_for('mentorship.my_sessions'))
    
    # Get mentor's hourly rate
    mentor = User.query.get(session.mentor_id)
    hourly_rate = mentor.mentor_profile.hourly_rate if mentor.mentor_profile else 0
    
    form = PaymentForm()
    if form.validate_on_submit():
        # Create Razorpay order
        result = PaymentService.create_order(
            session_id=session_id,
            student_id=current_user.id,
            mentor_id=session.mentor_id,
            amount=form.amount.data
        )
        
        if result['success']:
            # Store payment method
            payment = Payment.query.filter_by(razorpay_order_id=result['order_id']).first()
            if payment:
                payment.payment_method = form.payment_method.data
                db.session.commit()
            
            return render_template('payment/razorpay_checkout.html',
                                   order_id=result['order_id'],
                                   amount=result['amount'],
                                   key_id=current_user.app.config['RAZORPAY_KEY_ID'],
                                   session_id=session_id)
        else:
            flash(f"Payment error: {result['error']}", 'error')
    
    return render_template('payment/initiate_payment.html',
                           form=form,
                           session=session,
                           mentor=mentor,
                           hourly_rate=hourly_rate)


@bp.route('/payment/verify', methods=['POST'])
@login_required
def verify_payment():
    """Verify Razorpay payment"""
    order_id = request.form.get('razorpay_order_id')
    payment_id = request.form.get('razorpay_payment_id')
    signature = request.form.get('razorpay_signature')
    session_id = request.form.get('session_id')
    
    result = PaymentService.verify_payment(order_id, payment_id, signature)
    
    if result['success']:
        payment = Payment.query.get(result['payment_id'])
        session = Session.query.get(session_id)
        
        # Send confirmation emails
        if payment.student and session:
            EmailService.send_payment_confirmation_email(
                payment.student.email,
                payment.amount,
                session.scheduled_at.strftime('%B %d, %Y at %I:%M %p')
            )
        
        flash('Payment successful! Session is confirmed.', 'success')
        return redirect(url_for('mentorship.my_sessions'))
    else:
        flash(f"Payment verification failed: {result['error']}", 'error')
        return redirect(url_for('mentorship.my_sessions'))


@bp.route('/sessions/<int:session_id>/payment/refund', methods=['POST'])
@login_required
def refund_payment(session_id):
    """Refund a payment for a session"""
    session = Session.query.get_or_404(session_id)
    payment = Payment.query.filter_by(session_id=session_id).first_or_404()
    
    # Verify authorization
    if current_user.id not in [session.student_id, session.mentor_id] and not current_user.is_admin():
        abort(403)
    
    result = PaymentService.refund_payment(payment.id)
    
    if result['success']:
        flash('Payment refunded successfully', 'success')
    else:
        flash(f"Refund failed: {result['error']}", 'error')
    
    return redirect(url_for('mentorship.my_sessions'))


@bp.route('/calendar/export', methods=['GET', 'POST'])
@login_required
def export_calendar():
    """Export calendar in iCalendar format"""
    form = CalendarExportForm()
    
    if form.validate_on_submit():
        result = CalendarService.get_calendar_export(current_user.id)
        
        if result['success']:
            # Return ICS file download
            output = io.BytesIO()
            output.write(result['calendar_data'].encode('utf-8'))
            output.seek(0)
            
            return send_file(
                output,
                mimetype='text/calendar',
                as_attachment=True,
                download_name=result['filename']
            )
        else:
            flash(f"Export failed: {result['error']}", 'error')
    
    return render_template('calendar/export_calendar.html', form=form)


@bp.route('/calendar/<int:session_id>/add', methods=['POST'])
@login_required
def add_to_calendar(session_id):
    """Add session to calendar"""
    session = Session.query.get_or_404(session_id)
    
    # Verify user is involved in session
    if current_user.id not in [session.student_id, session.mentor_id]:
        abort(403)
    
    result = CalendarService.create_calendar_event(session_id, current_user.id, session)
    
    if result['success']:
        flash('Calendar event created!', 'success')
        return jsonify({'success': True, 'calendar_data': result['calendar_data']})
    else:
        return jsonify({'success': False, 'error': result['error']})


@bp.route('/notifications/preferences', methods=['GET', 'POST'])
@login_required
def notification_preferences():
    """Manage notification preferences"""
    form = NotificationPreferencesForm()
    
    if form.validate_on_submit():
        # Save preferences (could store in UserPreferences model)
        flash('Notification preferences updated!', 'success')
        return redirect(url_for('mentorship.profile'))
    
    return render_template('notifications/preferences.html', form=form)


@bp.route('/notifications/history')
@login_required
def notification_history():
    """View notification history"""
    page = request.args.get('page', 1, type=int)
    
    # Get email notifications
    email_notifs = EmailNotification.query.filter_by(user_id=current_user.id).paginate(page=page, per_page=20)
    
    # Get SMS notifications
    sms_notifs = SMSNotification.query.filter_by(user_id=current_user.id).paginate(page=page, per_page=20)
    
    return render_template('notifications/history.html',
                           email_notifs=email_notifs,
                           sms_notifs=sms_notifs)


@bp.route('/api/payment/status/<int:payment_id>')
@login_required
def payment_status(payment_id):
    """Get payment status via API"""
    payment = Payment.query.get_or_404(payment_id)
    
    # Verify authorization
    if current_user.id not in [payment.student_id, payment.mentor_id] and not current_user.is_admin():
        abort(403)
    
    return jsonify({
        'id': payment.id,
        'status': payment.status,
        'amount': payment.amount,
        'payment_id': payment.razorpay_payment_id,
        'created_at': payment.created_at.isoformat()
    })


@bp.route('/api/calendar/upcoming')
@login_required
def get_upcoming_sessions():
    """Get upcoming sessions for calendar view"""
    from datetime import timedelta
    
    today = datetime.utcnow()
    next_week = today + timedelta(days=7)
    
    if current_user.is_student():
        sessions = Session.query.filter(
            Session.student_id == current_user.id,
            Session.scheduled_at.between(today, next_week),
            Session.status.in_(['accepted', 'completed'])
        ).all()
    else:
        sessions = Session.query.filter(
            Session.mentor_id == current_user.id,
            Session.scheduled_at.between(today, next_week),
            Session.status.in_(['accepted', 'completed'])
        ).all()
    
    return jsonify([{
        'id': s.id,
        'title': s.topic,
        'start': s.scheduled_at.isoformat(),
        'end': (s.scheduled_at + timedelta(hours=1)).isoformat(),
        'status': s.status
    } for s in sessions])


@bp.route('/sessions/<int:session_id>/calendar-reminder')
@login_required
def send_calendar_reminder(session_id):
    """Manually trigger calendar reminder"""
    session = Session.query.get_or_404(session_id)
    
    # Verify authorization
    if current_user.id not in [session.student_id, session.mentor_id]:
        abort(403)
    
    result = CalendarService.send_calendar_reminder(current_user.id, days_before=1)
    
    if result['success']:
        flash(f"{result['reminders_sent']} reminder(s) sent!", 'success')
    else:
        flash(f"Error: {result['error']}", 'error')
    
    return redirect(url_for('mentorship.my_sessions'))
