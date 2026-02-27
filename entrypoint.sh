#!/bin/bash
# Bella Docker Container Entrypoint
# Automatically fix Docker socket permissions on startup

set -e

echo "=========================================="
echo "Bella - Docker Container Backup System"
echo "=========================================="
echo ""

# Try to fix Docker socket permissions
if [ -S /var/run/docker.sock ]; then
    echo "🔧 Docker socket detected"

    # Try to make socket readable
    if chmod 666 /var/run/docker.sock 2>/dev/null; then
        echo "✅ Docker socket permissions fixed"
    else
        echo "⚠️  Could not modify socket permissions (may require privileged mode)"
        echo "   Run with: docker run --privileged ..."
    fi

    # Test Docker connection
    echo "🧪 Testing Docker connection..."
    if python3 -c "import docker; docker.from_env().ping()" 2>/dev/null; then
        echo "✅ Docker connection successful!"
    else
        echo "⚠️  Docker connection failed - running in degraded mode"
    fi
else
    echo "⚠️  Docker socket not found at /var/run/docker.sock"
    echo "   Bella will run in degraded mode"
fi

echo ""
echo "=========================================="
echo "Starting Flask application..."
echo "=========================================="
echo ""

# Start the application
exec python main.py
