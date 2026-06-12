import secrets
from datetime import datetime

import pyotp
from email_validator import EmailNotValidError, validate_email
from flask import Blueprint, current_app, flash, redirect, render_template, request, session, url_for
from flask_login import current_user, login_required, login_user, logout_user
from sqlalchemy import or_
from werkzeug.security import check_password_hash

from ..database import db
from ..extensions import limiter
from ..models import AdminUser, EmailLog, PasswordResetOTP, Trainer, TwoFactorAuth
from ..models_license import LicenseKey
from ..utils.mail import send_html_email
from ..utils.security_helpers import is_safe_redirect_url

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

_DEFAULT_ADMIN_PASSWORD = 'adminvenom@123'


def _find_reset_trainer(identifier):
    identifier = (identifier or '').strip()
    if not identifier:
        return None
    return Trainer.query.filter(
        or_(
            Trainer.username.ilike(identifier),
            Trainer.email.ilike(identifier),
        )
    ).first()


def _password_reset_context():
    trainer_id = session.get('password_reset_trainer_id')
    if not trainer_id:
        return None, None
    trainer = Trainer.query.get(trainer_id)
    record = PasswordResetOTP.query.filter_by(trainer_id=trainer_id).first()
    if not trainer or not record:
        session.pop('password_reset_trainer_id', None)
        session.pop('password_reset_verified', None)
        return None, None
    return trainer, record


def _send_password_reset_otp(trainer, otp):
    gym_name = current_app.config.get('GYM_NAME', 'Gym Tracker')
    subject = f"{gym_name} password reset code"
    expiry_minutes = current_app.config.get('PASSWORD_RESET_OTP_MINUTES', 10)
    sent = send_html_email(
        trainer.email,
        subject,
        'password_reset_otp',
        trainer_name=trainer.username,
        otp_code=otp,
        expiry_minutes=expiry_minutes,
        gym_name=gym_name,
    )
    log_entry = EmailLog(
        trainer_id=trainer.id,
        recipient_email=trainer.email,
        subject=subject,
        email_type='password_reset_otp',
        status='sent' if sent else 'failed',
        error_message=None if sent else 'SMTP delivery failed or SMTP credentials missing',
    )
    db.session.add(log_entry)
    db.session.commit()
    return sent


def _unlock_expired_login(trainer):
    if trainer.locked_until and trainer.locked_until <= datetime.utcnow():
        trainer.reset_login_lockout()


