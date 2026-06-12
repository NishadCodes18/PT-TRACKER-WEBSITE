"""Shared context for HTML email templates."""
from datetime import datetime

from flask import current_app


def resolve_gym_name(client=None, override=None):
    """Prefer per-client gym, then explicit override, then app config."""
    if override and str(override).strip():
        return str(override).strip()
    if client is not None:
        client_gym = getattr(client, 'gym_name', None)
        if client_gym and str(client_gym).strip():
            return str(client_gym).strip()
    return current_app.config.get('GYM_NAME', 'Gym Tracker')


def build_email_context(**overrides):
    """Defaults used by every email template extending base.html."""
    gym_name = overrides.pop('gym_name', None) or current_app.config.get('GYM_NAME', 'Gym Tracker')
    context = {
        'gym_name': gym_name,
        'subject': overrides.get('subject', ''),
        'year': datetime.utcnow().year,
        'support_email': 'nishadpatil2008@gmail.com',
        'app_developer': current_app.config.get('APP_DEVELOPER', 'NISHAD PATIL'),
        'trainer_name': overrides.get('trainer_name'),
    }
    context.update(overrides)
    return context
