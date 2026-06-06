"""SMTP Testing and Diagnostics for Render Platform"""
import os
from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
from ..utils.mail import send_html_email, validate_smtp_configured

smtp_test_bp = Blueprint('smtp_test', __name__, url_prefix='/api/smtp-test')


def _is_admin():
    return getattr(current_user, 'is_admin', False)


@smtp_test_bp.route('/config', methods=['GET'])
@login_required
def get_smtp_config():
    """Get current SMTP configuration (admin only)"""
    if not _is_admin():
        return jsonify({"error": "Admin access required"}), 403

    from flask import current_app

    config = {
        "smtp_server": current_app.config.get('SMTP_SERVER'),
        "smtp_port": current_app.config.get('SMTP_PORT'),
        "smtp_use_tls": current_app.config.get('SMTP_USE_TLS'),
        "smtp_use_ssl": current_app.config.get('SMTP_USE_SSL'),
        "smtp_user": current_app.config.get('SMTP_USER'),
        "smtp_password_set": bool(current_app.config.get('SMTP_PASSWORD')),
        "is_configured": validate_smtp_configured(),
        "environment": {
            "RENDER": os.environ.get('RENDER'),
            "PORT": os.environ.get('PORT'),
        }
    }

    return jsonify(config)


@smtp_test_bp.route('/send-test', methods=['POST'])
@login_required
def send_test_email():
    """Send a test email (admin only)"""
    if not _is_admin():
        return jsonify({"error": "Admin access required"}), 403

    data = request.get_json() or {}
    test_email = data.get('email', '').strip()

    if not test_email:
        return jsonify({"error": "Email address required"}), 400

    if not validate_smtp_configured():
        return jsonify({
            "error": "SMTP not configured. Check environment variables on Render.",
            "success": False
        }), 400

    try:
        # Send test email
        success = send_html_email(
            recipient=test_email,
            subject="Test Email from PT Tracker",
            template_name="welcome",
            trainer_id=current_user.id if not _is_admin() else None,
            email_type="test",
            client_name="Test Client",
            gym_name="Test Gym",
            trainer_name="Test Trainer",
        )

        if success:
            return jsonify({
                "success": True,
                "message": f"Test email sent successfully to {test_email}. Check your inbox."
            })
        else:
            return jsonify({
                "success": False,
                "error": "Failed to send test email. Check server logs for details."
            }), 500

    except Exception as e:
        return jsonify({
            "success": False,
            "error": f"Exception while sending test email: {str(e)}"
        }), 500
