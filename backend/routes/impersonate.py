from flask import Blueprint, jsonify, session, redirect, url_for
from flask_login import login_required, current_user, login_user
from ..models import Trainer

impersonate_bp = Blueprint('impersonate', __name__, url_prefix='/api/impersonate')

def _admin_required():
    return getattr(current_user, 'is_admin', False)

@impersonate_bp.route('/switch/<int:trainer_id>', methods=['POST'])
@login_required
def switch_user(trainer_id):
    """Allow admin to impersonate a trainer"""
    if not _admin_required():
        return jsonify({'error': 'Admin access required'}), 403

    trainer = Trainer.query.get_or_404(trainer_id)

    # Store the original admin status in session
    if 'original_user' not in session:
        session['original_user'] = 'admin'
        session['is_impersonating'] = True

    # Log in as the trainer
    login_user(trainer)

    return jsonify({
        'message': f'Switched to {trainer.username}',
        'username': trainer.username
    })

@impersonate_bp.route('/stop', methods=['POST'])
@login_required
def stop_impersonating():
    """Return to admin account"""
    if 'original_user' not in session:
        return jsonify({'error': 'Not impersonating'}), 400

    from ..models import AdminUser
    # Clear impersonation
    session.pop('original_user', None)
    session.pop('is_impersonating', None)

    # Log back in as admin
    login_user(AdminUser())

    return jsonify({'message': 'Returned to admin account'})

@impersonate_bp.route('/status', methods=['GET'])
@login_required
def impersonation_status():
    """Check if currently impersonating"""
    return jsonify({
        'is_impersonating': session.get('is_impersonating', False),
        'current_user': current_user.username,
        'original_user': session.get('original_user')
    })
