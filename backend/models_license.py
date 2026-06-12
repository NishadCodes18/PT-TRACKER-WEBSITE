"""License key model for registration validation."""
from datetime import datetime
from .database import db


class LicenseKey(db.Model):
    """License keys for controlling access to the gym tracker system."""
    __tablename__ = 'license_keys'

    id = db.Column(db.Integer, primary_key=True)
    license_key = db.Column(db.String(100), unique=True, nullable=False, index=True)
    is_used = db.Column(db.Boolean, default=False, nullable=False)
    used_by_trainer_id = db.Column(db.Integer, db.ForeignKey('trainers.id'), nullable=True)
    used_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    notes = db.Column(db.String(200), nullable=True)

    # Relationship to trainer who used this license
    used_by = db.relationship('Trainer', backref='license_key_used', foreign_keys=[used_by_trainer_id])

    def mark_as_used(self, trainer_id):
        """Mark this license key as used by a trainer."""
        self.is_used = True
        self.used_by_trainer_id = trainer_id
        self.used_at = datetime.utcnow()

    def __repr__(self):
        return f'<LicenseKey {self.license_key[:8]}... used={self.is_used}>'
