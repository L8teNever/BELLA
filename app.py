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
            container_data.append({
                'id': c.short_id,
                'name': c.name,
                'status': c.status,
                'image': c.image.tags[0] if c.image.tags else "None",
                'uptime': c.attrs.get('State', {}).get('StartedAt', 'N/A')
            })
        return jsonify(container_data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
