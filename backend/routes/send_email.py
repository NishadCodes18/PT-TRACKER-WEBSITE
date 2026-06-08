"""
API endpoint for sending emails to clients from the dashboard
"""
from datetime import datetime, timedelta
from flask import Blueprint, jsonify, request, current_app
from flask_login import login_required, current_user

from ..models import Client
from ..utils.client_emails import send_client_welcome_email, dispatch_client_welcome_email
from ..services.reminder_service import _send_for_client

send_email_bp = Blueprint('send_email', __name__, url_prefix='/api/send-email')


def _is_admin():
    return getattr(current_user, 'is_admin', False)


@send_email_bp.route('/<int:client_id>', methods=['POST'])
@login_required
def send_email_to_client(client_id):
    """Send an email to a specific client"""

    query = Client.query.filter_by(id=client_id)

    if not _is_admin():
        query = query.filter_by(trainer_id=current_user.id)

    client = query.first()

    if not client:
        return jsonify({"error": "Client not found"}), 404

    if not client.email:
        return jsonify({"error": "Client has no email address"}), 400

    data = request.get_json() or {}
    email_type = data.get('type', 'welcome')

    if email_type != 'welcome':
        return jsonify({"error": "Only 'welcome' email type is supported"}), 400

    dispatch_client_welcome_email(current_app._get_current_object(), client)

    return jsonify({
        "success": True,
        "message": f"Email is being sent to {client.email}"
    })


@send_email_bp.route('/due-members', methods=['POST'])
@login_required
def send_email_to_due_members():
    """Send reminder emails to all due/overdue members"""

    data = request.get_json() or {}
    days_threshold = data.get('days_threshold', 4)  # Default to 4 days before due
    include_overdue = data.get('include_overdue', True)

    try:
        days_threshold = int(days_threshold)
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid days_threshold"}), 400

    # Build query for due clients
    query = Client.query.filter(
        Client.status == 'ongoing',
        Client.email.isnot(None),
        Client.email != '',
        Client.renewal_date.isnot(None)
    )

    if not _is_admin():
        query = query.filter_by(trainer_id=current_user.id)

    today = datetime.utcnow().date()
    cutoff_date = today + timedelta(days=days_threshold)

    # Get clients whose renewal is within threshold or overdue
    all_clients = query.all()
    due_clients = []

    for client in all_clients:
        if client.renewal_date:
            if include_overdue and client.renewal_date < today:
                due_clients.append(client)
            elif client.renewal_date <= cutoff_date:
                due_clients.append(client)

    if not due_clients:
        return jsonify({
            "success": True,
            "message": "No due or overdue members found",
            "sent_count": 0
        })

    # Send emails
    sent_count = 0
    for client in due_clients:
        if _send_for_client(client, skip_recent_check=False):
            sent_count += 1

    return jsonify({
        "success": True,
        "message": f"Sent reminder emails to {sent_count} out of {len(due_clients)} due/overdue members",
        "sent_count": sent_count,
        "total_due": len(due_clients)
    })
