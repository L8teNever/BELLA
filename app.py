import os
import shutil
import threading
import json
import logging
import traceback
import zipfile
from datetime import datetime
from typing import List, Tuple, Dict, Optional, Any
from flask import Flask, render_template, jsonify, request, send_file
import docker
from apscheduler.schedulers.background import BackgroundScheduler

# Logging Setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Docker Setup
client = None
try:
    client = docker.from_env()
    logger.info("Docker client initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize Docker client: {e}")
    logger.warning("Docker client is not available. Some features will not work.")

# Configuration
BACKUP_DIR = '/app/backups'
HOST_PREFIX = '/hostfs'
os.makedirs(BACKUP_DIR, exist_ok=True)

# Scheduler Setup
scheduler = BackgroundScheduler()
scheduler.start()
logger.info("Background scheduler started")


def translate_windows_path(host_path: str) -> str:
    """Translate Windows/WSL host paths to container /hostfs paths."""
    if not host_path:
        return host_path

    translated_path = host_path

    if ':\\' in host_path:
        # Handle Windows paths: "C:\Path" -> "/hostfs/run/desktop/mnt/host/c/Path"
        parts = host_path.split(':\\', 1)
        drive = parts[0].lower()
        rest = parts[1].replace('\\', '/').lstrip('/')

        possible_paths = [
            os.path.join(HOST_PREFIX, 'run', 'desktop', 'mnt', 'host', drive, rest),
            os.path.join(HOST_PREFIX, 'mnt', drive, rest),
            os.path.join(HOST_PREFIX, drive, rest),
            os.path.join(HOST_PREFIX, 'host_mnt', drive, rest)
        ]

        for path in possible_paths:
            if os.path.exists(path):
                translated_path = path
                logger.debug(f"Path {host_path} found at {path}")
                return translated_path

        # Return first guess if none found
        translated_path = possible_paths[0]
        logger.warning(f"Path {host_path} not found. Using fallback: {translated_path}")

    elif host_path.startswith('/'):
        # Unix-like path, prepend hostfs
        translated_path = os.path.join(HOST_PREFIX, host_path.lstrip('/'))

    return translated_path


def perform_backup(container_id: str, container_name: str) -> None:
    """Perform a backup of a Docker container."""
    logger.info(f"Starting backup for {container_name} ({container_id})")
    if not client:
        logger.error("Docker client not available")
        return
    try:
        container = client.containers.get(container_id)

        # 1. Stop the container
        logger.info(f"Stopping container {container_name}...")
        container.stop()

        # 2. Gather paths to backup
        paths_to_backup: List[str] = []

        # Mounts
        if 'Mounts' in container.attrs:
            for mount in container.attrs['Mounts']:
                if 'Source' not in mount:
                    continue

                host_path = mount['Source']
                translated_path = translate_windows_path(host_path)

                logger.info(f"Checking mount: {host_path} -> {translated_path}")

                if os.path.exists(translated_path):
                    paths_to_backup.append(translated_path)
                elif os.path.exists(host_path):
                    paths_to_backup.append(host_path)
                else:
                    logger.warning(f"Path {host_path} not found on host system")

        # Compose project working dir
        labels = container.labels
        working_dir = labels.get('com.docker.compose.project.working_dir')
        if working_dir:
            translated_working_dir = translate_windows_path(working_dir)

            logger.info(f"Checking compose dir: {working_dir} -> {translated_working_dir}")

            if os.path.exists(translated_working_dir) and translated_working_dir not in paths_to_backup:
                paths_to_backup.append(translated_working_dir)
            elif os.path.exists(working_dir) and working_dir not in paths_to_backup:
                paths_to_backup.append(working_dir)

        # 3. Create zip archive
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        temp_dir = os.path.join(BACKUP_DIR, f"temp_{container_name}_{timestamp}")
        os.makedirs(temp_dir, exist_ok=True)

        # Copy data
        logger.info(f"Backing up {len(paths_to_backup)} paths")
        for path in paths_to_backup:
            basename = os.path.basename(path)
            dest = os.path.join(temp_dir, basename)
            logger.debug(f"Copying {path} to {dest}")
            try:
                if os.path.isdir(path):
                    shutil.copytree(path, dest, dirs_exist_ok=True)
                elif os.path.isfile(path):
                    shutil.copy2(path, dest)
            except Exception as copy_error:
                logger.error(f"Failed to copy {path}: {copy_error}")

        # Create metadata
        meta_data: Dict[str, Any] = {
            "tool": "BELLA Docker Watcher",
            "version": "1.0",
            "container_name": container_name,
            "container_id": container_id,
            "timestamp": timestamp,
            "original_paths": paths_to_backup
        }
        metadata_path = os.path.join(temp_dir, "bella_metadata.json")
        with open(metadata_path, "w") as f:
            json.dump(meta_data, f, indent=4)

        # Create archive
        archive_name = os.path.join(BACKUP_DIR, f"backup_{container_name}_{timestamp}")
        shutil.make_archive(archive_name, 'zip', temp_dir)

        # Cleanup
        shutil.rmtree(temp_dir)
        logger.info(f"Backup created: {archive_name}.zip")

    except docker.errors.DockerException as docker_error:
        logger.error(f"Docker error during backup of {container_name}: {docker_error}")
    except OSError as os_error:
        logger.error(f"OS error during backup of {container_name}: {os_error}")
    except Exception as e:
        logger.error(f"Unexpected error during backup of {container_name}: {e}", exc_info=True)
    finally:
        # 4. Restart container
        try:
            logger.info(f"Starting container {container_name}...")
            container.start()
        except docker.errors.DockerException as e:
            logger.error(f"Failed to start container {container_name}: {e}")

