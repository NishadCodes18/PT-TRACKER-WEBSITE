"""Scheduled tasks (Render cron / external scheduler)."""
from flask import Blueprint, current_app, request

from ..services.reminder_service import run_scheduled_renewal_reminders
from ..utils.api_responses import api_error, api_success
from ..utils.mail import validate_smtp_configured

cron_bp = Blueprint('cron', __name__, url_prefix='/api/cron')


def _authorize_cron():
    expected = current_app.config.get('CRON_SECRET')
    if not expected:
        return False
    auth = request.headers.get('Authorization', '')
    token = auth[7:] if auth.startswith('Bearer ') else request.headers.get('X-Cron-Secret', '')
    return token and token == expected


@cron_bp.route('/health', methods=['GET'])
def health():
    return api_success(data={'status': 'healthy'})


@cron_bp.route('/send-renewals', methods=['POST'])
def cron_send_renewals():
    if not _authorize_cron():
        return api_error('Unauthorized', code='unauthorized', status=401)

    if not validate_smtp_configured():
        return api_error('SMTP not configured', code='smtp_missing', status=503)

    sent_count = run_scheduled_renewal_reminders()
    return api_success(
        message=f'Automated renewal job finished. Dispatched {sent_count} reminder(s).',
        data={'sent_count': sent_count},
    )
