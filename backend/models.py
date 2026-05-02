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