def sequential_backup_task(containers_to_backup: List[Tuple[str, str]]) -> None:
    """Execute backups sequentially for a list of containers."""
    for container_id, container_name in containers_to_backup:
        perform_backup(container_id, container_name)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/backup/manual', methods=['POST'])
def trigger_manual_backup() -> Tuple[Dict, int]:
    """Trigger a manual backup for selected containers."""
    data = request.json
    if not data:
        logger.warning("Manual backup request with no JSON data")
        return jsonify({'error': 'No data provided'}), 400

    containers = data.get('containers', [])
    if not containers:
        logger.warning("Manual backup request with no containers")
        return jsonify({'error': 'No containers provided'}), 400

    # Validate container format
    if not all(isinstance(c, (list, tuple)) and len(c) == 2 for c in containers):
        return jsonify({'error': 'Invalid container format'}), 400

    logger.info(f"Starting manual backup for {len(containers)} containers")
    threading.Thread(target=sequential_backup_task, args=(containers,), daemon=True).start()
    return jsonify({'message': 'Backup started in background'}), 200

@app.route('/api/backup/schedule', methods=['POST'])
def schedule_backup() -> Tuple[Dict, int]:
    """Schedule a backup at a specific time."""
    data = request.json
    if not data:
        return jsonify({'error': 'No data provided'}), 400

    containers = data.get('containers', [])
    time_str = data.get('time')

    if not containers or not time_str:
        logger.warning(f"Schedule backup missing: containers={bool(containers)}, time={bool(time_str)}")
        return jsonify({'error': 'Missing containers or time'}), 400

    try:
        hour, minute = map(int, time_str.split(':'))
        if not (0 <= hour <= 23 and 0 <= minute <= 59):
            return jsonify({'error': 'Invalid time format. Use HH:MM (00:00-23:59)'}), 400

        job_id = f"backup_job_{int(datetime.now().timestamp() * 1000)}"
        scheduler.add_job(
            sequential_backup_task,
            'cron',
            hour=hour,
            minute=minute,
            id=job_id,
            args=[containers],
            replace_existing=True
        )
        logger.info(f"Backup scheduled at {time_str} with job ID {job_id}")
        return jsonify({'message': f'Backup scheduled at {time_str}'}), 200
    except ValueError as e:
        logger.error(f"Invalid time format: {time_str}: {e}")
        return jsonify({'error': 'Invalid time format. Use HH:MM'}), 400
    except Exception as e:
        logger.error(f"Error scheduling backup: {e}", exc_info=True)
        return jsonify({'error': 'Failed to schedule backup'}), 500

