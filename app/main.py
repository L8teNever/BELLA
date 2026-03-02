import logging
import os
from pathlib import Path
from fastapi import FastAPI, File, UploadFile, HTTPException, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.requests import Request
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional

from .config import settings
from .models import (
    Container,
    BackupInfo,
    BackupRequest,
    RestoreRequest,
    ScheduleRequest,
    BackupSchedule,
    APIResponse,
)
from .docker_manager import DockerManager
from .backup_manager import BackupManager
from .scheduler import BackupScheduler

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(settings.logs_dir / "app.log"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    debug=settings.debug,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
static_dir = settings.base_dir / "static"
templates_dir = settings.base_dir / "templates"

if static_dir.exists():
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

# Setup Jinja2 templates
templates = Jinja2Templates(directory=templates_dir)

# Initialize managers
docker_manager = DockerManager()
backup_manager = BackupManager()
scheduler = BackupScheduler()


# ============================================================================
# Startup and shutdown events
# ============================================================================

@app.on_event("startup")
async def startup_event():
    """Initialize on startup."""
    logger.info("Application starting up...")

    # Check Docker connection
    if docker_manager.is_connected():
        logger.info("Docker client connected successfully")
    else:
        logger.warning("Docker client connection failed - some features may not work")

    # Start scheduler
    scheduler.start()
    logger.info("Backup scheduler started")

    # Cleanup old backups
    deleted = backup_manager.cleanup_old_backups()
    if deleted > 0:
        logger.info(f"Cleaned up {deleted} old backups during startup")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    logger.info("Application shutting down...")
    scheduler.stop()
    logger.info("Backup scheduler stopped")


# ============================================================================
# Web Interface Routes
# ============================================================================

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Render main page."""
    try:
        return templates.TemplateResponse(
            "index.html",
            {
                "request": request,
                "app_name": settings.app_name,
                "app_version": settings.app_version,
            },
        )
    except Exception as e:
        logger.error(f"Error rendering index page: {e}")
        raise HTTPException(status_code=500, detail="Failed to render page")


# ============================================================================
# Docker Container API Routes
# ============================================================================

@app.get("/api/containers", response_model=List[Container])
async def list_containers():
    """Get list of all Docker containers."""
    try:
        containers = docker_manager.list_containers()
        return containers
    except Exception as e:
        logger.error(f"Error listing containers: {e}")
        raise HTTPException(status_code=500, detail="Failed to list containers")


@app.get("/api/containers/{container_id}", response_model=Container)
async def get_container(container_id: str):
    """Get details of a specific container."""
    try:
        container = docker_manager.get_container_info(container_id)
        if not container:
            raise HTTPException(status_code=404, detail="Container not found")
        return container
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting container {container_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get container")


@app.get("/api/containers/{container_id}/logs")
async def get_container_logs(container_id: str, lines: int = 100):
    """Get container logs."""
    try:
        logs = docker_manager.get_container_logs(container_id, lines)
        return APIResponse(
            success=True,
            message="Container logs retrieved",
            data={"logs": logs},
        )
    except Exception as e:
        logger.error(f"Error getting logs for {container_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get container logs")


# ============================================================================
# Backup API Routes
# ============================================================================

@app.post("/api/containers/{container_id}/backup")
async def create_backup(container_id: str, request: BackupRequest, background_tasks: BackgroundTasks):
    """Create a backup of a container."""
    try:
        # Run backup in background
        backup_filename = backup_manager.create_backup(
            container_id=container_id,
            include_volumes=request.include_volumes,
            include_config=request.include_config,
            include_database=request.include_database,
            include_image=request.include_image,
        )

        if not backup_filename:
            raise HTTPException(status_code=500, detail="Failed to create backup")

        return APIResponse(
            success=True,
            message="Backup created successfully",
            data={
                "filename": backup_filename,
                "container_id": container_id,
            },
        )
    except Exception as e:
        logger.error(f"Error creating backup for {container_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to create backup")


@app.get("/api/backups", response_model=List[BackupInfo])
async def list_backups():
    """Get list of all backups."""
    try:
        backups = backup_manager.list_backups()
        return backups
    except Exception as e:
        logger.error(f"Error listing backups: {e}")
        raise HTTPException(status_code=500, detail="Failed to list backups")


@app.get("/api/backups/stats")
async def get_backup_stats():
    """Get backup statistics."""
    try:
        stats = backup_manager.get_backup_stats()
        return APIResponse(
            success=True,
            message="Statistics retrieved",
            data=stats,
        )
    except Exception as e:
        logger.error(f"Error getting backup stats: {e}")
        raise HTTPException(status_code=500, detail="Failed to get statistics")


@app.get("/api/backups/{filename}/download")
async def download_backup(filename: str):
    """Download a backup file."""
    try:
        backup_path = settings.backup_dir / filename

        # Security check: prevent directory traversal
        if not backup_path.exists() or not str(backup_path).startswith(str(settings.backup_dir)):
            raise HTTPException(status_code=404, detail="Backup not found")

        return FileResponse(
            path=backup_path,
            filename=filename,
            media_type="application/zip",
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error downloading backup {filename}: {e}")
        raise HTTPException(status_code=500, detail="Failed to download backup")


@app.post("/api/backups/upload")
async def upload_backup(file: UploadFile = File(...)):
    """Upload a backup file."""
    try:
        # Validate file
        if not file.filename.endswith(".zip"):
            raise HTTPException(status_code=400, detail="Only ZIP files are allowed")

        # Save uploaded file
        backup_path = settings.backup_dir / file.filename
        with open(backup_path, "wb") as f:
            content = await file.read()
            if len(content) > settings.max_upload_size:
                raise HTTPException(status_code=413, detail="File too large")
            f.write(content)

        # Validate backup
        if not backup_manager.validate_backup(file.filename):
            backup_path.unlink()
            raise HTTPException(status_code=400, detail="Invalid backup file")

        return APIResponse(
            success=True,
            message="Backup uploaded successfully",
            data={"filename": file.filename},
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading backup: {e}")
        raise HTTPException(status_code=500, detail="Failed to upload backup")


@app.post("/api/backups/{filename}/restore")
async def restore_backup(filename: str, request: RestoreRequest):
    """Restore a backup."""
    try:
        # Validate target path
        target_path = Path(request.target_path).resolve()

        success = backup_manager.restore_backup(
            backup_filename=filename,
            target_path=str(target_path),
            restore_volumes=request.restore_volumes,
        )

        if not success:
            raise HTTPException(status_code=500, detail="Failed to restore backup")

        return APIResponse(
            success=True,
            message="Backup restored successfully",
            data={
                "filename": filename,
                "target_path": str(target_path),
            },
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error restoring backup {filename}: {e}")
        raise HTTPException(status_code=500, detail="Failed to restore backup")


@app.delete("/api/backups/{filename}")
async def delete_backup(filename: str):
    """Delete a backup file."""
    try:
        success = backup_manager.delete_backup(filename)
        if not success:
            raise HTTPException(status_code=404, detail="Backup not found")

        return APIResponse(
            success=True,
            message="Backup deleted successfully",
            data={"filename": filename},
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting backup {filename}: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete backup")


@app.post("/api/backups/{filename}/validate")
async def validate_backup(filename: str):
    """Validate a backup file."""
    try:
        is_valid = backup_manager.validate_backup(filename)

        return APIResponse(
            success=True,
            message="Backup validation completed",
            data={
                "filename": filename,
                "valid": is_valid,
            },
        )
    except Exception as e:
        logger.error(f"Error validating backup {filename}: {e}")
        raise HTTPException(status_code=500, detail="Failed to validate backup")


# ============================================================================
# Backup Schedule API Routes
# ============================================================================

@app.post("/api/schedules")
async def create_schedule(request: ScheduleRequest):
    """Create a backup schedule."""
    try:
        job_id = scheduler.add_job(
            container_id=request.container_id,
            cron_expression=request.cron_expression,
            include_volumes=request.include_volumes,
            include_config=request.include_config,
            include_database=request.include_database,
            include_image=request.include_image,
        )

        if not job_id:
            raise HTTPException(status_code=500, detail="Failed to create schedule")

        job_info = scheduler.get_job(job_id)
        return APIResponse(
            success=True,
            message="Schedule created successfully",
            data=job_info,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating schedule: {e}")
        raise HTTPException(status_code=500, detail="Failed to create schedule")


@app.get("/api/schedules")
async def list_schedules():
    """Get list of all backup schedules."""
    try:
        jobs = scheduler.list_jobs()
        return APIResponse(
            success=True,
            message="Schedules retrieved",
            data=jobs,
        )
    except Exception as e:
        logger.error(f"Error listing schedules: {e}")
        raise HTTPException(status_code=500, detail="Failed to list schedules")


@app.get("/api/schedules/{job_id}")
async def get_schedule(job_id: str):
    """Get details of a specific schedule."""
    try:
        job_info = scheduler.get_job(job_id)
        if not job_info:
            raise HTTPException(status_code=404, detail="Schedule not found")

        return APIResponse(
            success=True,
            message="Schedule retrieved",
            data=job_info,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting schedule {job_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get schedule")


@app.post("/api/schedules/{job_id}/trigger")
async def trigger_schedule(job_id: str):
    """Manually trigger a scheduled backup."""
    try:
        success = scheduler.trigger_job(job_id)
        if not success:
            raise HTTPException(status_code=404, detail="Schedule not found")

        return APIResponse(
            success=True,
            message="Schedule triggered successfully",
            data={"job_id": job_id},
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error triggering schedule {job_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to trigger schedule")


@app.delete("/api/schedules/{job_id}")
async def delete_schedule(job_id: str):
    """Delete a backup schedule."""
    try:
        success = scheduler.remove_job(job_id)
        if not success:
            raise HTTPException(status_code=404, detail="Schedule not found")

        return APIResponse(
            success=True,
            message="Schedule deleted successfully",
            data={"job_id": job_id},
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting schedule {job_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete schedule")


# ============================================================================
# System Info Routes
# ============================================================================

@app.get("/api/info")
async def get_info():
    """Get application information."""
    try:
        docker_connected = docker_manager.is_connected()
        scheduler_info = scheduler.get_scheduler_info()
        backup_stats = backup_manager.get_backup_stats()

        return APIResponse(
            success=True,
            message="Info retrieved",
            data={
                "app_name": settings.app_name,
                "app_version": settings.app_version,
                "docker_connected": docker_connected,
                "scheduler": scheduler_info,
                "backup_stats": backup_stats,
            },
        )
    except Exception as e:
        logger.error(f"Error getting info: {e}")
        raise HTTPException(status_code=500, detail="Failed to get info")


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "timestamp": str(Path(__file__).stat().st_mtime)}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info",
    )
