"""
Database models for Bella backup system
"""

from app import db
from datetime import datetime
import json


class Container(db.Model):
    """Model for tracked Docker containers"""

    __tablename__ = 'containers'

    id = db.Column(db.Integer, primary_key=True)
    container_id = db.Column(db.String(256), unique=True, nullable=False, index=True)
    name = db.Column(db.String(256), nullable=False)
    image = db.Column(db.String(512), nullable=True)
    backup_enabled = db.Column(db.Boolean, default=False, nullable=False)
    last_backup = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    backups = db.relationship('BackupHistory', backref='container', lazy=True, cascade='all, delete-orphan')
    config = db.relationship('BackupConfig', backref='container', lazy=True, cascade='all, delete-orphan',
                             uselist=False)

    def to_dict(self):
        """Convert model to dictionary"""
        return {
            'id': self.id,
            'container_id': self.container_id,
            'name': self.name,
            'image': self.image,
            'backup_enabled': self.backup_enabled,
            'last_backup': self.last_backup.isoformat() if self.last_backup else None,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
        }

    def __repr__(self):
        return f'<Container {self.name}>'


class BackupHistory(db.Model):
    """Model for backup history/logs"""

    __tablename__ = 'backup_history'

    id = db.Column(db.Integer, primary_key=True)
    container_id = db.Column(db.Integer, db.ForeignKey('containers.id'), nullable=False, index=True)
    backup_path = db.Column(db.String(512), nullable=True)
    status = db.Column(db.String(50), default='pending', nullable=False)  # pending, in_progress, success, failed
    start_time = db.Column(db.DateTime, nullable=True)
    end_time = db.Column(db.DateTime, nullable=True)
    error_message = db.Column(db.Text, nullable=True)
    file_size = db.Column(db.BigInteger, nullable=True)  # in bytes
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)

    def to_dict(self):
        """Convert model to dictionary"""
        return {
            'id': self.id,
            'container_id': self.container_id,
            'container_name': self.container.name,
            'backup_path': self.backup_path,
            'status': self.status,
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'error_message': self.error_message,
            'file_size': self.file_size,
            'created_at': self.created_at.isoformat(),
            'duration_seconds': self._get_duration(),
        }

    def _get_duration(self):
        """Get backup duration in seconds"""
        if self.start_time and self.end_time:
            delta = self.end_time - self.start_time
            return delta.total_seconds()
        return None

    def __repr__(self):
        return f'<BackupHistory {self.id} - {self.status}>'


class BackupConfig(db.Model):
    """Extended configuration for individual container backups"""

    __tablename__ = 'backup_config'

    id = db.Column(db.Integer, primary_key=True)
    container_id = db.Column(db.Integer, db.ForeignKey('containers.id'), unique=True, nullable=False, index=True)
    retention_days = db.Column(db.Integer, default=30, nullable=False)  # Keep backups for N days
    max_backups = db.Column(db.Integer, default=10, nullable=False)  # Maximum number of backups to keep
    enable_compression = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def to_dict(self):
        """Convert model to dictionary"""
        return {
            'id': self.id,
            'container_id': self.container_id,
            'retention_days': self.retention_days,
            'max_backups': self.max_backups,
            'enable_compression': self.enable_compression,
        }

    def __repr__(self):
        return f'<BackupConfig container_id={self.container_id}>'
