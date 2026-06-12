import logging
import os
import time

from flask import Flask, g, jsonify, redirect, request, url_for
from flask_login import LoginManager, current_user
from sqlalchemy import text
from werkzeug.exceptions import HTTPException

from .config import Config
from .database import db
from .extensions import csrf, limiter
from .models import AdminUser, Trainer
from .utils.api_responses import api_error


def _column_exists(table_name, column_name):
    # PRAGMA table_info is safe from SQL injection as it only accepts table names
    # and SQLAlchemy's text() provides protection. Table names are hardcoded below.
    rows = db.session.execute(text(f"PRAGMA table_info({table_name})")).fetchall()
    return any(r[1] == column_name for r in rows)


def _run_sqlite_compat_migrations():
    """Backfill columns for users running older SQLite schema versions."""
    statements = []
    if not _column_exists("trainers", "role"):
        statements.append("ALTER TABLE trainers ADD COLUMN role TEXT DEFAULT 'trainer'")
    if not _column_exists("trainers", "email"):
        statements.append("ALTER TABLE trainers ADD COLUMN email TEXT")
    if not _column_exists("trainers", "phone"):
        statements.append("ALTER TABLE trainers ADD COLUMN phone TEXT")
    if not _column_exists("trainers", "is_active"):
        statements.append("ALTER TABLE trainers ADD COLUMN is_active INTEGER DEFAULT 1")
    if not _column_exists("trainers", "last_login"):
        statements.append("ALTER TABLE trainers ADD COLUMN last_login TIMESTAMP")
    if not _column_exists("trainers", "failed_login_attempts"):
        statements.append("ALTER TABLE trainers ADD COLUMN failed_login_attempts INTEGER DEFAULT 0")
    if not _column_exists("trainers", "locked_until"):
        statements.append("ALTER TABLE trainers ADD COLUMN locked_until TIMESTAMP")
    if not _column_exists("trainers", "last_failed_login"):
        statements.append("ALTER TABLE trainers ADD COLUMN last_failed_login TIMESTAMP")
    if not _column_exists("clients", "contact_number"):
        statements.append("ALTER TABLE clients ADD COLUMN contact_number TEXT")
    if not _column_exists("clients", "gym_name"):
        statements.append("ALTER TABLE clients ADD COLUMN gym_name TEXT")
    if not _column_exists("payments", "payment_mode"):
        statements.append("ALTER TABLE payments ADD COLUMN payment_mode TEXT DEFAULT 'cash'")
    if not _column_exists("payments", "gym_payment_done"):
        statements.append("ALTER TABLE payments ADD COLUMN gym_payment_done INTEGER DEFAULT 0")
    if not _column_exists("payments", "gym_payment_amount"):
        statements.append("ALTER TABLE payments ADD COLUMN gym_payment_amount NUMERIC(10, 2)")
    if not _column_exists("email_logs", "id"):
        statements.append("""CREATE TABLE IF NOT EXISTS email_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            trainer_id INTEGER NOT NULL,
            recipient_email VARCHAR(120) NOT NULL,
            recipient_name VARCHAR(100),
            subject VARCHAR(255) NOT NULL,
            email_type VARCHAR(50),
            status VARCHAR(20) DEFAULT 'sent',
            client_id INTEGER,
            error_message TEXT,
            sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (trainer_id) REFERENCES trainers(id),
            FOREIGN KEY (client_id) REFERENCES clients(id)
        )""")

    for sql in statements:
        db.session.execute(text(sql))

    if statements:
        db.session.commit()


