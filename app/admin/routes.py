import os
from datetime import datetime, date
from io import BytesIO

from flask import (Blueprint, render_template, redirect, url_for, flash,
                    request, send_file, abort, session, current_app)
from flask_login import login_required, current_user

from app.extensions import db
from app.models import (
    User, Role, Department, Course, Student, Faculty, Parent,
    LeaveRequest, Notification, AuditLog, Holiday, AcademicYear, Attendance
)
from app.forms import (
    DepartmentForm, CourseForm, CreateFacultyForm, CreateParentForm,
    CreateStudentForm, HolidayForm, AcademicYearForm, LeaveDecisionForm
)
from app.utils import role_required, notify, log_action, send_email

admin_bp = Blueprint('admin', __name__, template_folder='../templates/admin')


def _generate_temp_password():
    import secrets
    return secrets.token_urlsafe(9)


def _get_or_create_role(name):
    role = Role.query.filter_by(name=name).first()
    if not role:
        role = Role(name=name)
        db.session.add(role)
        db.session.flush()
    return role


@admin_bp.before_request
@login_required
def restrict_to_admin():
    if current_user.role_name != 'admin':
        abort(403)


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

@admin_bp.route('/dashboard')
def dashboard():
    total_students = Student.query.count()
    total_faculty = Faculty.query.count()
    total_parents = Parent.query.count()
    total_departments = Department.query.count()

    pending_leaves = LeaveRequest.query.filter(
        LeaveRequest.status.in_(['pending', 'faculty_approved'])
    ).count()
    approved_leaves = LeaveRequest.query.filter_by(status='approved').count()
    rejected_leaves = LeaveRequest.query.filter_by(status='rejected').count()

    recent_leaves = LeaveRequest.query.order_by(LeaveRequest.applied_on.desc()).limit(8).all()

    # Leave type distribution for chart
    from sqlalchemy import func
    from collections import OrderedDict
    from dateutil.relativedelta import relativedelta

    type_counts = db.session.query(
        LeaveRequest.leave_type, func.count(LeaveRequest.id)
    ).group_by(LeaveRequest.leave_type).all()

    # Monthly trend (last 6 months) for chart — computed in Python so it works
    # identically across MySQL, SQLite, Postgres, etc.
    today = date.today()
    month_buckets = OrderedDict()
    for i in range(5, -1, -1):
        bucket_date = (today.replace(day=1) - relativedelta(months=i))
        month_buckets[bucket_date.strftime('%Y-%m')] = 0

    all_applied = db.session.query(LeaveRequest.applied_on).all()
    for (applied_on,) in all_applied:
        key = applied_on.strftime('%Y-%m')
        if key in month_buckets:
            month_buckets[key] += 1

    monthly_counts = list(month_buckets.items())

    return render_template(
        'admin/dashboard.html',
        total_students=total_students,
        total_faculty=total_faculty,
        total_parents=total_parents,
        total_departments=total_departments,
        pending_leaves=pending_leaves,
        approved_leaves=approved_leaves,
        rejected_leaves=rejected_leaves,
        recent_leaves=recent_leaves,
        type_counts=type_counts,
        monthly_counts=monthly_counts,
    )


# ---------------------------------------------------------------------------
# Departments
# ---------------------------------------------------------------------------

@admin_bp.route('/departments', methods=['GET', 'POST'])
def departments():
    form = DepartmentForm()
    if form.validate_on_submit():
        dept = Department(name=form.name.data, code=form.code.data.upper())
        db.session.add(dept)
        db.session.commit()
        log_action(f"Created department {dept.code}")
        flash('Department created successfully.', 'success')
        return redirect(url_for('admin.departments'))

    all_departments = Department.query.order_by(Department.name).all()
    return render_template('admin/departments.html', form=form, departments=all_departments)


@admin_bp.route('/departments/<int:dept_id>/delete', methods=['POST'])
def delete_department(dept_id):
    dept = Department.query.get_or_404(dept_id)
    if dept.students or dept.courses or dept.faculty:
        flash('Cannot delete a department that has students, faculty, or courses.', 'danger')
    else:
        db.session.delete(dept)
        db.session.commit()
        log_action(f"Deleted department {dept.code}")
        flash('Department deleted.', 'info')
    return redirect(url_for('admin.departments'))


# ---------------------------------------------------------------------------
# Courses
# ---------------------------------------------------------------------------

