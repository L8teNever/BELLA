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
            # Versuche, den Mount-Pfad (Source) zu finden
            mounts = []
            if 'Mounts' in c.attrs:
                for m in c.attrs['Mounts']:
                    mounts.append({
                        'source': m.get('Source', 'N/A'),
                        'destination': m.get('Destination', 'N/A')
                    })

            container_data.append({
                'id': c.short_id,
                'name': c.name,
                'status': c.status,
                'image': c.image.tags[0] if c.image.tags else "None",
                'uptime': c.attrs.get('State', {}).get('StartedAt', 'N/A'),
                'mounts': mounts
            })
        return jsonify(container_data)
    except Exception as e:
        import traceback
        print(traceback.format_exc())
        return jsonify({'error': str(e)}), 500

@app.route('/api/compose-config')
def get_compose_config():
    try:
        import os
        compose_path = 'docker-compose.yml'
        if os.path.exists(compose_path):
            with open(compose_path, 'r') as f:
                return jsonify({'content': f.read()})
        return jsonify({'content': 'Keine docker-compose.yml gefunden.'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
