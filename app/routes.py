"""
Flask routes and API endpoints
"""

from flask import Blueprint, render_template, jsonify, request, current_app
from app import db
from app.models import Container, BackupHistory, BackupConfig
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

# Create blueprints
main_bp = Blueprint('main', __name__)
api_bp = Blueprint('api', __name__)


# ============================================================================
# Main Routes (HTML Pages)
# ============================================================================

@main_bp.route('/')
def dashboard():
    """Main dashboard page"""
    try:
        return render_template('index.html')
    except Exception as e:
        logger.error(f"Error rendering dashboard: {e}")
        return {'error': 'Failed to load dashboard'}, 500


@main_bp.route('/history')
def backup_history():
    """Backup history page"""
    try:
        return render_template('backup_history.html')
    except Exception as e:
        logger.error(f"Error rendering history page: {e}")
        return {'error': 'Failed to load history page'}, 500


@main_bp.route('/health')
def health():
    """Health check endpoint"""
    try:
        docker_health = current_app.docker_manager.health_check()
        return jsonify({
            'status': 'healthy' if docker_health else 'unhealthy',
            'docker': docker_health,
            'timestamp': datetime.utcnow().isoformat()
        })
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return jsonify({'status': 'error', 'error': str(e)}), 500


# ============================================================================
# API Routes - Container Management
# ============================================================================

@api_bp.route('/containers', methods=['GET'])
def get_containers():
    """
    Get all Docker containers and their backup status

    Returns:
        JSON list of containers with backup configuration
    """
    try:
        # Get containers from Docker
        docker_containers = current_app.docker_manager.get_all_containers()
        containers_data = []

        for docker_container in docker_containers:
            container_id = docker_container.id[:12]  # Short ID
            container_name = docker_container.name
            container_status = docker_container.status

            # Check if container exists in our database
            db_container = Container.query.filter_by(container_id=container_id).first()

            if not db_container:
                # Create new container record if not exists
                db_container = Container(
                    container_id=container_id,
                    name=container_name,
                    image=docker_container.image.tags[0] if docker_container.image.tags else 'unknown',
                    backup_enabled=False
                )
                db.session.add(db_container)
                db.session.commit()
                logger.debug(f"Added new container to database: {container_name}")

            # Get last backup
            last_backup = BackupHistory.query.filter_by(
                container_id=db_container.id,
                status='success'
            ).order_by(BackupHistory.created_at.desc()).first()

            containers_data.append({
                'id': db_container.id,
                'container_id': container_id,
                'name': container_name,
                'image': db_container.image,
                'status': container_status,
                'backup_enabled': db_container.backup_enabled,
                'last_backup': last_backup.created_at.isoformat() if last_backup else None,
                'volume_count': len(current_app.docker_manager.get_container_volumes(container_id))
            })

        logger.info(f"Retrieved {len(containers_data)} containers")
        return jsonify({'containers': containers_data})

    except Exception as e:
        logger.error(f"Error retrieving containers: {e}")
        return jsonify({'error': str(e)}), 500


@api_bp.route('/container/<int:container_id>/enable', methods=['POST'])
def enable_backup(container_id):
    """Enable backup for a container"""
    try:
        container = Container.query.get(container_id)
        if not container:
            return jsonify({'error': 'Container not found'}), 404

        container.backup_enabled = True
        db.session.commit()

        logger.info(f"Backup enabled for container: {container.name}")
        return jsonify({'success': True, 'message': f'Backup enabled for {container.name}'})

    except Exception as e:
        logger.error(f"Error enabling backup: {e}")
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@api_bp.route('/container/<int:container_id>/disable', methods=['POST'])
def disable_backup(container_id):
    """Disable backup for a container"""
    try:
        container = Container.query.get(container_id)
        if not container:
            return jsonify({'error': 'Container not found'}), 404

        container.backup_enabled = False
        db.session.commit()

        logger.info(f"Backup disabled for container: {container.name}")
        return jsonify({'success': True, 'message': f'Backup disabled for {container.name}'})

    except Exception as e:
        logger.error(f"Error disabling backup: {e}")
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@api_bp.route('/container/<int:container_id>/backup', methods=['POST'])
def manual_backup(container_id):
    """Trigger manual backup for a container"""
    try:
        container = Container.query.get(container_id)
        if not container:
            return jsonify({'error': 'Container not found'}), 404

        # Trigger backup
        success = current_app.backup_engine.backup_container(
            container.id,
            container.container_id,
            container.name
        )

        if success:
            logger.info(f"Manual backup completed for container: {container.name}")
            return jsonify({'success': True, 'message': f'Backup started for {container.name}'})
        else:
            logger.warning(f"Manual backup failed for container: {container.name}")
            return jsonify({'error': 'Backup failed'}), 500

    except Exception as e:
        logger.error(f"Error triggering manual backup: {e}")
        return jsonify({'error': str(e)}), 500


