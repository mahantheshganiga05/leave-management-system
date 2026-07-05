from datetime import date
from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import (
    StringField, PasswordField, BooleanField, SubmitField, SelectField,
    TextAreaField, DateField, IntegerField, HiddenField
)
from wtforms.validators import (
    DataRequired, Email, EqualTo, Length, ValidationError, Optional, NumberRange
)
from app.models import User, LEAVE_TYPES


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

class LoginForm(FlaskForm):
    username = StringField('Username or Email', validators=[DataRequired(), Length(max=120)])
    password = PasswordField('Password', validators=[DataRequired()])
    remember = BooleanField('Remember Me')
    submit = SubmitField('Login')


class ForgotPasswordForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    submit = SubmitField('Send Reset Link')


class ResetPasswordForm(FlaskForm):
    password = PasswordField('New Password', validators=[DataRequired(), Length(min=8)])
    confirm_password = PasswordField(
        'Confirm Password',
        validators=[DataRequired(), EqualTo('password', message='Passwords must match')]
    )
    submit = SubmitField('Reset Password')


class ChangePasswordForm(FlaskForm):
    current_password = PasswordField('Current Password', validators=[DataRequired()])
    new_password = PasswordField('New Password', validators=[DataRequired(), Length(min=8)])
    confirm_password = PasswordField(
        'Confirm New Password',
        validators=[DataRequired(), EqualTo('new_password', message='Passwords must match')]
    )
    submit = SubmitField('Change Password')


# ---------------------------------------------------------------------------
# Admin: user / academic management
# ---------------------------------------------------------------------------

class DepartmentForm(FlaskForm):
    name = StringField('Department Name', validators=[DataRequired(), Length(max=120)])
    code = StringField('Department Code', validators=[DataRequired(), Length(max=20)])
    submit = SubmitField('Save Department')


class CourseForm(FlaskForm):
    name = StringField('Course Name', validators=[DataRequired(), Length(max=120)])
    code = StringField('Course Code', validators=[DataRequired(), Length(max=20)])
    department_id = SelectField('Department', coerce=int, validators=[DataRequired()])
    duration_years = IntegerField('Duration (Years)', default=3,
                                   validators=[DataRequired(), NumberRange(min=1, max=6)])
    submit = SubmitField('Save Course')


