from flask import Flask, redirect, url_for
import os
import pathlib
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager, current_user
from flask_wtf import CSRFProtect
from flask_caching import Cache
from config import Config

db = SQLAlchemy()
migrate = Migrate()
login = LoginManager()
csrf = CSRFProtect()
cache = Cache(config={'CACHE_TYPE': 'simple'})


def create_app(config_class=Config):
    app = Flask(__name__)
    # Lightweight .env loader: read project-root .env and set any variables
    # that are not already present in the environment. This avoids relying
    # on external packages and ensures the running process sees the same
    # DATABASE_URL that developers edit in `.env`.
    try:
        project_root = pathlib.Path(__file__).resolve().parents[1]
        dotenv_path = project_root / '.env'
        if dotenv_path.exists():
            with dotenv_path.open('r', encoding='utf-8') as fh:
                for raw in fh:
                    line = raw.strip()
                    if not line or line.startswith('#'):
                        continue
                    if '=' not in line:
                        continue
                    key, val = line.split('=', 1)
                    key = key.strip()
                    val = val.strip().strip('"').strip("'")
                    if key and key not in os.environ:
                        os.environ[key] = val
    except Exception:
        # Non-fatal: don't block app startup if .env parsing fails
        pass

    app.config.from_object(config_class)

    # Print effective DB URI at startup (dev-only) to help debugging
    try:
        print(f"[startup] SQLALCHEMY_DATABASE_URI={app.config.get('SQLALCHEMY_DATABASE_URI')}")
    except Exception:
        pass

    db.init_app(app)
    migrate.init_app(app, db)
    login.init_app(app)
    csrf.init_app(app)
    cache.init_app(app)

    login.login_view = 'auth.login'

    # Register blueprints
    from app.auth import bp as auth_bp
    app.register_blueprint(auth_bp, url_prefix='/auth')

    from app.mentorship import bp as mentorship_bp
    app.register_blueprint(mentorship_bp, url_prefix='')

    from app.admin import bp as admin_bp
    app.register_blueprint(admin_bp, url_prefix='/admin')

    # Index route - redirect unauthenticated users to login
    @app.route('/')
    def index():
        from flask import render_template
        if not current_user.is_authenticated:
            return redirect(url_for('auth.login'))
        return render_template('index.html')

    # Development helper: auto-create tables if running in debug mode and
    # the database is reachable but migrations are not set up. This avoids
    # the common 'no such table' errors during local development.
    # NOTE: This will not run in production when DEBUG is False.
    try:
        if app.debug:
            with app.app_context():
                # Create missing tables (no-op if already present)
                db.create_all()
    except Exception:
        # If DB is unreachable or create_all fails, skip silently so the
        # app startup doesn't crash here; original error will surface
        # on first DB access and be easier to debug.
        pass

    return app

from app import models
