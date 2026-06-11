from datetime import datetime
from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
from sqlalchemy import func, or_
from ..database import db
from ..models import (
    Trainer,
    Payment,
    CommissionPolicy,
    Notification,
    ADMIN_DATA_OWNER_USERNAME,
)
admin_bp = Blueprint('admin', __name__, url_prefix='/api/admin')
def _admin_required():
    return getattr(current_user, 'is_admin', False)


def _is_hidden_trainer(trainer):
    return trainer.username == ADMIN_DATA_OWNER_USERNAME


def _serialize_trainer(trainer):
    locked_until = trainer.locked_until.isoformat() if trainer.locked_until else None
    is_locked = bool(trainer.locked_until and trainer.locked_until > datetime.utcnow())
    remaining_seconds = 0
    if is_locked:
        remaining_seconds = max(0, int((trainer.locked_until - datetime.utcnow()).total_seconds()))
    return {
        'id': trainer.id,
        'username': trainer.username,
        'role': trainer.role,
        'email': trainer.email,
        'is_active': trainer.is_active,
        'created_at': trainer.created_at.isoformat() if trainer.created_at else None,
        'client_count': len(trainer.clients),
        'commission_policy': _resolve_commission(trainer),
        'failed_login_attempts': trainer.failed_login_attempts or 0,
        'last_failed_login': trainer.last_failed_login.isoformat() if trainer.last_failed_login else None,
        'locked_until': locked_until,
        'is_locked': is_locked,
        'lockout_remaining_seconds': remaining_seconds,
        'lockout_remaining_minutes': max(1, (remaining_seconds + 59) // 60) if remaining_seconds else 0,
    }
def _month_start(date_obj):
    return date_obj.replace(day=1)
def _resolve_commission(trainer):
    policy = trainer.commission_policy
    if not policy:
        policy = CommissionPolicy(trainer_id=trainer.id)
        db.session.add(policy)
        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            raise
    return {
        'id': policy.id,
        'trainer_id': trainer.id,
        'monthly_target': float(policy.monthly_target),
        'above_target_percent': float(policy.above_target_percent),
        'below_target_percent': float(policy.below_target_percent),
        'override_percent': float(policy.override_percent) if policy.override_percent is not None else None,
    }
def _trainer_payout_summary(trainer):
    today = datetime.utcnow().date()
    month_start = _month_start(today)
    monthly_income_result = (
        db.session.query(func.sum(Payment.amount))
        .filter(Payment.trainer_id == trainer.id, Payment.payment_date >= month_start)
        .scalar()
    )
    monthly_income = float(monthly_income_result) if monthly_income_result else 0.0
    policy = trainer.commission_policy
    if not policy:
        policy = CommissionPolicy(trainer_id=trainer.id)
        db.session.add(policy)
        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            raise
    target = float(policy.monthly_target)
    if policy.override_percent is not None:
        payout_percent = float(policy.override_percent)
        payout_rule = 'manual_override'
    elif monthly_income >= target:
        payout_percent = float(policy.above_target_percent)
        payout_rule = 'target_achieved'
    else:
        payout_percent = float(policy.below_target_percent)
        payout_rule = 'below_target'
    payout_amount = round((monthly_income * payout_percent) / 100.0, 2)
    return {
        'trainer_id': trainer.id,
        'trainer_username': trainer.username,
        'monthly_income': monthly_income,
        'monthly_target': target,
        'payout_percent': payout_percent,
        'payout_amount': payout_amount,
        'payout_rule': payout_rule,
    }
@admin_bp.route('/panel-summary', methods=['GET'])
@login_required
def panel_summary():
    if not _admin_required():
        return jsonify({'error': 'Admin access required'}), 403
    trainers = (
        Trainer.query.filter(Trainer.username != ADMIN_DATA_OWNER_USERNAME)
        .order_by(Trainer.username)
        .all()
    )
    return jsonify({
        'trainer_count': len(trainers),
        'trainers': [_trainer_payout_summary(t) for t in trainers],
    })
@admin_bp.route('/trainers', methods=['GET'])
@login_required
def list_trainers():
    if not _admin_required():
        return jsonify({'error': 'Admin access required'}), 403
    trainers = (
        Trainer.query.filter(Trainer.username != ADMIN_DATA_OWNER_USERNAME)
        .order_by(Trainer.username)
        .all()
    )
    return jsonify([_serialize_trainer(trainer) for trainer in trainers])


@admin_bp.route('/trainers', methods=['POST'])
@login_required
def create_trainer():
    if not _admin_required():
        return jsonify({'error': 'Admin access required'}), 403
    data = request.get_json() or {}
    username = (data.get('username') or '').strip()
    password = data.get('password') or ''
    role = (data.get('role') or 'trainer').strip()
    if not username:
        return jsonify({'error': 'Username is required'}), 400
    if username == ADMIN_DATA_OWNER_USERNAME:
        return jsonify({'error': 'Reserved trainer username'}), 400
    if len(password) < 6:
        return jsonify({'error': 'Password must be at least 6 characters'}), 400
    if Trainer.query.filter_by(username=username).first():
        return jsonify({'error': 'Username already taken'}), 400
    trainer = Trainer(username=username, role=role)
    trainer.set_password(password)
    db.session.add(trainer)
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Failed to create trainer: {str(e)}'}), 500
    return jsonify(_serialize_trainer(trainer)), 201


@admin_bp.route('/trainers/<int:trainer_id>', methods=['PUT'])
@login_required
def update_trainer(trainer_id):
    if not _admin_required():
        return jsonify({'error': 'Admin access required'}), 403
    trainer = Trainer.query.get_or_404(trainer_id)
    if _is_hidden_trainer(trainer):
        return jsonify({'error': 'Cannot modify hidden system trainer'}), 400
    data = request.get_json() or {}
    if 'username' in data:
        username = (data.get('username') or '').strip()
        if not username:
            return jsonify({'error': 'Username is required'}), 400
        if username == ADMIN_DATA_OWNER_USERNAME:
            return jsonify({'error': 'Reserved trainer username'}), 400
        existing = Trainer.query.filter(Trainer.username == username, Trainer.id != trainer.id).first()
        if existing:
            return jsonify({'error': 'Username already taken'}), 400
        trainer.username = username
    if 'password' in data and (data.get('password') or '').strip():
        password = data.get('password') or ''
        if len(password) < 6:
            return jsonify({'error': 'Password must be at least 6 characters'}), 400
        trainer.set_password(password)
    if 'role' in data:
        trainer.role = (data.get('role') or 'trainer').strip()
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Failed to update trainer: {str(e)}'}), 500
    return jsonify(_serialize_trainer(trainer))


@admin_bp.route('/trainers/<int:trainer_id>', methods=['DELETE'])
@login_required
def delete_trainer(trainer_id):
    if not _admin_required():
        return jsonify({'error': 'Admin access required'}), 403
    trainer = Trainer.query.get_or_404(trainer_id)
    if _is_hidden_trainer(trainer):
        return jsonify({'error': 'Cannot delete hidden system trainer'}), 400

    try:
        # Import models needed for cleanup
        from ..models import (
            Client, Payment, Expense, CommissionPolicy,
            Notification, EmailLog, Attendance, Workout,
            ProgressMetric, GalleryImage, Nutrition, Goal,
            Badge, ClientReferral, AuditLog, TrainerRole,
            IntegrationToken, TwoFactorAuth, PasswordResetOTP
        )

        # Get all clients belonging to this trainer
        client_ids = [c.id for c in Client.query.filter_by(trainer_id=trainer_id).all()]

        # Delete client-related records first (in correct order to avoid FK constraints)
        for client_id in client_ids:
            # Delete referrals
            ClientReferral.query.filter_by(referrer_id=client_id).delete(synchronize_session=False)
            ClientReferral.query.filter_by(referred_client_id=client_id).update({'referred_client_id': None}, synchronize_session=False)

            # Delete gamification and tracking
            Badge.query.filter_by(client_id=client_id).delete(synchronize_session=False)
            Goal.query.filter_by(client_id=client_id).delete(synchronize_session=False)
            Nutrition.query.filter_by(client_id=client_id).delete(synchronize_session=False)
            GalleryImage.query.filter_by(client_id=client_id).delete(synchronize_session=False)
            ProgressMetric.query.filter_by(client_id=client_id).delete(synchronize_session=False)
            Workout.query.filter_by(client_id=client_id).delete(synchronize_session=False)
            Attendance.query.filter_by(client_id=client_id).delete(synchronize_session=False)

            # Delete payments and email logs
            Payment.query.filter_by(client_id=client_id).delete(synchronize_session=False)
            EmailLog.query.filter_by(client_id=client_id).delete(synchronize_session=False)

        # Delete clients
        Client.query.filter_by(trainer_id=trainer_id).delete(synchronize_session=False)

        # Delete trainer-specific records (order matters due to FK constraints)
        Payment.query.filter_by(trainer_id=trainer_id).delete(synchronize_session=False)
        Expense.query.filter_by(trainer_id=trainer_id).delete(synchronize_session=False)
        EmailLog.query.filter_by(trainer_id=trainer_id).delete(synchronize_session=False)
        Notification.query.filter_by(trainer_id=trainer_id).delete(synchronize_session=False)
        Attendance.query.filter_by(trainer_id=trainer_id).delete(synchronize_session=False)
        Workout.query.filter_by(trainer_id=trainer_id).delete(synchronize_session=False)
        ProgressMetric.query.filter_by(trainer_id=trainer_id).delete(synchronize_session=False)
        GalleryImage.query.filter_by(trainer_id=trainer_id).delete(synchronize_session=False)
        Nutrition.query.filter_by(trainer_id=trainer_id).delete(synchronize_session=False)
        Goal.query.filter_by(trainer_id=trainer_id).delete(synchronize_session=False)

        # Delete authentication and security records
        TwoFactorAuth.query.filter_by(trainer_id=trainer_id).delete(synchronize_session=False)
        PasswordResetOTP.query.filter_by(trainer_id=trainer_id).delete(synchronize_session=False)
        IntegrationToken.query.filter_by(trainer_id=trainer_id).delete(synchronize_session=False)
        TrainerRole.query.filter_by(trainer_id=trainer_id).delete(synchronize_session=False)

        # Delete commission policy and audit logs
        CommissionPolicy.query.filter_by(trainer_id=trainer_id).delete(synchronize_session=False)
        AuditLog.query.filter_by(user_id=trainer_id).delete(synchronize_session=False)

        # Finally delete the trainer
        db.session.delete(trainer)
        db.session.commit()

        return jsonify({'message': 'Trainer deleted successfully'})
    except Exception as e:
        db.session.rollback()
        import traceback
        error_details = traceback.format_exc()
        print(f"Error deleting trainer {trainer_id}: {error_details}")
        return jsonify({'error': f'Failed to delete trainer: {str(e)}'}), 500
@admin_bp.route('/trainers/<int:trainer_id>/commission-policy', methods=['PUT'])
@login_required
def update_commission_policy(trainer_id):
    if not _admin_required():
        return jsonify({'error': 'Admin access required'}), 403
    trainer = Trainer.query.get_or_404(trainer_id)
    if trainer.username == ADMIN_DATA_OWNER_USERNAME:
        return jsonify({'error': 'Cannot update hidden system trainer'}), 400
    data = request.get_json() or {}
    policy = trainer.commission_policy
    if not policy:
        policy = CommissionPolicy(trainer_id=trainer.id)
    monthly_target = data.get('monthly_target', policy.monthly_target or 8000)
    above_target_percent = data.get('above_target_percent', policy.above_target_percent or 50)
    below_target_percent = data.get('below_target_percent', policy.below_target_percent or 40)
    override_percent = data.get('override_percent', policy.override_percent)
    try:
        monthly_target = float(monthly_target)
        above_target_percent = float(above_target_percent)
        below_target_percent = float(below_target_percent)
        if override_percent in ('', None):
            override_percent = None
        else:
            override_percent = float(override_percent)
    except (TypeError, ValueError):
        return jsonify({'error': 'Invalid policy values'}), 400
    if monthly_target < 0:
        return jsonify({'error': 'Target must be non-negative'}), 400
    for pct in [above_target_percent, below_target_percent]:
        if pct < 0 or pct > 100:
            return jsonify({'error': 'Percentages must be between 0 and 100'}), 400
    if override_percent is not None and (override_percent < 0 or override_percent > 100):
        return jsonify({'error': 'Override percentage must be between 0 and 100'}), 400
    policy.monthly_target = monthly_target
    policy.above_target_percent = above_target_percent
    policy.below_target_percent = below_target_percent
    policy.override_percent = override_percent
    db.session.add(policy)
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Failed to update policy: {str(e)}'}), 500
    return jsonify({'message': 'Commission policy updated', 'commission_policy': _resolve_commission(trainer)})


@admin_bp.route('/trainers/<int:trainer_id>/unlock', methods=['POST'])
@login_required
def unlock_trainer_account(trainer_id):
    if not _admin_required():
        return jsonify({'error': 'Admin access required'}), 403

    trainer = Trainer.query.get_or_404(trainer_id)
    if trainer.username == ADMIN_DATA_OWNER_USERNAME:
        return jsonify({'error': 'Cannot modify hidden system trainer'}), 400

    trainer.reset_login_lockout()
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Failed to unlock trainer: {str(e)}'}), 500

    return jsonify({'message': 'Trainer account unlocked', 'trainer': _serialize_trainer(trainer)})
@admin_bp.route('/notifications', methods=['POST'])
@login_required
def create_notification():
    if not _admin_required():
        return jsonify({'error': 'Admin access required'}), 403
    data = request.get_json() or {}
    message = (data.get('message') or '').strip()
    trainer_id = data.get('trainer_id')
    if not message:
        return jsonify({'error': 'Message is required'}), 400
    notification = Notification(message=message, created_by=current_user.username)
    if trainer_id:
        trainer = Trainer.query.get(trainer_id)
        if not trainer or trainer.username == ADMIN_DATA_OWNER_USERNAME:
            return jsonify({'error': 'Invalid trainer'}), 400
        notification.trainer_id = trainer.id
    db.session.add(notification)
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Failed to create notification: {str(e)}'}), 500
    return jsonify({'message': 'Notification sent'}), 201
@admin_bp.route('/payouts', methods=['GET'])
@login_required
def trainer_payouts():
    if not _admin_required():
        return jsonify({'error': 'Admin access required'}), 403
    trainers = (
        Trainer.query.filter(Trainer.username != ADMIN_DATA_OWNER_USERNAME)
        .order_by(Trainer.username)
        .all()
    )
    return jsonify([_trainer_payout_summary(t) for t in trainers])
@admin_bp.route('/notifications', methods=['GET'])
@login_required
def get_admin_sent_notifications():
    if not _admin_required():
        return jsonify({'error': 'Admin access required'}), 403
    notifications = Notification.query.order_by(Notification.created_at.desc()).limit(50).all()
    return jsonify([
        {
            'id': n.id,
            'trainer_id': n.trainer_id,
            'trainer_username': n.trainer.username if n.trainer else 'All Trainers',
            'message': n.message,
            'is_read': n.is_read,
            'created_at': n.created_at.isoformat(),
        }
        for n in notifications
    ])
@admin_bp.route('/notifications/inbox', methods=['GET'])
@login_required
def get_inbox_notifications():
    notifications_query = Notification.query
    if not _admin_required():
        notifications_query = notifications_query.filter(
            or_(Notification.trainer_id == current_user.id, Notification.trainer_id.is_(None))
        )
    notifications = notifications_query.order_by(Notification.created_at.desc()).limit(50).all()
    return jsonify([
        {
            'id': n.id,
            'trainer_id': n.trainer_id,
            'trainer_username': n.trainer.username if n.trainer else 'Broadcast',
            'message': n.message,
            'is_read': n.is_read,
            'created_at': n.created_at.isoformat(),
        }
        for n in notifications
    ])
@admin_bp.route('/notifications/<int:notification_id>/read', methods=['POST'])
@login_required
def mark_notification_read(notification_id):
    notification = Notification.query.get_or_404(notification_id)
    if not _admin_required() and notification.trainer_id not in (None, current_user.id):
        return jsonify({'error': 'Unauthorized'}), 403
    notification.is_read = True
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Failed to mark as read: {str(e)}'}), 500
    return jsonify({'message': 'Notification marked as read'})