# ============================================================================
# API Routes - Backup History
# ============================================================================

@api_bp.route('/backups', methods=['GET'])
def get_backups():
    """
    Get backup history

    Query parameters:
        - container_id: Filter by container ID (optional)
        - limit: Maximum results (default 100)
    """
    try:
        container_id = request.args.get('container_id', type=int)
        limit = request.args.get('limit', default=100, type=int)

        query = BackupHistory.query
        if container_id:
            query = query.filter_by(container_id=container_id)

        backups = query.order_by(BackupHistory.created_at.desc()).limit(limit).all()

        backups_data = [backup.to_dict() for backup in backups]
        logger.debug(f"Retrieved {len(backups_data)} backup history records")

        return jsonify({'backups': backups_data})

    except Exception as e:
        logger.error(f"Error retrieving backups: {e}")
        return jsonify({'error': str(e)}), 500


@api_bp.route('/backups/container/<int:container_id>', methods=['GET'])
def get_container_backups(container_id):
    """Get backup history for a specific container"""
    try:
        container = Container.query.get(container_id)
        if not container:
            return jsonify({'error': 'Container not found'}), 404

        backups = BackupHistory.query.filter_by(container_id=container_id).order_by(
            BackupHistory.created_at.desc()
        ).limit(50).all()

        backups_data = [backup.to_dict() for backup in backups]

        return jsonify({
            'container': container.to_dict(),
            'backups': backups_data
        })

    except Exception as e:
        logger.error(f"Error retrieving container backups: {e}")
        return jsonify({'error': str(e)}), 500


@api_bp.route('/backups/<int:backup_id>/delete', methods=['DELETE'])
def delete_backup(backup_id):
    """Delete a backup"""
    try:
        backup = BackupHistory.query.get(backup_id)
        if not backup:
            return jsonify({'error': 'Backup not found'}), 404

        # Delete backup file
        import os
        if backup.backup_path and os.path.exists(backup.backup_path):
            try:
                os.remove(backup.backup_path)
                logger.info(f"Deleted backup file: {backup.backup_path}")
            except Exception as e:
                logger.error(f"Error deleting backup file: {e}")

        # Delete database record
        db.session.delete(backup)
        db.session.commit()

        logger.info(f"Deleted backup record: {backup_id}")
        return jsonify({'success': True, 'message': 'Backup deleted'})

    except Exception as e:
        logger.error(f"Error deleting backup: {e}")
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


# ============================================================================
# API Routes - Statistics & Status
# ============================================================================

@api_bp.route('/stats', methods=['GET'])
def get_stats():
    """Get backup statistics"""
    try:
        total_containers = Container.query.count()
        backup_enabled = Container.query.filter_by(backup_enabled=True).count()
        total_backups = BackupHistory.query.count()
        successful_backups = BackupHistory.query.filter_by(status='success').count()
        failed_backups = BackupHistory.query.filter_by(status='failed').count()

        # Calculate total backup size
        total_size = 0
        successful_backups_query = BackupHistory.query.filter_by(status='success').all()
        for backup in successful_backups_query:
            if backup.file_size:
                total_size += backup.file_size

        stats = {
            'total_containers': total_containers,
            'backup_enabled': backup_enabled,
            'total_backups': total_backups,
            'successful_backups': successful_backups,
            'failed_backups': failed_backups,
            'total_backup_size': total_size,
            'total_backup_size_mb': round(total_size / (1024 * 1024), 2)
        }

        return jsonify(stats)

    except Exception as e:
        logger.error(f"Error retrieving statistics: {e}")
        return jsonify({'error': str(e)}), 500


@api_bp.route('/scheduler/status', methods=['GET'])
def get_scheduler_status():
    """Get scheduler status"""
    try:
        status = current_app.scheduler.get_job_status()
        return jsonify(status)

    except Exception as e:
        logger.error(f"Error retrieving scheduler status: {e}")
        return jsonify({'error': str(e)}), 500


@api_bp.route('/scheduler/trigger', methods=['POST'])
def trigger_backup_now():
    """Manually trigger all backups now (for testing)"""
    try:
        results = current_app.scheduler.trigger_backup_now()
        logger.info(f"Manual scheduler trigger: {results}")
        return jsonify(results)

    except Exception as e:
        logger.error(f"Error triggering backup: {e}")
        return jsonify({'error': str(e)}), 500
