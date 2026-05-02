from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
from ..models import Trainer, AdminUser
from ..database import db
auth_bp = Blueprint('auth', __name__, url_prefix='/auth')
ADMIN_USERNAME = 'adminvenom'
ADMIN_PASSWORD = 'adminvenom@123'
@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Handle user login"""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.main'))
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        remember = bool(request.form.get('remember', False))
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            login_user(AdminUser(), remember=remember)
            next_page = request.args.get('next')
            return redirect(next_page if next_page else url_for('dashboard.admin_panel'))
        trainer = Trainer.query.filter_by(username=username).first()
        if trainer and trainer.check_password(password):
            login_user(trainer, remember=remember)
            next_page = request.args.get('next')
            return redirect(next_page if next_page else url_for('dashboard.main'))
        else:
            flash('Invalid username or password', 'error')
    return render_template('login.html')
@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """Handle new user registration"""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.main'))
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        if not username or not password:
            flash('Username and password are required', 'error')
        elif len(username) < 3:
            flash('Username must be at least 3 characters', 'error')
        elif len(password) < 6:
            flash('Password must be at least 6 characters', 'error')
        elif password != confirm_password:
            flash('Passwords do not match', 'error')
        else:
            existing = Trainer.query.filter_by(username=username).first()
            if existing:
                flash('Username already taken', 'error')
            else:
                trainer = Trainer(username=username)
                trainer.set_password(password)
                db.session.add(trainer)
                db.session.commit()
                flash('Account created! Please login.', 'success')
                return redirect(url_for('auth.login'))
    return render_template('register.html')
@auth_bp.route('/logout')
@login_required
def logout():
    """Handle user logout"""
    logout_user()
    flash('You have been logged out', 'info')
    return redirect(url_for('auth.login'))