from flask import Blueprint, render_template, jsonify, abort, redirect, url_for
from flask_login import login_required, current_user
from sqlalchemy import func
from datetime import datetime, timedelta
from ..models import Client, Payment, CommissionPolicy
from ..database import db
dashboard_bp = Blueprint('dashboard', __name__)
@dashboard_bp.route('/')
@login_required
def main():
    """Render main dashboard"""
    is_admin = getattr(current_user, 'is_admin', False)
    return render_template('dashboard.html', is_admin=is_admin)
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
        Client.renewal_date >= today,
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