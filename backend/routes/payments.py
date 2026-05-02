from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from datetime import datetime
import calendar
from ..models import Payment, Expense, Trainer
from ..database import db
def add_months(sourcedate, months):
    from datetime import timedelta
    return sourcedate + timedelta(days=months * 30)
def add_sessions(start_date, sessions, session_days):
    from datetime import timedelta
    valid_days = [0, 2, 4] if session_days == 'MWF' else [1, 3, 5]
    current_date = start_date
    sessions_remaining = sessions
    while sessions_remaining > 0:
        if current_date.weekday() in valid_days:
            sessions_remaining -= 1
            if sessions_remaining == 0:
                break
        current_date += timedelta(days=1)
    return current_date
payments_bp = Blueprint('payments', __name__, url_prefix='/api')
@payments_bp.route('/payments', methods=['GET'])
@login_required
def get_payments():
    """Get all payments for current trainer"""
    payments_query = Payment.query
    if not getattr(current_user, 'is_admin', False):
        payments_query = payments_query.filter_by(trainer_id=current_user.id)
    payments = payments_query.order_by(Payment.payment_date.desc()).all()
    return jsonify([
        {
            'id': p.id,
            'client_id': p.client_id,
            'client_name': p.client.name if p.client else 'Unknown',
            'amount': float(p.amount),
            'payment_date': p.payment_date.isoformat(),
            'description': p.description
        }
        for p in payments
    ])
@payments_bp.route('/payments', methods=['POST'])
@login_required
def create_payment():
    """Create a new payment"""
    data = request.get_json() or {}
    is_admin = getattr(current_user, 'is_admin', False)
    client_id = data.get('client_id')
    amount = data.get('amount')
    payment_date_str = data.get('payment_date')
    description = data.get('description', '').strip()
    duration_months = int(data.get('duration_months', 1))
    plan_type = data.get('plan_type', 'monthly')
    session_days = data.get('session_days', 'MWF')
    start_date_str = data.get('start_date') or payment_date_str
    if not client_id or not amount or not payment_date_str:
        return jsonify({'error': 'Client, amount, and date are required'}), 400
    from ..models import Client
    client_query = Client.query.filter_by(id=client_id)
    if not is_admin:
        client_query = client_query.filter_by(trainer_id=current_user.id)
    client = client_query.first_or_404()
    try:
        amount = float(amount)
        payment_date = datetime.strptime(payment_date_str, '%Y-%m-%d').date()
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
    except (ValueError, TypeError):
        return jsonify({'error': 'Invalid date or amount format'}), 400
    total_amount = amount * duration_months
    trainer_id = current_user.id if not is_admin else client.trainer_id
    payment = Payment(
        client_id=client_id,
        trainer_id=trainer_id,
        amount=total_amount,
        payment_date=payment_date,
        start_date=start_date,
        plan_type=plan_type,
        description=description
    )
    if plan_type == 'session':
        client.renewal_date = add_sessions(start_date, duration_months, session_days)
    else:
        client.renewal_date = add_months(start_date, duration_months)
    db.session.add(payment)
    db.session.commit()
    return jsonify({
        'id': payment.id,
        'client_id': payment.client_id,
        'client_name': payment.client.name,
        'amount': float(payment.amount),
        'payment_date': payment.payment_date.isoformat(),
        'description': payment.description
    }), 201
@payments_bp.route('/payments/<int:payment_id>', methods=['DELETE'])
@login_required
def delete_payment(payment_id):
    """Delete a payment"""
    payment_query = Payment.query.filter_by(id=payment_id)
    if not getattr(current_user, 'is_admin', False):
        payment_query = payment_query.filter_by(trainer_id=current_user.id)
    payment = payment_query.first_or_404()
    db.session.delete(payment)
    db.session.commit()
    return '', 204
@payments_bp.route('/expenses', methods=['GET'])
@login_required
def get_expenses():
    """Get all expenses for current trainer"""
    expenses_query = Expense.query
    if not getattr(current_user, 'is_admin', False):
        expenses_query = expenses_query.filter_by(trainer_id=current_user.id)
    expenses = expenses_query.order_by(Expense.expense_date.desc()).all()
    return jsonify([
        {
            'id': e.id,
            'expense_name': e.expense_name,
            'category': e.category,
            'amount': float(e.amount),
            'expense_date': e.expense_date.isoformat()
        }
        for e in expenses
    ])
@payments_bp.route('/expenses', methods=['POST'])
@login_required
def create_expense():
    """Create a new expense"""
    data = request.get_json() or {}
    is_admin = getattr(current_user, 'is_admin', False)
    expense_name = data.get('expense_name', '').strip()  
    category = data.get('category', 'other').strip()
    amount = data.get('amount')
    expense_date_str = data.get('expense_date')
    if not expense_name or not amount or not expense_date_str:
        return jsonify({'error': 'Expense name, amount, and date are required'}), 400
    try:
        amount = float(amount)
        expense_date = datetime.strptime(expense_date_str, '%Y-%m-%d').date()
    except (ValueError, TypeError):
        return jsonify({'error': 'Invalid amount or date format'}), 400
    trainer_id = current_user.id
    if is_admin:
        requested_trainer_id = data.get('trainer_id')
        if requested_trainer_id:
            trainer = Trainer.query.get(requested_trainer_id)
            if not trainer:
                return jsonify({'error': 'Invalid trainer_id'}), 400
            trainer_id = trainer.id
        else:
            trainer = Trainer.query.order_by(Trainer.id).first()
            if not trainer:
                return jsonify({'error': 'No trainer accounts available. Create a trainer first.'}), 400
            trainer_id = trainer.id
    expense = Expense(
        trainer_id=trainer_id,
        expense_name=expense_name,
        amount=amount,
        category=category,
        expense_date=expense_date
    )
    db.session.add(expense)
    db.session.commit()
    return jsonify({
        'id': expense.id,
        'expense_name': expense.expense_name,
        'category': expense.category,
        'amount': float(expense.amount),
        'expense_date': expense.expense_date.isoformat()
    }), 201
@payments_bp.route('/expenses/<int:expense_id>', methods=['DELETE'])
@login_required
def delete_expense(expense_id):
    """Delete an expense"""
    expense_query = Expense.query.filter_by(id=expense_id)
    if not getattr(current_user, 'is_admin', False):
        expense_query = expense_query.filter_by(trainer_id=current_user.id)
    expense = expense_query.first_or_404()
    db.session.delete(expense)
    db.session.commit()
    return '', 204
EXPENSE_CATEGORIES = [
    ('gym_cut', 'Gym Commission Cut'),
    ('supplements', 'Supplements for Client'),
    ('travel', 'Travel Expense'),
    ('equipment', 'Equipment/Gear'),
    ('certification', 'Certification/Course'),
    ('other', 'Other')
]