class CreateFacultyForm(FlaskForm):
    full_name = StringField('Full Name', validators=[DataRequired(), Length(max=120)])
    username = StringField('Username', validators=[DataRequired(), Length(max=80)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    phone = StringField('Phone', validators=[Optional(), Length(max=20)])
    employee_code = StringField('Employee Code', validators=[DataRequired(), Length(max=30)])
    department_id = SelectField('Department', coerce=int, validators=[DataRequired()])
    designation = StringField('Designation', default='Assistant Professor')
    password = PasswordField('Set Login Password', validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField(
        'Confirm Password', validators=[DataRequired(), EqualTo('password', message='Passwords must match')]
    )
    submit = SubmitField('Create Faculty')

    def validate_username(self, field):
        if User.query.filter_by(username=field.data).first():
            raise ValidationError('Username already taken.')

    def validate_email(self, field):
        if User.query.filter_by(email=field.data).first():
            raise ValidationError('Email already registered.')


class CreateParentForm(FlaskForm):
    full_name = StringField('Full Name', validators=[DataRequired(), Length(max=120)])
    username = StringField('Username', validators=[DataRequired(), Length(max=80)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    phone = StringField('Phone', validators=[Optional(), Length(max=20)])
    occupation = StringField('Occupation', validators=[Optional(), Length(max=120)])
    password = PasswordField('Set Login Password', validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField(
        'Confirm Password', validators=[DataRequired(), EqualTo('password', message='Passwords must match')]
    )
    submit = SubmitField('Create Parent')

    def validate_username(self, field):
        if User.query.filter_by(username=field.data).first():
            raise ValidationError('Username already taken.')

    def validate_email(self, field):
        if User.query.filter_by(email=field.data).first():
            raise ValidationError('Email already registered.')


class CreateStudentForm(FlaskForm):
    full_name = StringField('Full Name', validators=[DataRequired(), Length(max=120)])
    username = StringField('Username', validators=[DataRequired(), Length(max=80)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    phone = StringField('Phone', validators=[Optional(), Length(max=20)])
    roll_no = StringField('Roll Number', validators=[DataRequired(), Length(max=30)])
    department_id = SelectField('Department', coerce=int, validators=[DataRequired()])
    course_id = SelectField('Course', coerce=int, validators=[DataRequired()])
    semester = IntegerField('Semester', default=1, validators=[DataRequired(), NumberRange(min=1, max=12)])
    faculty_advisor_id = SelectField('Faculty Advisor', coerce=int, validators=[Optional()])
    parent_id = SelectField('Parent', coerce=int, validators=[Optional()])
    password = PasswordField('Set Login Password', validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField(
        'Confirm Password', validators=[DataRequired(), EqualTo('password', message='Passwords must match')]
    )
    submit = SubmitField('Create Student')

    def validate_username(self, field):
        if User.query.filter_by(username=field.data).first():
            raise ValidationError('Username already taken.')

    def validate_email(self, field):
        if User.query.filter_by(email=field.data).first():
            raise ValidationError('Email already registered.')

    def validate_roll_no(self, field):
        from app.models import Student
        if Student.query.filter_by(roll_no=field.data).first():
            raise ValidationError('Roll number already exists.')


class HolidayForm(FlaskForm):
    name = StringField('Holiday Name', validators=[DataRequired(), Length(max=120)])
    date = DateField('Date', validators=[DataRequired()])
    submit = SubmitField('Add Holiday')


class AcademicYearForm(FlaskForm):
    year_label = StringField('Academic Year (e.g. 2025-2026)', validators=[DataRequired(), Length(max=20)])
    start_date = DateField('Start Date', validators=[DataRequired()])
    end_date = DateField('End Date', validators=[DataRequired()])
    is_current = BooleanField('Set as Current Academic Year')
    submit = SubmitField('Save Academic Year')


class LeaveDecisionForm(FlaskForm):
    """Used by faculty/admin to approve or reject a leave request."""
    remarks = TextAreaField('Remarks', validators=[Optional(), Length(max=500)])
    action = HiddenField(validators=[DataRequired()])  # 'approve' or 'reject'
    submit = SubmitField('Submit Decision')


# ---------------------------------------------------------------------------
# Student
# ---------------------------------------------------------------------------

class LeaveApplicationForm(FlaskForm):
    leave_type = SelectField('Leave Type', choices=[(t, t) for t in LEAVE_TYPES],
                              validators=[DataRequired()])
    from_date = DateField('From Date', validators=[DataRequired()])
    to_date = DateField('To Date', validators=[DataRequired()])
    reason = TextAreaField('Reason', validators=[DataRequired(), Length(min=10, max=1000)])
    document = FileField('Medical Certificate (PDF/PNG/JPG, max 5MB)',
                          validators=[Optional(), FileAllowed(['pdf', 'png', 'jpg', 'jpeg'],
                                                               'Only PDF, PNG, JPG files allowed!')])
    submit = SubmitField('Apply for Leave')

    def validate_from_date(self, field):
        if field.data < date.today():
            raise ValidationError('Cannot apply leave for a past date.')

    def validate_to_date(self, field):
        if self.from_date.data and field.data < self.from_date.data:
            raise ValidationError('To Date cannot be earlier than From Date.')


class ProfileForm(FlaskForm):
    full_name = StringField('Full Name', validators=[DataRequired(), Length(max=120)])
    phone = StringField('Phone', validators=[Optional(), Length(max=20)])
    submit = SubmitField('Update Profile')
