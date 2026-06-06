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
    """Check if SMTP credentials are configured."""
    from flask import current_app
    user = current_app.config.get('SMTP_USER')
    password = current_app.config.get('SMTP_PASSWORD')
    return bool(user and password)

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
    """Send an HTML email using a template with DEBUG logging."""
    if not recipient:
        return False

    try:
        # 1. Prepare Message
        context = build_email_context(subject=subject, **context)
        template_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'templates')
        env = Environment(loader=FileSystemLoader(template_dir), autoescape=select_autoescape(['html', 'xml']))
        html_content = env.get_template(f'emails/{template_name}.html').render(**context)

        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = current_app.config.get('SMTP_USER')
        msg['To'] = recipient
        msg.attach(MIMEText(html_content, 'html'))

        # 2. Get Config
        host = current_app.config.get('SMTP_SERVER', 'smtp.gmail.com')
        port = int(current_app.config.get('SMTP_PORT', 587))
        user = current_app.config.get('SMTP_USER')
        password = current_app.config.get('SMTP_PASSWORD')

        if not user or not password:
            print("DEBUG: SMTP credentials missing in config")
            return False

        # 3. Secure Connection & Send
        with smtplib.SMTP(host, port, timeout=30) as server:
            server.set_debuglevel(0)
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(user, password)
            server.send_message(msg)

        # 4. Log Success
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
        print(f"DEBUG: SMTP Error details: {str(e)}")
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
