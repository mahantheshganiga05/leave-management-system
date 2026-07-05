from datetime import datetime, date
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from itsdangerous import URLSafeTimedSerializer
from flask import current_app
from app.extensions import db


# ---------------------------------------------------------------------------
# Roles / Users
# ---------------------------------------------------------------------------

class Role(db.Model):
    __tablename__ = 'roles'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(20), unique=True, nullable=False)  # admin, faculty, student, parent

    users = db.relationship('User', backref='role', lazy=True)

    def __repr__(self):
        return f'<Role {self.name}>'


class User(db.Model, UserMixin):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    full_name = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(20))
    role_id = db.Column(db.Integer, db.ForeignKey('roles.id'), nullable=False)

    is_active_account = db.Column(db.Boolean, default=True)
    email_verified = db.Column(db.Boolean, default=False)
    failed_login_attempts = db.Column(db.Integer, default=0)
    locked_until = db.Column(db.DateTime, nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime, nullable=True)

    # profile relationships (one will be populated depending on role)
    student_profile = db.relationship('Student', backref='user', uselist=False,
                                       foreign_keys='Student.user_id', cascade='all, delete-orphan')
    faculty_profile = db.relationship('Faculty', backref='user', uselist=False,
                                       foreign_keys='Faculty.user_id', cascade='all, delete-orphan')
    parent_profile = db.relationship('Parent', backref='user', uselist=False,
                                      foreign_keys='Parent.user_id', cascade='all, delete-orphan')

    notifications = db.relationship('Notification', backref='user', lazy='dynamic',
                                     cascade='all, delete-orphan')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def get_reset_token(self, expires_sec=1800):
        s = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
        return s.dumps({'user_id': self.id}, salt='password-reset-salt')

    @staticmethod
    def verify_reset_token(token, expires_sec=1800):
        s = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
        try:
            data = s.loads(token, salt='password-reset-salt', max_age=expires_sec)
        except Exception:
            return None
        return User.query.get(data.get('user_id'))

    def get_email_verify_token(self):
        s = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
        return s.dumps({'user_id': self.id}, salt='email-verify-salt')

    @staticmethod
    def verify_email_token(token, expires_sec=86400):
        s = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
        try:
            data = s.loads(token, salt='email-verify-salt', max_age=expires_sec)
        except Exception:
            return None
        return User.query.get(data.get('user_id'))

    @property
    def is_active(self):
        return self.is_active_account

    @property
    def role_name(self):
        return self.role.name if self.role else None

    def __repr__(self):
        return f'<User {self.username} ({self.role_name})>'


# ---------------------------------------------------------------------------
# Academic structure
# ---------------------------------------------------------------------------

class Department(db.Model):
    __tablename__ = 'departments'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), unique=True, nullable=False)
    code = db.Column(db.String(20), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    courses = db.relationship('Course', backref='department', lazy=True)
    students = db.relationship('Student', backref='department', lazy=True)
    faculty = db.relationship('Faculty', backref='department', lazy=True)

    def __repr__(self):
        return f'<Department {self.code}>'


class Course(db.Model):
    __tablename__ = 'courses'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    code = db.Column(db.String(20), unique=True, nullable=False)
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'), nullable=False)
    duration_years = db.Column(db.Integer, default=3)

    students = db.relationship('Student', backref='course', lazy=True)

    def __repr__(self):
        return f'<Course {self.code}>'


# ---------------------------------------------------------------------------
# Role profiles
# ---------------------------------------------------------------------------

class Faculty(db.Model):
    __tablename__ = 'faculty'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, unique=True)
    employee_code = db.Column(db.String(30), unique=True, nullable=False)
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'), nullable=False)
    designation = db.Column(db.String(80), default='Assistant Professor')

    advisees = db.relationship('Student', backref='faculty_advisor', lazy=True,
                                foreign_keys='Student.faculty_advisor_id')

    def __repr__(self):
        return f'<Faculty {self.employee_code}>'


class Parent(db.Model):
    __tablename__ = 'parents'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, unique=True)
    occupation = db.Column(db.String(120))

    children = db.relationship('Student', backref='parent', lazy=True,
                                foreign_keys='Student.parent_id')

    def __repr__(self):
        return f'<Parent {self.id}>'


