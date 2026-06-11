from flask import Blueprint, render_template, jsonify, abort, redirect, url_for
from flask_login import login_required, current_user
from sqlalchemy import func
from datetime import datetime, timedelta
from ..models import Client, Payment, Expense, Trainer, CommissionPolicy, ADMIN_DATA_OWNER_USERNAME
from ..database import db
dashboard_bp = Blueprint('dashboard', __name__)
@dashboard_bp.route('/')
@login_required
def main():
    """Render main dashboard"""
    is_admin = getattr(current_user, 'is_admin', False)
    return render_template('dashboard.html', is_admin=is_admin)


@dashboard_bp.route('/profile')
@login_required
def profile():
    """Render the dedicated trainer profile page."""
    if getattr(current_user, 'is_admin', False):
        return redirect(url_for('dashboard.main'))
    return render_template('profile.html')
@dashboard_bp.route('/admin')
@login_required
def admin_panel():
    """Render dedicated admin panel."""
    if not getattr(current_user, 'is_admin', False):
        abort(403)
    return render_template('admin.html')
@dashboard_bp.route('/api/stats')
@login_required
def get_stats():
    """Get dashboard statistics for current trainer"""
    today = datetime.utcnow().date()
    is_admin = getattr(current_user, 'is_admin', False)
    active_query = Client.query.filter_by(status='ongoing')
    if not is_admin:
        active_query = active_query.filter_by(trainer_id=current_user.id)
    total_active = active_query.count()
    lost_query = Client.query.filter_by(status='lost')
    if not is_admin:
        lost_query = lost_query.filter_by(trainer_id=current_user.id)
    total_lost = lost_query.count()
    week_from_now = today + timedelta(days=7)
    upcoming_renewals_query = Client.query.filter(
        Client.status == 'ongoing',
        Client.renewal_date.isnot(None),
        Client.renewal_date <= week_from_now
    )
    if not is_admin:
        upcoming_renewals_query = upcoming_renewals_query.filter(Client.trainer_id == current_user.id)
    upcoming_renewals = upcoming_renewals_query.order_by(Client.renewal_date).all()
    total_income_query = db.session.query(func.sum(Payment.amount))
    if not is_admin:
        total_income_query = total_income_query.filter_by(trainer_id=current_user.id)
    total_income_result = total_income_query.scalar()
    total_income = float(total_income_result) if total_income_result else 0.0
    month_start = today.replace(day=1)
    monthly_income_query = db.session.query(func.sum(Payment.amount)).filter(
        Payment.payment_date >= month_start
    )
    if not is_admin:
        monthly_income_query = monthly_income_query.filter(Payment.trainer_id == current_user.id)
    monthly_income_result = monthly_income_query.scalar()
    monthly_income = float(monthly_income_result) if monthly_income_result else 0.0
    payout_summary = None
    if not is_admin:
        policy = current_user.commission_policy
        if not policy:
            policy = CommissionPolicy(trainer_id=current_user.id)
            db.session.add(policy)
            db.session.commit()
        if policy.override_percent is not None:
            payout_percent = float(policy.override_percent)
            payout_rule = 'manual_override'
        elif monthly_income >= float(policy.monthly_target):
            payout_percent = float(policy.above_target_percent)
            payout_rule = 'target_achieved'
        else:
            payout_percent = float(policy.below_target_percent)
            payout_rule = 'below_target'
        payout_summary = {
            'monthly_target': float(policy.monthly_target),
            'payout_percent': payout_percent,
            'payout_rule': payout_rule,
            'estimated_payout': round((monthly_income * payout_percent) / 100.0, 2),
        }
    return jsonify({
        'total_active_clients': total_active,
        'total_lost_clients': total_lost,
        'total_income': total_income,
        'monthly_income': monthly_income,
        'payout_summary': payout_summary,
        'upcoming_renewals': [
            {
                'id': c.id,
                'name': c.name,
                'contact_number': c.contact_number or 'N/A',
                'renewal_date': c.renewal_date.isoformat(),
                'days_until': (c.renewal_date - today).days,
                'pt_tier': c.pt_tier,
                'expected_amount': c.expected_amount
            }
            for c in upcoming_renewals
        ],
        'overdue_clients': [
            {
                'id': c.id,
                'name': c.name,
                'contact_number': c.contact_number or 'N/A',
                'renewal_date': c.renewal_date.isoformat(),
                'days_overdue': (today - c.renewal_date).days,
                'pt_tier': c.pt_tier
            }
            for c in (
                Client.query.filter(
                    Client.status == 'ongoing',
                    Client.renewal_date < today
                )
                if is_admin else
                Client.query.filter(
                    Client.trainer_id == current_user.id,
                    Client.status == 'ongoing',
                    Client.renewal_date < today
                )
            ).order_by(Client.renewal_date).all()
        ]
    })


