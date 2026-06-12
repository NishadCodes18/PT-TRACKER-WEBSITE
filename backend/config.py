import os
from datetime import timedelta

_BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
_DEFAULT_DB_PATH = os.path.join(_BASE_DIR, 'gym_tracker.db').replace('\\', '/')

def _env(name, default=None, *, strip=True, remove_spaces=False):
    value = os.environ.get(name, default)
    if value is None:
        return default
    value = str(value)
    if strip:
        value = value.strip()
    if remove_spaces:
        value = value.replace(' ', '')
    return value

def _env_bool(name, default=False):
    value = os.environ.get(name)
    if value is None:
        return default
    return str(value).strip().lower() in {'1', 'true', 'yes', 'on', 't'}

def _database_uri():
    uri = os.environ.get('DATABASE_URL')
    if uri:
        # Fix Heroku/Render postgres:// to postgresql://
        if uri.startswith('postgres://'):
            uri = uri.replace('postgres://', 'postgresql://', 1)
        # For Vercel with PostgreSQL, ensure proper connection parameters
        if _env_bool('VERCEL') and 'postgresql://' in uri:
            # Add sslmode if not present for PostgreSQL connections
            if '?' not in uri:
                uri += '?sslmode=require'
            elif 'sslmode=' not in uri:
                uri += '&sslmode=require'
        return uri
    return f'sqlite:///{_DEFAULT_DB_PATH}'

class Config:
    """Application configuration class"""
    BASE_DIR = _BASE_DIR
    IS_PRODUCTION = _env_bool('RENDER') or _env_bool('VERCEL') or _env('FLASK_ENV', '') == 'production'

    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-prod'
    SQLALCHEMY_DATABASE_URI = _database_uri()
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    # Vercel serverless functions need smaller connection pools and shorter timeouts
    _is_vercel = _env_bool('VERCEL')
    if _is_vercel:
        SQLALCHEMY_ENGINE_OPTIONS = {
            'pool_pre_ping': True,
            'pool_recycle': 300,
            'pool_size': 1,
            'max_overflow': 0,
            'pool_timeout': 10,
            'connect_args': {
                'connect_timeout': 10,
                'sslmode': 'require'
            }
        }
    else:
        SQLALCHEMY_ENGINE_OPTIONS = {
            'pool_pre_ping': True,
            'pool_recycle': 300,
            'pool_size': 10,
            'max_overflow': 5,
            'connect_args': {'connect_timeout': 10}
        }

    PERMANENT_SESSION_LIFETIME = timedelta(days=7)
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SECURE = _env_bool('SESSION_COOKIE_SECURE', IS_PRODUCTION)
    SESSION_COOKIE_SAMESITE = _env('SESSION_COOKIE_SAMESITE', 'Lax')
    REMEMBER_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_SECURE = _env_bool('REMEMBER_COOKIE_SECURE', IS_PRODUCTION)
    REMEMBER_COOKIE_SAMESITE = _env('REMEMBER_COOKIE_SAMESITE', 'Lax')

    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = int(_env('WTF_CSRF_TIME_LIMIT', 3600, strip=True))

    LOG_LEVEL = _env('LOG_LEVEL', 'WARNING')
    LOGIN_MAX_ATTEMPTS = int(_env('LOGIN_MAX_ATTEMPTS', 5, strip=True))
    LOGIN_LOCKOUT_MINUTES = int(_env('LOGIN_LOCKOUT_MINUTES', 15, strip=True))
    ADMIN_USERNAME = _env('ADMIN_USERNAME', 'adminvenom')
    ADMIN_PASSWORD = _env('ADMIN_PASSWORD', 'adminvenom@123')
    PASSWORD_RESET_OTP_MINUTES = int(_env('PASSWORD_RESET_OTP_MINUTES', 10, strip=True))
    PASSWORD_RESET_MAX_ATTEMPTS = int(_env('PASSWORD_RESET_MAX_ATTEMPTS', 5, strip=True))

    # --- EMAIL SETTINGS ---
    # SMTP (legacy - may not work on Render free tier)
    SMTP_SERVER = _env('SMTP_SERVER', 'smtp.gmail.com')
    SMTP_PORT = int(_env('SMTP_PORT', 587, strip=True))
    SMTP_USE_TLS = _env_bool('SMTP_USE_TLS', True)
    SMTP_USE_SSL = _env_bool('SMTP_USE_SSL', False)
    SMTP_USER = _env('SMTP_USER')
    SMTP_PASSWORD = _env('SMTP_PASSWORD', remove_spaces=True)

    # Brevo API (recommended for Render free tier)
    BREVO_API_KEY = _env('BREVO_API_KEY')
    BREVO_SENDER_EMAIL = _env('BREVO_SENDER_EMAIL')
    BREVO_SENDER_NAME = _env('BREVO_SENDER_NAME', 'PT Tracker')

    # Mailgun API (alternative for Render free tier)
    MAILGUN_API_KEY = _env('MAILGUN_API_KEY')
    MAILGUN_DOMAIN = _env('MAILGUN_DOMAIN')
    MAILGUN_FROM_EMAIL = _env('MAILGUN_FROM_EMAIL')

    # Email provider preference: 'brevo_api', 'mailgun_api' or 'smtp'
    EMAIL_PROVIDER = _env('EMAIL_PROVIDER', 'brevo_api')

    GYM_NAME = _env('GYM_NAME', 'NITRRO ZONE 360')
    APP_DEVELOPER = _env('APP_DEVELOPER', 'NISHAD PATIL')

    CRON_SECRET = _env('CRON_SECRET')
    RATELIMIT_ENABLED = _env_bool('RATELIMIT_ENABLED', True)
    RATELIMIT_DEFAULT = _env('RATELIMIT_DEFAULT', '500 per hour')
