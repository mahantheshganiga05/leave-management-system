import os
import uuid
import socket
import threading
from functools import wraps
from flask import abort, current_app, request
from flask_login import current_user
from flask_mail import Message
from app.extensions import db, mail
from app.models import Notification, AuditLog

# --- Force IPv4 for outbound connections (fixes "Network is unreachable"
# on Render's free tier, which has no IPv6 route to Gmail's SMTP server) ---
_original_getaddrinfo = socket.getaddrinfo

def _getaddrinfo_ipv4_only(host, port, family=0, type=0, proto=0, flags=0):
    return _original_getaddrinfo(host, port, socket.AF_INET, type, proto, flags)

socket.getaddrinfo = _getaddrinfo_ipv4_only


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
    with app.app_context():
        try:
            mail.send(msg)
            print(f"[EMAIL SENT] To: {msg.recipients} | Subject: {msg.subject}", flush=True)
        except Exception as exc:
            print(f"[EMAIL FAILED] To: {msg.recipients} | Subject: {msg.subject} | Error: {exc}", flush=True)


def send_email(subject, recipients, body_html):
    msg = Message(subject=subject, recipients=recipients, html=body_html)
    app = current_app._get_current_object()
    thread = threading.Thread(target=_send_async_email, args=(app, msg))
    thread.daemon = True
    thread.start()
    print(f"[EMAIL QUEUED] To: {recipients} | Subject: {subject}", flush=True)