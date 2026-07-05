from datetime import datetime, date
from flask import Blueprint, render_template, redirect, url_for, flash, request, abort
from flask_login import login_required, current_user

from app.extensions import db
from app.models import Faculty, Student, LeaveRequest, Attendance, User
from app.forms import LeaveDecisionForm, ProfileForm
from app.utils import notify, log_action, send_email

faculty_bp = Blueprint('faculty', __name__, template_folder='../templates/faculty')


@faculty_bp.before_request
@login_required
def restrict_to_faculty():
    if current_user.role_name != 'faculty':
        abort(403)


def _current_faculty():
    return Faculty.query.filter_by(user_id=current_user.id).first_or_404()


@faculty_bp.route('/dashboard')
def dashboard():
    faculty = _current_faculty()
    advisee_ids = [s.id for s in faculty.advisees]

    pending_count = LeaveRequest.query.filter(
        LeaveRequest.student_id.in_(advisee_ids) if advisee_ids else False,
        LeaveRequest.status == 'pending'
    ).count() if advisee_ids else 0

    recent_leaves = LeaveRequest.query.filter(
        LeaveRequest.student_id.in_(advisee_ids) if advisee_ids else False
    ).order_by(LeaveRequest.applied_on.desc()).limit(8).all() if advisee_ids else []

    return render_template(
        'faculty/dashboard.html', faculty=faculty,
        total_advisees=len(advisee_ids), pending_count=pending_count,
        recent_leaves=recent_leaves,
    )


@faculty_bp.route('/students')
def students():
    faculty = _current_faculty()
    return render_template('faculty/students.html', faculty=faculty, students=faculty.advisees)


@faculty_bp.route('/leave-requests')
def leave_requests():
    faculty = _current_faculty()
    advisee_ids = [s.id for s in faculty.advisees]
    status_filter = request.args.get('status', 'pending')

    query = LeaveRequest.query.filter(
        LeaveRequest.student_id.in_(advisee_ids) if advisee_ids else False
    )
    if status_filter != 'all':
        query = query.filter(LeaveRequest.status == status_filter)

    leaves = query.order_by(LeaveRequest.applied_on.desc()).all()
    return render_template('faculty/leave_requests.html', leaves=leaves, status_filter=status_filter)


@faculty_bp.route('/leave-requests/<int:leave_id>/decide', methods=['POST'])
def decide_leave(leave_id):
    faculty = _current_faculty()
    leave = LeaveRequest.query.get_or_404(leave_id)

    if leave.student.faculty_advisor_id != faculty.id:
        abort(403)
    if leave.status != 'pending':
        flash('This leave request has already been processed.', 'warning')
        return redirect(url_for('faculty.leave_requests'))

    form = LeaveDecisionForm()
    if form.validate_on_submit():
        action = form.action.data
        leave.faculty_id = faculty.id
        leave.faculty_remarks = form.remarks.data
        leave.faculty_action_at = datetime.utcnow()

        if action == 'approve':
            leave.status = 'faculty_approved'
            notify(leave.student.user_id,
                   f"Your {leave.leave_type} request was approved by your faculty advisor "
                   f"and forwarded to admin for final approval.")
            send_email(
    'Leave Request Status Updated',
    [leave.student.user.email],
    render_template(
        'auth/email_leave_decision.html',
        leave=leave,
        decision='Approved',
        decided_by_name=current_user.full_name
    )
)
            flash('Leave forwarded to admin for final approval.', 'success')
        elif action == 'reject':
            leave.status = 'rejected'
            notify(leave.student.user_id,
                   f"Your {leave.leave_type} request was rejected by your faculty advisor.")
            send_email('Leave Request Status Updated', [leave.student.user.email],
                       render_template('auth/email_leave_decision.html', leave=leave, decision='Rejected',
                                        decided_by_name=current_user.full_name))
            flash('Leave rejected.', 'info')

        db.session.commit()
        log_action(f"Faculty {action}d leave request #{leave.id}")

    return redirect(url_for('faculty.leave_requests'))


@faculty_bp.route('/attendance', methods=['GET', 'POST'])
def attendance():
    faculty = _current_faculty()
    students = faculty.advisees
    selected_date = request.args.get('date', date.today().isoformat())

    if request.method == 'POST':
        att_date = datetime.strptime(request.form.get('date'), '%Y-%m-%d').date()
        for student in students:
            status = request.form.get(f'status_{student.id}', 'present')
            record = Attendance.query.filter_by(student_id=student.id, date=att_date).first()
            if record:
                record.status = status
            else:
                record = Attendance(student_id=student.id, date=att_date,
                                     status=status, marked_by=current_user.id)
                db.session.add(record)
        db.session.commit()
        flash('Attendance saved.', 'success')
        return redirect(url_for('faculty.attendance', date=att_date.isoformat()))

    att_date_obj = datetime.strptime(selected_date, '%Y-%m-%d').date()
    existing = {a.student_id: a.status for a in
                Attendance.query.filter_by(date=att_date_obj).all()}

    return render_template('faculty/attendance.html', students=students,
                            selected_date=selected_date, existing=existing)


@faculty_bp.route('/profile', methods=['GET', 'POST'])
def profile():
    form = ProfileForm(obj=current_user)
    if form.validate_on_submit():
        current_user.full_name = form.full_name.data
        current_user.phone = form.phone.data
        db.session.commit()
        flash('Profile updated.', 'success')
        return redirect(url_for('faculty.profile'))
    return render_template('faculty/profile.html', form=form, faculty=_current_faculty())