@admin_bp.route('/courses', methods=['GET', 'POST'])
def courses():
    form = CourseForm()
    form.department_id.choices = [(d.id, d.name) for d in Department.query.order_by(Department.name)]

    if form.validate_on_submit():
        course = Course(
            name=form.name.data, code=form.code.data.upper(),
            department_id=form.department_id.data, duration_years=form.duration_years.data
        )
        db.session.add(course)
        db.session.commit()
        log_action(f"Created course {course.code}")
        flash('Course created successfully.', 'success')
        return redirect(url_for('admin.courses'))

    all_courses = Course.query.order_by(Course.name).all()
    return render_template('admin/courses.html', form=form, courses=all_courses)


@admin_bp.route('/courses/<int:course_id>/delete', methods=['POST'])
def delete_course(course_id):
    course = Course.query.get_or_404(course_id)
    if course.students:
        flash('Cannot delete a course that has enrolled students.', 'danger')
    else:
        db.session.delete(course)
        db.session.commit()
        log_action(f"Deleted course {course.code}")
        flash('Course deleted.', 'info')
    return redirect(url_for('admin.courses'))


# ---------------------------------------------------------------------------
# Faculty
# ---------------------------------------------------------------------------

@admin_bp.route('/faculty', methods=['GET', 'POST'])
def faculty_list():
    form = CreateFacultyForm()
    form.department_id.choices = [(d.id, d.name) for d in Department.query.order_by(Department.name)]

    if form.validate_on_submit():
        role = _get_or_create_role('faculty')
        chosen_password = form.password.data

        user = User(
            username=form.username.data, email=form.email.data.lower(),
            full_name=form.full_name.data, phone=form.phone.data,
            role_id=role.id, email_verified=True
        )
        user.set_password(chosen_password)
        db.session.add(user)
        db.session.flush()

        faculty = Faculty(
            user_id=user.id, employee_code=form.employee_code.data,
            department_id=form.department_id.data, designation=form.designation.data
        )
        db.session.add(faculty)
        db.session.commit()

        send_email(
            subject='Your Faculty Account - Leave Management System',
            recipients=[user.email],
            body_html=render_template('auth/email_new_account.html',
                                       user=user, temp_password=chosen_password, role='Faculty')
        )
        log_action(f"Created faculty account {user.username}")
        session['new_account_credentials'] = {
            'role': 'Faculty', 'full_name': user.full_name,
            'username': user.username, 'password': chosen_password
        }
        flash('Faculty account created successfully.', 'success')
        return redirect(url_for('admin.faculty_list'))

    all_faculty = Faculty.query.join(User).order_by(User.full_name).all()
    new_credentials = session.pop('new_account_credentials', None)
    return render_template('admin/faculty.html', form=form, faculty_members=all_faculty,
                            new_credentials=new_credentials)


@admin_bp.route('/faculty/<int:faculty_id>/toggle', methods=['POST'])
def toggle_faculty(faculty_id):
    faculty = Faculty.query.get_or_404(faculty_id)
    faculty.user.is_active_account = not faculty.user.is_active_account
    db.session.commit()
    flash('Faculty status updated.', 'info')
    return redirect(url_for('admin.faculty_list'))


@admin_bp.route('/faculty/<int:faculty_id>/delete', methods=['POST'])
def delete_faculty(faculty_id):
    faculty = Faculty.query.get_or_404(faculty_id)

    if faculty.advisees:
        flash(f'Cannot delete {faculty.user.full_name}: they are still the faculty advisor for '
              f'{len(faculty.advisees)} student(s). Reassign those students to another advisor first.',
              'danger')
        return redirect(url_for('admin.faculty_list'))

    faculty_name = faculty.user.full_name
    user_to_delete = faculty.user
    db.session.delete(user_to_delete)  # cascades: deletes the Faculty profile too
    db.session.commit()
    log_action(f"Admin deleted faculty account for {faculty_name}")
    flash(f'Faculty account for {faculty_name} has been permanently deleted.', 'info')
    return redirect(url_for('admin.faculty_list'))


# ---------------------------------------------------------------------------
# Parents
# ---------------------------------------------------------------------------

