"""Client-related transactional emails."""
from email_validator import EmailNotValidError, validate_email
from flask import current_app

from ..models import ADMIN_DATA_OWNER_USERNAME
from .email_context import resolve_gym_name
from .mail import send_html_email, send_html_email_async


def _trainer_display_name(trainer):
    if not trainer:
        return None
    if trainer.username == ADMIN_DATA_OWNER_USERNAME:
        return 'Admin'
    return trainer.username


def _normalize_client_email(email):
    raw = (email or '').strip()
    if not raw:
        return None
    try:
        return validate_email(raw, check_deliverability=False).normalized
    except EmailNotValidError:
        return None


def build_welcome_email_context(client):
    gym_name = resolve_gym_name(client=client)
    trainer_name = _trainer_display_name(client.trainer) or gym_name
    renewal_date = client.renewal_date.strftime('%d %b %Y') if client.renewal_date else None
    return {
        'client_name': client.name,
        'trainer_name': trainer_name,
        'gym_name': gym_name,
        'pt_tier': client.pt_tier or 'Silver',
        'time_slot': client.time_slot or 'To be confirmed',
        'renewal_date': renewal_date,
    }


def send_client_welcome_email(client):
    """Send welcome email synchronously. Returns True if sent."""
    email = _normalize_client_email(client.email)
    if not email:
        return False

    ctx = build_welcome_email_context(client)
    subject = f"Welcome to {ctx['gym_name']}!"
    return send_html_email(
        email,
        subject,
        'welcome_new',
        trainer_id=client.trainer_id,
        email_type='welcome',
        client_id=client.id,
        recipient_name=client.name,
        **ctx,
    )


def dispatch_client_welcome_email(app, client):
    """Queue welcome email after client create (non-blocking)."""
    email = _normalize_client_email(client.email)
    if not email:
        return False

    ctx = build_welcome_email_context(client)
    subject = f"Welcome to {ctx['gym_name']}!"
    send_html_email_async(
        app,
        email,
        subject,
        'welcome_new',
        trainer_id=client.trainer_id,
        email_type='welcome',
        client_id=client.id,
        recipient_name=client.name,
        **ctx,
    )
    return True
