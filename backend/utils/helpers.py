"""
Utility helper functions for PT Tracker
"""
from datetime import datetime, timedelta
from functools import wraps
from flask import jsonify, request
from flask_login import current_user
from ..models import AuditLog
from ..database import db


def log_action(action, resource_type=None, resource_id=None, details=None):
    """Log user action to audit trail"""
    try:
        log_entry = AuditLog(
            user_id=current_user.id if hasattr(current_user, 'id') else None,
            username=current_user.username if hasattr(current_user, 'username') else 'unknown',
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details,
            ip_address=request.remote_addr if request else None
        )
        db.session.add(log_entry)
        db.session.commit()
    except Exception as e:
        print(f"Error logging action: {e}")


def require_admin(f):
    """Decorator to require admin role"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not getattr(current_user, 'is_admin', False):
            return jsonify({'error': 'Admin access required'}), 403
        return f(*args, **kwargs)
    return decorated_function


def require_permission(permission):
    """Decorator to require specific permission"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if hasattr(current_user, 'has_permission'):
                if not current_user.has_permission(permission):
                    return jsonify({'error': f'Permission denied: {permission}'}), 403
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def format_currency(amount, currency='₹'):
    """Format amount as currency"""
    return f"{currency}{float(amount):,.2f}"


def calculate_date_range(period):
    """Calculate date range based on period string"""
    today = datetime.utcnow().date()
    
    if period == 'today':
        return today, today
    elif period == 'week':
        start = today - timedelta(days=today.weekday())
        return start, today
    elif period == 'month':
        return today.replace(day=1), today
    elif period == 'quarter':
        quarter_start = today.replace(month=((today.month - 1) // 3) * 3 + 1, day=1)
        return quarter_start, today
    elif period == 'year':
        return today.replace(month=1, day=1), today
    else:
        # Default: last 30 days
        return today - timedelta(days=30), today


def paginate_query(query, page=1, per_page=20):
    """Paginate a SQLAlchemy query"""
    return query.paginate(page=page, per_page=per_page)


def get_client_summary(client):
    """Get comprehensive summary of a client"""
    from sqlalchemy import func
    from .models import Payment, Attendance, Goal, Badge
    
    total_payments = db.session.query(func.sum(Payment.amount)).filter_by(
        client_id=client.id
    ).scalar() or 0
    
    total_sessions = Attendance.query.filter_by(
        client_id=client.id,
        status='attended'
    ).count()
    
    completed_goals = Goal.query.filter(
        Goal.client_id == client.id,
        Goal.status == 'completed'
    ).count()
    
    badges_count = Badge.query.filter_by(client_id=client.id).count()
    
    return {
        'total_revenue': float(total_payments),
        'total_sessions': total_sessions,
        'completed_goals': completed_goals,
        'badges': badges_count,
        'days_with_trainer': (datetime.utcnow() - client.created_at).days if client.created_at else 0
    }


def get_trainer_summary(trainer):
    """Get comprehensive summary of a trainer"""
    from sqlalchemy import func
    from .models import Client, Payment, Attendance
    
    total_clients = Client.query.filter_by(trainer_id=trainer.id).count()
    active_clients = Client.query.filter_by(trainer_id=trainer.id, status='ongoing').count()
    
    total_revenue = db.session.query(func.sum(Payment.amount)).filter_by(
        trainer_id=trainer.id
    ).scalar() or 0
    
    total_sessions = Attendance.query.filter_by(
        trainer_id=trainer.id,
        status='attended'
    ).count()
    
    return {
        'total_clients': total_clients,
        'active_clients': active_clients,
        'total_revenue': float(total_revenue),
        'total_sessions': total_sessions,
        'retention_rate': (active_clients / total_clients * 100) if total_clients > 0 else 0
    }


def validate_email(email):
    """Validate email format"""
    import re
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None


def validate_phone(phone):
    """Validate phone number"""
    import re
    pattern = r'^[0-9+\-\s()]{10,}$'
    return re.match(pattern, phone) is not None


def generate_referral_code(prefix='REF'):
    """Generate unique referral code"""
    import random
    import string
    code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
    return f"{prefix}_{code}"


def send_notification(trainer_id, message, notification_type='info'):
    """Send in-app notification to trainer"""
    from .models import Notification
    try:
        notification = Notification(
            trainer_id=trainer_id,
            message=message,
            created_by='system'
        )
        db.session.add(notification)
        db.session.commit()
        return True
    except Exception as e:
        print(f"Error sending notification: {e}")
        return False


def batch_notify_trainers(message):
    """Send notification to all trainers"""
    from .models import Trainer
    trainers = Trainer.query.filter_by(is_active=True).all()
    for trainer in trainers:
        send_notification(trainer.id, message)


def calculate_retention_rate(trainer_id=None):
    """Calculate client retention rate"""
    from sqlalchemy import func
    from .models import Client
    
    query = Client.query
    if trainer_id:
        query = query.filter_by(trainer_id=trainer_id)
    
    total = query.count()
    if total == 0:
        return 0
    
    active = query.filter_by(status='ongoing').count()
    return round((active / total) * 100, 2)


def get_overdue_clients(trainer_id=None):
    """Get list of clients with overdue renewals"""
    from .models import Client
    
    today = datetime.utcnow().date()
    query = Client.query.filter(
        Client.status == 'ongoing',
        Client.renewal_date < today
    )
    
    if trainer_id:
        query = query.filter_by(trainer_id=trainer_id)
    
    return query.all()


def get_upcoming_renewals(trainer_id=None, days=7):
    """Get clients with upcoming renewals"""
    from .models import Client
    
    today = datetime.utcnow().date()
    end_date = today + timedelta(days=days)
    
    query = Client.query.filter(
        Client.status == 'ongoing',
        Client.renewal_date >= today,
        Client.renewal_date <= end_date
    )
    
    if trainer_id:
        query = query.filter_by(trainer_id=trainer_id)
    
    return query.order_by(Client.renewal_date).all()


def export_to_dict(obj, exclude_fields=None):
    """Convert database object to dictionary"""
    exclude_fields = exclude_fields or []
    result = {}
    
    for column in obj.__table__.columns:
        if column.name not in exclude_fields:
            value = getattr(obj, column.name)
            if isinstance(value, datetime):
                result[column.name] = value.isoformat()
            else:
                result[column.name] = value
    
    return result


def check_system_health():
    """Check system health and status"""
    try:
        # Test database connection
        from .models import Trainer
        Trainer.query.limit(1).all()
        
        return {
            'status': 'healthy',
            'database': 'connected',
            'timestamp': datetime.utcnow().isoformat()
        }
    except Exception as e:
        return {
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }


def rate_limit(max_calls=100, time_window=3600):
    """Decorator for rate limiting"""
    def decorator(f):
        calls = {}
        
        @wraps(f)
        def decorated_function(*args, **kwargs):
            user_id = current_user.id if hasattr(current_user, 'id') else 'anonymous'
            now = datetime.utcnow().timestamp()
            
            if user_id not in calls:
                calls[user_id] = []
            
            # Remove old calls outside time window
            calls[user_id] = [call_time for call_time in calls[user_id] 
                             if now - call_time < time_window]
            
            if len(calls[user_id]) >= max_calls:
                return jsonify({'error': 'Rate limit exceeded'}), 429
            
            calls[user_id].append(now)
            return f(*args, **kwargs)
        
        return decorated_function
    return decorator
