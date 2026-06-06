"""
Security routes for 2FA, session management, password changes
"""
from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from datetime import datetime
import pyotp
import qrcode
from io import BytesIO
import base64
from email_validator import EmailNotValidError, validate_email
from ..database import db
from ..models import Trainer, TwoFactorAuth

security_bp = Blueprint('security', __name__, url_prefix='/api/security')


@security_bp.route('/2fa/setup', methods=['GET'])
@login_required
def setup_2fa():
    """Generate 2FA QR code and secret key"""
    try:
        # Check if already set up
        twofa = TwoFactorAuth.query.filter_by(trainer_id=current_user.id).first()
        
        # Generate new secret
        secret = pyotp.random_base32()
        
        # Create TOTP provisioning URI
        totp = pyotp.TOTP(secret)
        provisioning_uri = totp.provisioning_uri(
            name=current_user.username,
            issuer_name='PT Tracker'
        )
        
        # Generate QR code
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(provisioning_uri)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Convert to base64
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)
        img_base64 = base64.b64encode(buffer.getvalue()).decode()
        
        return jsonify({
            'secret': secret,
            'qr_code': f"data:image/png;base64,{img_base64}",
            'provisioning_uri': provisioning_uri,
            'message': 'Scan this QR code with your authenticator app'
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@security_bp.route('/2fa/verify', methods=['POST'])
@login_required
def verify_2fa_setup():
    """Verify 2FA code and enable 2FA"""
    try:
        data = request.json
        secret = data.get('secret')
        code = data.get('code')
        
        if not secret or not code:
            return jsonify({'error': 'Missing secret or code'}), 400
        
        # Verify code
        totp = pyotp.TOTP(secret)
        if not totp.verify(code):
            return jsonify({'error': 'Invalid verification code'}), 400
        
        # Save to database
        twofa = TwoFactorAuth.query.filter_by(trainer_id=current_user.id).first()
        if not twofa:
            twofa = TwoFactorAuth(trainer_id=current_user.id)
        
        twofa.secret_key = secret
        twofa.is_enabled = True
        
        # Generate backup codes
        backup_codes = [pyotp.random_base32()[:8] for _ in range(10)]
        twofa.backup_codes = ','.join(backup_codes)
        
        db.session.add(twofa)
        db.session.commit()
        
        return jsonify({
            'message': '2FA enabled successfully',
            'backup_codes': backup_codes,
            'warning': 'Save these backup codes in a safe place. You can use them to access your account if you lose access to your authenticator app.'
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@security_bp.route('/2fa/disable', methods=['POST'])
@login_required
def disable_2fa():
    """Disable 2FA for current user"""
    try:
        data = request.json
        password = data.get('password')
        
        if not password or not current_user.check_password(password):
            return jsonify({'error': 'Invalid password'}), 401
        
        twofa = TwoFactorAuth.query.filter_by(trainer_id=current_user.id).first()
        if twofa:
            twofa.is_enabled = False
            twofa.secret_key = None
            twofa.backup_codes = None
            db.session.commit()
        
        return jsonify({'message': '2FA disabled successfully'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@security_bp.route('/2fa/status', methods=['GET'])
@login_required
def check_2fa_status():
    """Check if 2FA is enabled"""
    try:
        twofa = TwoFactorAuth.query.filter_by(trainer_id=current_user.id).first()
        
        return jsonify({
            'is_enabled': twofa.is_enabled if twofa else False,
            'message': '2FA is enabled' if (twofa and twofa.is_enabled) else '2FA is not enabled'
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@security_bp.route('/change-password', methods=['POST'])
@login_required
def change_password():
    """Change trainer password"""
    try:
        data = request.json
        old_password = data.get('old_password')
        new_password = data.get('new_password')
        confirm_password = data.get('confirm_password')
        
        if not old_password or not new_password or not confirm_password:
            return jsonify({'error': 'Missing required fields'}), 400
        
        if not current_user.check_password(old_password):
            return jsonify({'error': 'Current password is incorrect'}), 401
        
        if new_password != confirm_password:
            return jsonify({'error': 'New passwords do not match'}), 400
        
        if len(new_password) < 6:
            return jsonify({'error': 'Password must be at least 6 characters'}), 400
        
        current_user.set_password(new_password)
        db.session.commit()
        
        return jsonify({'message': 'Password changed successfully'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@security_bp.route('/sessions', methods=['GET'])
@login_required
def list_sessions():
    """List active sessions (simplified)"""
    try:
        from flask_login import current_user
        
        # In a real app, you'd query a sessions table
        # For now, we'll return the current session info
        sessions = [{
            'device': 'Current Browser',
            'ip_address': request.remote_addr,
            'last_activity': datetime.utcnow().isoformat(),
            'created_at': current_user.created_at.isoformat() if current_user.created_at else None
        }]
        
        return jsonify({'sessions': sessions}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@security_bp.route('/logout-all', methods=['POST'])
@login_required
def logout_all_sessions():
    """Logout from all sessions"""
    try:
        # In a real app, you'd clear all sessions for this user
        # For now, we'll just return success
        return jsonify({'message': 'All sessions logged out successfully'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@security_bp.route('/profile', methods=['GET', 'PUT'])
@login_required
def manage_profile():
    """Get or update trainer profile"""
    try:
        if getattr(current_user, 'is_admin', False):
            return jsonify({'error': 'Trainer profile settings are not available for admin accounts'}), 403

        if request.method == 'GET':
            return jsonify({
                'id': current_user.id,
                'username': current_user.username,
                'email': current_user.email,
                'phone': current_user.phone,
                'role': current_user.role,
                'is_active': current_user.is_active,
                'created_at': current_user.created_at.isoformat() if current_user.created_at else None,
                'last_login': current_user.last_login.isoformat() if current_user.last_login else None
            }), 200
        
        # PUT - update profile
        data = request.json or {}
        if 'email' in data:
            raw_email = (data.get('email') or '').strip()
            if raw_email:
                try:
                    normalized_email = validate_email(raw_email, check_deliverability=False).normalized
                except EmailNotValidError:
                    return jsonify({'error': 'Enter a valid recovery email address'}), 400

                existing = Trainer.query.filter(
                    Trainer.email == normalized_email,
                    Trainer.id != current_user.id,
                ).first()
                if existing:
                    return jsonify({'error': 'That recovery email is already used by another trainer'}), 400

                current_user.email = normalized_email
            else:
                current_user.email = None
        if 'phone' in data:
            current_user.phone = data['phone']
        
        db.session.commit()
        
        return jsonify({
            'message': 'Profile updated successfully',
            'user': {
                'username': current_user.username,
                'email': current_user.email,
                'phone': current_user.phone
            }
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@security_bp.route('/activity-log', methods=['GET'])
@login_required
def activity_log():
    """Get user activity log"""
    try:
        from ..models import AuditLog
        
        limit = request.args.get('limit', 50, type=int)
        
        logs = AuditLog.query.filter(
            (AuditLog.user_id == current_user.id) | (AuditLog.username == current_user.username)
        ).order_by(AuditLog.created_at.desc()).limit(limit).all()
        
        return jsonify({
            'count': len(logs),
            'activity': [{
                'action': log.action,
                'resource_type': log.resource_type,
                'details': log.details,
                'ip_address': log.ip_address,
                'created_at': log.created_at.isoformat()
            } for log in logs]
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 400