class Student(db.Model):
    __tablename__ = 'students'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, unique=True)
    roll_no = db.Column(db.String(30), unique=True, nullable=False)
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)
    semester = db.Column(db.Integer, default=1)
    faculty_advisor_id = db.Column(db.Integer, db.ForeignKey('faculty.id'), nullable=True)
    parent_id = db.Column(db.Integer, db.ForeignKey('parents.id'), nullable=True)
    admission_year = db.Column(db.Integer, default=lambda: date.today().year)

    leave_requests = db.relationship('LeaveRequest', backref='student', lazy=True,
                                      cascade='all, delete-orphan')
    attendance_records = db.relationship('Attendance', backref='student', lazy=True,
                                          cascade='all, delete-orphan')

    def leave_balance(self, leave_type=None, year=None):
        """Total approved leave days taken (optionally filtered)."""
        year = year or date.today().year
        q = LeaveRequest.query.filter_by(student_id=self.id, status='approved')
        if leave_type:
            q = q.filter_by(leave_type=leave_type)
        total = 0
        for lr in q.all():
            if lr.from_date.year == year:
                total += lr.number_of_days()
        return total

    def __repr__(self):
        return f'<Student {self.roll_no}>'


# ---------------------------------------------------------------------------
# Leave management
# ---------------------------------------------------------------------------

LEAVE_TYPES = [
    'Sick Leave', 'Casual Leave', 'Medical Leave', 'Emergency Leave',
    'Sports Leave', 'Industrial Visit', 'Internship Leave',
    'On Duty Leave', 'Personal Leave',
]

LEAVE_STATUSES = ['pending', 'faculty_approved', 'approved', 'rejected', 'cancelled']

MEDICAL_REQUIRED_TYPES = {'Sick Leave', 'Medical Leave'}


class LeaveRequest(db.Model):
    __tablename__ = 'leave_requests'

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False)
    leave_type = db.Column(db.String(40), nullable=False)
    from_date = db.Column(db.Date, nullable=False)
    to_date = db.Column(db.Date, nullable=False)
    reason = db.Column(db.Text, nullable=False)

    status = db.Column(db.String(20), default='pending')  # see LEAVE_STATUSES

    faculty_id = db.Column(db.Integer, db.ForeignKey('faculty.id', ondelete='SET NULL'), nullable=True)
    faculty_remarks = db.Column(db.Text)
    faculty_action_at = db.Column(db.DateTime)

    admin_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    admin_remarks = db.Column(db.Text)
    admin_action_at = db.Column(db.DateTime)

    applied_on = db.Column(db.DateTime, default=datetime.utcnow)
    cancelled_at = db.Column(db.DateTime)

    documents = db.relationship('LeaveDocument', backref='leave_request', lazy=True,
                                 cascade='all, delete-orphan')

    def number_of_days(self):
        return (self.to_date - self.from_date).days + 1

    def status_label(self):
        return self.status.replace('_', ' ').title()

    def status_badge_class(self):
        return {
            'pending': 'warning',
            'faculty_approved': 'info',
            'approved': 'success',
            'rejected': 'danger',
            'cancelled': 'secondary',
        }.get(self.status, 'secondary')

    def __repr__(self):
        return f'<LeaveRequest {self.id} {self.status}>'


class LeaveDocument(db.Model):
    __tablename__ = 'leave_documents'

    id = db.Column(db.Integer, primary_key=True)
    leave_request_id = db.Column(db.Integer, db.ForeignKey('leave_requests.id'), nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    stored_filename = db.Column(db.String(255), nullable=False)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<LeaveDocument {self.filename}>'


class Attendance(db.Model):
    __tablename__ = 'attendance'

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False)
    date = db.Column(db.Date, nullable=False, default=date.today)
    status = db.Column(db.String(10), nullable=False, default='present')  # present, absent, leave
    marked_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)

    __table_args__ = (db.UniqueConstraint('student_id', 'date', name='uq_student_date'),)

    def __repr__(self):
        return f'<Attendance {self.student_id} {self.date} {self.status}>'


# ---------------------------------------------------------------------------
# Notifications / Audit / Calendar / Settings
# ---------------------------------------------------------------------------

class Notification(db.Model):
    __tablename__ = 'notifications'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    message = db.Column(db.String(255), nullable=False)
    link = db.Column(db.String(255))
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Notification {self.id}>'


class AuditLog(db.Model):
    __tablename__ = 'audit_logs'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    action = db.Column(db.String(255), nullable=False)
    ip_address = db.Column(db.String(45))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', foreign_keys=[user_id])

    def __repr__(self):
        return f'<AuditLog {self.action}>'


class Holiday(db.Model):
    __tablename__ = 'holidays'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    date = db.Column(db.Date, nullable=False, unique=True)

    def __repr__(self):
        return f'<Holiday {self.name} {self.date}>'


class AcademicYear(db.Model):
    __tablename__ = 'academic_year'

    id = db.Column(db.Integer, primary_key=True)
    year_label = db.Column(db.String(20), nullable=False, unique=True)  # e.g. "2025-2026"
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    is_current = db.Column(db.Boolean, default=False)

    def __repr__(self):
        return f'<AcademicYear {self.year_label}>'


class Settings(db.Model):
    __tablename__ = 'settings'

    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(80), unique=True, nullable=False)
    value = db.Column(db.String(255))

    def __repr__(self):
        return f'<Settings {self.key}={self.value}>'
