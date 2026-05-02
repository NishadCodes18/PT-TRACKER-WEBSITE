from flask import Blueprint, request, jsonify, current_app
from flask_login import login_required, current_user
from datetime import datetime, timedelta
import smtplib
from email.message import EmailMessage
from smtplib import SMTPAuthenticationError, SMTPException
from ..models import Client
from ..database import db
import threading

reminders_bp = Blueprint('reminders', __name__, url_prefix='/api/reminders')


def _normalize_smtp_value(value, *, remove_spaces=False):
    if value is None:
        return None
    value = str(value).strip()
    if remove_spaces:
        value = value.replace(' ', '')
    return value


def _get_smtp_settings():
    import os
    host = _normalize_smtp_value(current_app.config.get('SMTP_SERVER') or os.environ.get('SMTP_SERVER'))
    port = current_app.config.get('SMTP_PORT') or os.environ.get('SMTP_PORT', 587)
    user = _normalize_smtp_value(current_app.config.get('SMTP_USER') or os.environ.get('SMTP_USER'))
    password = _normalize_smtp_value(current_app.config.get('SMTP_PASSWORD') or os.environ.get('SMTP_PASSWORD'), remove_spaces=True)

    try:
        port = int(port)
    except (TypeError, ValueError):
        port = 587

    return host, port, user, password

def send_email_async(app, msg, server_info):
    with app.app_context():
        try:
            with smtplib.SMTP(server_info['host'], server_info['port'], timeout=20) as server:
                server.ehlo()
                server.starttls()
                server.ehlo()
                server.login(server_info['user'], server_info['password'])
                server.send_message(msg)
        except SMTPAuthenticationError as e:
            print(
                "Failed to send email: Gmail rejected the SMTP login. "
                "Use a Google App Password for SMTP_USER instead of your normal Gmail password. "
                f"Details: {e}"
            )
        except SMTPException as e:
            print(f"Failed to send email: SMTP error: {e}")
        except Exception as e:
            print(f"Failed to send email: {e}")

def dispatch_email(recipient, subject, body):
    if not recipient:
        return

    host, port, user, password = _get_smtp_settings()
    
    if not host or not user or not password:
        print(f"SMTP config missing. Host: {bool(host)}, User: {bool(user)}, Pass: {bool(password)}. Check .env")
        return
        
    msg = EmailMessage()
    msg['Subject'] = subject
    msg['From'] = user
    msg['To'] = recipient
    msg.set_content(body)
    
    server_info = {'host': host, 'port': port, 'user': user, 'password': password}
    
    thread = threading.Thread(target=send_email_async, args=(current_app._get_current_object(), msg, server_info))
    thread.start()


def validate_smtp_credentials():
    host, port, user, password = _get_smtp_settings()

    if not host or not user or not password:
        return 'SMTP config missing. Check SMTP_SERVER, SMTP_USER, and SMTP_PASSWORD in .env.'

    try:
        with smtplib.SMTP(host, port, timeout=20) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(user, password)
        return None
    except SMTPAuthenticationError:
        return 'Gmail rejected the login. Use a Google App Password for SMTP_PASSWORD, not your normal Gmail password.'
    except SMTPException as e:
        return f'SMTP error while validating Gmail credentials: {e}'
    except Exception as e:
        return f'Unable to reach the SMTP server: {e}'

@reminders_bp.route('/send', methods=['POST'])
@login_required
def send_reminders():
    data = request.get_json() or {}
    send_type = data.get('type', 'due_closest')
    client_id = data.get('client_id')
    
    query = Client.query.filter_by(status='ongoing')
    if not getattr(current_user, 'is_admin', False):
        query = query.filter_by(trainer_id=current_user.id)
        
    clients_to_email = []
    
    if send_type == 'specific':
        if not client_id:
            return jsonify({'error': 'client_id required for specific type'}), 400
        client = query.filter_by(id=client_id).first_or_404()
        clients_to_email.append(client)
    else:
        # Only clients with emails and auto-reminders enabled
        query = query.filter(Client.email.isnot(None), Client.email != '')
        query = query.filter_by(send_email_reminders=True)
        
        if send_type == 'due_closest':
            cutoff = datetime.utcnow().date() + timedelta(days=3)
            # Find clients whose renewal date is <= 3 days away (or overdue)
            clients_to_email = [c for c in query.all() if c.renewal_date and c.renewal_date <= cutoff]
        elif send_type == 'all':
            clients_to_email = query.all()
        else:
            return jsonify({'error': 'Invalid send type'}), 400

    if not clients_to_email:
        return jsonify({'message': 'No eligible clients found to send reminders.'}), 200

    smtp_error = validate_smtp_credentials()
    if smtp_error:
        return jsonify({'error': smtp_error}), 500

    sent_count = 0
    gym_name = current_app.config.get('GYM_NAME', 'NITRRO ZONE 360')
    
    for client in clients_to_email:
        if not client.email:
            continue
            
        subject = f"Your Membership Renewal at {gym_name}"
        date_str = client.renewal_date.strftime('%d %b %Y') if client.renewal_date else 'soon'
        
        body = f"Hello {client.name},\n\n"
        body += f"This is a friendly reminder from {gym_name} that your current plan is set to expire on {date_str}.\n"
        body += "Please renew your membership to continue your fitness journey without interruption.\n\n"
        body += "If you have already renewed, please ignore this email.\n\n"
        body += f"Best regards,\n{gym_name} Team"
        
        dispatch_email(client.email, subject, body)
        sent_count += 1
        
    return jsonify({'message': f'Dispatched {sent_count} email reminder(s).'}), 200
