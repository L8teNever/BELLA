import os
from pathlib import Path
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application configuration settings."""

    # Application
    app_name: str = "Docker Container Backup Manager"
    app_version: str = "1.0.0"
    debug: bool = False

    # Paths
    base_dir: Path = Path(__file__).parent.parent
    backup_dir: Path = base_dir / "backups"
    logs_dir: Path = base_dir / "logs"

    # Docker
    docker_socket: str = "unix:///var/run/docker.sock"
    docker_timeout: int = 30

    # Backup settings
    max_backup_size: int = 10 * 1024 * 1024 * 1024  # 10GB
    backup_retention_days: int = 30
    compress_level: int = 6  # 0-9, 6 is default

    # Scheduler
    scheduler_timezone: str = "UTC"
    scheduler_max_workers: int = 4

    # Upload settings
    max_upload_size: int = 5 * 1024 * 1024 * 1024  # 5GB
    allowed_backup_extensions: list = [".zip"]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

    def ensure_directories(self):
        """Ensure required directories exist."""
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        self.logs_dir.mkdir(parents=True, exist_ok=True)


settings = Settings()
settings.ensure_directories()
