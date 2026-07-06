"""
Seed script for the Leave Management System.

Run after migrations are applied:
    python seed.py

Creates:
  - Roles (admin, faculty, student, parent)
  - Departments & Courses
  - One admin account
  - A few faculty, student, and parent accounts (linked together)
  - A handful of sample leave requests and attendance records
  - A few holidays and the current academic year

All demo accounts use the password: Passw0rd!123
"""
import random
from datetime import date, timedelta, datetime

from app import create_app
from app.extensions import db
from app.models import (
    Role, User, Department, Course, Faculty, Parent, Student,
    LeaveRequest, Attendance, Holiday, AcademicYear
)

DEMO_PASSWORD = "Passw0rd!123"


def get_or_create_role(name):
    role = Role.query.filter_by(name=name).first()
    if not role:
        role = Role(name=name)
        db.session.add(role)
        db.session.flush()
    return role


def create_user(username, email, full_name, role, phone=None):
    existing = User.query.filter_by(username=username).first()
    if existing:
        return existing
    user = User(
        username=username, email=email, full_name=full_name,
        role_id=role.id, phone=phone, email_verified=True, is_active_account=True
    )
    user.set_password(DEMO_PASSWORD)
    db.session.add(user)
    db.session.flush()
    return user

def run_seed(app=None):
    if app is None:
        app = create_app('development')
    with app.app_context():
        print("Seeding database...")

        # --- Roles ---
        admin_role = get_or_create_role('admin')
        faculty_role = get_or_create_role('faculty')
        student_role = get_or_create_role('student')
        parent_role = get_or_create_role('parent')
        db.session.commit()

        # --- Admin account ---
        admin_user = create_user('admin', 'admin@college.edu', 'System Administrator', admin_role, '9999999999')
        db.session.commit()

        # --- Departments ---
        dept_data = [
            ('Computer Applications', 'BCA'),
            ('Computer Science', 'CSE'),
            ('Commerce', 'COM'),
        ]
        departments = {}
        for name, code in dept_data:
            dept = Department.query.filter_by(code=code).first()
            if not dept:
                dept = Department(name=name, code=code)
                db.session.add(dept)
                db.session.flush()
            departments[code] = dept
        db.session.commit()

        # --- Courses ---
        course_data = [
            ('Bachelor of Computer Applications', 'BCA', 'BCA', 3),
            ('B.Sc Computer Science', 'BSCCS', 'CSE', 3),
            ('Bachelor of Commerce', 'BCOM', 'COM', 3),
        ]
        courses = {}
        for name, code, dept_code, duration in course_data:
            course = Course.query.filter_by(code=code).first()
            if not course:
                course = Course(name=name, code=code, department_id=departments[dept_code].id,
                                 duration_years=duration)
                db.session.add(course)
                db.session.flush()
            courses[code] = course
        db.session.commit()

        # --- Faculty ---
        faculty_seed = [
            ('drsharma', 'sharma@college.edu', 'Dr. Ramesh Sharma', 'FAC001', 'BCA', 'Associate Professor'),
            ('profkumar', 'kumar@college.edu', 'Prof. Anita Kumar', 'FAC002', 'CSE', 'Assistant Professor'),
        ]
        faculty_members = {}
        for username, email, name, emp_code, dept_code, designation in faculty_seed:
            user = create_user(username, email, name, faculty_role, '9876500000')
            faculty = Faculty.query.filter_by(user_id=user.id).first()
            if not faculty:
                faculty = Faculty(user_id=user.id, employee_code=emp_code,
                                   department_id=departments[dept_code].id, designation=designation)
                db.session.add(faculty)
                db.session.flush()
            faculty_members[username] = faculty
        db.session.commit()

        # --- Parents ---
        parent_seed = [
            ('rajparent', 'raj.parent@example.com', 'Raj Mehta', 'Business'),
            ('sunitaparent', 'sunita.parent@example.com', 'Sunita Rao', 'Teacher'),
        ]
        parents = {}
        for username, email, name, occupation in parent_seed:
            user = create_user(username, email, name, parent_role, '9988700000')
            parent = Parent.query.filter_by(user_id=user.id).first()
            if not parent:
                parent = Parent(user_id=user.id, occupation=occupation)
                db.session.add(parent)
                db.session.flush()
            parents[username] = parent
        db.session.commit()

        # --- Students ---
        student_seed = [
            ('anitastudent', 'anita.student@example.com', 'Anita Singh', 'BCA2401', 'BCA', 'BCA', 3,
             'drsharma', 'rajparent'),
            ('vikramstudent', 'vikram.student@example.com', 'Vikram Patel', 'BCA2402', 'BCA', 'BCA', 3,
             'drsharma', 'sunitaparent'),
            ('priyastudent', 'priya.student@example.com', 'Priya Nair', 'CSE2401', 'CSE', 'BSCCS', 1,
             'profkumar', None),
        ]
        students = {}
        for (username, email, name, roll_no, dept_code, course_code, sem,
             faculty_key, parent_key) in student_seed:
            user = create_user(username, email, name, student_role, '9123400000')
            student = Student.query.filter_by(user_id=user.id).first()
            if not student:
                student = Student(
                    user_id=user.id, roll_no=roll_no, department_id=departments[dept_code].id,
                    course_id=courses[course_code].id, semester=sem,
                    faculty_advisor_id=faculty_members[faculty_key].id if faculty_key else None,
                    parent_id=parents[parent_key].id if parent_key else None,
                )
                db.session.add(student)
                db.session.flush()
            students[username] = student
        db.session.commit()

        # --- Holidays ---
        year = date.today().year
        holiday_seed = [
            ("New Year's Day", date(year, 1, 1)),
            ("Republic Day", date(year, 1, 26)),
            ("Independence Day", date(year, 8, 15)),
            ("Gandhi Jayanti", date(year, 10, 2)),
        ]
        for name, hdate in holiday_seed:
            if not Holiday.query.filter_by(date=hdate).first():
                db.session.add(Holiday(name=name, date=hdate))
        db.session.commit()

        # --- Academic Year ---
        if not AcademicYear.query.filter_by(is_current=True).first():
            db.session.add(AcademicYear(
                year_label=f"{year}-{year + 1}",
                start_date=date(year, 6, 1),
                end_date=date(year + 1, 5, 31),
                is_current=True
            ))
            db.session.commit()

        # --- Sample leave requests ---
        if LeaveRequest.query.count() == 0:
            anita = students['anitastudent']
            vikram = students['vikramstudent']

            lr1 = LeaveRequest(
                student_id=anita.id, leave_type='Casual Leave',
                from_date=date.today() + timedelta(days=2),
                to_date=date.today() + timedelta(days=3),
                reason='Attending a family function.', status='pending'
            )
            lr2 = LeaveRequest(
                student_id=vikram.id, leave_type='Sick Leave',
                from_date=date.today() - timedelta(days=5),
                to_date=date.today() - timedelta(days=3),
                reason='Fever and viral infection.', status='approved',
                faculty_id=faculty_members['drsharma'].id,
                faculty_action_at=datetime.utcnow() - timedelta(days=4),
                admin_id=admin_user.id,
                admin_action_at=datetime.utcnow() - timedelta(days=4),
            )
            lr3 = LeaveRequest(
                student_id=anita.id, leave_type='Sports Leave',
                from_date=date.today() - timedelta(days=20),
                to_date=date.today() - timedelta(days=18),
                reason='Inter-college basketball tournament.', status='rejected',
                faculty_id=faculty_members['drsharma'].id,
                faculty_remarks='Clashes with internal exams.',
                faculty_action_at=datetime.utcnow() - timedelta(days=19),
            )
            db.session.add_all([lr1, lr2, lr3])
            db.session.commit()

        # --- Sample attendance (last 10 days for each student) ---
        if Attendance.query.count() == 0:
            for student in students.values():
                for i in range(10):
                    day = date.today() - timedelta(days=i)
                    status = random.choices(['present', 'absent', 'leave'], weights=[85, 10, 5])[0]
                    db.session.add(Attendance(student_id=student.id, date=day, status=status))
            db.session.commit()

        print("\nSeed complete!\n")
        print("Demo login credentials (password for all: %s)\n" % DEMO_PASSWORD)
        print("  Admin    -> username: admin          ")
        print("  Faculty  -> username: drsharma / profkumar")
        print("  Student  -> username: anitastudent / vikramstudent / priyastudent")
        print("  Parent   -> username: rajparent / sunitaparent")


if __name__ == '__main__':
    run_seed()