@dashboard_bp.route('/api/expiring-clients')
@login_required
def get_expiring_clients():
    """Get clients with renewals expiring within 5 days."""
    today = datetime.utcnow().date()
    cutoff = today + timedelta(days=5)
    is_admin = getattr(current_user, 'is_admin', False)

    query = Client.query.filter(
        Client.status == 'ongoing',
        Client.renewal_date.isnot(None),
        Client.renewal_date <= cutoff
    )

    if not is_admin:
        query = query.filter(Client.trainer_id == current_user.id)

    expiring_clients = query.order_by(Client.renewal_date).all()

    return jsonify({
        'count': len(expiring_clients),
        'clients': [
            {
                'id': c.id,
                'name': c.name,
                'contact_number': c.contact_number or 'N/A',
                'email': c.email or '',
                'renewal_date': c.renewal_date.isoformat(),
                'days_until': (c.renewal_date - today).days,
                'pt_tier': c.pt_tier,
                'expected_amount': c.expected_amount
            }
            for c in expiring_clients
        ]
    })


@dashboard_bp.route('/api/insights')
@login_required
def get_insights():
    """Advanced insights for analytics cards and trend charts."""
    today = datetime.utcnow().date()
    months = 6
    start_date = today - timedelta(days=30 * months)
    is_admin = getattr(current_user, 'is_admin', False)

    payment_query = Payment.query.filter(Payment.payment_date >= start_date)
    expense_query = Expense.query.filter(Expense.expense_date >= start_date)
    client_query = Client.query
    if not is_admin:
        payment_query = payment_query.filter(Payment.trainer_id == current_user.id)
        expense_query = expense_query.filter(Expense.trainer_id == current_user.id)
        client_query = client_query.filter(Client.trainer_id == current_user.id)

    total_revenue = float(payment_query.with_entities(func.sum(Payment.amount)).scalar() or 0)
    total_expenses = float(expense_query.with_entities(func.sum(Expense.amount)).scalar() or 0)
    net_profit = round(total_revenue - total_expenses, 2)

    total_clients = client_query.count()
    active_clients = client_query.filter(Client.status == 'ongoing').count()
    retention_rate = round((active_clients / total_clients) * 100, 2) if total_clients else 0

    at_risk_threshold = today + timedelta(days=7)
    at_risk_clients = client_query.filter(
        Client.status == 'ongoing',
        Client.renewal_date.isnot(None),
        Client.renewal_date <= at_risk_threshold,
    ).count()

    timeline_rows = (
        payment_query.with_entities(Payment.payment_date, func.sum(Payment.amount).label('amount'))
        .group_by(Payment.payment_date)
        .order_by(Payment.payment_date)
        .all()
    )
    timeline = [{'date': d.isoformat(), 'amount': float(a or 0)} for d, a in timeline_rows]

    expense_rows = (
        expense_query.with_entities(Expense.category, func.sum(Expense.amount).label('amount'))
        .group_by(Expense.category)
        .order_by(func.sum(Expense.amount).desc())
        .all()
    )
    expense_breakdown = [{'category': c or 'other', 'amount': float(a or 0)} for c, a in expense_rows]

    clv_rows = (
        db.session.query(
            Client.id,
            Client.name,
            func.sum(Payment.amount).label('lifetime_value'),
        )
        .join(Payment, Payment.client_id == Client.id)
        .filter(Client.trainer_id == current_user.id if not is_admin else Client.id.isnot(None))
        .group_by(Client.id, Client.name)
        .order_by(func.sum(Payment.amount).desc())
        .limit(5)
        .all()
    )
    top_clients = [
        {
            'client_id': cid,
            'client_name': name,
            'lifetime_value': float(value or 0),
        }
        for cid, name, value in clv_rows
    ]

    trainer_performance = []
    if is_admin:
        trainer_rows = (
            db.session.query(
                Trainer.id,
                Trainer.username,
                func.sum(Payment.amount).label('revenue'),
            )
            .outerjoin(Payment, Payment.trainer_id == Trainer.id)
            .filter(Trainer.username != ADMIN_DATA_OWNER_USERNAME)
            .group_by(Trainer.id, Trainer.username)
            .order_by(func.sum(Payment.amount).desc())
            .all()
        )
        trainer_performance = [
            {
                'trainer_id': tid,
                'trainer_username': username,
                'revenue': float(revenue or 0),
            }
            for tid, username, revenue in trainer_rows
        ]

    return jsonify(
        {
            'revenue': total_revenue,
            'expenses': total_expenses,
            'net_profit': net_profit,
            'retention_rate': retention_rate,
            'at_risk_clients': at_risk_clients,
            'timeline': timeline,
            'expense_breakdown': expense_breakdown,
            'top_clients_by_clv': top_clients,
            'trainer_performance': trainer_performance,
        }
    )