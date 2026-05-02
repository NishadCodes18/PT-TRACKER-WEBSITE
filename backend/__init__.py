import os
from flask import Flask, redirect, url_for
from flask_login import LoginManager
from sqlalchemy import text
from .config import Config
from .database import db, init_db
from .models import Trainer, AdminUser
def _column_exists(table_name, column_name):
    rows = db.session.execute(text(f"PRAGMA table_info({table_name})")).fetchall()
    return any(r[1] == column_name for r in rows)
def _run_sqlite_compat_migrations():
    """Backfill columns for users running older SQLite schema versions."""
    statements = []
    if not _column_exists('trainers', 'shift_type'):
        statements.append("ALTER TABLE trainers ADD COLUMN shift_type TEXT DEFAULT '8-hour'")
    if not _column_exists('clients', 'contact_number'):
        statements.append("ALTER TABLE clients ADD COLUMN contact_number TEXT")
    for sql in statements:
        db.session.execute(text(sql))
    if statements:
        db.session.commit()
def create_app(config_class=Config):
    """Application factory for creating Flask app"""
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    app = Flask(
        __name__,
        template_folder=os.path.join(root_dir, 'templates'),
        static_folder=os.path.join(root_dir, 'static')
    )
    app.config.from_object(config_class)
    db.init_app(app)
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please log in to access this page.'
    @login_manager.user_loader
    def load_user(user_id):
        if user_id == 'admin':
            return AdminUser()
        try:
            return Trainer.query.get(int(user_id))
        except (TypeError, ValueError):
            return None
    with app.app_context():
        db.create_all()
        _run_sqlite_compat_migrations()
    from .routes.auth import auth_bp
    from .routes.dashboard import dashboard_bp
    from .routes.clients import clients_bp
    from .routes.payments import payments_bp
    from .routes.admin import admin_bp
    from .routes.reminders import reminders_bp
    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(clients_bp)
    app.register_blueprint(payments_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(reminders_bp)
    @app.route('/')
    def index():
        return redirect(url_for('dashboard.main'))

    @app.route('/login')
    def login_legacy():
        return redirect(url_for('auth.login'))

    @app.route('/register')
    def register_legacy():
        return redirect(url_for('auth.register'))

    return app