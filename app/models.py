from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class BackupType(str, Enum):
    """Backup type enumeration."""
    VOLUMES = "volumes"
    CONFIG = "config"
    DATABASE = "database"
    IMAGE = "image"


class ContainerStatus(str, Enum):
    """Container status enumeration."""
    RUNNING = "running"
    EXITED = "exited"
    PAUSED = "paused"
    RESTARTING = "restarting"
    REMOVING = "removing"
    DEAD = "dead"


class Container(BaseModel):
    """Docker container model."""
    id: str = Field(..., description="Container ID")
    name: str = Field(..., description="Container name")
    image: str = Field(..., description="Image name")
    status: str = Field(..., description="Container status")
    state: str = Field(..., description="Container state")
    ports: Dict[str, Any] = Field(default_factory=dict, description="Port mappings")
    volumes: List[str] = Field(default_factory=list, description="Volume paths")
    created_at: str = Field(..., description="Creation timestamp")
    started_at: Optional[str] = Field(None, description="Start timestamp")

    class Config:
        json_schema_extra = {
            "example": {
                "id": "abc123def456",
                "name": "my-container",
                "image": "ubuntu:latest",
                "status": "running",
                "state": "running",
                "ports": {"80/tcp": [{"HostIp": "0.0.0.0", "HostPort": "8000"}]},
                "volumes": ["/data", "/var/lib/mysql"],
                "created_at": "2024-01-01T10:00:00Z",
                "started_at": "2024-01-01T10:01:00Z"
            }
        }


class BackupInfo(BaseModel):
    """Backup information model."""
    filename: str = Field(..., description="Backup filename")
    container_id: str = Field(..., description="Container ID")
    container_name: str = Field(..., description="Container name")
    size: int = Field(..., description="Backup size in bytes")
    created_at: datetime = Field(..., description="Backup creation time")
    includes: List[str] = Field(default_factory=list, description="What is included in backup")
    checksum: Optional[str] = Field(None, description="SHA256 checksum")


class BackupRequest(BaseModel):
    """Backup creation request model."""
    container_id: str = Field(..., description="Container ID to backup")
    include_volumes: bool = Field(default=True, description="Include container volumes")
    include_config: bool = Field(default=True, description="Include container configuration")
    include_database: bool = Field(default=True, description="Include database dumps")
    include_image: bool = Field(default=False, description="Include container image")


class RestoreRequest(BaseModel):
    """Backup restore request model."""
    backup_filename: str = Field(..., description="Backup filename to restore")
    target_path: str = Field(..., description="Target path for restoration")
    restore_volumes: bool = Field(default=True, description="Restore volumes")
    restore_config: bool = Field(default=False, description="Restore configuration")
    restore_database: bool = Field(default=False, description="Restore database")


class ScheduleRequest(BaseModel):
    """Backup schedule creation request model."""
    container_id: str = Field(..., description="Container ID to backup")
    cron_expression: str = Field(..., description="Cron expression (e.g., '0 2 * * *' for 2:00 AM daily)")
    include_volumes: bool = Field(default=True)
    include_config: bool = Field(default=True)
    include_database: bool = Field(default=True)
    include_image: bool = Field(default=False)


class BackupSchedule(BaseModel):
    """Backup schedule model."""
    job_id: str = Field(..., description="Job ID")
    container_id: str = Field(..., description="Container ID")
    container_name: str = Field(..., description="Container name")
    cron_expression: str = Field(..., description="Cron expression")
    next_run_time: Optional[datetime] = Field(None, description="Next scheduled run time")
    last_run_time: Optional[datetime] = Field(None, description="Last execution time")


class BackupMetadata(BaseModel):
    """Backup metadata model (stored in backup)."""
    version: str = Field(default="1.0", description="Backup format version")
    container_id: str = Field(..., description="Container ID")
    container_name: str = Field(..., description="Container name")
    image: str = Field(..., description="Container image")
    created_at: datetime = Field(..., description="Backup creation time")
    includes: List[str] = Field(..., description="Included components")
    docker_inspect: Optional[Dict[str, Any]] = Field(None, description="Docker inspect output")
    compression: str = Field(default="zip", description="Compression format")


class APIResponse(BaseModel):
    """Generic API response model."""
    success: bool = Field(..., description="Operation success status")
    message: str = Field(..., description="Response message")
    data: Optional[Dict[str, Any] | List[Any]] = Field(None, description="Response data")
    error: Optional[str] = Field(None, description="Error message if failed")


class OperationProgress(BaseModel):
    """Operation progress model for long-running tasks."""
    operation_id: str = Field(..., description="Operation ID")
    operation: str = Field(..., description="Operation type (backup, restore, etc.)")
    progress: int = Field(..., ge=0, le=100, description="Progress percentage")
    status: str = Field(..., description="Current status")
    current_step: Optional[str] = Field(None, description="Current step description")
    total_steps: Optional[int] = Field(None, description="Total number of steps")
    started_at: datetime = Field(..., description="Operation start time")
    estimated_completion: Optional[datetime] = Field(None, description="Estimated completion time")
