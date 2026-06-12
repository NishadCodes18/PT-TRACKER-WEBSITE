"""Renewal reminder email dispatch."""
from datetime import datetime, timedelta

from flask import current_app

from ..models import Client, EmailLog, get_or_create_default_admin_trainer
from ..utils.email_context import resolve_gym_name
from ..utils.mail import send_html_email


def _eligible_clients_query(*, trainer_id=None, admin=False):
    query = Client.query.filter(
        Client.status == 'ongoing',
        Client.email.isnot(None),
        Client.email != '',
    )
    if not admin and trainer_id is not None:
        query = query.filter_by(trainer_id=trainer_id)
    return query


def _filter_by_send_preference(clients, *, respect_opt_in, allow_specific=False, client_id=None):
    if allow_specific and client_id:
        return [c for c in clients if c.id == client_id]
    if not respect_opt_in:
        return clients
    return [c for c in clients if c.send_email_reminders]


def _recent_reminder_sent(client_email, within_days=5):
    recent_log = EmailLog.query.filter(
        EmailLog.recipient_email == client_email,
        EmailLog.email_type == 'renewal_reminder',
        EmailLog.sent_at >= datetime.utcnow() - timedelta(days=within_days),
    ).first()
    return recent_log is not None


def _send_for_client(client, *, skip_recent_check=False):
    if not client.email:
        return False

    if not skip_recent_check and _recent_reminder_sent(client.email):
        return False

    gym_name = resolve_gym_name(client=client)
    trainer_name = client.trainer.username if client.trainer else gym_name
    sender_trainer_id = client.trainer.id if client.trainer else get_or_create_default_admin_trainer().id
    date_str = client.renewal_date.strftime('%d %b %Y') if client.renewal_date else 'soon'
    subject = f"Action Required: Your Personal Training Renewal at {gym_name}"

    send_html_email(
        client.email,
        subject,
        'member_renewal_reminder',
        trainer_id=sender_trainer_id,
        email_type='renewal_reminder',
        client_id=client.id,
        recipient_name=client.name,
        client_name=client.name,
        renewal_date=date_str,
        trainer_name=trainer_name,
        gym_name=gym_name,
    )

    if client.trainer and client.trainer.email:
        send_html_email(
            client.trainer.email,
            f"Automated Alert: Client Renewal Due - {client.name}",
            'trainer_renewal_notification',
            trainer_id=sender_trainer_id,
            email_type='renewal_reminder',
            client_id=client.id,
            recipient_name=client.trainer.username,
            trainer_name=client.trainer.username,
            client_name=client.name,
            renewal_date=date_str,
            contact_number=client.contact_number or 'N/A',
            client_email=client.email,
            gym_name=gym_name,
        )
    return True


def dispatch_renewal_reminders(
    send_type='due_closest',
    *,
    trainer_id=None,
    admin=False,
    client_id=None,
    respect_opt_in=True,
    skip_recent_check=False,
):
    """
    send_type: due_closest | all | specific
    respect_opt_in: when True, only clients with send_email_reminders enabled (except specific).
    """
    query = _eligible_clients_query(trainer_id=trainer_id, admin=admin)
    clients_to_email = []

    if send_type == 'specific':
        if not client_id:
            raise ValueError('client_id required for specific type')
        client = query.filter_by(id=client_id).first()
        if not client:
            return 0, 'not_found'
        clients_to_email = [client]
        respect_opt_in = False
    elif send_type == 'due_closest':
        cutoff = datetime.utcnow().date() + timedelta(days=5)
        clients_to_email = [c for c in query.all() if c.renewal_date and c.renewal_date <= cutoff]
    elif send_type == 'all':
        clients_to_email = query.all()
    else:
        raise ValueError('Invalid send type')

    clients_to_email = _filter_by_send_preference(
        clients_to_email,
        respect_opt_in=respect_opt_in,
        allow_specific=(send_type == 'specific'),
        client_id=client_id,
    )

    sent_count = 0
    for client in clients_to_email:
        if _send_for_client(client, skip_recent_check=skip_recent_check or send_type == 'specific'):
            sent_count += 1

    return sent_count, None


def run_scheduled_renewal_reminders():
    """Cron job: all trainers, due within 5 days, opt-in only."""
    return dispatch_renewal_reminders(
        'due_closest',
        admin=True,
        respect_opt_in=True,
        skip_recent_check=False,
    )[0]