@app.route('/api/backups', methods=['GET'])
def list_backups() -> Tuple[List[Dict], int]:
    """List all available backups."""
    backups: List[Dict[str, Any]] = []

    if not os.path.exists(BACKUP_DIR):
        return jsonify(backups), 200

    try:
        for filename in os.listdir(BACKUP_DIR):
            if not filename.endswith('.zip'):
                continue

            filepath = os.path.join(BACKUP_DIR, filename)
            try:
                size_mb = os.path.getsize(filepath) / (1024 * 1024)
                mtime = os.path.getmtime(filepath)
                backups.append({
                    'name': filename,
                    'size_mb': round(size_mb, 2),
                    'date': datetime.fromtimestamp(mtime).isoformat()
                })
            except OSError as e:
                logger.warning(f"Could not stat backup file {filename}: {e}")

        backups.sort(key=lambda x: x['date'], reverse=True)
    except OSError as e:
        logger.error(f"Error listing backups: {e}")

    return jsonify(backups), 200

@app.route('/api/fs/list', methods=['POST'])
def list_fs() -> Tuple[Dict, int]:
    """List directories in the host filesystem."""
    data = request.json
    if not data:
        return jsonify({'error': 'No data provided'}), 400

    path = data.get('path', '/').strip()

    # Ensure path starts with /
    if not path.startswith('/'):
        path = '/' + path

    full_path = os.path.abspath(os.path.join(HOST_PREFIX, path.lstrip('/')))

    # Security: prevent path traversal outside HOST_PREFIX
    if not full_path.startswith(HOST_PREFIX):
        logger.warning(f"Path traversal attempt detected: {path}")
        return jsonify({'error': 'Access denied'}), 403

    try:
        if not os.path.isdir(full_path):
            return jsonify({'error': 'Path is not a directory'}), 400

        folders: List[str] = []
        try:
            for item in os.listdir(full_path):
                item_full = os.path.join(full_path, item)
                try:
                    if os.path.isdir(item_full):
                        folders.append(item)
                except OSError:
                    logger.debug(f"Could not check {item_full}")
        except PermissionError:
            logger.warning(f"Permission denied listing {full_path}")
            return jsonify({'error': 'Permission denied'}), 403

        folders.sort()
        parent_path = os.path.dirname(path) if path != '/' else '/'

        return jsonify({'path': path, 'folders': folders, 'parent': parent_path}), 200

    except PermissionError:
        logger.warning(f"Permission denied accessing {full_path}")
        return jsonify({'error': 'Permission denied'}), 403
    except OSError as e:
        logger.error(f"OS error listing {full_path}: {e}")
        return jsonify({'error': 'Failed to list directory'}), 500
    except Exception as e:
        logger.error(f"Unexpected error listing {full_path}: {e}", exc_info=True)
        return jsonify({'error': 'Unexpected error'}), 500

@app.route('/api/backup/download/<filename>', methods=['GET'])
def download_backup(filename: str):
    """Download a backup file."""
    # Security: prevent path traversal
    if '..' in filename or '/' in filename or not filename.endswith('.zip'):
        logger.warning(f"Invalid backup download attempt: {filename}")
        return jsonify({'error': 'Invalid filename'}), 400

    path = os.path.join(BACKUP_DIR, filename)

    if not os.path.exists(path):
        logger.warning(f"Backup download not found: {filename}")
        return jsonify({'error': 'File not found'}), 404

    try:
        logger.info(f"Downloading backup: {filename}")
        return send_file(path, as_attachment=True, download_name=filename)
    except Exception as e:
        logger.error(f"Error downloading backup {filename}: {e}")
        return jsonify({'error': 'Download failed'}), 500

