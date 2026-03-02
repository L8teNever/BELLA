import logging
import zipfile
import json
import hashlib
import shutil
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from .models import BackupInfo, BackupMetadata, BackupRequest
from .config import settings
from .docker_manager import DockerManager

logger = logging.getLogger(__name__)


class BackupManager:
    """Manages backup operations for Docker containers."""

    def __init__(self):
        """Initialize backup manager."""
        self.docker_manager = DockerManager()
        self.backup_dir = settings.backup_dir
        self.backup_dir.mkdir(parents=True, exist_ok=True)

    def create_backup(
        self,
        container_id: str,
        include_volumes: bool = True,
        include_config: bool = True,
        include_database: bool = True,
        include_image: bool = False,
    ) -> Optional[str]:
        """Create a backup of a Docker container.

        Returns:
            Backup filename if successful, None otherwise.
        """
        try:
            # Get container info
            container = self.docker_manager.get_container_info(container_id)
            if not container:
                logger.error(f"Container {container_id} not found")
                return None

            # Create temporary backup directory
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = f"backup_{container.name}_{timestamp}"
            temp_backup_dir = self.backup_dir / f".{backup_name}"
            temp_backup_dir.mkdir(parents=True, exist_ok=True)

            logger.info(f"Starting backup for container {container.name} ({container.id})")

            includes = []

            # Export volumes
            if include_volumes:
                if self.docker_manager.export_container_volumes(container_id, temp_backup_dir):
                    includes.append("volumes")
                    logger.info(f"Volumes exported for {container.name}")

            # Export configuration
            if include_config:
                if self.docker_manager.export_container_config(container_id, temp_backup_dir):
                    includes.append("config")
                    logger.info(f"Config exported for {container.name}")

            # Export database
            if include_database:
                if self.docker_manager.export_database(container_id, temp_backup_dir):
                    includes.append("database")
                    logger.info(f"Database exported for {container.name}")

            # Save image
            if include_image:
                if self.docker_manager.save_container_image(container_id, temp_backup_dir):
                    includes.append("image")
                    logger.info(f"Image saved for {container.name}")

            # Create metadata file
            metadata = BackupMetadata(
                container_id=container.id,
                container_name=container.name,
                image=container.image,
                created_at=datetime.now(),
                includes=includes,
                docker_inspect={
                    "id": container.id,
                    "name": container.name,
                    "image": container.image,
                    "status": container.status,
                },
            )

            metadata_path = temp_backup_dir / "metadata.json"
            with open(metadata_path, "w") as f:
                json.dump(json.loads(metadata.model_dump_json()), f, indent=2, default=str)

            # Create ZIP archive
            zip_filename = f"{backup_name}.zip"
            zip_path = self.backup_dir / zip_filename

            with zipfile.ZipFile(
                zip_path, "w", zipfile.ZIP_DEFLATED, compresslevel=settings.compress_level
            ) as zipf:
                for file_path in temp_backup_dir.rglob("*"):
                    if file_path.is_file():
                        arcname = file_path.relative_to(temp_backup_dir)
                        zipf.write(file_path, arcname)

            # Calculate checksum
            checksum = self._calculate_checksum(zip_path)

            # Update metadata with checksum
            with zipfile.ZipFile(zip_path, "a") as zipf:
                metadata.checksum = checksum
                metadata_json = json.loads(metadata.model_dump_json(default=str))
                zipf.writestr("metadata.json", json.dumps(metadata_json, indent=2))

            # Clean up temporary directory
            shutil.rmtree(temp_backup_dir, ignore_errors=True)

            logger.info(f"Backup created successfully: {zip_filename} (Checksum: {checksum})")
            return zip_filename

        except Exception as e:
            logger.error(f"Failed to create backup for container {container_id}: {e}")
            # Clean up on error
            if temp_backup_dir.exists():
                shutil.rmtree(temp_backup_dir, ignore_errors=True)
            return None

    def list_backups(self) -> List[BackupInfo]:
        """List all available backups."""
        backups = []

        try:
            for backup_file in self.backup_dir.glob("backup_*.zip"):
                try:
                    info = self._get_backup_info(backup_file)
                    if info:
                        backups.append(info)
                except Exception as e:
                    logger.warning(f"Failed to read backup {backup_file}: {e}")

            # Sort by creation time (newest first)
            backups.sort(key=lambda x: x.created_at, reverse=True)
            return backups
        except Exception as e:
            logger.error(f"Failed to list backups: {e}")
            return []

    def restore_backup(
        self, backup_filename: str, target_path: str, restore_volumes: bool = True
    ) -> bool:
        """Restore a backup to a target path."""
        try:
            backup_path = self.backup_dir / backup_filename

            if not backup_path.exists():
                logger.error(f"Backup file not found: {backup_filename}")
                return False

            # Validate path to prevent directory traversal
            target_path = Path(target_path).resolve()
            if not str(target_path).startswith(str(Path(target_path.root).resolve())):
                logger.error(f"Invalid target path: {target_path}")
                return False

            target_path.mkdir(parents=True, exist_ok=True)

            logger.info(f"Starting restore of {backup_filename} to {target_path}")

            with zipfile.ZipFile(backup_path, "r") as zipf:
                # Extract to temporary directory first
                temp_dir = self.backup_dir / f".restore_{backup_filename[:-4]}"
                zipf.extractall(temp_dir)

                # Read metadata
                metadata_path = temp_dir / "metadata.json"
                metadata = None
                if metadata_path.exists():
                    with open(metadata_path, "r") as f:
                        metadata = json.load(f)

                # Restore volumes if requested
                if restore_volumes and (temp_dir / "volumes").exists():
                    self._restore_volumes(temp_dir / "volumes", target_path)

                # Copy entire extracted content to target
                for item in temp_dir.iterdir():
                    if item.name != "metadata.json":
                        target_item = target_path / item.name
                        if item.is_dir():
                            shutil.copytree(item, target_item, dirs_exist_ok=True)
                        else:
                            shutil.copy2(item, target_item)

                # Clean up temporary directory
                shutil.rmtree(temp_dir, ignore_errors=True)

            logger.info(f"Backup {backup_filename} restored successfully to {target_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to restore backup {backup_filename}: {e}")
            return False

    def delete_backup(self, backup_filename: str) -> bool:
        """Delete a backup file."""
        try:
            backup_path = self.backup_dir / backup_filename

            if not backup_path.exists():
                logger.warning(f"Backup file not found: {backup_filename}")
                return False

            backup_path.unlink()
            logger.info(f"Backup deleted: {backup_filename}")
            return True

        except Exception as e:
            logger.error(f"Failed to delete backup {backup_filename}: {e}")
            return False

    def cleanup_old_backups(self, retention_days: Optional[int] = None) -> int:
        """Delete backups older than retention period."""
        if retention_days is None:
            retention_days = settings.backup_retention_days

        deleted_count = 0
        cutoff_date = datetime.now() - timedelta(days=retention_days)

        try:
            for backup_file in self.backup_dir.glob("backup_*.zip"):
                file_time = datetime.fromtimestamp(backup_file.stat().st_mtime)

                if file_time < cutoff_date:
                    try:
                        backup_file.unlink()
                        deleted_count += 1
                        logger.info(f"Deleted old backup: {backup_file.name}")
                    except Exception as e:
                        logger.warning(f"Failed to delete old backup {backup_file.name}: {e}")

            if deleted_count > 0:
                logger.info(f"Cleanup completed: {deleted_count} backups deleted")

            return deleted_count
        except Exception as e:
            logger.error(f"Error during backup cleanup: {e}")
            return 0

    def validate_backup(self, backup_filename: str) -> bool:
        """Validate backup integrity."""
        try:
            backup_path = self.backup_dir / backup_filename

            if not backup_path.exists():
                logger.warning(f"Backup file not found: {backup_filename}")
                return False

            # Test ZIP file integrity
            with zipfile.ZipFile(backup_path, "r") as zipf:
                bad_file = zipf.testzip()
                if bad_file:
                    logger.error(f"Corrupted file in backup: {bad_file}")
                    return False

            logger.info(f"Backup validation passed: {backup_filename}")
            return True

        except Exception as e:
            logger.error(f"Backup validation failed for {backup_filename}: {e}")
            return False

    # Private helper methods

    def _get_backup_info(self, backup_path: Path) -> Optional[BackupInfo]:
        """Extract backup information from a backup file."""
        try:
            with zipfile.ZipFile(backup_path, "r") as zipf:
                # Read metadata
                with zipf.open("metadata.json") as f:
                    metadata_dict = json.load(f)
                    metadata = BackupMetadata(**metadata_dict)

                return BackupInfo(
                    filename=backup_path.name,
                    container_id=metadata.container_id,
                    container_name=metadata.container_name,
                    size=backup_path.stat().st_size,
                    created_at=metadata.created_at,
                    includes=metadata.includes,
                    checksum=metadata.checksum,
                )
        except Exception as e:
            logger.warning(f"Failed to read backup info from {backup_path}: {e}")
            return None

    def _calculate_checksum(self, file_path: Path) -> str:
        """Calculate SHA256 checksum of a file."""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()

    def _restore_volumes(self, volumes_dir: Path, target_path: Path) -> bool:
        """Restore volumes from backup."""
        try:
            for tar_file in volumes_dir.glob("*.tar"):
                try:
                    import tarfile

                    with tarfile.open(tar_file, "r") as tar:
                        tar.extractall(target_path)
                    logger.info(f"Restored volume: {tar_file.name}")
                except Exception as e:
                    logger.warning(f"Failed to extract volume {tar_file.name}: {e}")

            return True
        except Exception as e:
            logger.error(f"Error restoring volumes: {e}")
            return False

    def get_backup_size(self) -> int:
        """Get total size of all backups in bytes."""
        total_size = 0
        for backup_file in self.backup_dir.glob("backup_*.zip"):
            total_size += backup_file.stat().st_size
        return total_size

    def get_backup_stats(self) -> Dict[str, Any]:
        """Get backup statistics."""
        backups = self.list_backups()
        total_size = self.get_backup_size()

        return {
            "total_backups": len(backups),
            "total_size_bytes": total_size,
            "total_size_gb": round(total_size / (1024**3), 2),
            "oldest_backup": backups[-1].created_at if backups else None,
            "newest_backup": backups[0].created_at if backups else None,
        }
