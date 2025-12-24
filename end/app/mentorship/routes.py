from flask import render_template, redirect, url_for, flash, request, abort
from flask_login import current_user, login_required
from app import db, cache
from app.mentorship import bp
from app.mentorship.forms import ProfileForm, MentorProfileForm, BookingForm, MessageForm, ReviewForm
from app.models import User, MentorProfile, StudentProfile, Session, Message, Review, Notification
from datetime import datetime


def role_required(role):
    def decorator(f):
        def wrapper(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for('auth.login'))
            if getattr(current_user, 'role', None) != role:
                abort(403)
            return f(*args, **kwargs)
        wrapper.__name__ = f.__name__
        return wrapper
    return decorator


@bp.route('/profile')
@login_required
def profile():
    if current_user.is_student():
        profile = current_user.student_profile
        return render_template('profile.html', profile=profile)
    elif current_user.is_mentor():
        profile = current_user.mentor_profile
        return render_template('profile.html', profile=profile)
    else:
        return render_template('profile.html', profile=None)


@bp.route('/profile/edit', methods=['GET', 'POST'])
@login_required
def edit_profile():
    if current_user.is_student():
        form = ProfileForm(obj=current_user.student_profile)
        if form.validate_on_submit():
            p = current_user.student_profile
            p.academic_year = form.academic_year.data
            p.course = form.course.data
            p.interests = form.interests.data
            p.goals = form.goals.data
            db.session.commit()
            cache.clear()  # Invalidate cache on profile update
            flash('Profile updated')
            return redirect(url_for('mentorship.profile'))
        return render_template('edit_profile.html', form=form)
    elif current_user.is_mentor():
        form = MentorProfileForm(obj=current_user.mentor_profile)
        if form.validate_on_submit():
            p = current_user.mentor_profile
            p.title = form.title.data
            p.skills = form.skills.data
            p.years_of_experience = form.years_of_experience.data
            p.hourly_rate = float(form.hourly_rate.data) if form.hourly_rate.data else None
            p.profile_pic = form.profile_pic.data
            db.session.commit()
            cache.clear()  # Invalidate cache on profile update
            flash('Profile updated')
            return redirect(url_for('mentorship.profile'))
        return render_template('edit_profile.html', form=form)
    else:
        abort(403)


@bp.route('/mentors')
@cache.cached(timeout=3600, query_string=True)
def mentors_list():
    q = request.args.get('q', '')
    min_rating = request.args.get('min_rating')
    mentors = User.query.filter_by(role='mentor')
    if q:
        mentors = mentors.filter(User.name.ilike(f'%{q}%') | MentorProfile.skills.ilike(f'%{q}%'))
    mentors = mentors.all()
    return render_template('mentors/list.html', mentors=mentors)


@bp.route('/mentors/<int:user_id>', methods=['GET', 'POST'])
@cache.cached(timeout=1800, query_string=False, unless=lambda: request.method == 'POST' or not current_user.is_authenticated)
def mentor_detail(user_id):
    mentor = User.query.get_or_404(user_id)
    if mentor.role != 'mentor':
        abort(404)
    form = BookingForm()
    review_form = ReviewForm()
    if form.validate_on_submit() and current_user.is_authenticated and current_user.is_student():
        session = Session(student_id=current_user.id, mentor_id=mentor.id,
                          topic=form.topic.data, description=form.description.data,
                          scheduled_at=form.scheduled_at.data, status='requested')
        db.session.add(session)
        db.session.commit()
        notif = Notification(user_id=mentor.id, message=f'New session request from {current_user.name}')
        db.session.add(notif)
        db.session.commit()
        cache.clear()  # Invalidate cache on new session booking
        flash('Session request sent')
        return redirect(url_for('mentorship.mentor_detail', user_id=mentor.id))
    return render_template('mentors/detail.html', mentor=mentor, form=form, review_form=review_form)


@bp.route('/sessions')
@login_required
@cache.cached(timeout=600, query_string=False)
def my_sessions():
    if current_user.is_student():
        sessions = Session.query.filter_by(student_id=current_user.id).order_by(Session.scheduled_at.desc()).all()
    elif current_user.is_mentor():
        sessions = Session.query.filter_by(mentor_id=current_user.id).order_by(Session.scheduled_at.desc()).all()
    else:
        sessions = []
    return render_template('sessions/list.html', sessions=sessions)


