"""
Email logs API routes for viewing email sending history and audit trails
"""
from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from datetime import datetime, timedelta
from ..models import EmailLog
from ..database import db

email_logs_bp = Blueprint('email_logs', __name__, url_prefix='/api/email-logs')


@email_logs_bp.route('', methods=['GET'])
@login_required
def get_email_logs():
    """Get email sending logs with filtering and pagination"""
    is_admin = getattr(current_user, 'is_admin', False)

    query = EmailLog.query
    if not is_admin:
        query = query.filter_by(trainer_id=current_user.id)

    # Filtering
    email_type = request.args.get('email_type', '').strip()
    status = request.args.get('status', '').strip()
    days = request.args.get('days', 30, type=int)

    if email_type:
        query = query.filter_by(email_type=email_type)

    if status:
        query = query.filter_by(status=status)

    start_date = datetime.utcnow().date() - timedelta(days=days)
    query = query.filter(EmailLog.sent_at >= start_date)

    query = query.order_by(EmailLog.sent_at.desc())

    # Pagination
    page = max(request.args.get('page', 1, type=int), 1)
    per_page = min(max(request.args.get('per_page', 20, type=int), 5), 100)
    total = query.count()
    items = query.offset((page - 1) * per_page).limit(per_page).all()

    return jsonify({
        'items': [
            {
                'id': log.id,
                'recipient_email': log.recipient_email,
                'recipient_name': log.recipient_name,
                'subject': log.subject,
                'email_type': log.email_type,
                'status': log.status,
                'error_message': log.error_message,
                'sent_at': log.sent_at.isoformat(),
                'client_id': log.client_id
            }
            for log in items
        ],
        'pagination': {
            'page': page,
            'per_page': per_page,
            'total': total,
            'pages': max((total + per_page - 1) // per_page, 1),
            'has_next': (page * per_page) < total,
            'has_prev': page > 1,
        }
    })


@email_logs_bp.route('/stats', methods=['GET'])
@login_required
def email_logs_stats():
    """Get email sending statistics"""
    is_admin = getattr(current_user, 'is_admin', False)

    query = EmailLog.query
    if not is_admin:
        query = query.filter_by(trainer_id=current_user.id)

    days = request.args.get('days', 30, type=int)
    start_date = datetime.utcnow().date() - timedelta(days=days)
    query = query.filter(EmailLog.sent_at >= start_date)

    total_sent = query.filter_by(status='sent').count()
    total_failed = query.filter_by(status='failed').count()

    return jsonify({
        'total_sent': total_sent,
        'total_failed': total_failed,
        'period_days': days,
        'success_rate': round((total_sent / (total_sent + total_failed) * 100), 2) if (total_sent + total_failed) > 0 else 0
    })
