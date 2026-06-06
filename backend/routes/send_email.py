"""
API endpoint for sending emails to clients from the dashboard
"""
from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user

from ..models import Client
from ..utils.client_emails import send_client_welcome_email

send_email_bp = Blueprint('send_email', __name__, url_prefix='/api/send-email')


def _is_admin():
    return getattr(current_user, 'is_admin', False)


@send_email_bp.route('/<int:client_id>', methods=['POST'])
@login_required
def send_email_to_client(client_id):
    """Send an email to a specific client"""

    # Get the client
    query = Client.query.filter_by(id=client_id)

    # Non-admins can only send to their own clients
    if not _is_admin():
        query = query.filter_by(trainer_id=current_user.id)

    client = query.first()

    if not client:
        return jsonify({"error": "Client not found"}), 404

    if not client.email:
        return jsonify({"error": "Client has no email address"}), 400

    # Get email type from request
    data = request.get_json() or {}
    email_type = data.get('type', 'welcome')

    # Currently only support welcome email type
    if email_type != 'welcome':
        return jsonify({"error": "Only 'welcome' email type is supported"}), 400

    # Send the email
    try:
        success = send_client_welcome_email(client)

        if success:
            return jsonify({
                "success": True,
                "message": f"Email sent successfully to {client.email}"
            })
        else:
            return jsonify({
                "success": False,
                "error": "Failed to send email. Check SMTP configuration in Render environment variables."
            }), 500

    except Exception as e:
        return jsonify({
            "success": False,
            "error": f"Error sending email: {str(e)}"
        }), 500