def create_app(config_class=Config):
    """Application factory for creating Flask app."""
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    app = Flask(
        __name__,
        template_folder=os.path.join(root_dir, "templates"),
        static_folder=os.path.join(root_dir, "static"),
    )
    app.config.from_object(config_class)

    if app.config.get("SECRET_KEY") == "dev-secret-key-change-in-prod" and app.config.get("IS_PRODUCTION"):
        raise RuntimeError("Set a strong SECRET_KEY environment variable before running in production.")

    log_level = str(app.config.get("LOG_LEVEL", "WARNING")).upper()
    app.logger.setLevel(getattr(logging, log_level, logging.WARNING))

    db.init_app(app)
    csrf.init_app(app)
    limiter.init_app(app)

    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"
    login_manager.login_message = "Please log in to access this page."
    login_manager.session_protection = "strong"

    @login_manager.user_loader
    def load_user(user_id):
        if user_id == "admin":
            return AdminUser()
        try:
            return Trainer.query.get(int(user_id))
        except (TypeError, ValueError):
            return None

    @app.context_processor
    def inject_csrf():
        from flask_wtf.csrf import generate_csrf

        return dict(csrf_token=generate_csrf)

    @app.after_request
    def _add_security_headers(response):
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        if request.endpoint and str(request.endpoint).startswith("auth."):
            response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        return response

    # Initialize database with error handling for serverless
    is_vercel = os.environ.get('VERCEL') == 'true'

    with app.app_context():
        try:
            print("[OK] Testing database connection...")
            connection = db.engine.connect()
            connection.close()
            print("[OK] Database connection successful")

            print("[OK] Creating database tables...")
            db.create_all()
            print("[OK] Database tables created")

            if app.config["SQLALCHEMY_DATABASE_URI"].startswith("sqlite"):
                print("[OK] Running SQLite compatibility migrations...")
                _run_sqlite_compat_migrations()
                print("[OK] Migrations complete")
        except Exception as e:
            error_msg = f"[ERROR] DATABASE ERROR: {e}"
            print(error_msg)
            import traceback
            traceback.print_exc()

            # For Vercel, log but don't crash - let first request initialize
            if not is_vercel:
                raise
            else:
                print("[WARNING] Vercel: Deferring database initialization to first request")

    print("[OK] Registering blueprints")
    from .routes.admin import admin_bp
    from .routes.admin_management import admin_bp as admin_mgmt_bp
    from .routes.analytics import analytics_bp
    from .routes.auth import auth_bp
    from .routes.clients import clients_bp
    from .routes.cron import cron_bp
    from .routes.dashboard import dashboard_bp
    from .routes.export import export_bp
    from .routes.gamification import gamification_bp
    from .routes.payments import payments_bp
    from .routes.reminders import reminders_bp
    from .routes.security import security_bp
    from .routes.tracking import tracking_bp
    from .routes.email_logs import email_logs_bp
    from .routes.impersonate import impersonate_bp
    from .routes.send_email import send_email_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(clients_bp)
    app.register_blueprint(payments_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(reminders_bp)
    app.register_blueprint(tracking_bp)
    app.register_blueprint(analytics_bp)
    app.register_blueprint(export_bp)
    app.register_blueprint(admin_mgmt_bp)
    app.register_blueprint(gamification_bp)
    app.register_blueprint(security_bp)
    app.register_blueprint(email_logs_bp)
    app.register_blueprint(impersonate_bp)
    app.register_blueprint(cron_bp)
    app.register_blueprint(send_email_bp)

    csrf.exempt(cron_bp)
    print("[OK] All blueprints registered")

    @app.errorhandler(Exception)
    def handle_exception(e):
        """Global exception handler for better error reporting"""
        app.logger.error(f"Unhandled exception: {e}", exc_info=True)
        if isinstance(e, HTTPException):
            return e
        return jsonify({
            "error": "Internal server error",
            "message": str(e) if app.debug else "An unexpected error occurred"
        }), 500

    @app.route("/")
    def index():
        return redirect(url_for("dashboard.main"))

    @app.route("/health")
    def health():
        return jsonify({"ok": True, "status": "healthy"})

    @app.route("/login")
    def login_legacy():
        return redirect(url_for("auth.login"))

    @app.route("/register")
    def register_legacy():
        return redirect(url_for("auth.register"))

    print("=" * 60)
    print("[SUCCESS] FLASK APP INITIALIZED SUCCESSFULLY")
    print("=" * 60)
    return app
