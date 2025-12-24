from flask import render_template, redirect, url_for, flash
from flask_login import login_required, current_user
from app.admin import bp
from app.models import User, Session
from app import db


def admin_required(f):
    def wrapper(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin():
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    wrapper.__name__ = f.__name__
    return wrapper


@bp.route('/')
@login_required
@admin_required
def dashboard():
    users = User.query.all()
    sessions = Session.query.order_by(Session.created_at.desc()).limit(10).all()
    stats = {
        'total_users': User.query.count(),
        'active_mentors': User.query.filter_by(role='mentor').count(),
        'sessions': Session.query.count()
    }
    return render_template('admin/dashboard.html', users=users, sessions=sessions, stats=stats)


@bp.route('/users/<int:user_id>/deactivate')
@login_required
@admin_required
def deactivate(user_id):
    user = User.query.get_or_404(user_id)
    user.role = 'deactivated'
    db.session.commit()
    flash('User deactivated')
    return redirect(url_for('admin.dashboard'))
