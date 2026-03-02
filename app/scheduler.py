import logging
import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.job import Job
from .backup_manager import BackupManager
from .docker_manager import DockerManager
from .config import settings

logger = logging.getLogger(__name__)


class BackupScheduler:
    """Manages scheduled backup operations using APScheduler."""

    _instance = None

    def __new__(cls):
        """Singleton pattern to ensure only one scheduler instance."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        """Initialize the backup scheduler."""
        if self._initialized:
            return

        self.scheduler = BackgroundScheduler(timezone=settings.scheduler_timezone)
        self.scheduler.configure(max_workers=settings.scheduler_max_workers)
        self.backup_manager = BackupManager()
        self.docker_manager = DockerManager()

        # In-memory storage for job metadata (for persistence, use database)
        self.job_metadata: Dict[str, Dict[str, Any]] = {}

        self._initialized = True
        logger.info("BackupScheduler initialized")

    def start(self) -> bool:
        """Start the scheduler."""
        try:
            if not self.scheduler.running:
                self.scheduler.start()
                logger.info("Scheduler started successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to start scheduler: {e}")
            return False

    def stop(self) -> bool:
        """Stop the scheduler."""
        try:
            if self.scheduler.running:
                self.scheduler.shutdown()
                logger.info("Scheduler stopped successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to stop scheduler: {e}")
            return False

    def add_job(
        self,
        container_id: str,
        cron_expression: str,
        include_volumes: bool = True,
        include_config: bool = True,
        include_database: bool = True,
        include_image: bool = False,
    ) -> Optional[str]:
        """Add a scheduled backup job.

        Args:
            container_id: Docker container ID
            cron_expression: Cron expression (e.g., '0 2 * * *' for 2:00 AM daily)
            include_volumes: Include container volumes
            include_config: Include container configuration
            include_database: Include database dumps
            include_image: Include container image

        Returns:
            Job ID if successful, None otherwise.
        """
        try:
            # Get container info to validate it exists
            container = self.docker_manager.get_container_info(container_id)
            if not container:
                logger.error(f"Container {container_id} not found")
                return None

            # Create unique job ID
            job_id = f"backup_{container_id}_{uuid.uuid4().hex[:8]}"

            # Add job to scheduler
            job = self.scheduler.add_job(
                func=self._execute_backup_job,
                trigger=CronTrigger.from_crontab(cron_expression),
                id=job_id,
                args=(
                    container_id,
                    include_volumes,
                    include_config,
                    include_database,
                    include_image,
                ),
                replace_existing=False,
                max_instances=1,
                misfire_grace_time=300,  # Allow 5 minutes grace period
            )

            # Store metadata
            self.job_metadata[job_id] = {
                "container_id": container_id,
                "container_name": container.name,
                "cron_expression": cron_expression,
                "created_at": datetime.now().isoformat(),
                "last_run_time": None,
                "next_run_time": job.next_run_time,
            }

            logger.info(f"Scheduled backup job created: {job_id} for container {container.name}")
            return job_id

        except Exception as e:
            logger.error(f"Failed to add scheduled job for container {container_id}: {e}")
            return None

    def remove_job(self, job_id: str) -> bool:
        """Remove a scheduled job."""
        try:
            self.scheduler.remove_job(job_id)
            if job_id in self.job_metadata:
                del self.job_metadata[job_id]
            logger.info(f"Scheduled job removed: {job_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to remove job {job_id}: {e}")
            return False

    def list_jobs(self) -> List[Dict[str, Any]]:
        """List all scheduled backup jobs."""
        try:
            jobs = []
            for job in self.scheduler.get_jobs():
                if job.id.startswith("backup_"):
                    metadata = self.job_metadata.get(job.id, {})
                    jobs.append({
                        "job_id": job.id,
                        "container_id": job.args[0] if job.args else None,
                        "container_name": metadata.get("container_name"),
                        "cron_expression": metadata.get("cron_expression"),
                        "next_run_time": job.next_run_time.isoformat() if job.next_run_time else None,
                        "last_run_time": metadata.get("last_run_time"),
                        "created_at": metadata.get("created_at"),
                    })
            return jobs
        except Exception as e:
            logger.error(f"Failed to list jobs: {e}")
            return []

    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get details about a specific job."""
        try:
            job = self.scheduler.get_job(job_id)
            if not job:
                return None

            metadata = self.job_metadata.get(job_id, {})
            return {
                "job_id": job.id,
                "container_id": job.args[0] if job.args else None,
                "container_name": metadata.get("container_name"),
                "cron_expression": metadata.get("cron_expression"),
                "next_run_time": job.next_run_time.isoformat() if job.next_run_time else None,
                "last_run_time": metadata.get("last_run_time"),
                "created_at": metadata.get("created_at"),
            }
        except Exception as e:
            logger.error(f"Failed to get job {job_id}: {e}")
            return None

    def trigger_job(self, job_id: str) -> bool:
        """Manually trigger a scheduled job."""
        try:
            job = self.scheduler.get_job(job_id)
            if not job:
                logger.error(f"Job {job_id} not found")
                return False

            # Execute the job immediately
            job.func(*job.args, **job.kwargs)
            logger.info(f"Job {job_id} triggered manually")
            return True
        except Exception as e:
            logger.error(f"Failed to trigger job {job_id}: {e}")
            return False

    def reschedule_job(self, job_id: str, cron_expression: str) -> bool:
        """Reschedule an existing job."""
        try:
            job = self.scheduler.get_job(job_id)
            if not job:
                logger.error(f"Job {job_id} not found")
                return False

            self.scheduler.reschedule_job(job_id, trigger=CronTrigger.from_crontab(cron_expression))

            # Update metadata
            if job_id in self.job_metadata:
                self.job_metadata[job_id]["cron_expression"] = cron_expression

            logger.info(f"Job {job_id} rescheduled with cron expression: {cron_expression}")
            return True
        except Exception as e:
            logger.error(f"Failed to reschedule job {job_id}: {e}")
            return False

    def is_running(self) -> bool:
        """Check if scheduler is running."""
        return self.scheduler.running

    def get_scheduler_info(self) -> Dict[str, Any]:
        """Get information about the scheduler."""
        jobs = self.list_jobs()
        return {
            "running": self.scheduler.running,
            "timezone": settings.scheduler_timezone,
            "max_workers": settings.scheduler_max_workers,
            "total_jobs": len(jobs),
            "jobs": jobs,
        }

    # Private methods

    def _execute_backup_job(
        self,
        container_id: str,
        include_volumes: bool,
        include_config: bool,
        include_database: bool,
        include_image: bool,
    ) -> Optional[str]:
        """Execute a scheduled backup job."""
        try:
            logger.info(f"Executing scheduled backup for container {container_id}")

            backup_filename = self.backup_manager.create_backup(
                container_id=container_id,
                include_volumes=include_volumes,
                include_config=include_config,
                include_database=include_database,
                include_image=include_image,
            )

            if backup_filename:
                # Update last run time in metadata
                for job_id, metadata in self.job_metadata.items():
                    if metadata.get("container_id") == container_id:
                        metadata["last_run_time"] = datetime.now().isoformat()

                logger.info(f"Scheduled backup completed: {backup_filename}")
                return backup_filename
            else:
                logger.error(f"Scheduled backup failed for container {container_id}")
                return None

        except Exception as e:
            logger.error(f"Error executing scheduled backup for {container_id}: {e}")
            return None
