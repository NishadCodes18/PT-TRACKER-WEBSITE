from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from .database import db
ADMIN_DATA_OWNER_USERNAME = '__admin_owner__'
class AdminUser(UserMixin):
    """In-memory admin account used for full-system access."""
    id = 'admin'
    username = 'adminvenom'
    is_admin = True
    def get_id(self):
        return self.id
class Trainer(UserMixin, db.Model):
    """Trainer user model for authentication"""
    __tablename__ = 'trainers'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    shift_type = db.Column(db.String(20), default='8-hour')
    role = db.Column(db.String(50), default='trainer')  # admin, manager, trainer, assistant
    email = db.Column(db.String(120), unique=True, nullable=True)
    phone = db.Column(db.String(20))
    is_active = db.Column(db.Boolean, default=True)
    last_login = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    clients = db.relationship('Client', backref='trainer', lazy=True, cascade='all, delete-orphan')
    payments = db.relationship('Payment', backref='trainer', lazy=True, cascade='all, delete-orphan')
    expenses = db.relationship('Expense', backref='trainer', lazy=True, cascade='all, delete-orphan')
    commission_policy = db.relationship('CommissionPolicy', backref='trainer', uselist=False, lazy=True, cascade='all, delete-orphan')
    notifications = db.relationship('Notification', backref='trainer', lazy=True, cascade='all, delete-orphan')

    def set_password(self, password):
        """Hash and set password"""
        self.password_hash = generate_password_hash(password, method='pbkdf2:sha256')
    def check_password(self, password):
        """Verify password against hash"""
        return check_password_hash(self.password_hash, password)
    
    def has_permission(self, permission):
        """Check if trainer has a specific permission"""
        role_permissions = {
            'admin': ['manage_trainers', 'manage_payments', 'view_reports', 'manage_all_clients', 'manage_settings'],
            'manager': ['manage_payments', 'view_reports', 'manage_all_clients'],
            'trainer': ['view_reports', 'manage_own_clients'],
            'assistant': ['manage_own_clients']
        }
        return permission in role_permissions.get(self.role, [])
class Client(db.Model):
    """Client model for tracking PT clients"""
    __tablename__ = 'clients'
    id = db.Column(db.Integer, primary_key=True)
    trainer_id = db.Column(db.Integer, db.ForeignKey('trainers.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    contact_number = db.Column(db.String(20))
    email = db.Column(db.String(120), nullable=True)
    send_email_reminders = db.Column(db.Boolean, default=False)
    status = db.Column(db.String(20), default='ongoing')  
    pt_tier = db.Column(db.String(20), default='Silver')  
    time_slot = db.Column(db.String(50), nullable=True)
    renewal_date = db.Column(db.Date, nullable=True)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    @property
    def expected_amount(self):
        """Get expected payment amount based on tier (Indian pricing)"""
        tier_amounts = {'Silver': 8000, 'Gold': 12000, 'Platinum': 15000}
        return tier_amounts.get(self.pt_tier, 8000)
    payments = db.relationship('Payment', backref='client', lazy=True, cascade='all, delete-orphan')

class Payment(db.Model):
    """Payment model for tracking income"""
    __tablename__ = 'payments'
    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey('clients.id'), nullable=False)
    trainer_id = db.Column(db.Integer, db.ForeignKey('trainers.id'), nullable=False)
    plan_type = db.Column(db.String(20), default='monthly')
    start_date = db.Column(db.Date, nullable=True)
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    payment_date = db.Column(db.Date, nullable=False)
    description = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Expense(db.Model):
    """Expense model for tracking business costs"""
    __tablename__ = 'expenses'
    id = db.Column(db.Integer, primary_key=True)
    trainer_id = db.Column(db.Integer, db.ForeignKey('trainers.id'), nullable=False)
    expense_name = db.Column(db.String(100), nullable=False)  
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    expense_date = db.Column(db.Date, nullable=False)
    category = db.Column(db.String(50), default='other')  
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
class CommissionPolicy(db.Model):
    """Trainer payout policy configured by admin."""
    __tablename__ = 'commission_policies'
    id = db.Column(db.Integer, primary_key=True)
    trainer_id = db.Column(db.Integer, db.ForeignKey('trainers.id'), nullable=False, unique=True)
    monthly_target = db.Column(db.Numeric(10, 2), nullable=False, default=8000)
    above_target_percent = db.Column(db.Float, nullable=False, default=50.0)
    below_target_percent = db.Column(db.Float, nullable=False, default=40.0)
    override_percent = db.Column(db.Float, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
class Notification(db.Model):
    """Admin notifications for trainers (or broadcast when trainer_id is null)."""
    __tablename__ = 'notifications'
    id = db.Column(db.Integer, primary_key=True)
    trainer_id = db.Column(db.Integer, db.ForeignKey('trainers.id'), nullable=True)
    message = db.Column(db.Text, nullable=False)
    created_by = db.Column(db.String(50), nullable=False, default='admin')
    is_read = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
class Attendance(db.Model):
    """Track client attendance for training sessions"""
    __tablename__ = 'attendance'
    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey('clients.id'), nullable=False)
    trainer_id = db.Column(db.Integer, db.ForeignKey('trainers.id'), nullable=False)
    session_date = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(20), default='attended')  # attended, missed, rescheduled
    duration_minutes = db.Column(db.Integer)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
