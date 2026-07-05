"""
Quick recovery tool: reset the password for a specific username.

Usage:
    python reset_user_password.py <username> <new_password>

Example:
    python reset_user_password.py drnewfaculty MyNewPass123
"""
import sys
from app import create_app
from app.extensions import db
from app.models import User

if len(sys.argv) != 3:
    print("Usage: python reset_user_password.py <username> <new_password>")
    sys.exit(1)

username = sys.argv[1]
new_password = sys.argv[2]

app = create_app('development')
with app.app_context():
    user = User.query.filter_by(username=username).first()
    if not user:
        print(f"No user found with username '{username}'.")
        sys.exit(1)
    user.set_password(new_password)
    user.failed_login_attempts = 0
    user.locked_until = None
    db.session.commit()
    print(f"Password for '{username}' has been reset successfully.")
    print(f"You can now log in with username='{username}' and password='{new_password}'.")
