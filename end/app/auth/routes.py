from flask import render_template, redirect, url_for, flash, request
from flask_login import current_user, login_user, logout_user, login_required
from werkzeug.urls import url_parse
from app import db
from app.auth import bp
from app.auth.forms import LoginForm, RegistrationForm, ResetRequestForm, ResetPasswordForm
from app.models import User, StudentProfile, MentorProfile


@bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user is None or not user.check_password(form.password.data):
            flash('Invalid email or password')
            return redirect(url_for('auth.login'))
        login_user(user, remember=form.remember_me.data)
        next_page = request.args.get('next')
        if not next_page or url_parse(next_page).netloc != '':
            next_page = url_for('index')
        return redirect(next_page)
    return render_template('auth/login.html', form=form)


@bp.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('index'))


@bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(name=form.name.data, email=form.email.data, role=form.role.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()

        # create empty profile
        if user.is_student():
            profile = StudentProfile(user_id=user.id)
            db.session.add(profile)
        elif user.is_mentor():
            profile = MentorProfile(user_id=user.id)
            db.session.add(profile)
        db.session.commit()

        flash('Registration successful. You can now log in.')
        return redirect(url_for('auth.login'))
    return render_template('auth/register.html', form=form)


@bp.route('/reset_password_request', methods=['GET', 'POST'])
def reset_password_request():
    form = ResetRequestForm()
    if form.validate_on_submit():
        # In real app: send email; here we simulate
        user = User.query.filter_by(email=form.email.data).first()
        if user:
            token = f'reset-token-for-{user.id}'
            print(f'Password reset link: /auth/reset_password/{token}')
            flash('A password reset link was printed to the server console (simulated email).')
        else:
            flash('If that email exists, a reset link was sent (simulated).')
        return redirect(url_for('auth.login'))
    return render_template('auth/reset_request.html', form=form)


@bp.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    # token handling is simulated for MVP
    form = ResetPasswordForm()
    if form.validate_on_submit():
        # parse id from token
        try:
            user_id = int(token.split('-')[-1])
        except Exception:
            flash('Invalid token')
            return redirect(url_for('auth.login'))
        user = User.query.get(user_id)
        if user:
            user.set_password(form.password.data)
            db.session.commit()
            flash('Your password has been reset.')
            return redirect(url_for('auth.login'))
        else:
            flash('Invalid token')
            return redirect(url_for('auth.login'))
    return render_template('auth/reset_password.html', form=form)
