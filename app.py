import os
import shutil
import threading
import json
from datetime import datetime
from flask import Flask, render_template, jsonify, request, send_file
import docker
from apscheduler.schedulers.background import BackgroundScheduler

app = Flask(__name__)
client = docker.from_env()

# Ensure backups directory exists
BACKUP_DIR = '/app/backups'
HOST_PREFIX = '/hostfs'
os.makedirs(BACKUP_DIR, exist_ok=True)

scheduler = BackgroundScheduler()
scheduler.start()

def perform_backup(container_id, container_name):
    print(f"Starting backup for {container_name} ({container_id})")
    try:
        container = client.containers.get(container_id)
        
        # 1. Stop the container
        print(f"Stopping container {container_name}...")
        container.stop()
        
        # 2. Gather paths to backup
        paths_to_backup = []
        
        # Mounts
        if 'Mounts' in container.attrs:
            for mount in container.attrs['Mounts']:
                if 'Source' in mount:
                    host_path = mount['Source']
                    
                    # Custom translation for Windows/WSL hosts to the /hostfs root mount:
                    # Windows paths in docker often look like /run/desktop/mnt/host/wsl/docker-desktop-bind-mounts...
                    # Or they look like C:\Users\... or /c/Users/...
                    translated_path = host_path
                    if host_path.find(':\\') != -1:
                        # Drive letter handling "C:\Path" -> "/hostfs/c/Path" (often mounted like this in some systems)
                        # Or simply we strip C:\ and append to hostfs
                        parts = host_path.split(':\\', 1)
                        translated_path = os.path.join(HOST_PREFIX, parts[1].replace('\\', '/').lstrip('/'))
                    elif host_path.startswith('/'):
                        # Already unix-like path, prepend hostfs
                        translated_path = os.path.join(HOST_PREFIX, host_path.lstrip('/'))
                    
                    print(f"Checking mount: {host_path} -> Translates to: {translated_path}")
                    
                    if os.path.exists(translated_path):
                        paths_to_backup.append(translated_path)
                    elif os.path.exists(host_path): # fallback if internal docker path is identical
                        paths_to_backup.append(host_path)

        # Compose project working dir
        labels = container.labels
        working_dir = labels.get('com.docker.compose.project.working_dir')
        if working_dir:
            translated_working_dir = working_dir
            if working_dir.find(':\\') != -1:
                parts = working_dir.split(':\\', 1)
                translated_working_dir = os.path.join(HOST_PREFIX, parts[1].replace('\\', '/').lstrip('/'))
            elif working_dir.startswith('/'):
                translated_working_dir = os.path.join(HOST_PREFIX, working_dir.lstrip('/'))
                
            print(f"Checking compose dir: {working_dir} -> Translates to: {translated_working_dir}")
            
            if os.path.exists(translated_working_dir) and translated_working_dir not in paths_to_backup:
                 paths_to_backup.append(translated_working_dir)
            elif os.path.exists(working_dir) and working_dir not in paths_to_backup:
                 paths_to_backup.append(working_dir)

        # 3. Create zip archive
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        temp_dir = os.path.join(BACKUP_DIR, f"temp_{container_name}_{timestamp}")
        os.makedirs(temp_dir, exist_ok=True)
        
        # Copy data
        print(f"Paths to backup: {paths_to_backup}")
        for path in paths_to_backup:
            basename = os.path.basename(path)
            dest = os.path.join(temp_dir, basename)
            print(f"Copying {path} to {dest}")
            if os.path.isdir(path):
                shutil.copytree(path, dest, dirs_exist_ok=True)
            elif os.path.isfile(path):
                shutil.copy2(path, dest)
                
        # Zip it
        meta_data = {
            "tool": "BELLA Docker Watcher",
            "version": "1.0",
            "container_name": container_name,
            "container_id": container_id,
            "timestamp": timestamp,
            "original_paths": paths_to_backup
        }
        with open(os.path.join(temp_dir, "bella_metadata.json"), "w") as f:
            json.dump(meta_data, f, indent=4)
            
        archive_name = os.path.join(BACKUP_DIR, f"backup_{container_name}_{timestamp}")
        shutil.make_archive(archive_name, 'zip', temp_dir)
        
        # Cleanup temp
        shutil.rmtree(temp_dir)
        print(f"Backup created: {archive_name}.zip")
        
    except Exception as e:
        import traceback
        print(f"Error during backup of {container_name}: {e}")
        traceback.print_exc()
    finally:
        # 4. Start container
        try:
            print(f"Starting container {container_name}...")
            container.start()
        except:
             print(f"Failed to start container {container_name}")