@admin_bp.route('/parents', methods=['GET', 'POST'])
def parent_list():
    form = CreateParentForm()

    if form.validate_on_submit():
        role = _get_or_create_role('parent')
        chosen_password = form.password.data

        user = User(
            username=form.username.data, email=form.email.data.lower(),
            full_name=form.full_name.data, phone=form.phone.data,
            role_id=role.id, email_verified=True
        )
        user.set_password(chosen_password)
        db.session.add(user)
        db.session.flush()

        parent = Parent(user_id=user.id, occupation=form.occupation.data)
        db.session.add(parent)
        db.session.commit()

        send_email(
            subject='Your Parent Account - Leave Management System',
            recipients=[user.email],
            body_html=render_template('auth/email_new_account.html',
                                       user=user, temp_password=chosen_password, role='Parent')
        )
        log_action(f"Created parent account {user.username}")
        session['new_account_credentials'] = {
            'role': 'Parent', 'full_name': user.full_name,
            'username': user.username, 'password': chosen_password
        }
        flash('Parent account created successfully.', 'success')
        return redirect(url_for('admin.parent_list'))

    all_parents = Parent.query.join(User).order_by(User.full_name).all()
    new_credentials = session.pop('new_account_credentials', None)
    return render_template('admin/parents.html', form=form, parents=all_parents,
                            new_credentials=new_credentials)


# ---------------------------------------------------------------------------
# Students
# ---------------------------------------------------------------------------

@admin_bp.route('/students', methods=['GET', 'POST'])
def student_list():
    form = CreateStudentForm()
    form.department_id.choices = [(d.id, d.name) for d in Department.query.order_by(Department.name)]
    form.course_id.choices = [(c.id, c.name) for c in Course.query.order_by(Course.name)]
    form.faculty_advisor_id.choices = [(0, '-- None --')] + [
        (f.id, f.user.full_name) for f in Faculty.query.join(User).order_by(User.full_name)
    ]
    form.parent_id.choices = [(0, '-- None --')] + [
        (p.id, p.user.full_name) for p in Parent.query.join(User).order_by(User.full_name)
    ]

    if form.validate_on_submit():
        role = _get_or_create_role('student')
        chosen_password = form.password.data

        user = User(
            username=form.username.data, email=form.email.data.lower(),
            full_name=form.full_name.data, phone=form.phone.data,
            role_id=role.id, email_verified=True
        )
        user.set_password(chosen_password)
        db.session.add(user)
        db.session.flush()

        student = Student(
            user_id=user.id, roll_no=form.roll_no.data,
            department_id=form.department_id.data, course_id=form.course_id.data,
            semester=form.semester.data,
            faculty_advisor_id=form.faculty_advisor_id.data or None,
            parent_id=form.parent_id.data or None,
        )
        db.session.add(student)
        db.session.commit()

        send_email(
            subject='Your Student Account - Leave Management System',
            recipients=[user.email],
            body_html=render_template('auth/email_new_account.html',
                                       user=user, temp_password=chosen_password, role='Student')
        )
        log_action(f"Created student account {user.username}")
        session['new_account_credentials'] = {
            'role': 'Student', 'full_name': user.full_name,
            'username': user.username, 'password': chosen_password
        }
        flash('Student account created successfully.', 'success')
        return redirect(url_for('admin.student_list'))

    all_students = Student.query.join(User).order_by(User.full_name).all()
    new_credentials = session.pop('new_account_credentials', None)
    return render_template('admin/students.html', form=form, students=all_students,
                            new_credentials=new_credentials)


@admin_bp.route('/students/<int:student_id>/toggle', methods=['POST'])
def toggle_student(student_id):
    student = Student.query.get_or_404(student_id)
    student.user.is_active_account = not student.user.is_active_account
    db.session.commit()
    flash('Student status updated.', 'info')
    return redirect(url_for('admin.student_list'))


@admin_bp.route('/students/<int:student_id>/delete', methods=['POST'])
def delete_student(student_id):
    student = Student.query.get_or_404(student_id)
    student_name = student.user.full_name

    # Clean up any uploaded medical certificate files from disk before the
    # database rows are cascade-deleted, so we don't leave orphaned files.
    upload_folder = current_app.config['UPLOAD_FOLDER']
    for leave in student.leave_requests:
        for doc in leave.documents:
            file_path = os.path.join(upload_folder, doc.stored_filename)
            if os.path.exists(file_path):
                try:
                    os.remove(file_path)
                except OSError:
                    pass  # non-fatal: DB cleanup still proceeds

    user_to_delete = student.user
    db.session.delete(user_to_delete)  # cascades: deletes Student, leave_requests,
                                        # leave_documents, attendance, notifications
    db.session.commit()
    log_action(f"Admin deleted student account for {student_name}")
    flash(f'Student account for {student_name} has been permanently deleted, '
          f'along with their leave and attendance records.', 'info')
    return redirect(url_for('admin.student_list'))


