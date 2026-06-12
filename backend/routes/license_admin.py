"""Admin routes for license key management."""
from flask import Blueprint, jsonify, request, Response
from flask_login import login_required, current_user
from datetime import datetime
import secrets
import string

from ..database import db
from ..models_license import LicenseKey
from ..models import Trainer

license_admin_bp = Blueprint('license_admin', __name__, url_prefix='/api/admin/licenses')


def _is_admin():
    """Check if current user is admin."""
    return getattr(current_user, 'is_admin', False)


def _generate_license_key():
    """Generate a random license key in format: XXXX-XXXX-XXXX-XXXX"""
    chars = string.ascii_uppercase + string.digits
    parts = []
    for _ in range(4):
        part = ''.join(secrets.choice(chars) for _ in range(4))
        parts.append(part)
    return '-'.join(parts)


@license_admin_bp.route('', methods=['GET'])
@login_required
def get_licenses():
    """Get all license keys with pagination and filters."""
    if not _is_admin():
        return jsonify({'error': 'Unauthorized'}), 403

    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    status_filter = request.args.get('status', 'all')  # all, used, unused

    query = LicenseKey.query

    # Apply filters
    if status_filter == 'used':
        query = query.filter_by(is_used=True)
    elif status_filter == 'unused':
        query = query.filter_by(is_used=False)

    # Order by created date (newest first)
    query = query.order_by(LicenseKey.created_at.desc())

    # Paginate
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    # Serialize results
    licenses = []
    for lic in pagination.items:
        trainer_username = None
        if lic.used_by_trainer_id:
            trainer = Trainer.query.get(lic.used_by_trainer_id)
            if trainer:
                trainer_username = trainer.username

        licenses.append({
            'id': lic.id,
            'license_key': lic.license_key,
            'is_used': lic.is_used,
            'used_by_trainer_id': lic.used_by_trainer_id,
            'used_by_username': trainer_username,
            'used_at': lic.used_at.isoformat() if lic.used_at else None,
            'created_at': lic.created_at.isoformat(),
            'notes': lic.notes
        })

    # Get statistics
    total_count = LicenseKey.query.count()
    used_count = LicenseKey.query.filter_by(is_used=True).count()
    unused_count = LicenseKey.query.filter_by(is_used=False).count()

    return jsonify({
        'licenses': licenses,
        'pagination': {
            'page': pagination.page,
            'per_page': pagination.per_page,
            'total': pagination.total,
            'pages': pagination.pages,
            'has_prev': pagination.has_prev,
            'has_next': pagination.has_next
        },
        'statistics': {
            'total': total_count,
            'used': used_count,
            'unused': unused_count
        }
    })


@license_admin_bp.route('/generate', methods=['POST'])
@login_required
def generate_licenses():
    """Generate new license keys."""
    if not _is_admin():
        return jsonify({'error': 'Unauthorized'}), 403

    data = request.get_json() or {}
    count = data.get('count', 1)
    notes = data.get('notes', '')

    # Validate count
    if not isinstance(count, int) or count < 1 or count > 100:
        return jsonify({'error': 'Count must be between 1 and 100'}), 400

    generated = []
    for i in range(count):
        # Generate unique key
        while True:
            key = _generate_license_key()
            existing = LicenseKey.query.filter_by(license_key=key).first()
            if not existing:
                break

        # Create license record
        license_record = LicenseKey(
            license_key=key,
            notes=notes or f'Generated on {datetime.utcnow().strftime("%Y-%m-%d")}'
        )
        db.session.add(license_record)
        generated.append(key)

    db.session.commit()

    return jsonify({
        'message': f'Generated {count} license key(s)',
        'keys': generated,
        'count': len(generated)
    })


@license_admin_bp.route('/download', methods=['GET'])
@login_required
def download_licenses():
    """Download all unused license keys as a text file."""
    if not _is_admin():
        return jsonify({'error': 'Unauthorized'}), 403

    status_filter = request.args.get('status', 'unused')  # unused, all, used

    query = LicenseKey.query

    if status_filter == 'unused':
        query = query.filter_by(is_used=False)
    elif status_filter == 'used':
        query = query.filter_by(is_used=True)

    licenses = query.order_by(LicenseKey.created_at.desc()).all()

    # Generate text file content
    lines = []
    lines.append("=" * 70)
    lines.append("PT TRACKER - LICENSE KEYS")
    lines.append("=" * 70)
    lines.append(f"Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC")
    lines.append(f"Total Keys: {len(licenses)}")
    lines.append(f"Status Filter: {status_filter.upper()}")
    lines.append("=" * 70)
    lines.append("")

    if not licenses:
        lines.append("No license keys found.")
    else:
        for idx, lic in enumerate(licenses, 1):
            lines.append(f"{idx}. {lic.license_key}")
            if status_filter == 'all' or status_filter == 'used':
                status = "USED" if lic.is_used else "AVAILABLE"
                lines.append(f"   Status: {status}")
                if lic.is_used and lic.used_by_trainer_id:
                    trainer = Trainer.query.get(lic.used_by_trainer_id)
                    if trainer:
                        lines.append(f"   Used by: {trainer.username}")
                    lines.append(f"   Used at: {lic.used_at.strftime('%Y-%m-%d %H:%M')}")
            if lic.notes:
                lines.append(f"   Notes: {lic.notes}")
            lines.append("")

    lines.append("=" * 70)
    lines.append("Contact: nishadpatil2008@gmail.com")
    lines.append("PT Tracker - Made with 💪 by Nishad Patil")
    lines.append("=" * 70)

    content = '\n'.join(lines)

    # Create response with text file
    filename = f"pt-tracker-licenses-{status_filter}-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}.txt"

    return Response(
        content,
        mimetype='text/plain',
        headers={
            'Content-Disposition': f'attachment; filename={filename}'
        }
    )


@license_admin_bp.route('/statistics', methods=['GET'])
@login_required
def get_statistics():
    """Get detailed license key statistics."""
    if not _is_admin():
        return jsonify({'error': 'Unauthorized'}), 403

    total = LicenseKey.query.count()
    used = LicenseKey.query.filter_by(is_used=True).count()
    unused = LicenseKey.query.filter_by(is_used=False).count()

    # Recently used keys (last 10)
    recent_used = LicenseKey.query.filter_by(is_used=True).order_by(
        LicenseKey.used_at.desc()
    ).limit(10).all()

    recent_list = []
    for lic in recent_used:
        trainer = Trainer.query.get(lic.used_by_trainer_id) if lic.used_by_trainer_id else None
        recent_list.append({
            'license_key': lic.license_key,
            'used_by': trainer.username if trainer else 'Unknown',
            'used_at': lic.used_at.isoformat() if lic.used_at else None
        })

    return jsonify({
        'total': total,
        'used': used,
        'unused': unused,
        'usage_percentage': round((used / total * 100) if total > 0 else 0, 2),
        'recently_used': recent_list
    })


@license_admin_bp.route('/<int:license_id>', methods=['DELETE'])
@login_required
def delete_license(license_id):
    """Delete an unused license key."""
    if not _is_admin():
        return jsonify({'error': 'Unauthorized'}), 403

    license_key = LicenseKey.query.get(license_id)
    if not license_key:
        return jsonify({'error': 'License key not found'}), 404

    if license_key.is_used:
        return jsonify({'error': 'Cannot delete used license key'}), 400

    db.session.delete(license_key)
    db.session.commit()

    return jsonify({'message': 'License key deleted successfully'})