def sequential_backup_task(containers_to_backup):
    for c_id, c_name in containers_to_backup:
        perform_backup(c_id, c_name)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/backup/manual', methods=['POST'])
def trigger_manual_backup():
    data = request.json
    containers = data.get('containers', [])
    if not containers:
         return jsonify({'error': 'No containers provided'}), 400
    
    # Start backup in background thread
    threading.Thread(target=sequential_backup_task, args=(containers,)).start()
    return jsonify({'message': 'Backup started in background'})

@app.route('/api/backup/schedule', methods=['POST'])
def schedule_backup():
    data = request.json
    containers = data.get('containers', [])
    time_str = data.get('time') # Expected format HH:MM
    
    if not containers or not time_str:
         return jsonify({'error': 'Missing containers or time'}), 400
         
    try:
        hour, minute = map(int, time_str.split(':'))
        job_id = f"backup_job_{datetime.now().timestamp()}"
        scheduler.add_job(
            sequential_backup_task, 
            'cron', 
            hour=hour, 
            minute=minute, 
            id=job_id,
            args=[containers]
        )
        return jsonify({'message': f'Backup scheduled at {time_str}'})
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/api/backups', methods=['GET'])
def list_backups():
    backups = []
    if os.path.exists(BACKUP_DIR):
        for f in os.listdir(BACKUP_DIR):
            if f.endswith('.zip'):
                path = os.path.join(BACKUP_DIR, f)
                size = os.path.getsize(path) / (1024 * 1024) # MB
                mtime = os.path.getmtime(path)
                backups.append({
                    'name': f,
                    'size_mb': round(size, 2),
                    'date': datetime.fromtimestamp(mtime).isoformat()
                })
    backups.sort(key=lambda x: x['date'], reverse=True)
    return jsonify(backups)

@app.route('/api/fs/list', methods=['POST'])
def list_fs():
    data = request.json
    path = data.get('path', '/') 
    
    # Ensure path starts with /
    if not path.startswith('/'):
        path = '/' + path
        
    full_path = os.path.abspath(os.path.join(HOST_PREFIX, path.lstrip('/')))
    
    # Security: path traversal outside HOST_PREFIX is guarded by abspath and startswith
    if not full_path.startswith(HOST_PREFIX):
        return jsonify({'error': 'Invalid path'}), 400
        
    try:
        folders = []
        for item in os.listdir(full_path):
            item_full = os.path.join(full_path, item)
            if os.path.isdir(item_full):
                folders.append(item)
        folders.sort()
        
        parent_path = os.path.dirname(path) if path != '/' else '/'
        
        return jsonify({'path': path, 'folders': folders, 'parent': parent_path})
    except PermissionError:
        return jsonify({'error': 'Zugriff verweigert (Permission denied)'}), 403
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/api/backup/download/<filename>', methods=['GET'])
def download_backup(filename):
    path = os.path.join(BACKUP_DIR, filename)
    if os.path.exists(path) and filename.endswith('.zip'):
        return send_file(path, as_attachment=True)
    return jsonify({'error': 'File not found'}), 404

@app.route('/api/backup/restore_server', methods=['POST'])
def restore_backup_server():
    data = request.json
    filename = data.get('filename')
    target_path = data.get('target_path')
    
    if not filename or not target_path:
        return jsonify({'error': 'Filename and target_path required'}), 400
        
    zip_path = os.path.join(BACKUP_DIR, filename)
    if not os.path.exists(zip_path) or not filename.endswith('.zip'):
        return jsonify({'error': 'Backup file not found'}), 404
        
    try:
        # Translate host path to container path via /hostfs
        translated_path = target_path
        if translated_path.find(':\\') != -1:
            translated_path = translated_path.split(':\\', 1)[1]
            translated_path = translated_path.replace('\\', '/')
        
        container_dest = os.path.join(HOST_PREFIX, translated_path.lstrip('/'))
        os.makedirs(container_dest, exist_ok=True)
        
        import zipfile
        is_bella_backup = False
        meta_info = None
        
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            if 'bella_metadata.json' in zip_ref.namelist():
                is_bella_backup = True
                with zip_ref.open('bella_metadata.json') as f:
                    meta_info = json.load(f)
            zip_ref.extractall(container_dest)
            
        success_msg = f'Backup erfolgreich nach {target_path} extrahiert!'
        if is_bella_backup and meta_info:
            success_msg = f'[BELLA Backup Verifiziert] Backup von Container "{meta_info.get("container_name")}" ({meta_info.get("timestamp")}) erfolgreich nach {target_path} extrahiert!'
            
        return jsonify({'message': success_msg})
    except Exception as e:
        import traceback
        print(traceback.format_exc())
        return jsonify({'error': str(e)}), 500

