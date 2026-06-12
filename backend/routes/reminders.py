import smtplib

from flask import Blueprint, request
from flask_login import current_user, login_required
from smtplib import SMTPAuthenticationError, SMTPException

from ..extensions import limiter
from ..services.reminder_service import dispatch_renewal_reminders
from ..utils.api_responses import api_error, api_success

reminders_bp = Blueprint('reminders', __name__, url_prefix='/api/reminders')


def _smtp_validation_error():
    import os
    from flask import current_app

    host = current_app.config.get('SMTP_SERVER') or os.environ.get('SMTP_SERVER')
    port = current_app.config.get('SMTP_PORT') or 587
    use_ssl = current_app.config.get('SMTP_USE_SSL', False)
    use_tls = current_app.config.get('SMTP_USE_TLS', True)
    user = current_app.config.get('SMTP_USER') or os.environ.get('SMTP_USER')
    password = current_app.config.get('SMTP_PASSWORD') or os.environ.get('SMTP_PASSWORD')

    if not host or not user or not password:
        return 'SMTP config missing. Check SMTP_SERVER, SMTP_USER, and SMTP_PASSWORD in .env.'

    try:
        if use_ssl:
            # Use SMTP_SSL for port 465
            with smtplib.SMTP_SSL(host, int(port), timeout=10) as server:
                server.login(user, password)
        else:
            # Use SMTP with STARTTLS for port 587
            with smtplib.SMTP(host, int(port), timeout=10) as server:
                server.ehlo()
                if use_tls:
                    server.starttls()
                    server.ehlo()
                server.login(user, password)
        return None
    except SMTPAuthenticationError:
        return 'Gmail rejected the login. Use a Google App Password for SMTP_PASSWORD.'
    except smtplib.SMTPServerDisconnected:
        return 'SMTP server disconnected. Check firewall/network settings on Render.'
    except SMTPException as e:
        return f'SMTP error: {e}'
    except Exception as e:
        return f'Unable to reach SMTP server: {e}'


@reminders_bp.route('/test-smtp', methods=['GET'])
@login_required
def test_smtp():
    """Test SMTP connectivity (for debugging on Render)."""
    import socket
    from flask import current_app

    try:
        host = current_app.config.get('SMTP_SERVER', 'smtp.gmail.com')
        port = int(current_app.config.get('SMTP_PORT', 587))

        # Test DNS resolution
        ip = socket.gethostbyname(host)

        # Test connection
        with smtplib.SMTP(host, port, timeout=10) as server:
            server.ehlo()
            response = server.ehlo()[0]

        return api_success(
            message='SMTP server is reachable',
            data={'host': host, 'port': port, 'ip': ip, 'ehlo_code': response}
        )
    except socket.gaierror as e:
        return api_error(f'DNS resolution failed for {host}: {e}', code='dns_error', status=500)
    except smtplib.SMTPException as e:
        return api_error(f'SMTP error: {e}', code='smtp_error', status=500)
    except Exception as e:
        return api_error(f'Connection failed: {e}', code='connection_error', status=500)


@reminders_bp.route('/send', methods=['POST'])
@login_required
@limiter.limit('15 per hour')
def send_reminders():
    from flask import current_app
    data = request.get_json() or {}
    send_type = data.get('type', 'due_closest')
    client_id = data.get('client_id')
    is_admin = getattr(current_user, 'is_admin', False)
    trainer_id = None if is_admin else current_user.id

    if send_type == 'specific' and not client_id:
        return api_error('client_id required for specific type', code='validation_error', status=400)

    # Only validate SMTP if using SMTP provider
    email_provider = current_app.config.get('EMAIL_PROVIDER', 'smtp')
    if email_provider == 'smtp':
        smtp_error = _smtp_validation_error()
        if smtp_error:
            return api_error(smtp_error, code='smtp_error', status=500)

    try:
        sent_count, err = dispatch_renewal_reminders(
            send_type,
            trainer_id=trainer_id,
            admin=is_admin,
            client_id=client_id,
            respect_opt_in=(send_type != 'specific'),
        )
    except ValueError as e:
        return api_error(str(e), code='validation_error', status=400)

    if err == 'not_found':
        return api_error('Client not found or no access', code='not_found', status=404)

    if sent_count == 0:
        return api_success(
            message='No eligible clients found (check renewal dates, email opt-in, and recent sends).',
            data={'sent_count': 0},
        )

    return api_success(
        message=f'Dispatched {sent_count} email reminder(s).',
        data={'sent_count': sent_count},
    )