class Workout(db.Model):
    """Log workout details and exercises"""
    __tablename__ = 'workouts'
    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey('clients.id'), nullable=False)
    trainer_id = db.Column(db.Integer, db.ForeignKey('trainers.id'), nullable=False)
    workout_date = db.Column(db.Date, nullable=False)
    exercise_name = db.Column(db.String(100), nullable=False)
    sets = db.Column(db.Integer)
    reps = db.Column(db.Integer)
    weight_kg = db.Column(db.Float)
    duration_minutes = db.Column(db.Integer)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class ProgressMetric(db.Model):
    """Track client progress metrics (weight, measurements, etc.)"""
    __tablename__ = 'progress_metrics'
    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey('clients.id'), nullable=False)
    trainer_id = db.Column(db.Integer, db.ForeignKey('trainers.id'), nullable=False)
    metric_date = db.Column(db.Date, nullable=False)
    metric_type = db.Column(db.String(50), nullable=False)  # weight, chest, waist, arms, etc
    value = db.Column(db.Float, nullable=False)
    unit = db.Column(db.String(20), default='kg')  # kg, cm, lbs
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class GalleryImage(db.Model):
    """Store progress photos for clients"""
    __tablename__ = 'gallery_images'
    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey('clients.id'), nullable=False)
    trainer_id = db.Column(db.Integer, db.ForeignKey('trainers.id'), nullable=False)
    image_path = db.Column(db.String(500), nullable=False)
    caption = db.Column(db.String(200))
    upload_date = db.Column(db.Date, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Nutrition(db.Model):
    """Track client nutrition/meals"""
    __tablename__ = 'nutrition'
    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey('clients.id'), nullable=False)
    trainer_id = db.Column(db.Integer, db.ForeignKey('trainers.id'), nullable=False)
    meal_date = db.Column(db.Date, nullable=False)
    meal_type = db.Column(db.String(50), nullable=False)  # breakfast, lunch, dinner, snack
    meal_description = db.Column(db.Text, nullable=False)
    calories = db.Column(db.Integer)
    protein_g = db.Column(db.Float)
    carbs_g = db.Column(db.Float)
    fat_g = db.Column(db.Float)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Goal(db.Model):
    """Track fitness goals for clients"""
    __tablename__ = 'goals'
    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey('clients.id'), nullable=False)
    trainer_id = db.Column(db.Integer, db.ForeignKey('trainers.id'), nullable=False)
    goal_name = db.Column(db.String(100), nullable=False)
    goal_type = db.Column(db.String(50), nullable=False)  # weight_loss, muscle_gain, strength, endurance
    target_value = db.Column(db.Float)
    current_value = db.Column(db.Float)
    unit = db.Column(db.String(20))
    start_date = db.Column(db.Date, nullable=False)
    target_date = db.Column(db.Date)
    status = db.Column(db.String(20), default='in_progress')  # in_progress, completed, abandoned
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Badge(db.Model):
    """Gamification badges for achievements"""
    __tablename__ = 'badges'
    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey('clients.id'), nullable=False)
    badge_name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    badge_type = db.Column(db.String(50), nullable=False)  # milestone, streak, achievement
    earned_date = db.Column(db.DateTime, default=datetime.utcnow)

