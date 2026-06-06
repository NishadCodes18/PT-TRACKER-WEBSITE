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
    return str(value).strip().lower() in {'1', 'true', 'yes', 'on'}


def _database_uri():
    uri = os.environ.get('DATABASE_URL')
    if uri:
        if uri.startswith('postgres://'):
            uri = uri.replace('postgres://', 'postgresql://', 1)
        return uri
    return f'sqlite:///{_DEFAULT_DB_PATH}'


class Config:
    """Application configuration class"""
    BASE_DIR = _BASE_DIR
    IS_PRODUCTION = _env_bool('RENDER') or _env('FLASK_ENV', '') == 'production'

    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-prod'
    SQLALCHEMY_DATABASE_URI = _database_uri()
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {'pool_pre_ping': True}

    PERMANENT_SESSION_LIFETIME = timedelta(days=7)
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SECURE = _env_bool('SESSION_COOKIE_SECURE', IS_PRODUCTION)
    SESSION_COOKIE_SAMESITE = _env('SESSION_COOKIE_SAMESITE', 'Lax')
    REMEMBER_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_SECURE = _env_bool('REMEMBER_COOKIE_SECURE', IS_PRODUCTION)
    REMEMBER_COOKIE_SAMESITE = _env('REMEMBER_COOKIE_SAMESITE', 'Lax')

    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = int(_env('WTF_CSRF_TIME_LIMIT', 3600, strip=True))

    LOG_LEVEL = _env('LOG_LEVEL', 'INFO')
    SLOW_REQUEST_MS = int(_env('SLOW_REQUEST_MS', 400, strip=True))
    LOGIN_MAX_ATTEMPTS = int(_env('LOGIN_MAX_ATTEMPTS', 5, strip=True))
    LOGIN_LOCKOUT_MINUTES = int(_env('LOGIN_LOCKOUT_MINUTES', 15, strip=True))
    ADMIN_USERNAME = _env('ADMIN_USERNAME', 'adminvenom')
    ADMIN_PASSWORD = _env('ADMIN_PASSWORD', 'adminvenom@123')
    PASSWORD_RESET_OTP_MINUTES = int(_env('PASSWORD_RESET_OTP_MINUTES', 10, strip=True))
    PASSWORD_RESET_MAX_ATTEMPTS = int(_env('PASSWORD_RESET_MAX_ATTEMPTS', 5, strip=True))

    SMTP_SERVER = _env('SMTP_SERVER', 'smtp.gmail.com')
    SMTP_PORT = int(_env('SMTP_PORT', 587, strip=True))
    SMTP_USER = _env('SMTP_USER')
    SMTP_PASSWORD = _env('SMTP_PASSWORD', remove_spaces=True)
    GYM_NAME = _env('GYM_NAME', 'NITRRO ZONE 360')
    APP_DEVELOPER = _env('APP_DEVELOPER', 'NISHAD PATIL')

    CRON_SECRET = _env('CRON_SECRET')
    RATELIMIT_ENABLED = _env_bool('RATELIMIT_ENABLED', True)
    RATELIMIT_DEFAULT = _env('RATELIMIT_DEFAULT', '200 per hour')
