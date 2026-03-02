import docker
from flask import Flask, render_template, jsonify

app = Flask(__name__)
client = docker.from_env()

@app.route('/')
def index():
    return render_template('index.html')

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
