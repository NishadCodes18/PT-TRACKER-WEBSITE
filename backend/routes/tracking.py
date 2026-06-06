"""
Tracking routes for attendance, workouts, progress metrics, nutrition, and goals
"""
from flask import Blueprint, request, jsonify, current_app
from flask_login import login_required, current_user
from datetime import datetime, timedelta
from werkzeug.utils import secure_filename
import os
from ..models import (
    Client, Attendance, Workout, ProgressMetric, GalleryImage,
    Nutrition, Goal, db
)

tracking_bp = Blueprint('tracking', __name__, url_prefix='/api/tracking')

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_upload_folder():
    """Get or create the uploads folder for progress images"""
    root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    upload_folder = os.path.join(root_dir, 'static', 'uploads', 'progress_images')
    os.makedirs(upload_folder, exist_ok=True)
    return upload_folder


@tracking_bp.route('/attendance', methods=['POST'])
@login_required
def log_attendance():
    """Log client attendance for a training session"""
    try:
        data = request.json
        client_id = data.get('client_id')
        session_date = data.get('session_date')
        status = data.get('status', 'attended')
        duration_minutes = data.get('duration_minutes')
        notes = data.get('notes', '')
        
        # Verify client exists and belongs to trainer
        client = Client.query.get(client_id)
        if not client or (client.trainer_id != current_user.id and not getattr(current_user, 'is_admin', False)):
            return jsonify({'error': 'Unauthorized'}), 403
        
        attendance = Attendance(
            client_id=client_id,
            trainer_id=current_user.id if not getattr(current_user, 'is_admin', False) else client.trainer_id,
            session_date=datetime.strptime(session_date, '%Y-%m-%d').date(),
            status=status,
            duration_minutes=duration_minutes,
            notes=notes
        )
        
        db.session.add(attendance)
        db.session.commit()
        
        return jsonify({
            'id': attendance.id,
            'client_id': attendance.client_id,
            'session_date': attendance.session_date.isoformat(),
            'status': attendance.status,
            'duration_minutes': attendance.duration_minutes,
            'notes': attendance.notes
        }), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@tracking_bp.route('/attendance/<int:client_id>', methods=['GET'])
