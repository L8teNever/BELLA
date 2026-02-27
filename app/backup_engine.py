"""
Backup Engine
Core backup logic: stop container, archive volumes, restart container
"""

import os
import tarfile
import logging
from datetime import datetime
from pathlib import Path
from app import db
from app.models import Container, BackupHistory

logger = logging.getLogger(__name__)


class BackupEngine:
    """Handles backup operations for Docker containers"""

    def __init__(self, docker_manager, config):
        """
        Initialize backup engine

        Args:
            docker_manager: DockerManager instance
            config: Flask configuration object
        """
        self.docker_manager = docker_manager
        self.config = config
        self.backup_dir = config.BACKUP_DIR
        self.stop_timeout = config.CONTAINER_STOP_TIMEOUT

        # Create backup directory if it doesn't exist
        Path(self.backup_dir).mkdir(parents=True, exist_ok=True)
        logger.info(f"Backup engine initialized with backup directory: {self.backup_dir}")

    def run_scheduled_backups(self):
        """
        Run backups for all containers with backup_enabled=True
        Called by scheduler at scheduled time (1:00 AM)

        Returns:
            Dictionary with backup results
        """
        logger.info("Starting scheduled backup run")

        results = {
            'total': 0,
            'succeeded': 0,
            'failed': 0,
            'containers': []
        }

        try:
            # Get all containers with backup enabled
            containers = Container.query.filter_by(backup_enabled=True).all()
            results['total'] = len(containers)

            logger.info(f"Found {len(containers)} containers to backup")

            for container in containers:
                try:
                    success = self.backup_container(container.id, container.container_id, container.name)
                    if success:
                        results['succeeded'] += 1
                        results['containers'].append({
                            'name': container.name,
                            'status': 'success'
                        })
                    else:
                        results['failed'] += 1
                        results['containers'].append({
                            'name': container.name,
                            'status': 'failed'
                        })
                except Exception as e:
                    logger.error(f"Unexpected error backing up container {container.name}: {e}")
                    results['failed'] += 1
                    results['containers'].append({
                        'name': container.name,
                        'status': 'error'
                    })

            logger.info(f"Scheduled backup run completed: {results['succeeded']}/{results['total']} succeeded")
            return results

        except Exception as e:
            logger.error(f"Scheduled backup run failed: {e}")
            return results

    def backup_container(self, db_container_id, docker_container_id, container_name):
        """
        Backup a single container

        Procedure:
        1. Check if container exists and get volumes
        2. Create backup history entry
        3. Stop container (gracefully with timeout)
        4. Backup each volume as tar.gz
        5. Start container (even if backup failed)
        6. Update backup history

        Args:
            db_container_id: Database container ID
            docker_container_id: Docker container ID
            container_name: Container name (for naming backups)

        Returns:
            True if successful, False otherwise
        """
        logger.info(f"Starting backup for container: {container_name}")

        backup_entry = None
        volumes = []
        backup_files = []

        try:
            # Get volumes for this container
            volumes = self.docker_manager.get_container_volumes(docker_container_id)
            if not volumes:
                logger.warning(f"Container {container_name} has no volumes to backup")
                return self._record_backup_result(db_container_id, 'success', None, None, "No volumes to backup")

            logger.debug(f"Container {container_name} has {len(volumes)} volumes")

            # Create backup history entry
            backup_entry = BackupHistory(
                container_id=db_container_id,
                status='in_progress',
                start_time=datetime.utcnow()
            )
            db.session.add(backup_entry)
            db.session.commit()
            logger.debug(f"Created backup history entry: {backup_entry.id}")

            # Stop container
            logger.info(f"Stopping container {container_name}")
            stop_result = self.docker_manager.stop_container(docker_container_id, timeout=self.stop_timeout)
            if not stop_result:
                logger.warning(f"Failed to stop container {container_name}")

            # Backup volumes
            for volume_info in volumes:
                try:
                    backup_file = self._backup_volume(volume_info, container_name)
                    if backup_file:
                        backup_files.append(backup_file)
                        logger.info(f"Successfully backed up volume: {backup_file}")
                except Exception as e:
                    logger.error(f"Error backing up volume {volume_info.get('Name', 'unknown')}: {e}")

            if not backup_files:
                raise Exception("No volumes were successfully backed up")

            # Update backup entry
            backup_entry.status = 'success'
            backup_entry.end_time = datetime.utcnow()
            backup_entry.backup_path = ', '.join(backup_files)  # Store all backup paths
            total_size = sum(os.path.getsize(f) for f in backup_files if os.path.exists(f))
            backup_entry.file_size = total_size
            db.session.commit()

            logger.info(f"Backup completed successfully for {container_name}")
            return True

        except Exception as e:
            logger.error(f"Backup failed for container {container_name}: {e}")

            # Record failure
            if backup_entry:
                backup_entry.status = 'failed'
                backup_entry.end_time = datetime.utcnow()
                backup_entry.error_message = str(e)
                db.session.commit()
            else:
                self._record_backup_result(db_container_id, 'failed', None, None, str(e))

            return False

        finally:
            # Always restart container, even if backup failed
            logger.info(f"Restarting container {container_name}")
            try:
                start_result = self.docker_manager.start_container(docker_container_id)
                if not start_result:
                    logger.error(f"Failed to restart container {container_name}")
                else:
                    logger.info(f"Container {container_name} restarted successfully")
            except Exception as e:
                logger.error(f"Error restarting container {container_name}: {e}")

    def _backup_volume(self, volume_info, container_name):
        """
        Backup a single volume as tar.gz archive

        Args:
            volume_info: Volume mount information dict
            container_name: Container name (for naming)

        Returns:
            Path to backup file or None if failed
        """
        try:
            # Extract volume information
            volume_name = volume_info.get('Name', volume_info.get('Source', 'unknown'))
            volume_type = volume_info.get('Type', 'unknown')

            logger.debug(f"Backing up volume: {volume_name} (type: {volume_type})")

            # Create backup filename
            timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
            safe_volume_name = volume_name.replace('/', '_').replace('\\', '_')
            backup_filename = f"{container_name}_{safe_volume_name}_{timestamp}.tar.gz"
            backup_path = os.path.join(self.backup_dir, backup_filename)

            # Get source path to archive
            source_path = volume_info.get('Source')
            if not source_path:
                logger.warning(f"Could not determine source path for volume {volume_name}")
                return None

            logger.debug(f"Creating tar.gz archive: {backup_path} from {source_path}")

            # Create tar.gz archive
            with tarfile.open(backup_path, 'w:gz') as tar:
                tar.add(source_path, arcname=os.path.basename(source_path))

            file_size = os.path.getsize(backup_path)
            logger.info(f"Volume backup created: {backup_filename} ({file_size} bytes)")

            return backup_path

        except Exception as e:
            logger.error(f"Error backing up volume {volume_info.get('Name', 'unknown')}: {e}")
            return None

    def _record_backup_result(self, db_container_id, status, backup_path, file_size, error_message=None):
        """
        Record backup result in database

        Args:
            db_container_id: Database container ID
            status: Backup status (success, failed)
            backup_path: Path to backup file
            file_size: Size of backup in bytes
            error_message: Error message if failed

        Returns:
            True if recorded, False otherwise
        """
        try:
            backup_entry = BackupHistory(
                container_id=db_container_id,
                status=status,
                backup_path=backup_path,
                file_size=file_size,
                error_message=error_message,
                start_time=datetime.utcnow(),
                end_time=datetime.utcnow()
            )
            db.session.add(backup_entry)
            db.session.commit()
            logger.debug(f"Recorded backup result: {status}")
            return True
        except Exception as e:
            logger.error(f"Error recording backup result: {e}")
            return False

    def get_backup_history(self, container_id=None, limit=50):
        """
        Get backup history

        Args:
            container_id: Optional container ID to filter
            limit: Maximum number of records

        Returns:
            List of BackupHistory records
        """
        try:
            query = BackupHistory.query
            if container_id:
                query = query.filter_by(container_id=container_id)

            history = query.order_by(BackupHistory.created_at.desc()).limit(limit).all()
            return history
        except Exception as e:
            logger.error(f"Error retrieving backup history: {e}")
            return []

    def cleanup_old_backups(self, retention_days=30):
        """
        Delete old backups beyond retention period

        Args:
            retention_days: Keep backups for this many days

        Returns:
            Number of backups deleted
        """
        from datetime import timedelta

        deleted_count = 0

        try:
            cutoff_date = datetime.utcnow() - timedelta(days=retention_days)
            old_backups = BackupHistory.query.filter(
                BackupHistory.created_at < cutoff_date,
                BackupHistory.status == 'success'
            ).all()

            logger.info(f"Found {len(old_backups)} backups older than {retention_days} days")

            for backup in old_backups:
                try:
                    if backup.backup_path and os.path.exists(backup.backup_path):
                        os.remove(backup.backup_path)
                        logger.debug(f"Deleted backup file: {backup.backup_path}")

                    db.session.delete(backup)
                    deleted_count += 1
                except Exception as e:
                    logger.error(f"Error deleting backup {backup.id}: {e}")

            db.session.commit()
            logger.info(f"Deleted {deleted_count} old backups")
            return deleted_count

        except Exception as e:
            logger.error(f"Error cleaning up old backups: {e}")
            return deleted_count
