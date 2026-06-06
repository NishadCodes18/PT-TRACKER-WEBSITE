"""
Brevo (formerly Sendinblue) API email sending
Uses Brevo's transactional email API with proper error handling
"""
import os
import threading
from flask import current_app
from jinja2 import Environment, FileSystemLoader, select_autoescape

from .email_context import build_email_context

try:
    import sib_api_v3_sdk
    from sib_api_v3_sdk.rest import ApiException
    BREVO_AVAILABLE = True
except ImportError:
    BREVO_AVAILABLE = False


def validate_brevo_configured():
    """Check if Brevo API credentials are configured."""
    api_key = current_app.config.get('BREVO_API_KEY')
    sender_email = current_app.config.get('BREVO_SENDER_EMAIL')
    return bool(api_key and sender_email and BREVO_AVAILABLE)


def send_email_via_brevo_api(
    recipient,
    subject,
    template_name,
    trainer_id=None,
    email_type='renewal_reminder',
    client_id=None,
    recipient_name=None,
    **context,
):
    """Send an HTML email using Brevo API."""
    if not recipient:
        return False

    api_key = current_app.config.get('BREVO_API_KEY')
    sender_email = current_app.config.get('BREVO_SENDER_EMAIL')
    sender_name = current_app.config.get('BREVO_SENDER_NAME', 'PT Tracker')

    if not api_key or not sender_email:
        return False

    # Build email context and render template
    context = build_email_context(subject=subject, **context)
    template_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'templates')
    env = Environment(loader=FileSystemLoader(template_dir), autoescape=select_autoescape(['html', 'xml']))
    html_content = env.get_template(f'emails/{template_name}.html').render(**context)

    # Configure Brevo API
    configuration = sib_api_v3_sdk.Configuration()
    configuration.api_key['api-key'] = api_key
    api_instance = sib_api_v3_sdk.TransactionalEmailsApi(sib_api_v3_sdk.ApiClient(configuration))

    # Prepare email
    send_smtp_email = sib_api_v3_sdk.SendSmtpEmail(
        to=[{"email": recipient, "name": recipient_name or recipient}],
        sender={"email": sender_email, "name": sender_name},
        subject=subject,
        html_content=html_content
    )

    try:
        api_response = api_instance.send_transac_email(send_smtp_email)

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

    except ApiException as e:
        error_msg = f"Brevo API error: {e}"

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


def send_email_via_brevo_api_async(app, recipient, subject, template_name, **context):
    """Send email asynchronously using Brevo API."""

    def _send():
        try:
            with app.app_context():
                send_email_via_brevo_api(recipient, subject, template_name, **context)
        except:
            pass

    thread = threading.Thread(target=_send)
    thread.daemon = True
    thread.start()
