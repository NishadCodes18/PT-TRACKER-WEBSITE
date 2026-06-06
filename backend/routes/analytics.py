"""
Analytics and insights routes for revenue, client retention, metrics
"""
from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from datetime import datetime, timedelta
from sqlalchemy import func
from ..models import (
    Client, Payment, Expense, Attendance, Goal, db
)

analytics_bp = Blueprint('analytics', __name__, url_prefix='/api/analytics')


@analytics_bp.route('/revenue', methods=['GET'])
@login_required
def revenue_analytics():
    """Get detailed revenue analytics"""
    try:
        period = request.args.get('period', 'monthly')  # daily, weekly, monthly, yearly
        months = request.args.get('months', 12, type=int)
        
        start_date = datetime.utcnow().date() - timedelta(days=30*months)
        
        # Build query
        query = db.session.query(
            Payment.payment_date,
            func.sum(Payment.amount).label('total_amount'),
            func.count(Payment.id).label('transaction_count')
        ).filter(Payment.payment_date >= start_date)
        
        if not getattr(current_user, 'is_admin', False):
            query = query.filter_by(trainer_id=current_user.id)
        
        query = query.group_by(Payment.payment_date).order_by(Payment.payment_date)
        
        results = query.all()
        
        revenue_data = {
            'total_revenue': 0,
            'transaction_count': 0,
            'average_transaction': 0,
            'timeline': []
        }
        
        for date, total, count in results:
            revenue_data['total_revenue'] += float(total or 0)
            revenue_data['transaction_count'] += count
            revenue_data['timeline'].append({
                'date': date.isoformat(),
                'amount': float(total or 0),
                'transactions': count
            })
        
        if revenue_data['transaction_count'] > 0:
            revenue_data['average_transaction'] = round(revenue_data['total_revenue'] / revenue_data['transaction_count'], 2)
        
        return jsonify(revenue_data), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@analytics_bp.route('/income-by-tier', methods=['GET'])
