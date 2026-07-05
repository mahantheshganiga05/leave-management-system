from datetime import date
from flask import Blueprint, render_template, redirect, url_for, flash, request, abort, send_from_directory, current_app
from flask_login import login_required, current_user

from app.extensions import db
from app.models import Student, LeaveRequest, LeaveDocument, Attendance, MEDICAL_REQUIRED_TYPES
from app.forms import LeaveApplicationForm, ProfileForm
from app.utils import save_upload, allowed_file, notify, log_action, send_email

student_bp = Blueprint('student', __name__, template_folder='../templates/student')


@student_bp.before_request
@login_required
def restrict_to_student():
    if current_user.role_name != 'student':
        abort(403)


def _current_student():
    return Student.query.filter_by(user_id=current_user.id).first_or_404()


@student_bp.route('/dashboard')
def dashboard():
    student = _current_student()
    leaves = LeaveRequest.query.filter_by(student_id=student.id) \
        .order_by(LeaveRequest.applied_on.desc()).limit(5).all()

    total = LeaveRequest.query.filter_by(student_id=student.id).count()
    approved = LeaveRequest.query.filter_by(student_id=student.id, status='approved').count()
    pending = LeaveRequest.query.filter(
        LeaveRequest.student_id == student.id,
        LeaveRequest.status.in_(['pending', 'faculty_approved'])
    ).count()
    rejected = LeaveRequest.query.filter_by(student_id=student.id, status='rejected').count()

    total_attendance = Attendance.query.filter_by(student_id=student.id).count()
    present = Attendance.query.filter_by(student_id=student.id, status='present').count()
    attendance_pct = round((present / total_attendance) * 100, 1) if total_attendance else 0.0

    return render_template('student/dashboard.html', student=student, leaves=leaves,
                            total=total, approved=approved, pending=pending, rejected=rejected,
                            attendance_pct=attendance_pct)


@student_bp.route('/apply-leave', methods=['GET', 'POST'])
def apply_leave():
    student = _current_student()
    form = LeaveApplicationForm()

    if form.validate_on_submit():
        # --- Business validations ---
        overlapping = LeaveRequest.query.filter(
            LeaveRequest.student_id == student.id,
            LeaveRequest.status.in_(['pending', 'faculty_approved', 'approved']),
            LeaveRequest.from_date <= form.to_date.data,
            LeaveRequest.to_date >= form.from_date.data,
        ).first()
        if overlapping:
            flash('You already have a leave request that overlaps these dates.', 'danger')
            return render_template('student/apply_leave.html', form=form)

        days_requested = (form.to_date.data - form.from_date.data).days + 1
        if days_requested > 15:
            flash('A single leave request cannot exceed 15 days. Contact admin for extended leave.', 'danger')
            return render_template('student/apply_leave.html', form=form)

        if form.leave_type.data in MEDICAL_REQUIRED_TYPES and not form.document.data:
            flash(f'A medical certificate attachment is required for {form.leave_type.data}.', 'danger')
            return render_template('student/apply_leave.html', form=form)

        leave = LeaveRequest(
            student_id=student.id, leave_type=form.leave_type.data,
            from_date=form.from_date.data, to_date=form.to_date.data,
            reason=form.reason.data, status='pending'
        )
        db.session.add(leave)
        db.session.flush()

        if form.document.data:
            original_name, stored_name = save_upload(form.document.data)
            doc = LeaveDocument(leave_request_id=leave.id, filename=original_name,
                                 stored_filename=stored_name)
            db.session.add(doc)

        db.session.commit()

        if student.faculty_advisor_id:
            notify(student.faculty_advisor.user_id,
                   f"{student.user.full_name} applied for {leave.leave_type} "
                   f"({leave.from_date} to {leave.to_date}).",
                   link=url_for('faculty.leave_requests'))
            send_email(
                'New Leave Request - Student Leave Management System',
                [student.faculty_advisor.user.email],
                render_template('auth/email_faculty_new_leave.html', leave=leave, student=student)
            )
        send_email('Leave Application Submitted', [student.user.email],
                   render_template('auth/email_leave_submitted.html', leave=leave))

        log_action(f"Student {current_user.username} applied for {leave.leave_type}")
        flash('Leave application submitted successfully.', 'success')
        return redirect(url_for('student.leave_history'))

    return render_template('student/apply_leave.html', form=form)


@student_bp.route('/leave-history')
def leave_history():
    student = _current_student()
    leaves = LeaveRequest.query.filter_by(student_id=student.id) \
        .order_by(LeaveRequest.applied_on.desc()).all()
    return render_template('student/leave_history.html', leaves=leaves)


@student_bp.route('/leave-requests/<int:leave_id>/cancel', methods=['POST'])
def cancel_leave(leave_id):
    student = _current_student()
    leave = LeaveRequest.query.get_or_404(leave_id)
    if leave.student_id != student.id:
        abort(403)
    if leave.status not in ('pending', 'faculty_approved'):
        flash('Only pending leave requests can be cancelled.', 'danger')
    else:
        from datetime import datetime
        leave.status = 'cancelled'
        leave.cancelled_at = datetime.utcnow()
        db.session.commit()
        log_action(f"Student {current_user.username} cancelled leave request #{leave.id}")
        flash('Leave request cancelled.', 'info')
    return redirect(url_for('student.leave_history'))


@student_bp.route('/attendance')
def attendance():
    student = _current_student()
    records = Attendance.query.filter_by(student_id=student.id).order_by(Attendance.date.desc()).all()
    return render_template('student/attendance.html', records=records)


@student_bp.route('/documents/<int:doc_id>')
def download_document(doc_id):
    student = _current_student()
    doc = LeaveDocument.query.get_or_404(doc_id)
    if doc.leave_request.student_id != student.id:
        abort(403)
    return send_from_directory(current_app.config['UPLOAD_FOLDER'], doc.stored_filename,
                                as_attachment=True, download_name=doc.filename)


@student_bp.route('/profile', methods=['GET', 'POST'])
def profile():
    form = ProfileForm(obj=current_user)
    if form.validate_on_submit():
        current_user.full_name = form.full_name.data
        current_user.phone = form.phone.data
        db.session.commit()
        flash('Profile updated.', 'success')
        return redirect(url_for('student.profile'))
    return render_template('student/profile.html', form=form, student=_current_student())
