from datetime import datetime, timedelta
from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_user, logout_user, login_required, current_user
from sqlalchemy import or_

from app.extensions import db, limiter
from app.models import User
from app.forms import LoginForm, ForgotPasswordForm, ResetPasswordForm, ChangePasswordForm
from app.utils import send_email, log_action

auth_bp = Blueprint('auth', __name__, template_folder='../templates/auth')

MAX_FAILED_ATTEMPTS = 5
LOCKOUT_MINUTES = 15


@auth_bp.route('/login', methods=['GET', 'POST'])
@limiter.limit("10 per minute")
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))

    form = LoginForm()
    if form.validate_on_submit():
        identifier = form.username.data.strip()
        user = User.query.filter(
            or_(User.username == identifier, User.email == identifier)
        ).first()

        if user and user.locked_until and user.locked_until > datetime.utcnow():
            flash(f'Account locked due to repeated failed attempts. Try again after '
                  f'{user.locked_until.strftime("%H:%M:%S")}.', 'danger')
            return render_template('auth/login.html', form=form)

        if user and user.check_password(form.password.data):
            if not user.is_active_account:
                flash('Your account has been deactivated. Contact the administrator.', 'danger')
                return render_template('auth/login.html', form=form)

            user.failed_login_attempts = 0
            user.locked_until = None
            user.last_login = datetime.utcnow()
            db.session.commit()

            login_user(user, remember=form.remember.data)
            log_action(f"User {user.username} logged in")
            flash(f'Welcome back, {user.full_name}!', 'success')

            next_page = request.args.get('next')
            return redirect(next_page or url_for('main.dashboard'))
        else:
            if user:
                user.failed_login_attempts = (user.failed_login_attempts or 0) + 1
                if user.failed_login_attempts >= MAX_FAILED_ATTEMPTS:
                    user.locked_until = datetime.utcnow() + timedelta(minutes=LOCKOUT_MINUTES)
                    flash('Too many failed attempts. Account locked for 15 minutes.', 'danger')
                db.session.commit()
            flash('Invalid username/email or password.', 'danger')

    return render_template('auth/login.html', form=form)


@auth_bp.route('/logout')
@login_required
def logout():
    log_action(f"User {current_user.username} logged out")
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth.login'))


@auth_bp.route('/forgot-password', methods=['GET', 'POST'])
@limiter.limit("5 per minute")
def forgot_password():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))

    form = ForgotPasswordForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data.strip().lower()).first()
        if user:
            token = user.get_reset_token()
            reset_url = url_for('auth.reset_password', token=token, _external=True)
            send_email(
                subject='Password Reset Request - Leave Management System',
                recipients=[user.email],
                body_html=render_template('auth/email_reset_password.html',
                                           user=user, reset_url=reset_url)
            )
        # Always show the same message to prevent user enumeration
        flash('If that email exists in our system, a password reset link has been sent.', 'info')
        return redirect(url_for('auth.login'))

    return render_template('auth/forgot_password.html', form=form)


@auth_bp.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    user = User.verify_reset_token(token)
    if not user:
        flash('That reset link is invalid or has expired.', 'danger')
        return redirect(url_for('auth.forgot_password'))

    form = ResetPasswordForm()
    if form.validate_on_submit():
        user.set_password(form.password.data)
        user.failed_login_attempts = 0
        user.locked_until = None
        db.session.commit()
        log_action(f"User {user.username} reset their password")
        flash('Your password has been reset. You may now log in.', 'success')
        return redirect(url_for('auth.login'))

    return render_template('auth/reset_password.html', form=form)


@auth_bp.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    form = ChangePasswordForm()
    if form.validate_on_submit():
        if not current_user.check_password(form.current_password.data):
            flash('Current password is incorrect.', 'danger')
        else:
            current_user.set_password(form.new_password.data)
            db.session.commit()
            log_action(f"User {current_user.username} changed their password")
            flash('Password changed successfully.', 'success')
            return redirect(url_for('main.dashboard'))

    return render_template('auth/change_password.html', form=form)


@auth_bp.route('/verify-email/<token>')
def verify_email(token):
    user = User.verify_email_token(token)
    if not user:
        flash('That verification link is invalid or has expired.', 'danger')
        return redirect(url_for('auth.login'))
    user.email_verified = True
    db.session.commit()
    flash('Your email has been verified. You may now log in.', 'success')
    return redirect(url_for('auth.login'))
