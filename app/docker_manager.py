import docker
import logging
import tarfile
import io
import subprocess
from typing import List, Dict, Any, Optional
from pathlib import Path
from datetime import datetime
from .models import Container
from .config import settings

logger = logging.getLogger(__name__)


class DockerManager:
    """Manages Docker container operations."""

    def __init__(self):
        """Initialize Docker client."""
        try:
            self.client = docker.from_env()
            self.client.ping()
            logger.info("Docker client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Docker client: {e}")
            self.client = None

    def is_connected(self) -> bool:
        """Check if Docker is connected."""
        return self.client is not None

    def list_containers(self, running_only: bool = False) -> List[Container]:
        """List all Docker containers."""
        if not self.is_connected():
            logger.error("Docker client not connected")
            return []

        try:
            containers = self.client.containers.list(all=not running_only)
            result = []

            for container in containers:
                try:
                    result.append(self._container_to_model(container))
                except Exception as e:
                    logger.warning(f"Failed to process container {container.id}: {e}")

            return result
        except Exception as e:
            logger.error(f"Failed to list containers: {e}")
            return []

    def get_container_info(self, container_id: str) -> Optional[Container]:
        """Get detailed information about a specific container."""
        if not self.is_connected():
            return None

        try:
            container = self.client.containers.get(container_id)
            return self._container_to_model(container)
        except Exception as e:
            logger.error(f"Failed to get container info for {container_id}: {e}")
            return None

    def stop_container(self, container_id: str, timeout: int = 10) -> bool:
        """Stop a container."""
        if not self.is_connected():
            return False

        try:
            container = self.client.containers.get(container_id)
            container.stop(timeout=timeout)
            logger.info(f"Container {container_id} stopped successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to stop container {container_id}: {e}")
            return False

    def start_container(self, container_id: str) -> bool:
        """Start a container."""
        if not self.is_connected():
            return False

        try:
            container = self.client.containers.get(container_id)
            container.start()
            logger.info(f"Container {container_id} started successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to start container {container_id}: {e}")
            return False

    def export_container_volumes(self, container_id: str, backup_path: Path) -> bool:
        """Export container volumes to a tar file."""
        if not self.is_connected():
            return False

        try:
            container = self.client.containers.get(container_id)
            volumes_dir = backup_path / "volumes"
            volumes_dir.mkdir(parents=True, exist_ok=True)

            # Get volume information
            container_data = container.attrs
            mounts = container_data.get("Mounts", [])

            if not mounts:
                logger.info(f"No volumes found for container {container_id}")
                return True

            for idx, mount in enumerate(mounts):
                if mount["Type"] == "volume":
                    volume_name = mount.get("Name")
                    if volume_name:
                        try:
                            volume = self.client.volumes.get(volume_name)
                            # Export volume using tar
                            tar_path = volumes_dir / f"{volume_name}.tar"
                            self._export_volume(container_id, mount.get("Destination"), tar_path)
                        except Exception as e:
                            logger.warning(f"Failed to export volume {volume_name}: {e}")
                elif mount["Type"] == "bind":
                    # For bind mounts, copy the source directory
                    source = mount.get("Source")
                    if source and Path(source).exists():
                        try:
                            tar_path = volumes_dir / f"bind_mount_{idx}.tar"
                            self._create_tar_archive(source, tar_path)
                        except Exception as e:
                            logger.warning(f"Failed to export bind mount {source}: {e}")

            logger.info(f"Volumes exported for container {container_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to export volumes for container {container_id}: {e}")
            return False

    def export_container_config(self, container_id: str, backup_path: Path) -> bool:
        """Export container configuration to JSON."""
        if not self.is_connected():
            return False

        try:
            container = self.client.containers.get(container_id)
            config_dir = backup_path / "config"
            config_dir.mkdir(parents=True, exist_ok=True)

            # Save container inspect output
            import json
            inspect_path = config_dir / "container_inspect.json"
            with open(inspect_path, "w") as f:
                json.dump(container.attrs, f, indent=2, default=str)

            logger.info(f"Container config exported for {container_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to export config for container {container_id}: {e}")
            return False

    def export_database(self, container_id: str, backup_path: Path) -> bool:
        """Export database dumps from container."""
        if not self.is_connected():
            return False

        try:
            container = self.client.containers.get(container_id)
            db_dir = backup_path / "database"
            db_dir.mkdir(parents=True, exist_ok=True)

            # Try to detect and dump common databases
            databases_exported = False

            # MySQL/MariaDB
            if self._is_mysql_container(container):
                if self._dump_mysql(container, db_dir):
                    databases_exported = True

            # PostgreSQL
            if self._is_postgresql_container(container):
                if self._dump_postgresql(container, db_dir):
                    databases_exported = True

            # MongoDB
            if self._is_mongodb_container(container):
                if self._dump_mongodb(container, db_dir):
                    databases_exported = True

            if databases_exported:
                logger.info(f"Database dumps created for {container_id}")
            else:
                logger.info(f"No databases detected in container {container_id}")

            return True
        except Exception as e:
            logger.error(f"Failed to export database for container {container_id}: {e}")
            return False

    def save_container_image(self, container_id: str, backup_path: Path) -> bool:
        """Save container image to tar file."""
        if not self.is_connected():
            return False

        try:
            container = self.client.containers.get(container_id)
            image_dir = backup_path / "image"
            image_dir.mkdir(parents=True, exist_ok=True)

            image = container.image
            tar_path = image_dir / f"{image.tags[0].replace('/', '_')}.tar" if image.tags else image_dir / "image.tar"

            # Save image
            image_data = self.client.images.get(image.id).save()
            with open(tar_path, "wb") as f:
                for chunk in image_data:
                    f.write(chunk)

            logger.info(f"Container image saved for {container_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to save image for container {container_id}: {e}")
            return False

    def get_container_logs(self, container_id: str, lines: int = 100) -> str:
        """Get container logs."""
        if not self.is_connected():
            return ""

        try:
            container = self.client.containers.get(container_id)
            logs = container.logs(tail=lines).decode("utf-8")
            return logs
        except Exception as e:
            logger.error(f"Failed to get logs for container {container_id}: {e}")
            return ""

    # Private helper methods

    def _container_to_model(self, container) -> Container:
        """Convert Docker container object to Container model."""
        attrs = container.attrs
        return Container(
            id=container.id[:12],
            name=container.name,
            image=container.image.tags[0] if container.image.tags else container.image.id[:12],
            status=attrs.get("State", {}).get("Status", "unknown"),
            state=attrs.get("State", {}).get("Status", "unknown"),
            ports=attrs.get("NetworkSettings", {}).get("Ports", {}),
            volumes=[m.get("Destination") for m in attrs.get("Mounts", [])],
            created_at=attrs.get("Created", ""),
            started_at=attrs.get("State", {}).get("StartedAt"),
        )

    def _export_volume(self, container_id: str, volume_path: str, output_path: Path) -> bool:
        """Export volume using docker cp and tar."""
        try:
            container = self.client.containers.get(container_id)
            bits, stat = container.get_archive(volume_path)

            with open(output_path, "wb") as f:
                for chunk in bits:
                    f.write(chunk)

            logger.info(f"Volume {volume_path} exported to {output_path}")
            return True
        except Exception as e:
            logger.warning(f"Failed to export volume {volume_path}: {e}")
            return False

    def _create_tar_archive(self, source_path: str, output_path: Path) -> bool:
        """Create tar archive from a directory."""
        try:
            with tarfile.open(output_path, "w") as tar:
                tar.add(source_path, arcname=Path(source_path).name)
            return True
        except Exception as e:
            logger.error(f"Failed to create tar archive: {e}")
            return False

    def _is_mysql_container(self, container) -> bool:
        """Check if container is running MySQL."""
        env = container.attrs.get("Config", {}).get("Env", [])
        image = container.attrs.get("Config", {}).get("Image", "").lower()
        return "mysql" in image or any("MYSQL" in e for e in env)

    def _is_postgresql_container(self, container) -> bool:
        """Check if container is running PostgreSQL."""
        env = container.attrs.get("Config", {}).get("Env", [])
        image = container.attrs.get("Config", {}).get("Image", "").lower()
        return "postgres" in image or any("POSTGRES" in e for e in env)

    def _is_mongodb_container(self, container) -> bool:
        """Check if container is running MongoDB."""
        image = container.attrs.get("Config", {}).get("Image", "").lower()
        return "mongo" in image

    def _dump_mysql(self, container, output_dir: Path) -> bool:
        """Create MySQL dump."""
        try:
            cmd = "mysqldump --all-databases -u root"
            result = container.exec_run(cmd)
            if result.exit_code == 0:
                with open(output_dir / "mysql_dump.sql", "wb") as f:
                    f.write(result.output)
                return True
        except Exception as e:
            logger.warning(f"MySQL dump failed: {e}")
        return False

    def _dump_postgresql(self, container, output_dir: Path) -> bool:
        """Create PostgreSQL dump."""
        try:
            cmd = "pg_dumpall"
            result = container.exec_run(cmd)
            if result.exit_code == 0:
                with open(output_dir / "postgresql_dump.sql", "wb") as f:
                    f.write(result.output)
                return True
        except Exception as e:
            logger.warning(f"PostgreSQL dump failed: {e}")
        return False

    def _dump_mongodb(self, container, output_dir: Path) -> bool:
        """Create MongoDB dump."""
        try:
            cmd = "mongodump --archive"
            result = container.exec_run(cmd)
            if result.exit_code == 0:
                with open(output_dir / "mongodb_dump.archive", "wb") as f:
                    f.write(result.output)
                return True
        except Exception as e:
            logger.warning(f"MongoDB dump failed: {e}")
        return False