# ---------------------------------------------------------------------------
# Leave requests: view / approve / reject / cancel
# ---------------------------------------------------------------------------

@admin_bp.route('/leave-requests')
def leave_requests():
    status_filter = request.args.get('status', 'all')
    query = LeaveRequest.query.join(Student).join(User, Student.user_id == User.id)

    if status_filter != 'all':
        query = query.filter(LeaveRequest.status == status_filter)

    leaves = query.order_by(LeaveRequest.applied_on.desc()).all()
    return render_template('admin/leave_requests.html', leaves=leaves, status_filter=status_filter)


@admin_bp.route('/leave-requests/<int:leave_id>/decide', methods=['POST'])
def decide_leave(leave_id):
    leave = LeaveRequest.query.get_or_404(leave_id)
    form = LeaveDecisionForm()

    if form.validate_on_submit():
        action = form.action.data
        if action == 'approve':
            leave.status = 'approved'
            leave.admin_remarks = form.remarks.data
            leave.admin_id = current_user.id
            leave.admin_action_at = datetime.utcnow()
            notify(leave.student.user_id,
                   f"Your {leave.leave_type} request has been approved by admin.",
                   link=url_for('student.leave_history'))
            send_email('Leave Request Status Updated', [leave.student.user.email],
                       render_template('auth/email_leave_decision.html', leave=leave, decision='Approved',
                                        decided_by_name=current_user.full_name))
            flash('Leave approved.', 'success')
        elif action == 'reject':
            leave.status = 'rejected'
            leave.admin_remarks = form.remarks.data
            leave.admin_id = current_user.id
            leave.admin_action_at = datetime.utcnow()
            notify(leave.student.user_id,
                   f"Your {leave.leave_type} request has been rejected by admin.",
                   link=url_for('student.leave_history'))
            send_email('Leave Request Status Updated', [leave.student.user.email],
                       render_template('auth/email_leave_decision.html', leave=leave, decision='Rejected',
                                        decided_by_name=current_user.full_name))
            flash('Leave rejected.', 'info')
        db.session.commit()
        log_action(f"Admin {action}d leave request #{leave.id}")

    return redirect(url_for('admin.leave_requests'))


@admin_bp.route('/leave-requests/<int:leave_id>/cancel', methods=['POST'])
def cancel_leave(leave_id):
    leave = LeaveRequest.query.get_or_404(leave_id)
    leave.status = 'cancelled'
    leave.cancelled_at = datetime.utcnow()
    db.session.commit()
    notify(leave.student.user_id, f"Your {leave.leave_type} request was cancelled by admin.")
    log_action(f"Admin cancelled leave request #{leave.id}")
    flash('Leave request cancelled.', 'info')
    return redirect(url_for('admin.leave_requests'))


# ---------------------------------------------------------------------------
# Attendance report
# ---------------------------------------------------------------------------

@admin_bp.route('/attendance-report')
def attendance_report():
    department_id = request.args.get('department_id', type=int)
    query = Student.query.join(User)
    if department_id:
        query = query.filter(Student.department_id == department_id)
    students = query.order_by(User.full_name).all()

    report_rows = []
    for s in students:
        total = Attendance.query.filter_by(student_id=s.id).count()
        present = Attendance.query.filter_by(student_id=s.id, status='present').count()
        on_leave = Attendance.query.filter_by(student_id=s.id, status='leave').count()
        absent = Attendance.query.filter_by(student_id=s.id, status='absent').count()
        pct = round((present / total) * 100, 1) if total else 0.0
        report_rows.append({
            'student': s, 'total': total, 'present': present,
            'absent': absent, 'on_leave': on_leave, 'percentage': pct
        })

    departments = Department.query.order_by(Department.name).all()
    return render_template('admin/attendance_report.html', rows=report_rows,
                            departments=departments, selected_dept=department_id)


