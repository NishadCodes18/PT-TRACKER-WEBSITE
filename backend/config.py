import os
from datetime import timedelta


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


class Config:
    """Application configuration class"""
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-prod'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///../gym_tracker.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    PERMANENT_SESSION_LIFETIME = timedelta(days=7)
    WTF_CSRF_ENABLED = True
    
    SMTP_SERVER = _env('SMTP_SERVER', 'smtp.gmail.com')
    SMTP_PORT = int(_env('SMTP_PORT', 587, strip=True))
    SMTP_USER = _env('SMTP_USER')
    SMTP_PASSWORD = _env('SMTP_PASSWORD', remove_spaces=True)
    GYM_NAME = _env('GYM_NAME', 'NITRRO ZONE 360')