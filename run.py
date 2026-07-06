import os
from app import create_app
from app.extensions import db
from app.models import (
    User, Role, Department, Course, Student, Faculty, Parent,
    LeaveRequest, LeaveDocument, Attendance, Notification, AuditLog,
    Holiday, AcademicYear, Settings
)

app = create_app(os.environ.get('FLASK_CONFIG', 'production'))

# ---------------------------------------------------------------------------
# Render's free plan has no Shell access, so we can't run
# `flask db upgrade` / `python seed.py` manually there. This block does it
# automatically on startup instead. Both operations are idempotent/safe to
# repeat (db.create_all only creates missing tables; seed.py's run_seed
# checks for existing records before inserting anything).
#
# Set RUN_SEED_ON_START=true as an environment variable in Render to also
# populate demo data on this startup. You can remove that env var afterward
# (or leave it — it's harmless since it won't create duplicates).
# ---------------------------------------------------------------------------
with app.app_context():
    db.create_all()

    if os.environ.get('RUN_SEED_ON_START', 'false').lower() == 'true':
        from seed import run_seed
        run_seed(app)


@app.shell_context_processor
def make_shell_context():
    """Enables `flask shell` to have all models pre-imported."""
    return dict(
        db=db, User=User, Role=Role, Department=Department, Course=Course,
        Student=Student, Faculty=Faculty, Parent=Parent, LeaveRequest=LeaveRequest,
        LeaveDocument=LeaveDocument, Attendance=Attendance, Notification=Notification,
        AuditLog=AuditLog, Holiday=Holiday, AcademicYear=AcademicYear, Settings=Settings
    )


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=app.config.get('DEBUG', False))