@admin_bp.route('/reports/leave/export/excel')
def export_leave_excel():
    from openpyxl import Workbook
    wb = Workbook()
    ws = wb.active
    ws.title = "Leave Report"
    ws.append(['ID', 'Student', 'Roll No', 'Leave Type', 'From', 'To', 'Days', 'Status', 'Applied On'])

    for lr in LeaveRequest.query.order_by(LeaveRequest.applied_on.desc()).all():
        ws.append([
            lr.id, lr.student.user.full_name, lr.student.roll_no, lr.leave_type,
            lr.from_date.strftime('%Y-%m-%d'), lr.to_date.strftime('%Y-%m-%d'),
            lr.number_of_days(), lr.status_label(), lr.applied_on.strftime('%Y-%m-%d %H:%M')
        ])

    buffer = BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    log_action("Exported leave report to Excel")
    return send_file(buffer, as_attachment=True, download_name='leave_report.xlsx',
                      mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')


@admin_bp.route('/reports/leave/export/pdf')
def export_leave_pdf():
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
    from reportlab.lib.styles import getSampleStyleSheet

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(A4))
    styles = getSampleStyleSheet()
    elements = [Paragraph("Leave Report - Leave Management System", styles['Title'])]

    data = [['ID', 'Student', 'Roll No', 'Type', 'From', 'To', 'Days', 'Status']]
    for lr in LeaveRequest.query.order_by(LeaveRequest.applied_on.desc()).all():
        data.append([
            lr.id, lr.student.user.full_name, lr.student.roll_no, lr.leave_type,
            lr.from_date.strftime('%Y-%m-%d'), lr.to_date.strftime('%Y-%m-%d'),
            lr.number_of_days(), lr.status_label()
        ])

    table = Table(data, repeatRows=1)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4f46e5')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f3f4f6')]),
    ]))
    elements.append(table)
    doc.build(elements)
    buffer.seek(0)
    log_action("Exported leave report to PDF")
    return send_file(buffer, as_attachment=True, download_name='leave_report.pdf',
                      mimetype='application/pdf')


# ---------------------------------------------------------------------------
# Academic calendar / holidays
# ---------------------------------------------------------------------------

@admin_bp.route('/holidays', methods=['GET', 'POST'])
def holidays():
    form = HolidayForm()
    if form.validate_on_submit():
        holiday = Holiday(name=form.name.data, date=form.date.data)
        db.session.add(holiday)
        db.session.commit()
        flash('Holiday added.', 'success')
        return redirect(url_for('admin.holidays'))

    all_holidays = Holiday.query.order_by(Holiday.date).all()
    return render_template('admin/holidays.html', form=form, holidays=all_holidays)


@admin_bp.route('/holidays/<int:holiday_id>/delete', methods=['POST'])
def delete_holiday(holiday_id):
    holiday = Holiday.query.get_or_404(holiday_id)
    db.session.delete(holiday)
    db.session.commit()
    flash('Holiday removed.', 'info')
    return redirect(url_for('admin.holidays'))


@admin_bp.route('/academic-years', methods=['GET', 'POST'])
def academic_years():
    form = AcademicYearForm()
    if form.validate_on_submit():
        if form.is_current.data:
            AcademicYear.query.update({AcademicYear.is_current: False})
        ay = AcademicYear(
            year_label=form.year_label.data, start_date=form.start_date.data,
            end_date=form.end_date.data, is_current=form.is_current.data
        )
        db.session.add(ay)
        db.session.commit()
        flash('Academic year saved.', 'success')
        return redirect(url_for('admin.academic_years'))

    all_years = AcademicYear.query.order_by(AcademicYear.start_date.desc()).all()
    return render_template('admin/academic_years.html', form=form, academic_years=all_years)


# ---------------------------------------------------------------------------
# Audit logs
# ---------------------------------------------------------------------------

@admin_bp.route('/audit-logs')
def audit_logs():
    logs = AuditLog.query.order_by(AuditLog.timestamp.desc()).limit(300).all()
    return render_template('admin/audit_logs.html', logs=logs)


# ---------------------------------------------------------------------------
# Role / permission management (view + toggle active status is the practical
# permission control in this system, since roles are fixed to 4 types)
# ---------------------------------------------------------------------------

@admin_bp.route('/users')
def user_management():
    users = User.query.join(Role).order_by(Role.name, User.full_name).all()
    return render_template('admin/user_management.html', users=users)


@admin_bp.route('/users/<int:user_id>/toggle', methods=['POST'])
def toggle_user(user_id):
    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        flash("You can't deactivate your own account.", 'danger')
        return redirect(url_for('admin.user_management'))
    user.is_active_account = not user.is_active_account
    db.session.commit()
    log_action(f"Toggled active status for user {user.username}")
    flash('User status updated.', 'info')
    return redirect(url_for('admin.user_management'))
