"""Email sending utilities with HTML templates."""
import os
import smtplib
import ssl
import threading
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from flask import current_app
from jinja2 import Environment, FileSystemLoader, select_autoescape

from .email_context import build_email_context

try:
    from .mailgun_api import send_email_via_mailgun_api, validate_mailgun_configured
    MAILGUN_AVAILABLE = True
except ImportError:
    MAILGUN_AVAILABLE = False

try:
    from .brevo_api import send_email_via_brevo_api, validate_brevo_configured
    BREVO_AVAILABLE = True
except ImportError:
    BREVO_AVAILABLE = False

def validate_smtp_configured():
    """Check if SMTP credentials are configured."""
    from flask import current_app
    user = current_app.config.get('SMTP_USER')
    password = current_app.config.get('SMTP_PASSWORD')
    server = current_app.config.get('SMTP_SERVER')
    return bool(user and password and server)

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
    """Send an HTML email using configured provider (Brevo API, Mailgun API or SMTP)."""
    if not recipient:
        return False

    # Check which email provider is configured
    email_provider = current_app.config.get('EMAIL_PROVIDER', 'smtp')

    # Try Brevo API first if configured
    if email_provider == 'brevo_api' and BREVO_AVAILABLE:
        if validate_brevo_configured():
            return send_email_via_brevo_api(
                recipient, subject, template_name,
                trainer_id=trainer_id,
                email_type=email_type,
                client_id=client_id,
                recipient_name=recipient_name,
                **context
            )

    # Try Mailgun API if configured
    if email_provider == 'mailgun_api' and MAILGUN_AVAILABLE:
        if validate_mailgun_configured():
            return send_email_via_mailgun_api(
                recipient, subject, template_name,
                trainer_id=trainer_id,
                email_type=email_type,
                client_id=client_id,
                recipient_name=recipient_name,
                **context
            )

    # Fall back to SMTP
    return _send_html_email_smtp(
        recipient, subject, template_name,
        trainer_id=trainer_id,
        email_type=email_type,
        client_id=client_id,
        recipient_name=recipient_name,
        **context
    )


def _send_html_email_smtp(
    recipient,
    subject,
    template_name,
    trainer_id=None,
    email_type='renewal_reminder',
    client_id=None,
    recipient_name=None,
    **context,
):
    """Send an HTML email using SMTP (legacy method)."""
    if not recipient:
        return False

    host = current_app.config.get('SMTP_SERVER', 'smtp.gmail.com')
    port = int(current_app.config.get('SMTP_PORT', 587))
    use_ssl = current_app.config.get('SMTP_USE_SSL', False)
    use_tls = current_app.config.get('SMTP_USE_TLS', True)
    user = current_app.config.get('SMTP_USER')
    password = current_app.config.get('SMTP_PASSWORD')

    if not user or not password:
        return False

    context = build_email_context(subject=subject, **context)
    template_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'templates')
    env = Environment(loader=FileSystemLoader(template_dir), autoescape=select_autoescape(['html', 'xml']))
    html_content = env.get_template(f'emails/{template_name}.html').render(**context)

    msg = MIMEMultipart('alternative')
    msg['Subject'] = subject
    msg['From'] = user
    msg['To'] = recipient
    msg.attach(MIMEText(html_content, 'html'))

    try:
        if use_ssl and port == 465:
            context = ssl.create_default_context()
            with smtplib.SMTP_SSL(host, port, timeout=60, context=context) as server:
                server.login(user, password)
                server.send_message(msg)
        else:
            with smtplib.SMTP(host, port, timeout=60) as server:
                server.ehlo()
                if use_tls:
                    context = ssl.create_default_context()
                    server.starttls(context=context)
                    server.ehlo()
                server.login(user, password)
                server.send_message(msg)

        if trainer_id:
            from ..database import db
            from ..models import EmailLog
            log_entry = EmailLog(trainer_id=trainer_id, recipient_email=recipient,
                                 recipient_name=recipient_name, subject=subject,
                                 email_type=email_type, status='sent', client_id=client_id)
            db.session.add(log_entry)
            db.session.commit()

        return True

    except Exception as e:
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


def send_html_email_async(app, recipient, subject, template_name, **context):
    """
    DEPRECATED: Do not use on Vercel - threads are killed immediately.

    This function uses threading which is incompatible with Vercel's serverless
    architecture. Vercel terminates the process immediately after the response
    is sent, killing any background threads before emails can be delivered.

    Use send_html_email() instead for synchronous email sending.

    This function is kept for backward compatibility with non-Vercel deployments only.
    """

    def _send():
        try:
            with app.app_context():
                send_html_email(recipient, subject, template_name, **context)
        except:
            pass

    thread = threading.Thread(target=_send)
    thread.daemon = True
    thread.start()
