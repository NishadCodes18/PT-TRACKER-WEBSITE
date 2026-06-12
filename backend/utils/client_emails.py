"""Client-related transactional emails."""
from email_validator import EmailNotValidError, validate_email
from flask import current_app

from ..models import ADMIN_DATA_OWNER_USERNAME
from .email_context import resolve_gym_name
from .mail import send_html_email


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

    # Format time_slot to include AM/PM if it's a time
    session_time = client.time_slot or 'To be confirmed'
    if session_time and session_time != 'To be confirmed':
        # Try to format time with AM/PM if it contains time information
        # Example: "9:00" becomes "9:00 AM", "14:30" becomes "2:30 PM"
        import re
        time_pattern = r'(\d{1,2}):(\d{2})'
        match = re.search(time_pattern, session_time)
        if match:
            hour = int(match.group(1))
            minute = match.group(2)
            period = 'AM' if hour < 12 else 'PM'
            display_hour = hour if hour <= 12 else hour - 12
            display_hour = 12 if display_hour == 0 else display_hour
            session_time = re.sub(time_pattern, f'{display_hour}:{minute} {period}', session_time)

    return {
        'client_name': client.name,
        'trainer_name': trainer_name,
        'gym_name': gym_name,
        'pt_amount': f'₹{client.pt_tier}' if client.pt_tier else '₹5000',
        'session_time': session_time,
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
    """Send welcome email synchronously (Vercel-compatible)."""
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