@app.route('/api/restore', methods=['POST'])
def restore_backup():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    
    if file and file.filename.endswith('.zip'):
        try:
            # 1. Save uploaded zip
            upload_path = os.path.join(BACKUP_DIR, 'upload_' + file.filename)
            file.save(upload_path)
            
            # 2. Extract zip
            temp_extract_dir = os.path.join(BACKUP_DIR, 'temp_restore_' + datetime.now().strftime('%Y%m%d%H%M%S'))
            os.makedirs(temp_extract_dir, exist_ok=True)
            import zipfile
            
            is_bella_backup = False
            meta_info = None
            
            with zipfile.ZipFile(upload_path, 'r') as zip_ref:
                if 'bella_metadata.json' in zip_ref.namelist():
                    is_bella_backup = True
                    with zip_ref.open('bella_metadata.json') as f:
                        meta_info = json.load(f)
                zip_ref.extractall(temp_extract_dir)

            # 3. Figure out where properties belong (this requires manual intervention or heuristics)
            # For simplicity in this iteration: We expect the user to manually place 
            # the extracted folders back to their host destination or use a defined restore path.
            # Realistically, restoring arbitrary host paths from a generic zip without metadata 
            # is complex. We will provide the extracted files in a specific 'restore' directory
            # and instruct the user.
            
            restore_dest = os.path.join(HOST_PREFIX, 'restored_data', file.filename.replace('.zip', ''))
            os.makedirs(restore_dest, exist_ok=True)
            
            # Copy contents back to a generic host accessible restore folder
            for item in os.listdir(temp_extract_dir):
                s = os.path.join(temp_extract_dir, item)
                d = os.path.join(restore_dest, item)
                if os.path.isdir(s):
                    shutil.copytree(s, d, dirs_exist_ok=True)
                else:
                    shutil.copy2(s, d)

            # Cleanup
            shutil.rmtree(temp_extract_dir)
            os.remove(upload_path)
            
            # Note: We inform the user where the files are stored on the host
            host_restore_path = restore_dest.replace(HOST_PREFIX, '')
            if host_restore_path.startswith('/'):
                 # Assuming it was C:\restored_data
                 host_restore_path = f"C:\\{host_restore_path.lstrip('/')}"
                 host_restore_path = host_restore_path.replace('/', '\\')

            msg = f'Die Dateien wurden auf dem Host unter {host_restore_path} abgelegt. Bitte manuell an den Zielort verschieben.'
            if is_bella_backup and meta_info:
                msg = f'[BELLA VERIFIZIERT] Container: {meta_info.get("container_name")}. ' + msg
                
            return jsonify({'message': msg})

        except Exception as e:
            import traceback
            print(traceback.format_exc())
            return jsonify({'error': str(e)}), 500
            
    return jsonify({'error': 'Invalid file'}), 400

@app.route('/api/containers')
def get_containers():
    try:
        containers = client.containers.list(all=True)
        container_data = []
        for c in containers:
            # Mounts
            mounts = []
            if 'Mounts' in c.attrs:
                for m in c.attrs['Mounts']:
                    mounts.append({
                        'source': m.get('Source', 'N/A'),
                        'destination': m.get('Destination', 'N/A')
                    })

            # Docker Compose Labels extrahieren
            labels = c.labels
            compose_info = {
                'project': labels.get('com.docker.compose.project', 'N/A'),
                'service': labels.get('com.docker.compose.service', 'N/A'),
                'version': labels.get('com.docker.compose.version', 'N/A'),
                'config_files': labels.get('com.docker.compose.project.config_files', 'N/A'),
                'working_dir': labels.get('com.docker.compose.project.working_dir', 'N/A')
            }

            container_data.append({
                'id': c.short_id,
                'name': c.name,
                'status': c.status,
                'image': c.image.tags[0] if c.image.tags else "None",
                'uptime': c.attrs.get('State', {}).get('StartedAt', 'N/A'),
                'mounts': mounts,
                'compose': compose_info
            })
        return jsonify(container_data)
    except Exception as e:
        import traceback
        print(traceback.format_exc())
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
