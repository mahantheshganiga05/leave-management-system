import os
import uuid
import threading
from functools import wraps
from flask import abort, current_app, request
from flask_login import current_user
from flask_mail import Message
from app.extensions import db, mail
from app.models import Notification, AuditLog


def role_required(*roles):
    """Restrict a view to one or more role names, e.g. @role_required('admin')."""
    def decorator(view_func):
        @wraps(view_func)
        def wrapped(*args, **kwargs):
            if not current_user.is_authenticated:
                abort(401)
            if current_user.role_name not in roles:
                abort(403)
            return view_func(*args, **kwargs)
        return wrapped
    return decorator


def save_upload(file_storage, subfolder=None):
    """Save an uploaded file securely with a randomized filename. Returns (original_name, stored_name)."""
    from werkzeug.utils import secure_filename
    original_name = secure_filename(file_storage.filename)
    ext = original_name.rsplit('.', 1)[-1].lower()
    stored_name = f"{uuid.uuid4().hex}.{ext}"
    folder = current_app.config['UPLOAD_FOLDER']
    if subfolder:
        folder = os.path.join(folder, subfolder)
        os.makedirs(folder, exist_ok=True)
    file_storage.save(os.path.join(folder, stored_name))
    return original_name, stored_name


def allowed_file(filename):
    ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
    return ext in current_app.config['ALLOWED_EXTENSIONS']


def notify(user_id, message, link=None):
    n = Notification(user_id=user_id, message=message, link=link)
    db.session.add(n)
    db.session.commit()
    return n


def log_action(action, user_id=None):
    entry = AuditLog(
        user_id=user_id or (current_user.id if current_user.is_authenticated else None),
        action=action,
        ip_address=request.remote_addr if request else None,
    )
    db.session.add(entry)
    db.session.commit()
    return entry


def _send_async_email(app, msg):
    """Runs in a background thread so a slow/hanging SMTP server can NEVER
    block or crash the request-handling worker."""
    with app.app_context():
        try:
            mail.send(msg)
            app.logger.info(f"[EMAIL SENT] To: {msg.recipients} | Subject: {msg.subject}")
        except Exception as exc:
            app.logger.warning(f"[EMAIL FAILED] To: {msg.recipients} | Subject: {msg.subject} | Error: {exc}")


def send_email(subject, recipients, body_html):
    """Queue an email to be sent in the background. Returns immediately —
    the HTTP request never waits on the SMTP connection."""
    msg = Message(subject=subject, recipients=recipients, html=body_html)
    app = current_app._get_current_object()
    thread = threading.Thread(target=_send_async_email, args=(app, msg))
    thread.daemon = True
    thread.start()
    current_app.logger.info(f"[EMAIL QUEUED] To: {recipients} | Subject: {subject}")