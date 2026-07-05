import os
from app import create_app
from app.extensions import db
from app.models import (
    User, Role, Department, Course, Student, Faculty, Parent,
    LeaveRequest, LeaveDocument, Attendance, Notification, AuditLog,
    Holiday, AcademicYear, Settings
)

app = create_app(os.environ.get('FLASK_CONFIG', 'development'))


@app.shell_context_processor
def make_shell_context():
    return dict(
        db=db, User=User, Role=Role, Department=Department, Course=Course,
        Student=Student, Faculty=Faculty, Parent=Parent, LeaveRequest=LeaveRequest,
        LeaveDocument=LeaveDocument, Attendance=Attendance, Notification=Notification,
        AuditLog=AuditLog, Holiday=Holiday, AcademicYear=AcademicYear, Settings=Settings
    )


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)