@app.route('/api/backup/restore_server', methods=['POST'])
def restore_backup_server() -> Tuple[Dict, int]:
    """Restore a backup to a specified path on the server."""
    data = request.json
    if not data:
        return jsonify({'error': 'No data provided'}), 400

    filename = data.get('filename', '').strip()
    target_path = data.get('target_path', '').strip()

    if not filename or not target_path:
        return jsonify({'error': 'Filename and target_path required'}), 400

    # Security: prevent path traversal
    if '..' in filename or '/' in filename or not filename.endswith('.zip'):
        logger.warning(f"Invalid restore attempt: {filename}")
        return jsonify({'error': 'Invalid filename'}), 400

    zip_path = os.path.join(BACKUP_DIR, filename)
    if not os.path.exists(zip_path):
        logger.warning(f"Backup file not found: {filename}")
        return jsonify({'error': 'Backup file not found'}), 404

    try:
        # Translate host path to container path via /hostfs
        translated_path = translate_windows_path(target_path)
        container_dest = os.path.abspath(translated_path)

        # Security check
        if not container_dest.startswith(HOST_PREFIX):
            logger.warning(f"Path traversal attempt in restore: {target_path}")
            return jsonify({'error': 'Invalid target path'}), 403

        os.makedirs(container_dest, exist_ok=True)

        is_bella_backup = False
        meta_info: Optional[Dict] = None

        logger.info(f"Restoring backup {filename} to {container_dest}")

        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            if 'bella_metadata.json' in zip_ref.namelist():
                is_bella_backup = True
                with zip_ref.open('bella_metadata.json') as f:
                    meta_info = json.load(f)
            zip_ref.extractall(container_dest)

        if is_bella_backup and meta_info:
            container_name = meta_info.get('container_name', 'Unknown')
            timestamp = meta_info.get('timestamp', 'Unknown')
            success_msg = f'[BELLA Verified] Backup from container "{container_name}" ({timestamp}) successfully restored to {target_path}'
        else:
            success_msg = f'Backup successfully restored to {target_path}'

        logger.info(success_msg)
        return jsonify({'message': success_msg}), 200

    except zipfile.BadZipFile:
        logger.error(f"Invalid zip file: {filename}")
        return jsonify({'error': 'Invalid backup file format'}), 400
    except PermissionError:
        logger.error(f"Permission denied restoring to {target_path}")
        return jsonify({'error': 'Permission denied'}), 403
    except OSError as e:
        logger.error(f"OS error during restore: {e}")
        return jsonify({'error': 'Failed to restore backup'}), 500
    except Exception as e:
        logger.error(f"Unexpected error during restore: {e}", exc_info=True)
        return jsonify({'error': 'Unexpected error'}), 500