def _lockout_message(trainer):
    if not trainer.locked_until:
        return 'Account locked due to too many failed attempts.'
    remaining = trainer.locked_until - datetime.utcnow()
    remaining_seconds = max(0, int(remaining.total_seconds()))
    remaining_minutes = max(1, (remaining_seconds + 59) // 60)
    return f'Account locked due to too many failed attempts. Try again in {remaining_minutes} minute(s).'


def _register_login_failure(trainer):
    lockout_threshold = current_app.config.get('LOGIN_MAX_ATTEMPTS', 5)
    lockout_minutes = current_app.config.get('LOGIN_LOCKOUT_MINUTES', 15)
    trainer.record_failed_login(lockout_threshold=lockout_threshold, lockout_minutes=lockout_minutes)
    db.session.commit()


def _register_login_success(trainer):
    trainer.reset_login_lockout()
    trainer.last_login = datetime.utcnow()
    db.session.commit()


def _trainer_requires_2fa(trainer):
    twofa = TwoFactorAuth.query.filter_by(trainer_id=trainer.id).first()
    return bool(twofa and twofa.is_enabled and twofa.secret_key)


def _admin_login_allowed(username, password):
    admin_username = current_app.config.get('ADMIN_USERNAME', 'adminvenom')
    admin_password = current_app.config.get('ADMIN_PASSWORD', _DEFAULT_ADMIN_PASSWORD)
    if username != admin_username or password != admin_password:
        return False
    if current_app.config.get('IS_PRODUCTION') and admin_password == _DEFAULT_ADMIN_PASSWORD:
        flash('Set a strong ADMIN_PASSWORD in your hosting environment before using admin login.', 'error')
        return False
    return True


@auth_bp.route('/login', methods=['GET', 'POST'])
@limiter.limit('12 per minute')
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.main'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        remember = bool(request.form.get('remember', False))

        if _admin_login_allowed(username, password):
            login_user(AdminUser(), remember=remember)
            next_page = request.args.get('next')
            if next_page and is_safe_redirect_url(next_page):
                return redirect(next_page)
            return redirect(url_for('dashboard.admin_panel'))

        # Allow login with username or email
        trainer = Trainer.query.filter(
            or_(
                Trainer.username == username,
                Trainer.email == username
            )
        ).first()
        if trainer:
            _unlock_expired_login(trainer)
            if trainer.is_login_locked():
                db.session.commit()
                flash(_lockout_message(trainer), 'error')
                return render_template('login.html')

        if trainer and trainer.check_password(password):
            if _trainer_requires_2fa(trainer):
                session['pending_2fa_trainer_id'] = trainer.id
                session['pending_2fa_remember'] = remember
                return redirect(url_for('auth.login_2fa'))

            _register_login_success(trainer)
            login_user(trainer, remember=remember)
            next_page = request.args.get('next')
            if next_page and is_safe_redirect_url(next_page):
                return redirect(next_page)
            return redirect(url_for('dashboard.main'))

        if trainer:
            _register_login_failure(trainer)
            if trainer.is_login_locked():
                flash(_lockout_message(trainer), 'error')
                return render_template('login.html')
        flash('Invalid username or password', 'error')

    return render_template('login.html')


@auth_bp.route('/login/2fa', methods=['GET', 'POST'])
@limiter.limit('12 per minute')
def login_2fa():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.main'))

    trainer_id = session.get('pending_2fa_trainer_id')
    if not trainer_id:
        return redirect(url_for('auth.login'))

    trainer = Trainer.query.get(trainer_id)
    twofa = TwoFactorAuth.query.filter_by(trainer_id=trainer_id).first() if trainer else None
    if not trainer or not twofa or not twofa.is_enabled:
        session.pop('pending_2fa_trainer_id', None)
        return redirect(url_for('auth.login'))

    if request.method == 'POST':
        code = request.form.get('code', '').strip().replace(' ', '')
        totp = pyotp.TOTP(twofa.secret_key)
        if totp.verify(code, valid_window=1):
            remember = bool(session.pop('pending_2fa_remember', False))
            session.pop('pending_2fa_trainer_id', None)
            _register_login_success(trainer)
            login_user(trainer, remember=remember)
            flash('Signed in successfully.', 'success')
            return redirect(url_for('dashboard.main'))
        flash('Invalid authentication code. Try again.', 'error')

    return render_template('login_2fa.html', trainer=trainer)


@auth_bp.route('/forgot-password', methods=['GET', 'POST'])
@limiter.limit('6 per hour')
def forgot_password():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.main'))

    if request.method == 'POST':
        identifier = request.form.get('identifier', '').strip()
        trainer = _find_reset_trainer(identifier)

        if not trainer or not trainer.email:
            flash('If the account exists and has an email address on file, an OTP will be sent.', 'info')
            return render_template('forgot_password.html')

        otp = f"{secrets.randbelow(1000000):06d}"
        record = PasswordResetOTP.query.filter_by(trainer_id=trainer.id).first()
        if not record:
            record = PasswordResetOTP(trainer_id=trainer.id, otp_hash='pending', expires_at=datetime.utcnow())
        record.store_otp(otp, current_app.config.get('PASSWORD_RESET_OTP_MINUTES', 10))
        db.session.add(record)
        db.session.commit()

        if _send_password_reset_otp(trainer, otp):
            session['password_reset_trainer_id'] = trainer.id
            session['password_reset_verified'] = False
            flash('OTP sent to your email. Enter it to continue.', 'success')
            return redirect(url_for('auth.verify_reset_otp'))

        flash('Unable to send the reset OTP. Check SMTP settings and try again.', 'error')

    return render_template('forgot_password.html')


@auth_bp.route('/forgot-password/verify', methods=['GET', 'POST'])
@limiter.limit('20 per hour')
def verify_reset_otp():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.main'))

    trainer, record = _password_reset_context()
    if not trainer or not record:
        flash('Start the reset process again.', 'info')
        return redirect(url_for('auth.forgot_password'))

    if request.method == 'POST':
        otp = request.form.get('otp', '').strip()
        max_attempts = current_app.config.get('PASSWORD_RESET_MAX_ATTEMPTS', 5)

        if not otp or len(otp) != 6 or not otp.isdigit():
            flash('Enter the 6-digit code from your email.', 'error')
            return render_template('verify_reset_otp.html', trainer=trainer)

        if record.is_expired() or record.consumed_at:
            flash('That OTP has expired. Request a new one.', 'error')
            return redirect(url_for('auth.forgot_password'))

        if not record.can_retry(max_attempts):
            flash('Too many invalid attempts. Request a new OTP.', 'error')
            return redirect(url_for('auth.forgot_password'))

        if not check_password_hash(record.otp_hash, otp):
            record.attempts += 1
            db.session.commit()
            flash('Invalid OTP. Please try again.', 'error')
            return render_template('verify_reset_otp.html', trainer=trainer)

        record.verified_at = datetime.utcnow()
        db.session.commit()
        session['password_reset_verified'] = True
        flash('OTP verified. Set your new password now.', 'success')
        return redirect(url_for('auth.reset_password'))

    return render_template('verify_reset_otp.html', trainer=trainer)


@auth_bp.route('/forgot-password/reset', methods=['GET', 'POST'])
@limiter.limit('10 per hour')
def reset_password():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.main'))

    trainer, record = _password_reset_context()
    if not trainer or not record or not session.get('password_reset_verified'):
        flash('Verify your OTP before setting a new password.', 'info')
        return redirect(url_for('auth.forgot_password'))

    if record.is_expired() or record.consumed_at:
        flash('That reset link has expired. Please request a new OTP.', 'error')
        return redirect(url_for('auth.forgot_password'))

    if request.method == 'POST':
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')

        if len(password) < 8:
            flash('Password must be at least 8 characters long.', 'error')
        elif password != confirm_password:
            flash('Passwords do not match.', 'error')
        else:
            trainer.set_password(password)
            record.consumed_at = datetime.utcnow()
            db.session.commit()
            session.pop('password_reset_trainer_id', None)
            session.pop('password_reset_verified', None)
            flash('Password reset successfully. You can sign in now.', 'success')
            return redirect(url_for('auth.login'))

    return render_template('reset_password.html', trainer=trainer)


@auth_bp.route('/register', methods=['GET', 'POST'])
@limiter.limit('8 per hour')
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.main'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        license_key = request.form.get('license_key', '').strip()

        # Validate license key first
        if not license_key:
            flash('License key is required to create an account', 'error')
            return render_template('register.html')

        # Check if license key exists and is valid
        license_record = LicenseKey.query.filter_by(license_key=license_key).first()
        if not license_record:
            flash('Invalid license key', 'error')
            return render_template('register.html')

        if license_record.is_used:
            flash('This license key has already been used', 'error')
            return render_template('register.html')

        if not username or not email or not password:
            flash('Username, email, and password are required', 'error')
            return render_template('register.html')

        if len(username) < 3:
            flash('Username must be at least 3 characters', 'error')
            return render_template('register.html')

        try:
            email = validate_email(email, check_deliverability=False).normalized
        except EmailNotValidError:
            flash('Enter a valid email address', 'error')
            return render_template('register.html')

        if len(password) < 8:
            flash('Password must be at least 8 characters', 'error')
            return render_template('register.html')

        if password != confirm_password:
            flash('Passwords do not match', 'error')
            return render_template('register.html')

        if Trainer.query.filter_by(username=username).first():
            flash('Username already taken', 'error')
            return render_template('register.html')
        if Trainer.query.filter_by(email=email).first():
            flash('Email already registered', 'error')
            return render_template('register.html')

        # Create trainer account
        trainer = Trainer(username=username, email=email)
        trainer.set_password(password)
        db.session.add(trainer)
        db.session.flush()  # Get trainer.id before marking license as used

        # Mark license key as used
        license_record.mark_as_used(trainer.id)
        db.session.commit()

        flash('Account created successfully! Please login.', 'success')
        return redirect(url_for('auth.login'))

    return render_template('register.html')


@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    session.pop('password_reset_trainer_id', None)
    session.pop('password_reset_verified', None)
    session.pop('pending_2fa_trainer_id', None)
    session.pop('pending_2fa_remember', None)
    flash('You have been logged out', 'info')
    return redirect(url_for('auth.login'))
