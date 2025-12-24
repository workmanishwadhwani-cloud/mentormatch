# MentorConnect — Student Mentorship Platform (Flask MVP)

This repository contains a minimal, production-minded Flask application implementing a Student Mentorship Platform (MVP).

Tech stack
- Python 3.x
- Flask, Flask-Login, Flask-WTF
- Flask-Migrate, Flask-SQLAlchemy
- SQLite (default)

Quick setup

1. Create and activate a virtualenv

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

2. Set environment variables (optional)

```powershell
$env:FLASK_APP='run.py'
$env:FLASK_ENV='development'
$env:SECRET_KEY='change-this'
```

3. Initialize DB and seed data

```powershell
python seed.py
```

4. Run the app

```powershell
python run.py
```

Default accounts
- Admin: `admin@example.com` / `adminpass`
- Mentor: `mentor1@example.com` / `mentorpass`
- Student: `student1@example.com` / `studentpass`

Notes
- This MVP focuses on a clear architecture (factory, blueprints, models) and implements core features: auth, profiles, mentor listing, session requests, messaging, reviews, and admin dashboard.
- For production: configure a proper SMTP server for password resets, switch to PostgreSQL, enable migrations (`flask db init/migrate/upgrade`), and add file uploads for avatars.
