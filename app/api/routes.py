from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user

from app.models import LeaveRequest, Student, Attendance, Notification, User
from app.utils import role_required

api_bp = Blueprint('api', __name__)


def _serialize_leave(lr):
    return {
        'id': lr.id,
        'student': lr.student.user.full_name,
        'roll_no': lr.student.roll_no,
        'leave_type': lr.leave_type,
        'from_date': lr.from_date.isoformat(),
        'to_date': lr.to_date.isoformat(),
        'days': lr.number_of_days(),
        'reason': lr.reason,
        'status': lr.status,
        'applied_on': lr.applied_on.isoformat(),
    }


@api_bp.route('/auth/status')
@login_required
def auth_status():
    return jsonify({
        'authenticated': True,
        'username': current_user.username,
        'role': current_user.role_name,
        'full_name': current_user.full_name,
    })


@api_bp.route('/leaves')
@login_required
def list_leaves():
    """Return leave requests scoped to the current user's role."""
    role = current_user.role_name
    if role == 'admin':
        leaves = LeaveRequest.query.order_by(LeaveRequest.applied_on.desc()).limit(100).all()
    elif role == 'faculty':
        from app.models import Faculty
        faculty = Faculty.query.filter_by(user_id=current_user.id).first()
        advisee_ids = [s.id for s in faculty.advisees] if faculty else []
        leaves = LeaveRequest.query.filter(LeaveRequest.student_id.in_(advisee_ids)) \
            .order_by(LeaveRequest.applied_on.desc()).all() if advisee_ids else []
    elif role == 'student':
        student = Student.query.filter_by(user_id=current_user.id).first()
        leaves = LeaveRequest.query.filter_by(student_id=student.id) \
            .order_by(LeaveRequest.applied_on.desc()).all() if student else []
    elif role == 'parent':
        from app.models import Parent
        parent = Parent.query.filter_by(user_id=current_user.id).first()
        child_ids = [c.id for c in parent.children] if parent else []
        leaves = LeaveRequest.query.filter(LeaveRequest.student_id.in_(child_ids)) \
            .order_by(LeaveRequest.applied_on.desc()).all() if child_ids else []
    else:
        leaves = []

    return jsonify([_serialize_leave(lr) for lr in leaves])


@api_bp.route('/leaves/<int:leave_id>')
@login_required
def get_leave(leave_id):
    leave = LeaveRequest.query.get_or_404(leave_id)
    return jsonify(_serialize_leave(leave))


@api_bp.route('/notifications/unread-count')
@login_required
def unread_notifications_count():
    count = Notification.query.filter_by(user_id=current_user.id, is_read=False).count()
    return jsonify({'unread_count': count})


@api_bp.route('/students/<int:student_id>/attendance-summary')
@login_required
def attendance_summary(student_id):
    total = Attendance.query.filter_by(student_id=student_id).count()
    present = Attendance.query.filter_by(student_id=student_id, status='present').count()
    absent = Attendance.query.filter_by(student_id=student_id, status='absent').count()
    on_leave = Attendance.query.filter_by(student_id=student_id, status='leave').count()
    pct = round((present / total) * 100, 1) if total else 0.0
    return jsonify({
        'student_id': student_id, 'total': total, 'present': present,
        'absent': absent, 'on_leave': on_leave, 'attendance_percentage': pct
    })


@api_bp.route('/dashboard/stats')
@login_required
@role_required('admin')
def dashboard_stats():
    from app.models import Student, Faculty, Parent, Department
    return jsonify({
        'students': Student.query.count(),
        'faculty': Faculty.query.count(),
        'parents': Parent.query.count(),
        'departments': Department.query.count(),
        'pending_leaves': LeaveRequest.query.filter(
            LeaveRequest.status.in_(['pending', 'faculty_approved'])
        ).count(),
        'approved_leaves': LeaveRequest.query.filter_by(status='approved').count(),
        'rejected_leaves': LeaveRequest.query.filter_by(status='rejected').count(),
    })