@app.route('/api/restore', methods=['POST'])
def restore_backup() -> Tuple[Dict, int]:
    """Upload and extract a backup file."""
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400

    file = request.files['file']
    if not file or file.filename == '':
        return jsonify({'error': 'No file selected'}), 400

    if not file.filename.endswith('.zip'):
        return jsonify({'error': 'Only .zip files are supported'}), 400

    try:
        # 1. Save uploaded zip
        upload_filename = f"upload_{datetime.now().strftime('%Y%m%d%H%M%S')}_{file.filename}"
        upload_path = os.path.join(BACKUP_DIR, upload_filename)
        file.save(upload_path)
        logger.info(f"Backup uploaded: {upload_filename}")

        # 2. Extract zip
        temp_extract_dir = os.path.join(BACKUP_DIR, f"temp_restore_{datetime.now().strftime('%Y%m%d%H%M%S')}")
        os.makedirs(temp_extract_dir, exist_ok=True)

        is_bella_backup = False
        meta_info: Optional[Dict] = None

        with zipfile.ZipFile(upload_path, 'r') as zip_ref:
            if 'bella_metadata.json' in zip_ref.namelist():
                is_bella_backup = True
                with zip_ref.open('bella_metadata.json') as f:
                    meta_info = json.load(f)
            zip_ref.extractall(temp_extract_dir)

        # 3. Copy to restore directory
        base_name = file.filename.replace('.zip', '')
        restore_dest = os.path.join(HOST_PREFIX, 'restored_data', base_name)
        os.makedirs(restore_dest, exist_ok=True)

        # Copy extracted files
        for item in os.listdir(temp_extract_dir):
            source = os.path.join(temp_extract_dir, item)
            destination = os.path.join(restore_dest, item)
            try:
                if os.path.isdir(source):
                    shutil.copytree(source, destination, dirs_exist_ok=True)
                else:
                    shutil.copy2(source, destination)
            except OSError as e:
                logger.warning(f"Failed to copy {source}: {e}")

        # Cleanup
        shutil.rmtree(temp_extract_dir)
        os.remove(upload_path)

        # Generate message
        host_restore_path = restore_dest.replace(HOST_PREFIX, '')
        if host_restore_path.startswith('/'):
            host_restore_path = f"C:\\{host_restore_path.lstrip('/')}"
            host_restore_path = host_restore_path.replace('/', '\\')

        if is_bella_backup and meta_info:
            container_name = meta_info.get('container_name', 'Unknown')
            msg = f'[BELLA Verified] Container: {container_name}. Files restored to {host_restore_path}'
        else:
            msg = f'Files restored to {host_restore_path}. Please move to desired location.'

        logger.info(f"Restore completed: {host_restore_path}")
        return jsonify({'message': msg}), 200

    except zipfile.BadZipFile:
        logger.error(f"Invalid zip file uploaded")
        return jsonify({'error': 'Invalid backup file format'}), 400
    except PermissionError:
        logger.error("Permission denied during restore")
        return jsonify({'error': 'Permission denied'}), 403
    except OSError as e:
        logger.error(f"OS error during restore: {e}")
        return jsonify({'error': 'Failed to process backup'}), 500
    except Exception as e:
        logger.error(f"Unexpected error during restore: {e}", exc_info=True)
        return jsonify({'error': 'Unexpected error'}), 500
    finally:
        # Cleanup any remaining temp files
        try:
            if os.path.exists(upload_path):
                os.remove(upload_path)
        except Exception:
            pass

@app.route('/api/containers')
def get_containers() -> Tuple[Dict, int]:
    """Get list of all Docker containers."""
    if not client:
        logger.warning("Docker client not available, returning empty container list")
        return jsonify([]), 200
    try:
        containers = client.containers.list(all=True)
        container_data: List[Dict[str, Any]] = []

        for container in containers:
            try:
                # Extract mounts
                mounts: List[Dict[str, str]] = []
                if 'Mounts' in container.attrs:
                    for mount in container.attrs['Mounts']:
                        mounts.append({
                            'source': mount.get('Source', 'N/A'),
                            'destination': mount.get('Destination', 'N/A')
                        })

                # Extract Docker Compose info
                labels = container.labels or {}
                compose_info = {
                    'project': labels.get('com.docker.compose.project', 'N/A'),
                    'service': labels.get('com.docker.compose.service', 'N/A'),
                    'version': labels.get('com.docker.compose.version', 'N/A'),
                    'config_files': labels.get('com.docker.compose.project.config_files', 'N/A'),
                    'working_dir': labels.get('com.docker.compose.project.working_dir', 'N/A')
                }

                # Get image tag safely
                image_name = 'None'
                if container.image and container.image.tags:
                    image_name = container.image.tags[0]

                container_data.append({
                    'id': container.short_id,
                    'name': container.name,
                    'status': container.status,
                    'image': image_name,
                    'uptime': container.attrs.get('State', {}).get('StartedAt', 'N/A'),
                    'mounts': mounts,
                    'compose': compose_info
                })
            except Exception as e:
                logger.warning(f"Error processing container {container.short_id}: {e}")

        logger.info(f"Retrieved {len(container_data)} containers")
        return jsonify(container_data), 200

    except docker.errors.DockerException as e:
        logger.error(f"Docker error fetching containers: {e}")
        return jsonify({'error': 'Docker error'}), 500
    except Exception as e:
        logger.error(f"Unexpected error fetching containers: {e}", exc_info=True)
        return jsonify({'error': 'Unexpected error'}), 500

if __name__ == '__main__':
    logger.info("Starting Docker Watcher application")
    try:
        app.run(host='0.0.0.0', port=5000, debug=False)
    except KeyboardInterrupt:
        logger.info("Shutting down...")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        raise
