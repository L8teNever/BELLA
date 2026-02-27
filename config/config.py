import os
from datetime import datetime


class Config:
    """Base configuration"""

    # Database configuration
    SQLALCHEMY_DATABASE_URI = f"sqlite:///{os.getenv('DATABASE_PATH', '/app/data/bella.db')}"
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Backup configuration
    BACKUP_DIR = os.getenv('BACKUP_DIR', '/backups')
    BACKUP_TIME = os.getenv('BACKUP_TIME', '01:00')

    # Docker configuration
    DOCKER_SOCKET = '/var/run/docker.sock'

    # Retention policy
    DEFAULT_RETENTION_DAYS = 30
    DEFAULT_MAX_BACKUPS = 10

    # Flask configuration
    SECRET_KEY = os.getenv('SECRET_KEY', 'bella-backup-secret-key-change-in-production')

    # Backup settings
    CONTAINER_STOP_TIMEOUT = 30  # seconds
    BACKUP_COMPRESSION = 'gz'  # gzip compression

    @staticmethod
    def init_app(app):
        """Initialize application with configuration"""
        pass
