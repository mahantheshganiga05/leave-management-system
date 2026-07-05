"""
Quick test to verify your real email (SMTP) configuration actually works,
before relying on it inside the full app.

Usage:
    python test_email_config.py your-email@gmail.com

This sends a real test email to the address you provide, using whatever
MAIL_* settings are currently in your .env file.
"""
import sys
from app import create_app
from app.extensions import mail
from flask_mail import Message

if len(sys.argv) != 2:
    print("Usage: python test_email_config.py your-email@gmail.com")
    sys.exit(1)

recipient = sys.argv[1]

app = create_app('development')

with app.app_context():
    print("Current mail configuration being used:")
    print(f"  MAIL_SERVER   = {app.config.get('MAIL_SERVER')}")
    print(f"  MAIL_PORT     = {app.config.get('MAIL_PORT')}")
    print(f"  MAIL_USE_TLS  = {app.config.get('MAIL_USE_TLS')}")
    print(f"  MAIL_USERNAME = {app.config.get('MAIL_USERNAME')}")
    print(f"  MAIL_SUPPRESS_SEND = {app.config.get('MAIL_SUPPRESS_SEND')}")
    print()

    if app.config.get('MAIL_SUPPRESS_SEND'):
        print("MAIL_USERNAME is not set in your .env file, so emails are being")
        print("suppressed (logged only, not actually sent). Set MAIL_USERNAME")
        print("and MAIL_PASSWORD in .env first, then run this script again.")
        sys.exit(1)

    try:
        msg = Message(
            subject='Test Email - Leave Management System',
            recipients=[recipient],
            html='<h3>It works!</h3><p>Your email configuration is set up correctly.</p>'
        )
        mail.send(msg)
        print(f"SUCCESS: Test email sent to {recipient}. Check that inbox now.")
    except Exception as exc:
        print(f"FAILED to send email: {exc}")
        print()
        print("Common causes:")
        print("  - Using your normal Gmail password instead of an App Password")
        print("  - 2-Step Verification not enabled on the Gmail account")
        print("    (App Passwords require 2-Step Verification to be turned on)")
        print("  - Typo in MAIL_USERNAME or MAIL_PASSWORD in .env")
        sys.exit(1)
