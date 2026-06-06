"""Email sending utilities with HTML templates."""
import os
import smtplib
import socket
import ssl
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
    server = current_app.config.get('SMTP_SERVER')
    port = current_app.config.get('SMTP_PORT')

    print(f"DEBUG SMTP Config Check:")
    print(f"  SMTP_SERVER: {server}")
    print(f"  SMTP_PORT: {port}")
    print(f"  SMTP_USER: {user}")
    print(f"  SMTP_PASSWORD: {'***' if password else 'NOT SET'}")

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
    """Send an HTML email using a template with enhanced Render platform support."""
    if not recipient:
        print("DEBUG: No recipient provided")
        return False

    try:
        # 1. Get Config First
        host = current_app.config.get('SMTP_SERVER', 'smtp.gmail.com')
        port = int(current_app.config.get('SMTP_PORT', 587))
        use_ssl = current_app.config.get('SMTP_USE_SSL', False)
        use_tls = current_app.config.get('SMTP_USE_TLS', True)
        user = current_app.config.get('SMTP_USER')
        password = current_app.config.get('SMTP_PASSWORD')

        print(f"DEBUG: Attempting to send email to {recipient}")
        print(f"DEBUG: SMTP Config - Host: {host}, Port: {port}, SSL: {use_ssl}, TLS: {use_tls}")
        print(f"DEBUG: SMTP User: {user}, Password: {'***' if password else 'NOT SET'}")

        if not user or not password:
            print("ERROR: SMTP credentials missing in config")
            return False

        # 2. Prepare Message
        context = build_email_context(subject=subject, **context)
        template_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'templates')
        env = Environment(loader=FileSystemLoader(template_dir), autoescape=select_autoescape(['html', 'xml']))
        html_content = env.get_template(f'emails/{template_name}.html').render(**context)

        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = user
        msg['To'] = recipient
        msg.attach(MIMEText(html_content, 'html'))

        # 3. Enhanced Connection & Send with Render-specific fixes
        try:
            print(f"DEBUG: Connecting to {host}:{port}...")

            if use_ssl and port == 465:
                # SSL connection for port 465
                print("DEBUG: Using SMTP_SSL (port 465)")
                context = ssl.create_default_context()
                with smtplib.SMTP_SSL(host, port, timeout=30, context=context) as server:
                    server.set_debuglevel(1)  # Enable debug output
                    print("DEBUG: Logging in...")
                    server.login(user, password)
                    print("DEBUG: Sending message...")
                    server.send_message(msg)
                    print("DEBUG: Email sent successfully via SSL")
            else:
                # STARTTLS connection for port 587
                print("DEBUG: Using SMTP with STARTTLS (port 587)")
                with smtplib.SMTP(host, port, timeout=30) as server:
                    server.set_debuglevel(1)  # Enable debug output
                    print("DEBUG: EHLO...")
                    server.ehlo()

                    if use_tls:
                        print("DEBUG: Starting TLS...")
                        context = ssl.create_default_context()
                        server.starttls(context=context)
                        server.ehlo()
                        print("DEBUG: TLS established")

                    print("DEBUG: Logging in...")
                    server.login(user, password)
                    print("DEBUG: Sending message...")
                    server.send_message(msg)
                    print("DEBUG: Email sent successfully via STARTTLS")

        except socket.gaierror as e:
            print(f"ERROR: DNS/Network error - Cannot resolve {host}: {str(e)}")
            raise Exception(f"Cannot connect to SMTP server {host}. Check network or DNS on Render.")
        except socket.timeout as e:
            print(f"ERROR: Connection timeout to {host}:{port}: {str(e)}")
            raise Exception(f"Connection timeout to SMTP server. Check firewall or network on Render.")
        except smtplib.SMTPServerDisconnected as e:
            print(f"ERROR: SMTP server disconnected: {str(e)}")
            raise Exception(f"SMTP server disconnected. This may be a network issue on Render: {str(e)}")
        except smtplib.SMTPAuthenticationError as e:
            print(f"ERROR: SMTP authentication failed: {str(e)}")
            raise Exception(f"SMTP authentication failed. Check SMTP_USER and SMTP_PASSWORD in Render environment variables: {str(e)}")
        except smtplib.SMTPException as e:
            print(f"ERROR: SMTP error: {str(e)}")
            raise Exception(f"SMTP error: {str(e)}")
        except Exception as e:
            print(f"ERROR: Unexpected error during SMTP connection: {str(e)}")
            raise

        # 4. Log Success
        if trainer_id:
            from ..database import db
            from ..models import EmailLog
            log_entry = EmailLog(trainer_id=trainer_id, recipient_email=recipient,
                                 recipient_name=recipient_name, subject=subject,
                                 email_type=email_type, status='sent', client_id=client_id)
            db.session.add(log_entry)
            db.session.commit()

        print(f"SUCCESS: Email sent to {recipient}")
        return True

    except Exception as e:
        error_msg = str(e)
        print(f"FATAL ERROR: Failed to send email - {error_msg}")
        current_app.logger.error(f'Failed to send email to {recipient}: {error_msg}')

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
                    error_message=error_msg[:500],  # Truncate long errors
                    client_id=client_id,
                )
                db.session.add(log_entry)
                db.session.commit()
            except Exception as log_error:
                print(f"ERROR: Could not log email failure: {str(log_error)}")
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
