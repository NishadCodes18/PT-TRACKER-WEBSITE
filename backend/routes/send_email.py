"""
API endpoint for sending emails to clients from the dashboard
"""
from flask import Blueprint, jsonify, request, current_app
from flask_login import login_required, current_user

from ..models import Client
from ..utils.client_emails import send_client_welcome_email, dispatch_client_welcome_email

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
