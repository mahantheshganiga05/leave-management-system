from flask import Blueprint, render_template, redirect, url_for
from flask_login import login_required, current_user

main_bp = Blueprint('main', __name__)


@main_bp.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    return render_template('index.html')


@main_bp.route('/dashboard')
@login_required
def dashboard():
    role = current_user.role_name
    if role == 'admin':
        return redirect(url_for('admin.dashboard'))
    if role == 'faculty':
        return redirect(url_for('faculty.dashboard'))
    if role == 'student':
        return redirect(url_for('student.dashboard'))
    if role == 'parent':
        return redirect(url_for('parent.dashboard'))
    return redirect(url_for('auth.login'))


@main_bp.route('/notifications')
@login_required
def notifications():
    from app.models import Notification
    from app.extensions import db
    items = Notification.query.filter_by(user_id=current_user.id) \
        .order_by(Notification.created_at.desc()).limit(50).all()
    for n in items:
        n.is_read = True
    db.session.commit()
    return render_template('notifications.html', notifications=items)
