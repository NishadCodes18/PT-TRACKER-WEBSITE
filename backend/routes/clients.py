from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from datetime import datetime
from sqlalchemy.orm import joinedload
from ..models import Client, Trainer, get_or_create_default_admin_trainer, ADMIN_DATA_OWNER_USERNAME
from ..database import db
clients_bp = Blueprint('clients', __name__, url_prefix='/api/clients')


def _is_admin():
    return getattr(current_user, 'is_admin', False)


def _trainer_display_name(trainer):
    if not trainer:
        return None
    if trainer.username == ADMIN_DATA_OWNER_USERNAME:
        return 'Admin'
    return trainer.username


def _serialize_client(client):
    return {
        'id': client.id,
        'trainer_id': client.trainer_id,
        'trainer_username': _trainer_display_name(client.trainer),
        'name': client.name,
        'contact_number': client.contact_number or 'N/A',
        'status': client.status,
        'pt_tier': client.pt_tier,
        'time_slot': client.time_slot,
        'email': client.email,
        'send_email_reminders': client.send_email_reminders,
        'expected_amount': client.expected_amount,
        'renewal_date': client.renewal_date.isoformat() if client.renewal_date else None,
        'notes': client.notes,
        'is_overdue': bool(client.renewal_date and client.renewal_date < datetime.utcnow().date() and client.status == 'ongoing'),
    }


def _resolve_trainer(requested_trainer_id=None):
    if requested_trainer_id in (None, ''):
        trainer = Trainer.query.filter(Trainer.username != ADMIN_DATA_OWNER_USERNAME).order_by(Trainer.id).first()
        if trainer:
            return None
        trainer = get_or_create_default_admin_trainer()
        return trainer
    try:
        requested_trainer_id = int(requested_trainer_id)
    except (TypeError, ValueError):
        return None
    trainer = Trainer.query.get(requested_trainer_id)
    if not trainer or trainer.username == ADMIN_DATA_OWNER_USERNAME:
        return None
    return trainer


def _client_query():
    return Client.query.options(joinedload(Client.trainer))


@clients_bp.route('', methods=['GET'])
@login_required
def get_clients():
    """Get all clients for the current trainer or all clients for admins."""
    status_filter = request.args.get('status')
    is_admin = _is_admin()
    query = _client_query()
    if not is_admin:
        query = query.filter_by(trainer_id=current_user.id)
    if status_filter:
        query = query.filter_by(status=status_filter)
    clients = query.order_by(Client.name).all()
    return jsonify([_serialize_client(c) for c in clients])
@clients_bp.route('', methods=['POST'])
@login_required
def create_client():
    """Create a new client"""
    data = request.get_json() or {}
    is_admin = _is_admin()
    name = data.get('name', '').strip()
    contact_number = data.get('contact_number', '').strip()
    status = data.get('status', 'ongoing').strip().lower()
    pt_tier = data.get('pt_tier', 'Silver')
    time_slot = data.get('time_slot', '').strip()
    email = data.get('email', '').strip()
    send_email_reminders = bool(data.get('send_email_reminders', False))
    notes = data.get('notes', '').strip()
    if not name:
        return jsonify({'error': 'Name is required'}), 400
    if status not in ('ongoing', 'lost'):
        return jsonify({'error': 'Status must be ongoing or lost'}), 400
    trainer = None
    if is_admin:
        trainer = _resolve_trainer(data.get('trainer_id'))
        if trainer is None:
            return jsonify({'error': 'Invalid trainer_id'}), 400
    else:
        trainer = current_user
    client = Client(
        trainer=trainer,
        name=name,
        contact_number=contact_number,
        status=status,
        pt_tier=pt_tier,
        time_slot=time_slot,
        email=email,
        send_email_reminders=send_email_reminders,
        notes=notes
    )
    db.session.add(client)
    db.session.commit()
    return jsonify(_serialize_client(client)), 201
@clients_bp.route('/<int:client_id>', methods=['GET'])
@login_required
def get_client(client_id):
    """Get a specific client"""
    client_query = _client_query().filter_by(id=client_id)
    if not _is_admin():
        client_query = client_query.filter_by(trainer_id=current_user.id)
    client = client_query.first_or_404()
    return jsonify(_serialize_client(client))
@clients_bp.route('/<int:client_id>', methods=['PUT'])
@login_required
def update_client(client_id):
    """Update an existing client"""
    client_query = _client_query().filter_by(id=client_id)
    is_admin = _is_admin()
    if not is_admin:
        client_query = client_query.filter_by(trainer_id=current_user.id)
    client = client_query.first_or_404()
    data = request.get_json() or {}
    if 'name' in data:
        client.name = data['name'].strip()
    if 'contact_number' in data:
        client.contact_number = data['contact_number'].strip()
    if 'status' in data:
        status = str(data['status']).strip().lower()
        if status not in ('ongoing', 'lost'):
            return jsonify({'error': 'Status must be ongoing or lost'}), 400
        client.status = status
    if 'pt_tier' in data:
        client.pt_tier = data['pt_tier']
    if 'time_slot' in data:
        client.time_slot = data['time_slot'].strip()
    if 'email' in data:
        client.email = data['email'].strip()
    if 'send_email_reminders' in data:
        client.send_email_reminders = bool(data['send_email_reminders'])
    if 'renewal_date' in data:
        try:
            client.renewal_date = datetime.strptime(data['renewal_date'], '%Y-%m-%d').date()
        except ValueError:
            return jsonify({'error': 'Invalid date format'}), 400
    if 'notes' in data:
        client.notes = data['notes'].strip()
    if 'trainer_id' in data:
        if not is_admin:
            return jsonify({'error': 'Only admins can reassign clients'}), 403
        trainer = _resolve_trainer(data.get('trainer_id'))
        if trainer is None:
            return jsonify({'error': 'Invalid trainer_id'}), 400
        client.trainer = trainer
    db.session.commit()
    return jsonify(_serialize_client(client))
@clients_bp.route('/<int:client_id>', methods=['DELETE'])
@login_required
def delete_client(client_id):
    """Delete a client"""
    if not _is_admin():
        return jsonify({'error': 'Only admins can permanently delete clients'}), 403
    client = Client.query.filter_by(id=client_id).first_or_404()
    db.session.delete(client)
    db.session.commit()
    return '', 204