@bp.route('/requests')
@login_required
def requests():
    if current_user.is_mentor():
        incoming = Session.query.filter_by(mentor_id=current_user.id, status='requested').all()
        return render_template('mentors/requests.html', requests=incoming)
    elif current_user.is_student():
        outgoing = Session.query.filter_by(student_id=current_user.id).all()
        return render_template('sessions/list.html', sessions=outgoing)
    else:
        return redirect(url_for('index'))


@bp.route('/requests/<int:session_id>/respond/<action>')
@login_required
def respond_request(session_id, action):
    s = Session.query.get_or_404(session_id)
    if not current_user.is_mentor() or s.mentor_id != current_user.id:
        abort(403)
    if action == 'accept':
        s.status = 'accepted'
        db.session.add(Notification(user_id=s.student_id, message=f'Your request was accepted by {current_user.name}'))
    elif action == 'decline':
        s.status = 'declined'
        db.session.add(Notification(user_id=s.student_id, message=f'Your request was declined by {current_user.name}'))
    db.session.commit()
    cache.clear()  # Invalidate cache on session status change
    flash('Response recorded')
    return redirect(url_for('mentorship.requests'))


@bp.route('/messages')
@login_required
def messages_list():
    from sqlalchemy import desc, func, or_
    
    # Get latest message from each conversation partner
    subquery = db.session.query(
        func.max(Message.id).label('id')
    ).filter(
        or_(
            Message.sender_id == current_user.id,
            Message.receiver_id == current_user.id
        )
    ).group_by(
        or_(
            Message.receiver_id,
            Message.sender_id
        )
    ).subquery()
    
    conversations = db.session.query(Message).filter(
        Message.id.in_(db.session.query(subquery.c.id))
    ).order_by(desc(Message.created_at)).all()
    
    # Extract unique users and their latest message info
    user_messages = {}
    for msg in conversations:
        other_id = msg.receiver_id if msg.sender_id == current_user.id else msg.sender_id
        if other_id not in user_messages:
            user_messages[other_id] = msg
    
    users_data = []
    for user_id, msg in user_messages.items():
        user = User.query.get(user_id)
        if user:
            users_data.append({
                'user': user,
                'latest_message': msg,
                'is_read': msg.receiver_id != current_user.id or getattr(msg, 'is_read', True)
            })
    
    return render_template('messages/list.html', users_data=users_data)


@bp.route('/messages/<int:user_id>', methods=['GET', 'POST'])
@login_required
def conversation(user_id):
    other = User.query.get_or_404(user_id)
    if other.id == current_user.id:
        flash('Cannot message yourself', 'error')
        return redirect(url_for('mentorship.messages_list'))
    
    form = MessageForm()
    if form.validate_on_submit():
        try:
            # Check message length
            if len(form.content.data.strip()) == 0:
                flash('Message cannot be empty', 'error')
            else:
                m = Message(
                    sender_id=current_user.id,
                    receiver_id=other.id,
                    content=form.content.data.strip()
                )
                db.session.add(m)
                db.session.add(Notification(
                    user_id=other.id,
                    message=f'New message from {current_user.name}'
                ))
                db.session.commit()
                flash('Message sent', 'success')
                form.content.data = ''
        except Exception as e:
            db.session.rollback()
            flash('Failed to send message', 'error')
    
    # Optimized query with proper indexing
    thread = Message.query.filter(
        db.or_(
            db.and_(Message.sender_id == current_user.id, Message.receiver_id == other.id),
            db.and_(Message.sender_id == other.id, Message.receiver_id == current_user.id)
        )
    ).order_by(Message.created_at.asc()).all()
    
    return render_template('messages/conversation.html', other=other, thread=thread, form=form)


@bp.route('/reviews/<int:session_id>', methods=['POST'])
@login_required
def leave_review(session_id):
    s = Session.query.get_or_404(session_id)
    if s.student_id != current_user.id:
        abort(403)
    form = ReviewForm()
    if form.validate_on_submit():
        r = Review(session_id=s.id, student_id=current_user.id, mentor_id=s.mentor_id, rating=int(form.rating.data), comment=form.comment.data)
        s.status = 'completed'
        db.session.add(r)
        db.session.commit()
        cache.clear()  # Invalidate cache on review submission
        flash('Review submitted')
    return redirect(url_for('mentorship.my_sessions'))