class ClientReferral(db.Model):
    """Track client referrals"""
    __tablename__ = 'client_referrals'
    id = db.Column(db.Integer, primary_key=True)
    referrer_id = db.Column(db.Integer, db.ForeignKey('clients.id'), nullable=False)
    referred_client_id = db.Column(db.Integer, db.ForeignKey('clients.id'), nullable=True)  # nullable until client signs up
    referred_email = db.Column(db.String(120))
    referred_name = db.Column(db.String(100))
    referral_status = db.Column(db.String(20), default='pending')  # pending, signed_up, completed
    reward_amount = db.Column(db.Numeric(10, 2), default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class AuditLog(db.Model):
    """Track all user actions for audit trail"""
    __tablename__ = 'audit_logs'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('trainers.id'), nullable=True)
    username = db.Column(db.String(80))
    action = db.Column(db.String(100), nullable=False)  # create, update, delete, login, logout
    resource_type = db.Column(db.String(50))  # Client, Payment, Expense, etc
    resource_id = db.Column(db.Integer)
    details = db.Column(db.Text)  # JSON details of changes
    ip_address = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class SystemSettings(db.Model):
    """Store system-wide configuration"""
    __tablename__ = 'system_settings'
    id = db.Column(db.Integer, primary_key=True)
    setting_key = db.Column(db.String(100), unique=True, nullable=False)
    setting_value = db.Column(db.Text, nullable=False)
    description = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class TrainerRole(db.Model):
    """Define trainer roles for RBAC"""
    __tablename__ = 'trainer_roles'
    id = db.Column(db.Integer, primary_key=True)
    trainer_id = db.Column(db.Integer, db.ForeignKey('trainers.id'), nullable=False, unique=True)
    role = db.Column(db.String(50), default='trainer')  # admin, manager, trainer, assistant
    can_manage_trainers = db.Column(db.Boolean, default=False)
    can_manage_payments = db.Column(db.Boolean, default=False)
    can_view_reports = db.Column(db.Boolean, default=True)
    can_manage_all_clients = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class IntegrationToken(db.Model):
    """Store OAuth tokens for external integrations"""
    __tablename__ = 'integration_tokens'
    id = db.Column(db.Integer, primary_key=True)
    trainer_id = db.Column(db.Integer, db.ForeignKey('trainers.id'), nullable=False)
    service = db.Column(db.String(50), nullable=False)  # google_calendar, slack, stripe
    access_token = db.Column(db.String(500))
    refresh_token = db.Column(db.String(500))
    token_expiry = db.Column(db.DateTime)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class TwoFactorAuth(db.Model):
    """Store 2FA settings for users"""
    __tablename__ = 'two_factor_auth'
    id = db.Column(db.Integer, primary_key=True)
    trainer_id = db.Column(db.Integer, db.ForeignKey('trainers.id'), nullable=False, unique=True)
    is_enabled = db.Column(db.Boolean, default=False)
    secret_key = db.Column(db.String(100))  # For TOTP
    backup_codes = db.Column(db.Text)  # JSON list of backup codes
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

def get_or_create_default_admin_trainer():
    """Ensure there is a trainer record to own data created while logged in as admin."""
    trainer = Trainer.query.filter_by(username=ADMIN_DATA_OWNER_USERNAME).first()
    if trainer:
        return trainer
    trainer = Trainer(username=ADMIN_DATA_OWNER_USERNAME)
    trainer.set_password('admin-owner-not-for-login')
    db.session.add(trainer)
    db.session.commit()
    return trainer