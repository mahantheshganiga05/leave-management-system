from flask import Blueprint, render_template, abort
from flask_login import login_required, current_user

from app.models import Parent, LeaveRequest, Attendance

parent_bp = Blueprint('parent', __name__, template_folder='../templates/parent')


@parent_bp.before_request
@login_required
def restrict_to_parent():
    if current_user.role_name != 'parent':
        abort(403)


def _current_parent():
    return Parent.query.filter_by(user_id=current_user.id).first_or_404()


@parent_bp.route('/dashboard')
def dashboard():
    parent = _current_parent()
    children = parent.children
    child_summaries = []
    for child in children:
        total_att = Attendance.query.filter_by(student_id=child.id).count()
        present = Attendance.query.filter_by(student_id=child.id, status='present').count()
        pct = round((present / total_att) * 100, 1) if total_att else 0.0
        pending_leaves = LeaveRequest.query.filter(
            LeaveRequest.student_id == child.id,
            LeaveRequest.status.in_(['pending', 'faculty_approved'])
        ).count()
        child_summaries.append({'student': child, 'attendance_pct': pct, 'pending_leaves': pending_leaves})

    return render_template('parent/dashboard.html', parent=parent, child_summaries=child_summaries)


@parent_bp.route('/child/<int:student_id>/leaves')
def child_leaves(student_id):
    parent = _current_parent()
    child = next((c for c in parent.children if c.id == student_id), None)
    if not child:
        abort(403)
    leaves = LeaveRequest.query.filter_by(student_id=child.id) \
        .order_by(LeaveRequest.applied_on.desc()).all()
    return render_template('parent/child_leaves.html', child=child, leaves=leaves)


@parent_bp.route('/child/<int:student_id>/attendance')
def child_attendance(student_id):
    parent = _current_parent()
    child = next((c for c in parent.children if c.id == student_id), None)
    if not child:
        abort(403)
    records = Attendance.query.filter_by(student_id=child.id).order_by(Attendance.date.desc()).all()
    return render_template('parent/child_attendance.html', child=child, records=records)
