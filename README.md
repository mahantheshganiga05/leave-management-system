# College Leave Management System

A production-structured, role-based Leave Management System built with Flask, MySQL,
and Bootstrap 5. Supports four portals — **Admin**, **Faculty**, **Student**, and **Parent**
— with a multi-stage leave approval workflow (Student → Faculty Advisor → Admin),
attendance tracking, email notifications, file uploads, audit logging, and reports.

---

## Tech Stack

- **Backend:** Python 3.12, Flask, Flask-Login, Flask-Migrate, Flask-SQLAlchemy, Flask-WTF,
  Flask-Mail, Flask-Limiter
- **Frontend:** Bootstrap 5, Bootstrap Icons, Chart.js, vanilla JS (dark mode, sidebar toggle)
- **Database:** MySQL via SQLAlchemy ORM + Alembic migrations (Flask-Migrate)
- **Reports:** openpyxl (Excel export), ReportLab (PDF export)

---

## Features

| Area | Highlights |
|---|---|
| Auth | Login, Remember Me, Forgot/Reset Password (emailed token), Change Password, Email Verification, account lockout after repeated failed logins, session timeout |
| Admin | Dashboard with charts, manage Students/Faculty/Parents/Departments/Courses, approve/reject/cancel leave, attendance reports, Excel/PDF export, holiday & academic year management, audit logs, user activation toggle |
| Faculty | Dashboard, view assigned students, approve/reject leave requests (first-stage approval), mark daily attendance, profile |
| Student | Apply for leave (with validation), upload medical certificate, view leave history, cancel pending leave, view attendance, profile |
| Parent | View linked children, their leave status, and attendance |
| Leave workflow | Student → Faculty Advisor approval → Admin final approval; rejection possible at either stage; validations for past dates, overlaps, max duration, and required medical attachments |
| Security | CSRF protection (Flask-WTF), password hashing (Werkzeug), role-based access control, rate limiting on login/password-reset endpoints, parameterized queries via SQLAlchemy ORM (SQL-injection safe), Jinja2 autoescaping (XSS safe) |
| REST API | JSON endpoints for leave data, notifications, and dashboard stats, scoped by role |

---

## Project Structure

```
leave_management_system/
├── app/
│   ├── __init__.py          # Application factory
│   ├── extensions.py        # db, login_manager, migrate, mail, csrf, limiter
│   ├── models.py            # All SQLAlchemy models
│   ├── forms.py             # All Flask-WTF forms
│   ├── utils.py             # Shared helpers (role_required, uploads, email, audit log)
│   ├── main/routes.py       # Landing page + role-based dashboard redirect
│   ├── auth/routes.py       # Login / logout / password reset / change password
│   ├── admin/routes.py      # Admin portal
│   ├── faculty/routes.py    # Faculty portal
│   ├── student/routes.py    # Student portal
│   ├── parent/routes.py     # Parent portal
│   ├── api/routes.py        # REST API (JSON)
│   ├── templates/           # Jinja2 templates (per-blueprint folders + shared base.html)
│   ├── static/css, static/js
│   └── uploads/medical_certificates/
├── migrations/               # Created by `flask db init`
├── config.py
├── run.py
├── seed.py
├── requirements.txt
├── .env.example
└── README.md
```

---

## Setup Instructions

### 1. Prerequisites
- Python 3.12+
- MySQL Server 8.0+ (running locally or remotely)

### 2. Create the MySQL database
```sql
CREATE DATABASE leave_management CHARACTER SET utf8mb4;
```

### 3. Clone/copy the project and set up a virtual environment
```bash
python -m venv venv
source venv/bin/activate        # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 4. Configure environment variables
```bash
cp .env.example .env
```
Edit `.env` and set at minimum:
- `SECRET_KEY` — any long random string
- `DATABASE_URL` — e.g. `mysql+pymysql://root:yourpassword@localhost:3306/leave_management`
- `MAIL_USERNAME` / `MAIL_PASSWORD` (optional — if left blank, emails are logged to the
  console instead of sent, so the app still works fully without SMTP configured)

### 5. Initialize the database
```bash
flask db init
flask db migrate -m "Initial migration"
flask db upgrade
```

### 6. Seed demo data
```bash
python seed.py
```
This creates an admin account, sample faculty/student/parent accounts (all linked together),
departments, courses, holidays, and a few sample leave/attendance records.

**Demo login credentials** (password for all accounts: `Passw0rd!123`):

| Role | Username |
|---|---|
| Admin | `admin` |
| Faculty | `drsharma`, `profkumar` |
| Student | `anitastudent`, `vikramstudent`, `priyastudent` |
| Parent | `rajparent`, `sunitaparent` |

### 7. Run the application
```bash
python run.py
```
Visit **http://localhost:5000** and log in with any of the demo accounts above.

---

## Notes on Scope

This is a genuinely working, end-to-end system covering the core leave-management workflow,
all four role portals, auth, validations, file uploads, notifications, dashboards backed by
real database queries, and Excel/PDF export. A few of the more peripheral items from the
original "kitchen sink" spec (e.g. granular per-field permission management beyond role-based
access, a full drag-and-drop academic calendar UI) were intentionally kept simple/functional
rather than heavily skinned, so they can be extended based on your actual needs. If you want
any of these expanded further, they can be built on top of this foundation without
restructuring anything.

## Security Notes for Production

- Set `FLASK_CONFIG=production` and use a real `SECRET_KEY`.
- Put this behind a real WSGI server (gunicorn/uwsgi) + reverse proxy (nginx), not `run.py`'s
  dev server.
- Use HTTPS so `SESSION_COOKIE_SECURE`/`REMEMBER_COOKIE_SECURE` (enabled in `ProductionConfig`)
  actually apply.
- Configure real SMTP credentials so password reset and leave notification emails send.