@login_required
def income_by_tier():
    """Income breakdown by PT tier"""
    try:
        query = db.session.query(
            Client.pt_tier,
            func.sum(Payment.amount).label('total_amount'),
            func.count(Client.id).label('client_count'),
            func.avg(Payment.amount).label('avg_payment')
        ).join(Payment, Client.id == Payment.client_id)
        
        if not getattr(current_user, 'is_admin', False):
            query = query.filter(Client.trainer_id == current_user.id)
        
        query = query.group_by(Client.pt_tier)
        
        results = query.all()
        
        tier_data = []
        for tier, total, count, avg in results:
            tier_data.append({
                'tier': tier,
                'total_revenue': float(total or 0),
                'client_count': count,
                'average_payment': float(avg or 0)
            })
        
        return jsonify({'income_by_tier': tier_data}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@analytics_bp.route('/client-retention', methods=['GET'])
@login_required
def client_retention():
    """Analyze client retention rate"""
    try:
        query = Client.query
        if not getattr(current_user, 'is_admin', False):
            query = query.filter_by(trainer_id=current_user.id)
        
        total_clients = query.count()
        active_clients = query.filter_by(status='ongoing').count()
        lost_clients = query.filter_by(status='lost').count()
        
        retention_rate = 0
        if total_clients > 0:
            retention_rate = round((active_clients / total_clients) * 100, 2)
        
        # Identify at-risk clients (renewal date within 7 days)
        today = datetime.utcnow().date()
        at_risk = query.filter(
            Client.status == 'ongoing',
            Client.renewal_date <= today + timedelta(days=7),
            Client.renewal_date >= today
        ).all()
        
        return jsonify({
            'total_clients': total_clients,
            'active_clients': active_clients,
            'lost_clients': lost_clients,
            'retention_rate': retention_rate,
            'at_risk_count': len(at_risk),
            'at_risk_clients': [{'id': c.id, 'name': c.name, 'renewal_date': c.renewal_date.isoformat()} for c in at_risk]
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@analytics_bp.route('/expense-breakdown', methods=['GET'])
@login_required
def expense_breakdown():
    """Get expense breakdown by category"""
    try:
        months = request.args.get('months', 12, type=int)
        start_date = datetime.utcnow().date() - timedelta(days=30*months)
        
        query = db.session.query(
            Expense.category,
            func.sum(Expense.amount).label('total_amount'),
            func.count(Expense.id).label('transaction_count')
        ).filter(Expense.expense_date >= start_date)
        
        if not getattr(current_user, 'is_admin', False):
            query = query.filter_by(trainer_id=current_user.id)
        
        query = query.group_by(Expense.category)
        
        results = query.all()
        
        expense_data = []
        total_expenses = 0
        for category, total, count in results:
            total = float(total or 0)
            expense_data.append({
                'category': category,
                'amount': total,
                'count': count
            })
            total_expenses += total
        
        return jsonify({
            'total_expenses': total_expenses,
            'breakdown': expense_data
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@analytics_bp.route('/profit-analysis', methods=['GET'])
@login_required
def profit_analysis():
    """Calculate net profit (revenue - expenses)"""
    try:
        months = request.args.get('months', 12, type=int)
        start_date = datetime.utcnow().date() - timedelta(days=30*months)
        
        # Revenue
        revenue_query = db.session.query(func.sum(Payment.amount)).filter(
            Payment.payment_date >= start_date
        )
        if not getattr(current_user, 'is_admin', False):
            revenue_query = revenue_query.filter_by(trainer_id=current_user.id)
        
        total_revenue = float(revenue_query.scalar() or 0)
        
        # Expenses
        expense_query = db.session.query(func.sum(Expense.amount)).filter(
            Expense.expense_date >= start_date
        )
        if not getattr(current_user, 'is_admin', False):
            expense_query = expense_query.filter_by(trainer_id=current_user.id)
        
        total_expenses = float(expense_query.scalar() or 0)
        
        net_profit = total_revenue - total_expenses
        profit_margin = 0
        if total_revenue > 0:
            profit_margin = round((net_profit / total_revenue) * 100, 2)
        
        return jsonify({
            'total_revenue': total_revenue,
            'total_expenses': total_expenses,
            'net_profit': net_profit,
            'profit_margin_percent': profit_margin
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@analytics_bp.route('/client-lifetime-value', methods=['GET'])
@login_required
def client_lifetime_value():
    """Calculate CLV for each client"""
    try:
        query = Client.query
        if not getattr(current_user, 'is_admin', False):
            query = query.filter_by(trainer_id=current_user.id)
        
        clients = query.all()
        
        clv_data = []
        for client in clients:
            # Sum all payments for this client
            total_payments = db.session.query(func.sum(Payment.amount)).filter_by(
                client_id=client.id
            ).scalar() or 0
            
            # Calculate months with trainer
            months_active = 0
            if client.created_at:
                months_active = (datetime.utcnow() - client.created_at).days / 30
            
            # Average monthly value
            avg_monthly = float(total_payments) / months_active if months_active > 0 else 0
            
            clv_data.append({
                'client_id': client.id,
                'client_name': client.name,
                'total_lifetime_value': float(total_payments),
                'months_active': round(months_active, 1),
                'average_monthly_value': round(avg_monthly, 2),
                'status': client.status
            })
        
        # Sort by CLV descending
        clv_data.sort(key=lambda x: x['total_lifetime_value'], reverse=True)
        
        return jsonify({
            'client_count': len(clv_data),
            'average_clv': round(sum(c['total_lifetime_value'] for c in clv_data) / len(clv_data), 2) if clv_data else 0,
            'clients': clv_data
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@analytics_bp.route('/attendance-trends/<int:client_id>', methods=['GET'])
@login_required
def attendance_trends(client_id):
    """Get attendance trends for a client"""
    try:
        client = Client.query.get(client_id)
        if not client or (client.trainer_id != current_user.id and not getattr(current_user, 'is_admin', False)):
            return jsonify({'error': 'Unauthorized'}), 403
        
        months = request.args.get('months', 3, type=int)
        start_date = datetime.utcnow().date() - timedelta(days=30*months)
        
        from ..models import Attendance
        query = db.session.query(
            Attendance.status,
            func.count(Attendance.id).label('count')
        ).filter(
            Attendance.client_id == client_id,
            Attendance.session_date >= start_date
        ).group_by(Attendance.status)
        
        results = query.all()
        
        attendance_stats = {}
        for status, count in results:
            attendance_stats[status] = count
        
        total_sessions = sum(attendance_stats.values())
        attendance_rate = 0
        if total_sessions > 0:
            attendance_rate = round((attendance_stats.get('attended', 0) / total_sessions) * 100, 2)
        
        return jsonify({
            'client_id': client_id,
            'client_name': client.name,
            'attendance_stats': attendance_stats,
            'total_sessions': total_sessions,
            'attendance_rate': attendance_rate
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 400
