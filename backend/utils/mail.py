"""Email sending utilities with HTML templates."""
import os
import smtplib
import threading
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from flask import current_app
from jinja2 import Environment, FileSystemLoader, select_autoescape

from .email_context import build_email_context


def validate_smtp_configured():
    """Return True when SMTP credentials are present."""
    user = current_app.config.get('SMTP_USER')
    password = current_app.config.get('SMTP_PASSWORD')
    return bool(user and password)


def render_email_template(template_name, **context):
    """Render an email template from backend/templates/emails/"""
    template_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'templates')

    template_path = os.path.join(template_dir, 'emails', f'{template_name}.html')
    if not os.path.exists(template_path):
        raise FileNotFoundError(f"Email template not found: {template_path}")

    env = Environment(
        loader=FileSystemLoader(template_dir),
        autoescape=select_autoescape(['html', 'xml']),
    )
    template = env.get_template(f'emails/{template_name}.html')
    return template.render(**context)


def create_html_email(recipient, subject, template_name, **context):
    """Create a MIME email with HTML content."""
    context = build_email_context(subject=subject, **context)
    html_content = render_email_template(template_name, **context)

    msg = MIMEMultipart('alternative')
    msg['Subject'] = subject
    msg['From'] = current_app.config.get('SMTP_USER')
    msg['To'] = recipient

    plain_bits = [subject]
    if context.get('trainer_name'):
        plain_bits.append(f"Trainer: {context['trainer_name']}")
    if context.get('gym_name'):
        plain_bits.append(f"Gym: {context['gym_name']}")
    plain_text = '\n\n'.join(plain_bits) + '\n\nPlease view this email in HTML format.'
    msg.attach(MIMEText(plain_text, 'plain'))
    msg.attach(MIMEText(html_content, 'html'))
    return msg


def send_html_email(
    recipient,
    subject,
    template_name,
    trainer_id=None,
    email_type='renewal_reminder',
    client_id=None,
    recipient_name=None,
    **context,
):
    """Send an HTML email using a template."""
    if not recipient:
        return False

    try:
        msg = create_html_email(recipient, subject, template_name, **context)

        host = current_app.config.get('SMTP_SERVER', 'smtp.gmail.com')
        port = current_app.config.get('SMTP_PORT', 587)
        user = current_app.config.get('SMTP_USER')
        password = current_app.config.get('SMTP_PASSWORD')

        if not user or not password:
            current_app.logger.warning('SMTP credentials not configured')
            return False

        with smtplib.SMTP(host, port, timeout=20) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(user, password)
            server.send_message(msg)

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
                client_id=client_id,
            )
            db.session.add(log_entry)
            db.session.commit()

        return True
    except Exception as e:
        current_app.logger.warning('Failed to send email to %s: %s', recipient, e)

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
                    error_message=str(e),
                    client_id=client_id,
                )
                db.session.add(log_entry)
                db.session.commit()
            except Exception:
                db.session.rollback()

        return False


def send_html_email_async(app, recipient, subject, template_name, **context):
    """Send HTML email asynchronously in a thread."""

    def _send():
        with app.app_context():
            send_html_email(recipient, subject, template_name, **context)

    thread = threading.Thread(target=_send)
    thread.daemon = True
    thread.start()
