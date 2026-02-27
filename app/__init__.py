"""
Bella - Docker Container Backup System
Main Flask application factory
"""

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
import logging
import os

# Initialize SQLAlchemy
db = SQLAlchemy()

# Logger
logger = logging.getLogger(__name__)


def create_app(config_name='development'):
    """
    Create and configure the Flask application

    Args:
        config_name: Configuration environment ('development', 'production')

    Returns:
        Configured Flask application
    """

    app = Flask(__name__)

    # Load configuration
    from config.config import Config
    app.config.from_object(Config)

    # Initialize database
    db.init_app(app)

    # Create database tables
    with app.app_context():
        db.create_all()
        logger.info("Database tables created/verified")

    # Register blueprints
    from app.routes import main_bp, api_bp
    app.register_blueprint(main_bp)
    app.register_blueprint(api_bp, url_prefix='/api')

    # Initialize Docker manager
    from app.docker_manager import DockerManager
    app.docker_manager = DockerManager()
    logger.info("Docker manager initialized")

    # Initialize backup engine
    from app.backup_engine import BackupEngine
    app.backup_engine = BackupEngine(app.docker_manager, app.config)
    logger.info("Backup engine initialized")

    # Initialize and start scheduler
    from app.scheduler import BackupScheduler
    app.scheduler = BackupScheduler(app.backup_engine)
    app.scheduler.start()
    logger.info("Backup scheduler started")

    # Error handlers
    @app.errorhandler(404)
    def not_found(e):
        return {'error': 'Not found'}, 404

    @app.errorhandler(500)
    def internal_error(e):
        logger.error(f"Internal server error: {e}")
        return {'error': 'Internal server error'}, 500

    logger.info("Flask application created successfully")
    return app
