import os
import uuid
import threading
from functools import wraps
from flask import abort, current_app, request
from flask_login import current_user
from app.extensions import db
from app.models import Notification, AuditLog

import sib_api_v3_sdk
from sib_api_v3_sdk.rest import ApiException

_brevo_config = sib_api_v3_sdk.Configuration()
_brevo_config.api_key['api-key'] = os.environ.get('BREVO_API_KEY')

# The sender email MUST be the one you verified in Brevo's
# Settings -> Senders, Domains & Dedicated IPs -> Senders tab.
BREVO_SENDER_EMAIL = os.environ.get('BREVO_SENDER_EMAIL', 'mahantheshganiga05@gmail.com')
BREVO_SENDER_NAME = 'Leave Management System'


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


def _send_async_email(app, subject, recipients, body_html):
    """Runs in a background thread and uses Brevo's HTTPS API (port 443)
    instead of raw SMTP (port 587), because Render's free tier blocks
    outbound SMTP traffic entirely. This also means the request never
    waits on the email call, so a slow/failing send can never crash or
    hang the request-handling worker."""
    with app.app_context():
        try:
            api_instance = sib_api_v3_sdk.TransactionalEmailsApi(
                sib_api_v3_sdk.ApiClient(_brevo_config)
            )
            send_smtp_email = sib_api_v3_sdk.SendSmtpEmail(
                to=[{"email": r} for r in recipients],
                sender={"name": BREVO_SENDER_NAME, "email": BREVO_SENDER_EMAIL},
                subject=subject,
                html_content=body_html,
            )
            api_instance.send_transac_email(send_smtp_email)
            print(f"[EMAIL SENT] To: {recipients} | Subject: {subject}", flush=True)
        except ApiException as exc:
            print(f"[EMAIL FAILED] To: {recipients} | Subject: {subject} | Error: {exc}", flush=True)
        except Exception as exc:
            print(f"[EMAIL FAILED] To: {recipients} | Subject: {subject} | Error: {exc}", flush=True)


def send_email(subject, recipients, body_html):
    """Queue an email to be sent in the background via Brevo's API.
    Returns immediately — the HTTP request never waits on the email send."""
    app = current_app._get_current_object()
    thread = threading.Thread(target=_send_async_email, args=(app, subject, recipients, body_html))
    thread.daemon = True
    thread.start()
    print(f"[EMAIL QUEUED] To: {recipients} | Subject: {subject}", flush=True)