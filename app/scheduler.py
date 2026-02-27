"""
Backup Scheduler
APScheduler for automatic backups at 1:00 AM
"""

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import logging

logger = logging.getLogger(__name__)


class BackupScheduler:
    """Manages scheduled backup jobs"""

    def __init__(self, backup_engine, backup_time='01:00'):
        """
        Initialize scheduler

        Args:
            backup_engine: BackupEngine instance
            backup_time: Time to run backups in format 'HH:MM' (default '01:00')
        """
        self.backup_engine = backup_engine
        self.scheduler = BackgroundScheduler()
        self.backup_time = backup_time
        self._parse_backup_time(backup_time)

    def _parse_backup_time(self, time_str):
        """
        Parse backup time string and set hour/minute

        Args:
            time_str: Time string in format 'HH:MM'
        """
        try:
            parts = time_str.split(':')
            self.backup_hour = int(parts[0])
            self.backup_minute = int(parts[1])
            logger.info(f"Backup time set to {self.backup_hour:02d}:{self.backup_minute:02d}")
        except (ValueError, IndexError):
            logger.warning(f"Invalid backup time format: {time_str}, using default 01:00")
            self.backup_hour = 1
            self.backup_minute = 0

    def start(self):
        """
        Start the scheduler with cron job for daily backups

        Job runs at configured time (default 1:00 AM) every day
        """
        try:
            # Add daily backup job
            self.scheduler.add_job(
                func=self._run_backup_job,
                trigger=CronTrigger(
                    hour=self.backup_hour,
                    minute=self.backup_minute
                ),
                id='daily_backup',
                name='Daily Backup Job',
                replace_existing=True
            )

            # Start scheduler in background
            self.scheduler.start()
            logger.info(f"Scheduler started. Daily backups scheduled at {self.backup_hour:02d}:{self.backup_minute:02d}")

        except Exception as e:
            logger.error(f"Failed to start scheduler: {e}")
            raise

    def stop(self):
        """Stop the scheduler"""
        try:
            self.scheduler.shutdown(wait=True)
            logger.info("Scheduler stopped")
        except Exception as e:
            logger.error(f"Error stopping scheduler: {e}")

    def _run_backup_job(self):
        """
        Internal method called by scheduler
        Wraps backup engine call with logging
        """
        logger.info("=== SCHEDULED BACKUP JOB STARTED ===")
        try:
            results = self.backup_engine.run_scheduled_backups()
            logger.info(
                f"Scheduled backup job completed: "
                f"Total={results['total']}, "
                f"Succeeded={results['succeeded']}, "
                f"Failed={results['failed']}"
            )
        except Exception as e:
            logger.error(f"Scheduled backup job failed: {e}")
        logger.info("=== SCHEDULED BACKUP JOB FINISHED ===")

    def trigger_backup_now(self):
        """
        Manually trigger a backup immediately (for testing)

        Returns:
            Backup results dictionary
        """
        logger.info("Manual backup triggered")
        return self.backup_engine.run_scheduled_backups()

    def get_job_status(self):
        """
        Get status of scheduled jobs

        Returns:
            Dictionary with job information
        """
        try:
            jobs = self.scheduler.get_jobs()
            status = {
                'running': self.scheduler.running,
                'job_count': len(jobs),
                'jobs': []
            }

            for job in jobs:
                status['jobs'].append({
                    'id': job.id,
                    'name': job.name,
                    'next_run_time': str(job.next_run_time),
                    'trigger': str(job.trigger)
                })

            return status
        except Exception as e:
            logger.error(f"Error getting job status: {e}")
            return {'running': False, 'error': str(e)}

    def pause_scheduler(self):
        """Pause the scheduler (jobs won't run)"""
        try:
            if self.scheduler.running:
                self.scheduler.pause()
                logger.info("Scheduler paused")
                return True
            return False
        except Exception as e:
            logger.error(f"Error pausing scheduler: {e}")
            return False

    def resume_scheduler(self):
        """Resume the scheduler"""
        try:
            if self.scheduler.running:
                self.scheduler.resume()
                logger.info("Scheduler resumed")
                return True
            return False
        except Exception as e:
            logger.error(f"Error resuming scheduler: {e}")
            return False