@login_required
def get_attendance_history(client_id):
    """Get attendance history for a client"""
    try:
        client = Client.query.get(client_id)
        if not client or (client.trainer_id != current_user.id and not getattr(current_user, 'is_admin', False)):
            return jsonify({'error': 'Unauthorized'}), 403
        
        days = request.args.get('days', 30, type=int)
        start_date = datetime.utcnow().date() - timedelta(days=days)
        
        attendance_records = Attendance.query.filter(
            Attendance.client_id == client_id,
            Attendance.session_date >= start_date
        ).order_by(Attendance.session_date.desc()).all()
        
        return jsonify({
            'client_id': client_id,
            'client_name': client.name,
            'attendance_count': len(attendance_records),
            'attendance': [{
                'id': a.id,
                'session_date': a.session_date.isoformat(),
                'status': a.status,
                'duration_minutes': a.duration_minutes,
                'notes': a.notes
            } for a in attendance_records]
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@tracking_bp.route('/attendance-calendar', methods=['GET'])
@login_required
def attendance_calendar():
    """Calendar-ready attendance feed for all visible clients."""
    try:
        days = request.args.get('days', 30, type=int)
        start_date = datetime.utcnow().date() - timedelta(days=max(days, 1))

        query = db.session.query(Attendance, Client.name).join(Client, Client.id == Attendance.client_id).filter(Attendance.session_date >= start_date)
        if not getattr(current_user, 'is_admin', False):
            query = query.filter(Attendance.trainer_id == current_user.id)

        records = query.order_by(Attendance.session_date.desc()).all()
        return jsonify(
            {
                'events': [
                    {
                        'id': attendance.id,
                        'client_id': attendance.client_id,
                        'client_name': client_name,
                        'date': attendance.session_date.isoformat(),
                        'status': attendance.status,
                        'duration_minutes': attendance.duration_minutes,
                    }
                    for attendance, client_name in records
                ]
            }
        ), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@tracking_bp.route('/workout', methods=['POST'])
@login_required
def log_workout():
    """Log workout details for a client"""
    try:
        data = request.json
        client_id = data.get('client_id')
        workout_date = data.get('workout_date')
        exercise_name = data.get('exercise_name')
        sets = data.get('sets')
        reps = data.get('reps')
        weight_kg = data.get('weight_kg')
        duration_minutes = data.get('duration_minutes')
        notes = data.get('notes', '')
        
        client = Client.query.get(client_id)
        if not client or (client.trainer_id != current_user.id and not getattr(current_user, 'is_admin', False)):
            return jsonify({'error': 'Unauthorized'}), 403
        
        workout = Workout(
            client_id=client_id,
            trainer_id=current_user.id if not getattr(current_user, 'is_admin', False) else client.trainer_id,
            workout_date=datetime.strptime(workout_date, '%Y-%m-%d').date(),
            exercise_name=exercise_name,
            sets=sets,
            reps=reps,
            weight_kg=weight_kg,
            duration_minutes=duration_minutes,
            notes=notes
        )
        
        db.session.add(workout)
        db.session.commit()
        
        return jsonify({
            'id': workout.id,
            'exercise_name': workout.exercise_name,
            'sets': workout.sets,
            'reps': workout.reps,
            'weight_kg': workout.weight_kg
        }), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@tracking_bp.route('/progress/<int:client_id>', methods=['GET', 'POST'])
@login_required
def manage_progress_metrics(client_id):
    """Get or log progress metrics for a client"""
    try:
        client = Client.query.get(client_id)
        if not client or (client.trainer_id != current_user.id and not getattr(current_user, 'is_admin', False)):
            return jsonify({'error': 'Unauthorized'}), 403
        
        if request.method == 'POST':
            data = request.json
            metric = ProgressMetric(
                client_id=client_id,
                trainer_id=current_user.id if not getattr(current_user, 'is_admin', False) else client.trainer_id,
                metric_date=datetime.strptime(data['metric_date'], '%Y-%m-%d').date(),
                metric_type=data['metric_type'],  # weight, chest, waist, etc
                value=data['value'],
                unit=data.get('unit', 'kg'),
                notes=data.get('notes', '')
            )
            db.session.add(metric)
            db.session.commit()
            return jsonify({'id': metric.id, 'metric_type': metric.metric_type, 'value': metric.value}), 201
        
        # GET - retrieve progress history
        days = request.args.get('days', 90, type=int)
        start_date = datetime.utcnow().date() - timedelta(days=days)
        
        metrics = ProgressMetric.query.filter(
            ProgressMetric.client_id == client_id,
            ProgressMetric.metric_date >= start_date
        ).order_by(ProgressMetric.metric_date).all()
        
        # Group by metric type
        grouped = {}
        for m in metrics:
            if m.metric_type not in grouped:
                grouped[m.metric_type] = []
            grouped[m.metric_type].append({
                'date': m.metric_date.isoformat(),
                'value': float(m.value),
                'unit': m.unit
            })
        
        return jsonify({'client_id': client_id, 'metrics': grouped}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@tracking_bp.route('/gallery/<int:client_id>', methods=['GET', 'POST'])
@login_required
def manage_gallery(client_id):
    """Store and fetch progress photos for a client - file upload only."""
    try:
        client = Client.query.get(client_id)
        if not client or (client.trainer_id != current_user.id and not getattr(current_user, 'is_admin', False)):
            return jsonify({'error': 'Unauthorized'}), 403

        if request.method == 'POST':
            # Check if file is present in request
            if 'image' not in request.files:
                return jsonify({'error': 'No image file provided'}), 400

            file = request.files['image']
            if file.filename == '':
                return jsonify({'error': 'No file selected'}), 400

            if not allowed_file(file.filename):
                return jsonify({'error': 'Invalid file type. Allowed: png, jpg, jpeg, gif, webp'}), 400

            # Generate secure filename
            filename = secure_filename(file.filename)
            timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
            unique_filename = f"client_{client_id}_{timestamp}_{filename}"

            # Save file
            upload_folder = get_upload_folder()
            filepath = os.path.join(upload_folder, unique_filename)
            file.save(filepath)

            # Store relative path in database
            relative_path = f"/static/uploads/progress_images/{unique_filename}"

            caption = request.form.get('caption', '').strip()
            upload_date = request.form.get('upload_date', datetime.utcnow().date().isoformat())

            gallery_image = GalleryImage(
                client_id=client_id,
                trainer_id=current_user.id if not getattr(current_user, 'is_admin', False) else client.trainer_id,
                image_path=relative_path,
                caption=caption,
                upload_date=datetime.strptime(upload_date, '%Y-%m-%d').date(),
            )
            db.session.add(gallery_image)
            db.session.commit()
            return jsonify({
                'id': gallery_image.id,
                'image_path': gallery_image.image_path,
                'caption': gallery_image.caption
            }), 201

        # GET - retrieve images
        images = (
            GalleryImage.query.filter_by(client_id=client_id)
            .order_by(GalleryImage.upload_date.desc())
            .limit(100)
            .all()
        )
        return jsonify(
            {
                'client_id': client_id,
                'client_name': client.name,
                'images': [
                    {
                        'id': img.id,
                        'image_path': img.image_path,
                        'caption': img.caption,
                        'upload_date': img.upload_date.isoformat() if img.upload_date else None,
                    }
                    for img in images
                ],
            }
        ), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@tracking_bp.route('/gallery/image/<int:image_id>', methods=['DELETE'])
@login_required
def delete_gallery_image(image_id):
    """Delete a specific progress photo."""
    try:
        image = GalleryImage.query.get(image_id)
        if not image:
            return jsonify({'error': 'Image not found'}), 404
            
        client = Client.query.get(image.client_id)
        if not client or (client.trainer_id != current_user.id and not getattr(current_user, 'is_admin', False)):
            return jsonify({'error': 'Unauthorized'}), 403
            
        db.session.delete(image)
        db.session.commit()
        return '', 204
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@tracking_bp.route('/goal/<int:client_id>', methods=['GET', 'POST'])
@login_required
def manage_goals(client_id):
    """Get or create fitness goals for a client"""
    try:
        client = Client.query.get(client_id)
        if not client or (client.trainer_id != current_user.id and not getattr(current_user, 'is_admin', False)):
            return jsonify({'error': 'Unauthorized'}), 403
        
        if request.method == 'POST':
            data = request.json
            goal = Goal(
                client_id=client_id,
                trainer_id=current_user.id if not getattr(current_user, 'is_admin', False) else client.trainer_id,
                goal_name=data['goal_name'],
                goal_type=data['goal_type'],
                target_value=data.get('target_value'),
                current_value=data.get('current_value'),
                unit=data.get('unit'),
                start_date=datetime.strptime(data['start_date'], '%Y-%m-%d').date(),
                target_date=datetime.strptime(data.get('target_date'), '%Y-%m-%d').date() if data.get('target_date') else None,
                status='in_progress'
            )
            db.session.add(goal)
            db.session.commit()
            return jsonify({'id': goal.id, 'goal_name': goal.goal_name}), 201
        
        # GET
        goals = Goal.query.filter_by(client_id=client_id).all()
        return jsonify({
            'client_id': client_id,
            'goals': [{
                'id': g.id,
                'goal_name': g.goal_name,
                'goal_type': g.goal_type,
                'target_value': float(g.target_value) if g.target_value else None,
                'current_value': float(g.current_value) if g.current_value else None,
                'status': g.status,
                'progress_percent': int((g.current_value / g.target_value * 100) if g.target_value and g.current_value else 0)
            } for g in goals]
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@tracking_bp.route('/nutrition/<int:client_id>', methods=['GET', 'POST'])
@login_required
def manage_nutrition(client_id):
    """Track nutrition/meals for a client"""
    try:
        client = Client.query.get(client_id)
        if not client or (client.trainer_id != current_user.id and not getattr(current_user, 'is_admin', False)):
            return jsonify({'error': 'Unauthorized'}), 403
        
        if request.method == 'POST':
            data = request.json
            nutrition = Nutrition(
                client_id=client_id,
                trainer_id=current_user.id if not getattr(current_user, 'is_admin', False) else client.trainer_id,
                meal_date=datetime.strptime(data['meal_date'], '%Y-%m-%d').date(),
                meal_type=data['meal_type'],
                meal_description=data['meal_description'],
                calories=data.get('calories'),
                protein_g=data.get('protein_g'),
                carbs_g=data.get('carbs_g'),
                fat_g=data.get('fat_g'),
                notes=data.get('notes', '')
            )
            db.session.add(nutrition)
            db.session.commit()
            return jsonify({'id': nutrition.id, 'meal_type': nutrition.meal_type}), 201
        
        # GET
        date_str = request.args.get('date')
        query = Nutrition.query.filter_by(client_id=client_id)
        if date_str:
            meal_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            query = query.filter_by(meal_date=meal_date)
        else:
            start_date = datetime.utcnow().date() - timedelta(days=7)
            query = query.filter(Nutrition.meal_date >= start_date)
        
        meals = query.order_by(Nutrition.meal_date.desc()).all()
        
        return jsonify({
            'client_id': client_id,
            'meals': [{
                'id': m.id,
                'meal_date': m.meal_date.isoformat(),
                'meal_type': m.meal_type,
                'meal_description': m.meal_description,
                'calories': m.calories
            } for m in meals]
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 400
