"""
Gamification routes for badges, achievements, leaderboards
"""
from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from datetime import datetime, timedelta
from sqlalchemy import func
from ..models import (
    Client, Badge, Payment, Attendance, Goal, db
)

gamification_bp = Blueprint('gamification', __name__, url_prefix='/api/gamification')


@gamification_bp.route('/badges/<int:client_id>', methods=['GET', 'POST'])
@login_required
def manage_badges(client_id):
    """Get or award badges to a client"""
    try:
        from ..models import Client
        client = Client.query.get(client_id)
        if not client or (client.trainer_id != current_user.id and not getattr(current_user, 'is_admin', False)):
            return jsonify({'error': 'Unauthorized'}), 403
        
        if request.method == 'POST':
            data = request.json
            badge = Badge(
                client_id=client_id,
                badge_name=data['badge_name'],
                description=data.get('description', ''),
                badge_type=data.get('badge_type', 'achievement')
            )
            db.session.add(badge)
            db.session.commit()
            
            return jsonify({
                'id': badge.id,
                'badge_name': badge.badge_name,
                'earned_date': badge.earned_date.isoformat()
            }), 201
        
        # GET - retrieve badges
        badges = Badge.query.filter_by(client_id=client_id).order_by(Badge.earned_date.desc()).all()
        
        return jsonify({
            'client_id': client_id,
            'total_badges': len(badges),
            'badges': [{
                'id': b.id,
                'badge_name': b.badge_name,
                'badge_type': b.badge_type,
                'description': b.description,
                'earned_date': b.earned_date.isoformat()
            } for b in badges]
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@gamification_bp.route('/check-achievements/<int:client_id>', methods=['GET'])
@login_required
def check_achievements(client_id):
    """Check and auto-award achievements based on milestones"""
    try:
        from ..models import Client
        client = Client.query.get(client_id)
        if not client or (client.trainer_id != current_user.id and not getattr(current_user, 'is_admin', False)):
            return jsonify({'error': 'Unauthorized'}), 403
        
        achievements_earned = []
        today = datetime.utcnow().date()
        
        # Check for attendance streaks
        recent_attendance = Attendance.query.filter(
            Attendance.client_id == client_id,
            Attendance.status == 'attended'
        ).order_by(Attendance.session_date.desc()).limit(10).all()
        
        if len(recent_attendance) >= 10:
            # Check if they have a 10-session streak
            existing_badge = Badge.query.filter_by(
                client_id=client_id,
                badge_name='10 Sessions Streak'
            ).first()
            if not existing_badge:
                badge = Badge(
                    client_id=client_id,
                    badge_name='10 Sessions Streak',
                    description='Completed 10 consecutive training sessions',
                    badge_type='streak'
                )
                db.session.add(badge)
                achievements_earned.append('10 Sessions Streak')
        
        if len(recent_attendance) >= 30:
            existing_badge = Badge.query.filter_by(
                client_id=client_id,
                badge_name='30 Sessions Commitment'
            ).first()
            if not existing_badge:
                badge = Badge(
                    client_id=client_id,
                    badge_name='30 Sessions Commitment',
                    description='Completed 30 training sessions',
                    badge_type='milestone'
                )
                db.session.add(badge)
                achievements_earned.append('30 Sessions Commitment')
        
        # Check for goal completion
        completed_goals = Goal.query.filter(
            Goal.client_id == client_id,
            Goal.status == 'completed'
        ).count()
        
        if completed_goals >= 1:
            existing_badge = Badge.query.filter_by(
                client_id=client_id,
                badge_name='Goal Getter'
            ).first()
            if not existing_badge:
                badge = Badge(
                    client_id=client_id,
                    badge_name='Goal Getter',
                    description='Completed your first fitness goal',
                    badge_type='achievement'
                )
                db.session.add(badge)
                achievements_earned.append('Goal Getter')
        
        if completed_goals >= 5:
            existing_badge = Badge.query.filter_by(
                client_id=client_id,
                badge_name='Goal Master'
            ).first()
            if not existing_badge:
                badge = Badge(
                    client_id=client_id,
                    badge_name='Goal Master',
                    description='Completed 5 fitness goals',
                    badge_type='achievement'
                )
                db.session.add(badge)
                achievements_earned.append('Goal Master')
        
        # Check for payment history
        total_payments = db.session.query(func.count(Payment.id)).filter_by(client_id=client_id).scalar() or 0
        
        if total_payments >= 12:
            existing_badge = Badge.query.filter_by(
                client_id=client_id,
                badge_name='One Year Member'
            ).first()
            if not existing_badge:
                badge = Badge(
                    client_id=client_id,
                    badge_name='One Year Member',
                    description='Been training for one year',
                    badge_type='milestone'
                )
                db.session.add(badge)
                achievements_earned.append('One Year Member')
        
        db.session.commit()
        
        return jsonify({
            'client_id': client_id,
            'achievements_earned': achievements_earned,
            'total_badges': Badge.query.filter_by(client_id=client_id).count()
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@gamification_bp.route('/leaderboard', methods=['GET'])
@login_required
def leaderboard():
    """Get trainer leaderboard based on performance metrics"""
    try:
        period = request.args.get('period', 'monthly')  # daily, weekly, monthly, yearly
        limit = request.args.get('limit', 10, type=int)
        
        # Determine date range
        if period == 'daily':
            days = 1
        elif period == 'weekly':
            days = 7
        elif period == 'monthly':
            days = 30
        else:
            days = 365
        
        start_date = datetime.utcnow().date() - timedelta(days=days)
        
        from ..models import Trainer
        trainers = Trainer.query.filter(Trainer.is_active == True).all()
        
        leaderboard_data = []
        
        for trainer in trainers:
            # Revenue
            revenue = db.session.query(func.sum(Payment.amount)).filter(
                Payment.trainer_id == trainer.id,
                Payment.payment_date >= start_date
            ).scalar() or 0
            
            # Client count
            active_clients = Client.query.filter(
                Client.trainer_id == trainer.id,
                Client.status == 'ongoing'
            ).count()
            
            # Attendance sessions
            attendance_count = Attendance.query.filter(
                Attendance.trainer_id == trainer.id,
                Attendance.session_date >= start_date,
                Attendance.status == 'attended'
            ).count()
            
            # Score calculation
            score = float(revenue) + (active_clients * 1000) + (attendance_count * 100)
            
            leaderboard_data.append({
                'trainer_id': trainer.id,
                'trainer_name': trainer.username,
                'score': score,
                'revenue': float(revenue),
                'active_clients': active_clients,
                'sessions_completed': attendance_count
            })
        
        # Sort by score descending
        leaderboard_data.sort(key=lambda x: x['score'], reverse=True)
        
        return jsonify({
            'period': period,
            'leaderboard': leaderboard_data[:limit]
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@gamification_bp.route('/client-leaderboard', methods=['GET'])
@login_required
def client_leaderboard():
    """Get client leaderboard (top clients by various metrics)"""
    try:
        metric = request.args.get('metric', 'attendance')  # attendance, payments, goals
        limit = request.args.get('limit', 10, type=int)
        
        if not getattr(current_user, 'is_admin', False):
            # Only show clients of current trainer
            clients = Client.query.filter_by(trainer_id=current_user.id).all()
        else:
            clients = Client.query.all()
        
        leaderboard_data = []
        
        for client in clients:
            if metric == 'attendance':
                value = Attendance.query.filter(
                    Attendance.client_id == client.id,
                    Attendance.status == 'attended'
                ).count()
                label = 'Sessions Attended'
            elif metric == 'payments':
                value = db.session.query(func.sum(Payment.amount)).filter_by(
                    client_id=client.id
                ).scalar() or 0
                label = 'Total Revenue'
            elif metric == 'goals':
                value = Goal.query.filter(
                    Goal.client_id == client.id,
                    Goal.status == 'completed'
                ).count()
                label = 'Goals Completed'
            else:
                continue
            
            leaderboard_data.append({
                'client_id': client.id,
                'client_name': client.name,
                'value': float(value) if isinstance(value, float) else value,
                'tier': client.pt_tier
            })
        
        # Sort by value descending
        leaderboard_data.sort(key=lambda x: x['value'], reverse=True)
        
        return jsonify({
            'metric': metric,
            'label': label,
            'leaderboard': leaderboard_data[:limit]
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 400
