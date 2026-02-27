"""
Docker API Manager
Handles all Docker operations: listing containers, stop/start, volume management
"""

import docker
from docker.errors import DockerException, APIError
import logging

logger = logging.getLogger(__name__)


class DockerManager:
    """Wrapper around Docker Python SDK"""

    def __init__(self):
        """Initialize Docker client with graceful degradation"""
        self.client = None
        self.docker_available = False

        try:
            # Try explicit socket path first (more reliable in containers)
            self.client = docker.DockerClient(base_url='unix:///var/run/docker.sock')
            self.docker_available = True
            logger.info("Docker client initialized successfully (via unix socket)")
        except Exception as e:
            logger.warning(f"Docker socket connection failed: {e}")
            logger.info("Attempting TCP fallback...")
            try:
                # Fallback to TCP
                self.client = docker.DockerClient(base_url='tcp://127.0.0.1:2375')
                self.docker_available = True
                logger.info("Docker client initialized via TCP")
            except Exception as e2:
                logger.warning(f"TCP fallback also failed: {e2}")
                logger.warning("=" * 70)
                logger.warning("Docker is NOT available - Running in degraded mode!")
                logger.warning("Bella will start but Docker features are disabled.")
                logger.warning("=" * 70)
                self.docker_available = False

    def get_all_containers(self):
        """
        Get all Docker containers (running and stopped)

        Returns:
            List of container objects
        """
        if not self.docker_available or not self.client:
            logger.warning("Docker not available - returning empty container list")
            return []

        try:
            containers = self.client.containers.list(all=True)
            logger.debug(f"Retrieved {len(containers)} containers")
            return containers
        except Exception as e:
            logger.error(f"Error retrieving containers: {e}")
            return []

    def get_container_details(self, container_id):
        """
        Get detailed information about a specific container

        Args:
            container_id: Container ID or name

        Returns:
            Container object or None if not found
        """
        try:
            container = self.client.containers.get(container_id)
            return container
        except docker.errors.NotFound:
            logger.warning(f"Container not found: {container_id}")
            return None
        except APIError as e:
            logger.error(f"Error retrieving container details: {e}")
            return None

    def get_container_volumes(self, container_id):
        """
        Get volume mount information for a container

        Args:
            container_id: Container ID or name

        Returns:
            List of volume mount information or empty list
        """
        try:
            container = self.get_container_details(container_id)
            if not container:
                return []

            mounts = container.attrs.get('Mounts', [])
            logger.debug(f"Retrieved {len(mounts)} mounts for container {container_id}")
            return mounts
        except Exception as e:
            logger.error(f"Error retrieving volumes for container {container_id}: {e}")
            return []

    def stop_container(self, container_id, timeout=30):
        """
        Stop a running container gracefully

        Args:
            container_id: Container ID or name
            timeout: Timeout in seconds (default 30)

        Returns:
            True if stopped successfully, False otherwise
        """
        try:
            container = self.get_container_details(container_id)
            if not container:
                return False

            # Only stop if running
            if container.status == 'running':
                container.stop(timeout=timeout)
                logger.info(f"Container {container_id} stopped successfully")
                return True
            else:
                logger.debug(f"Container {container_id} is not running (status: {container.status})")
                return True
        except APIError as e:
            logger.error(f"Error stopping container {container_id}: {e}")
            return False

    def start_container(self, container_id):
        """
        Start a stopped container

        Args:
            container_id: Container ID or name

        Returns:
            True if started successfully, False otherwise
        """
        try:
            container = self.get_container_details(container_id)
            if not container:
                return False

            # Only start if not running
            if container.status != 'running':
                container.start()
                logger.info(f"Container {container_id} started successfully")
                return True
            else:
                logger.debug(f"Container {container_id} is already running")
                return True
        except APIError as e:
            logger.error(f"Error starting container {container_id}: {e}")
            return False

    def get_container_status(self, container_id):
        """
        Get the current status of a container

        Args:
            container_id: Container ID or name

        Returns:
            Status string ('running', 'exited', 'paused', etc.) or None
        """
        try:
            container = self.get_container_details(container_id)
            if not container:
                return None

            status = container.status
            logger.debug(f"Container {container_id} status: {status}")
            return status
        except Exception as e:
            logger.error(f"Error getting container status: {e}")
            return None

    def is_container_running(self, container_id):
        """
        Check if a container is running

        Args:
            container_id: Container ID or name

        Returns:
            True if running, False otherwise
        """
        status = self.get_container_status(container_id)
        return status == 'running'

    def get_volume_info(self, volume_name):
        """
        Get information about a specific volume

        Args:
            volume_name: Volume name

        Returns:
            Volume object or None
        """
        try:
            volume = self.client.volumes.get(volume_name)
            return volume
        except docker.errors.NotFound:
            logger.warning(f"Volume not found: {volume_name}")
            return None
        except APIError as e:
            logger.error(f"Error retrieving volume info: {e}")
            return None

    def health_check(self):
        """
        Check if Docker connection is healthy

        Returns:
            True if healthy, False otherwise
        """
        try:
            self.client.ping()
            logger.debug("Docker health check passed")
            return True
        except Exception as e:
            logger.error(f"Docker health check failed: {e}")
            return False
