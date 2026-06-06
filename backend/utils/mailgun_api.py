"""
Mailgun HTTP API email sending (works on Render free tier)
This bypasses SMTP port blocks by using Mailgun's REST API
"""
import os
import threading
import requests
from flask import current_app
from jinja2 import Environment, FileSystemLoader, select_autoescape

from .email_context import build_email_context


def validate_mailgun_configured():
    """Check if Mailgun API credentials are configured."""
    api_key = current_app.config.get('MAILGUN_API_KEY')
    domain = current_app.config.get('MAILGUN_DOMAIN')
    return bool(api_key and domain)


def send_email_via_mailgun_api(
    recipient,
    subject,
    template_name,
    trainer_id=None,
    email_type='renewal_reminder',
    client_id=None,
    recipient_name=None,
    **context,
):
    """Send an HTML email using Mailgun HTTP API."""
    if not recipient:
        return False

    api_key = current_app.config.get('MAILGUN_API_KEY')
    domain = current_app.config.get('MAILGUN_DOMAIN')
    from_email = current_app.config.get('MAILGUN_FROM_EMAIL')

    if not api_key or not domain:
        return False

    # Default from email if not configured
    if not from_email:
        from_email = f"PT Tracker <noreply@{domain}>"

    # Build email context and render template
    context = build_email_context(subject=subject, **context)
    template_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'templates')
    env = Environment(loader=FileSystemLoader(template_dir), autoescape=select_autoescape(['html', 'xml']))
    html_content = env.get_template(f'emails/{template_name}.html').render(**context)

    # Mailgun API endpoint
    url = f"https://api.mailgun.net/v3/{domain}/messages"

    # Prepare the request
    auth = ("api", api_key)
    data = {
        "from": from_email,
        "to": recipient,
        "subject": subject,
        "html": html_content,
    }

    try:
        response = requests.post(url, auth=auth, data=data, timeout=30)
        response.raise_for_status()

        # Log success
        if trainer_id:
            from ..database import db
            from ..models import EmailLog
            log_entry = EmailLog(
                trainer_id=trainer_id,
                recipient_email=recipient,
                recipient_name=recipient_name,
                subject=subject,
                email_type=email_type,
                status='sent',
                client_id=client_id
            )
            db.session.add(log_entry)
            db.session.commit()

        return True

    except Exception as e:
        # Log failure
        if trainer_id:
            try:
                from ..database import db
                from ..models import EmailLog
                log_entry = EmailLog(
                    trainer_id=trainer_id,
                    recipient_email=recipient,
                    recipient_name=recipient_name,
                    subject=subject,
                    email_type=email_type,
                    status='failed',
                    error_message=str(e)[:500],
                    client_id=client_id,
                )
                db.session.add(log_entry)
                db.session.commit()
            except:
                db.session.rollback()

        return False


def send_email_via_mailgun_api_async(app, recipient, subject, template_name, **context):
    """Send email asynchronously using Mailgun API."""

    def _send():
        try:
            with app.app_context():
                send_email_via_mailgun_api(recipient, subject, template_name, **context)
        except:
            pass

    thread = threading.Thread(target=_send)
    thread.daemon = True
    thread.start()
