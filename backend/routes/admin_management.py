"""
Admin management routes for trainer management, RBAC, audit logs, system settings
"""
from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from datetime import datetime
from ..models import (
    Trainer, TrainerRole, AuditLog, SystemSettings, db
)

admin_bp = Blueprint('admin_management', __name__, url_prefix='/api/admin_management')


def _require_admin():
    """Decorator to require admin role"""
    if not getattr(current_user, 'is_admin', False):
        return False
    return True


@admin_bp.route('/trainers', methods=['GET'])
@login_required
def list_trainers():
    """Get all trainers (admin only)"""
    try:
        if not _require_admin():
            return jsonify({'error': 'Admin access required'}), 403
        
        trainers = Trainer.query.all()
        
        trainer_list = []
        for trainer in trainers:
            role = TrainerRole.query.filter_by(trainer_id=trainer.id).first()
            trainer_list.append({
                'id': trainer.id,
                'username': trainer.username,
                'email': trainer.email,
                'role': role.role if role else trainer.role,
                'is_active': trainer.is_active,
                'created_at': trainer.created_at.isoformat() if trainer.created_at else None,
                'last_login': trainer.last_login.isoformat() if trainer.last_login else None
            })
        
        return jsonify({'trainers': trainer_list}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@admin_bp.route('/trainers/<int:trainer_id>/role', methods=['GET', 'PUT'])
@login_required
def manage_trainer_role(trainer_id):
    """Get or update trainer role and permissions"""
    try:
        if not _require_admin():
            return jsonify({'error': 'Admin access required'}), 403
        
        trainer = Trainer.query.get(trainer_id)
        if not trainer:
            return jsonify({'error': 'Trainer not found'}), 404
        
        if request.method == 'GET':
            role = TrainerRole.query.filter_by(trainer_id=trainer_id).first()
            if not role:
                # Create default role
                role = TrainerRole(trainer_id=trainer_id, role='trainer')
                db.session.add(role)
                db.session.commit()
            
            return jsonify({
                'trainer_id': trainer_id,
                'role': role.role,
                'permissions': {
                    'can_manage_trainers': role.can_manage_trainers,
                    'can_manage_payments': role.can_manage_payments,
                    'can_view_reports': role.can_view_reports,
                    'can_manage_all_clients': role.can_manage_all_clients
                }
            }), 200
        
        # PUT - update role
        data = request.json
        role = TrainerRole.query.filter_by(trainer_id=trainer_id).first()
        if not role:
            role = TrainerRole(trainer_id=trainer_id)
        
        role.role = data.get('role', role.role)
        role.can_manage_trainers = data.get('can_manage_trainers', False)
        role.can_manage_payments = data.get('can_manage_payments', False)
        role.can_view_reports = data.get('can_view_reports', True)
        role.can_manage_all_clients = data.get('can_manage_all_clients', False)
        
        db.session.add(role)
        trainer.role = role.role
        db.session.commit()
        
        # Log action
        _log_audit('role_updated', f'Updated role for trainer {trainer.username}', trainer_id)
        
        return jsonify({'message': 'Role updated successfully', 'role': role.role}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@admin_bp.route('/trainers/<int:trainer_id>/status', methods=['PUT'])
@login_required
def toggle_trainer_status(trainer_id):
    """Activate or deactivate a trainer"""
    try:
        if not _require_admin():
            return jsonify({'error': 'Admin access required'}), 403
        
        trainer = Trainer.query.get(trainer_id)
        if not trainer:
            return jsonify({'error': 'Trainer not found'}), 404
        
        data = request.json
        trainer.is_active = data.get('is_active', True)
        db.session.commit()
        
        _log_audit('status_changed', f"Trainer {'activated' if trainer.is_active else 'deactivated'}", trainer_id)
        
        return jsonify({'message': 'Trainer status updated', 'is_active': trainer.is_active}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@admin_bp.route('/audit-logs', methods=['GET'])
@login_required
def get_audit_logs():
    """Get audit logs (admin only)"""
    try:
        if not _require_admin():
            return jsonify({'error': 'Admin access required'}), 403
        
        limit = request.args.get('limit', 100, type=int)
        action_filter = request.args.get('action')
        
        query = AuditLog.query.order_by(AuditLog.created_at.desc())
        
        if action_filter:
            query = query.filter_by(action=action_filter)
        
        logs = query.limit(limit).all()
        
        return jsonify({
            'count': len(logs),
            'logs': [{
                'id': log.id,
                'user': log.username,
                'action': log.action,
                'resource_type': log.resource_type,
                'resource_id': log.resource_id,
                'details': log.details,
                'ip_address': log.ip_address,
                'created_at': log.created_at.isoformat()
            } for log in logs]
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@admin_bp.route('/settings', methods=['GET', 'PUT'])
@login_required
def manage_system_settings():
    """Get or update system settings (admin only)"""
    try:
        if not _require_admin():
            return jsonify({'error': 'Admin access required'}), 403
        
        if request.method == 'GET':
            settings = SystemSettings.query.all()
            
            return jsonify({
                'settings': {s.setting_key: s.setting_value for s in settings}
            }), 200
        
        # PUT - update settings
        data = request.json
        for key, value in data.items():
            setting = SystemSettings.query.filter_by(setting_key=key).first()
            if setting:
                setting.setting_value = str(value)
            else:
                setting = SystemSettings(setting_key=key, setting_value=str(value))
                db.session.add(setting)
        
        db.session.commit()
        
        _log_audit('settings_updated', 'System settings updated', None)
        
        return jsonify({'message': 'Settings updated successfully'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@admin_bp.route('/trainer-performance', methods=['GET'])
@login_required
def trainer_performance():
    """Get performance metrics for all trainers"""
    try:
        if not _require_admin():
            return jsonify({'error': 'Admin access required'}), 403
        
        from sqlalchemy import func
        from ..models import Client, Payment
        
        trainers = Trainer.query.all()
        performance_data = []
        
        for trainer in trainers:
            # Client count
            client_count = Client.query.filter_by(trainer_id=trainer.id).count()
            active_clients = Client.query.filter_by(trainer_id=trainer.id, status='ongoing').count()
            
            # Revenue
            total_revenue = db.session.query(func.sum(Payment.amount)).filter_by(
                trainer_id=trainer.id
            ).scalar() or 0
            
            # Last login
            last_login = trainer.last_login.isoformat() if trainer.last_login else 'Never'
            
            performance_data.append({
                'trainer_id': trainer.id,
                'username': trainer.username,
                'total_clients': client_count,
                'active_clients': active_clients,
                'total_revenue': float(total_revenue),
                'last_login': last_login,
                'is_active': trainer.is_active
            })
        
        # Sort by revenue
        performance_data.sort(key=lambda x: x['total_revenue'], reverse=True)
        
        return jsonify({'trainers': performance_data}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 400


def _log_audit(action, details=None, resource_id=None, resource_type='trainer'):
    """Log an audit event"""
    try:
        from flask import request as flask_request
        
        log = AuditLog(
            user_id=current_user.id if hasattr(current_user, 'id') else None,
            username=current_user.username if hasattr(current_user, 'username') else 'admin',
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details,
            ip_address=flask_request.remote_addr if flask_request else None
        )
        db.session.add(log)
        db.session.commit()
    except Exception as e:
        print(f"Error logging audit: {e}")


@admin_bp.route('/trainer-delete/<int:trainer_id>', methods=['DELETE'])
@login_required
def delete_trainer(trainer_id):
    """Delete a trainer (admin only)"""
    try:
        if not _require_admin():
            return jsonify({'error': 'Admin access required'}), 403

        trainer = Trainer.query.get(trainer_id)
        if not trainer:
            return jsonify({'error': 'Trainer not found'}), 404

        # Prevent deleting admin owner account
        from ..models import ADMIN_DATA_OWNER_USERNAME
        if trainer.username == ADMIN_DATA_OWNER_USERNAME:
            return jsonify({'error': 'Cannot delete admin owner account'}), 400

        username = trainer.username

        # Manually delete all related records to avoid foreign key constraint issues
        from ..models import (
            TrainerRole, IntegrationToken, TwoFactorAuth,
            EmailLog, AuditLog, CommissionPolicy
        )

        # Delete trainer role
        TrainerRole.query.filter_by(trainer_id=trainer_id).delete()

        # Delete integration tokens
        IntegrationToken.query.filter_by(trainer_id=trainer_id).delete()

        # Delete 2FA settings
        TwoFactorAuth.query.filter_by(trainer_id=trainer_id).delete()

        # Delete commission policy
        CommissionPolicy.query.filter_by(trainer_id=trainer_id).delete()

        # Delete email logs
        EmailLog.query.filter_by(trainer_id=trainer_id).delete()

        # Set audit logs user_id to NULL instead of deleting
        AuditLog.query.filter_by(user_id=trainer_id).update({'user_id': None})

        # The cascade='all, delete-orphan' in models will handle:
        # - clients, payments, expenses, notifications

        # Now delete the trainer
        db.session.delete(trainer)
        db.session.commit()

        _log_audit('trainer_deleted', f'Deleted trainer {username}', trainer_id)

        return jsonify({'message': 'Trainer deleted successfully'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Failed to delete trainer: {str(e)}'}), 400
