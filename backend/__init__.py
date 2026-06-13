import logging
import os
import time

from flask import Flask, g, jsonify, redirect, render_template, request, url_for
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

    # Track database initialization state
    app.config['DB_INITIALIZED'] = False

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

    @app.before_request
    def check_db_initialization():
        """Show loading page if database is not ready yet"""
        # Skip for static files, health check, and loading page itself
        if (request.path.startswith('/static/') or
            request.path == '/health' or
            request.path == '/favicon.ico' or
            request.path == '/favicon.png'):
            return None

        # If database not initialized, try to initialize it now
        if not app.config.get('DB_INITIALIZED', False):
            try:
                app.logger.info("[RETRY] Attempting database initialization on first request...")
                connection = db.engine.connect()
                connection.close()
                db.create_all()

                if app.config["SQLALCHEMY_DATABASE_URI"].startswith("sqlite"):
                    _run_sqlite_compat_migrations()

                app.config['DB_INITIALIZED'] = True
                app.logger.info("[OK] Database initialized successfully on first request")
                return None  # Continue with the request
            except Exception as e:
                app.logger.error(f"[ERROR] Database initialization failed: {e}")
                # Show loading page with 503 status
                return render_template('loading.html'), 503

    @app.after_request
    def _add_security_headers(response):
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("X-Content-Type-Options", "nosniff")

        # Add compression hint
        if 'gzip' in request.headers.get('Accept-Encoding', '').lower():
            response.headers.setdefault('Vary', 'Accept-Encoding')

        # Cache static assets aggressively
        if request.path.startswith('/static/'):
            response.headers['Cache-Control'] = 'public, max-age=31536000, immutable'
        elif request.endpoint and str(request.endpoint).startswith("auth."):
            response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        else:
            # API responses - short cache
            response.headers['Cache-Control'] = 'public, max-age=60'

        return response

    # Initialize database with error handling for serverless
    is_vercel = os.environ.get('VERCEL') == 'true'

    with app.app_context():
        try:
            app.logger.info("[OK] Testing database connection...")
            print("[OK] Testing database connection...")
            connection = db.engine.connect()
            connection.close()
            app.logger.info("[OK] Database connection successful")
            print("[OK] Database connection successful")

            app.logger.info("[OK] Creating database tables...")
            print("[OK] Creating database tables...")
            db.create_all()
            app.logger.info("[OK] Database tables created")
            print("[OK] Database tables created")

            if app.config["SQLALCHEMY_DATABASE_URI"].startswith("sqlite"):
                app.logger.info("[OK] Running SQLite compatibility migrations...")
                print("[OK] Running SQLite compatibility migrations...")
                _run_sqlite_compat_migrations()
                app.logger.info("[OK] Migrations complete")
                print("[OK] Migrations complete")

            # Mark database as initialized
            app.config['DB_INITIALIZED'] = True
        except Exception as e:
            error_msg = f"[ERROR] DATABASE ERROR: {e}"
            app.logger.error(error_msg, exc_info=True)
            print(error_msg)
            import traceback
            traceback.print_exc()

            # Provide helpful hints for common issues
            error_str = str(e).lower()
            if "could not translate host name" in error_str or "name or service not known" in error_str:
                hint = "\nHINT: Cannot resolve database hostname. If using Render database on Vercel:\n"
                hint += "- Use the EXTERNAL database URL from Render (with .render.com suffix)\n"
                hint += "- Example: postgresql://user:pass@dpg-xxx.oregon-postgres.render.com/db\n"
                hint += "- NOT the internal URL: postgresql://user:pass@dpg-xxx/db\n"
                hint += "- Get external URL from Render Dashboard > Database > Connections > External Database URL\n"
                print(hint)
                app.logger.error(hint)
            elif "connect_timeout" in error_str or "timeout" in error_str:
                hint = "\nHINT: Database connection timeout. Check:\n"
                hint += "- Database is running and accessible\n"
                hint += "- Firewall/security groups allow connections from Vercel IPs\n"
                hint += "- DATABASE_URL has correct credentials\n"
                print(hint)
                app.logger.error(hint)
            elif "password authentication failed" in error_str:
                hint = "\nHINT: Database authentication failed. Check:\n"
                hint += "- DATABASE_URL has correct username and password\n"
                hint += "- Password doesn't contain special characters that need URL encoding\n"
                print(hint)
                app.logger.error(hint)

            # For Vercel, log but don't crash - let first request initialize
            if not is_vercel:
                raise
            else:
                app.logger.warning("[WARNING] Vercel: Deferring database initialization to first request")
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
    from .routes.license_admin import license_admin_bp

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
    app.register_blueprint(license_admin_bp)

    csrf.exempt(cron_bp)
    print("[OK] All blueprints registered")

    @app.errorhandler(Exception)
    def handle_exception(e):
        """Global exception handler for better error reporting"""
        # Don't log 404s as errors - they're expected
        if isinstance(e, HTTPException):
            if e.code == 404:
                app.logger.debug(f"404 Not Found: {request.url}")
            return e

        # Log actual errors
        app.logger.error(f"Unhandled exception: {e}", exc_info=True)
        return jsonify({
            "error": "Internal server error",
            "message": str(e) if app.debug else "An unexpected error occurred"
        }), 500

    @app.route("/")
    def index():
        # Show loading page if database not initialized yet
        if not app.config.get('DB_INITIALIZED', False):
            return render_template('loading.html')
        return redirect(url_for("dashboard.main"))

    @app.route("/health")
    def health():
        db_ready = app.config.get('DB_INITIALIZED', False)
        return jsonify({
            "ok": db_ready,
            "status": "healthy" if db_ready else "initializing",
            "db_initialized": db_ready
        })

    @app.route("/favicon.ico")
    @app.route("/favicon.png")
    def favicon():
        """Handle favicon requests to prevent 404 errors in logs"""
        from flask import send_from_directory
        import os
        # Try both .ico and .png
        for filename in ['favicon.ico', 'favicon.png']:
            favicon_path = os.path.join(app.static_folder, filename)
            if os.path.exists(favicon_path):
                mimetype = 'image/vnd.microsoft.icon' if filename.endswith('.ico') else 'image/png'
                return send_from_directory(app.static_folder, filename, mimetype=mimetype)
        # Return 204 No Content if favicon doesn't exist
        return '', 204

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
