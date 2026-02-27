# Bella - Docker Container Backup System

A Python-based automated backup system for Docker containers with a web interface. Bella monitors Docker containers, allows selective backup configuration, and performs automatic backups at scheduled times.

## Features

✨ **Web Dashboard**
- Real-time container monitoring
- Toggle backups per container
- Manual backup triggers
- Backup history and statistics

🔄 **Automatic Backups**
- Scheduled daily backups at 1:00 AM
- Graceful container shutdown during backup
- Automatic container restart after backup
- tar.gz compression of volumes

📊 **Backup Management**
- Backup history with detailed logs
- Backup file management
- Success/failure tracking
- Error logging and reporting

🐳 **Docker Integration**
- Direct Docker API integration
- Volume detection and backup
- Container status monitoring
- Multi-container support

## Requirements

- Docker and Docker Compose
- Python 3.11 (for local development)
- Linux/macOS/Windows with Docker Desktop

## Installation

### Using Docker Compose (Recommended)

1. Clone or download this repository
2. Navigate to the project directory:
```bash
cd BELLA
```

3. Build and start the container:
```bash
docker-compose up -d
```

4. Access the web interface:
```
http://localhost:5000
```

### Local Development

1. Install Python 3.11+
2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set environment variables:
```bash
export DATABASE_PATH=/tmp/bella.db
export BACKUP_DIR=/tmp/backups
export BACKUP_TIME=01:00
```

4. Run the application:
```bash
python main.py
```

## Configuration

### Environment Variables

Set these in your `docker-compose.yml` or shell environment:

```bash
BACKUP_DIR=/backups              # Backup storage location
DATABASE_PATH=/app/data/bella.db # Database file path
BACKUP_TIME=01:00               # Daily backup time (HH:MM format)
TZ=Europe/Berlin                # Timezone for scheduling
FLASK_ENV=production            # Flask environment
```

### Docker Compose Configuration

The `docker-compose.yml` file includes:
- Docker Socket mounting for container management
- Persistent volumes for database and backups
- Port mapping (5000:5000)
- Environment variables

## Usage

### Dashboard

1. **View Containers**: All Docker containers are listed automatically
2. **Enable Backups**: Toggle the backup switch for each container
3. **Manual Backup**: Click "Backup" to start immediate backup
4. **View Stats**: Dashboard shows total containers, enabled backups, etc.

### History

- View all backup operations
- Filter by container
- Check backup status and duration
- Delete old backups

### Scheduler

- Backups run automatically at 1:00 AM (configurable)
- View scheduled jobs in the status endpoint
- Manually trigger backups via API

## API Endpoints

### Containers
- `GET /api/containers` - List all containers
- `POST /api/container/<id>/enable` - Enable backup
- `POST /api/container/<id>/disable` - Disable backup
- `POST /api/container/<id>/backup` - Manual backup

### Backups
- `GET /api/backups` - List all backups
- `GET /api/backups/container/<id>` - Container backups
- `DELETE /api/backups/<id>/delete` - Delete backup

### Status
- `GET /api/stats` - Backup statistics
- `GET /api/scheduler/status` - Scheduler status
- `POST /api/scheduler/trigger` - Trigger backups now
- `GET /health` - Health check

## Backup Process

For each enabled container:

1. **Stop Container**: Gracefully stop the container (30s timeout)
2. **Backup Volumes**: Create tar.gz archives of all mounted volumes
3. **Start Container**: Restart the container immediately
4. **Log Results**: Record success/failure in history

Files are named: `{container_name}_{volume_name}_{timestamp}.tar.gz`

Example:
```
mongodb_data_20240227_011234.tar.gz
postgres_config_20240227_011234.tar.gz
```

## Storage

### Backup Volume
All backups are stored in the `bella-backups` Docker volume, which is persistent across container restarts.

### Database
SQLite database (`bella.db`) stores:
- Container configurations
- Backup history and logs
- Retention policies

## Troubleshooting

### Docker Connection Issues
```bash
# Check Docker socket permissions
docker exec bella-backup-system ls -la /var/run/docker.sock

# View logs
docker logs bella-backup-system
```

### Database Issues
```bash
# Remove database and reinitialize
docker volume rm bella-database
docker-compose restart
```

### Backups Not Running
```bash
# Check scheduler status
curl http://localhost:5000/api/scheduler/status

# Trigger manual backup
curl -X POST http://localhost:5000/api/scheduler/trigger
```

## Logs

View application logs:
```bash
docker logs -f bella-backup-system
```

Search for errors:
```bash
docker logs bella-backup-system | grep ERROR
```

## Security Considerations

⚠️ **Important**: This system has no authentication by default. Only use in trusted networks.

- Docker Socket: Container has full Docker access
- Backups: Stored unencrypted (consider enabling HTTPS/SSL)
- Web UI: No authentication (add reverse proxy or basic auth if needed)

## Limitations

- Backups are full (not incremental)
- No automatic backup cleanup (manual or via retention policy)
- Single Docker host only
- No backup encryption
- No remote storage support (local volumes only)

## Future Enhancements

- [ ] Backup retention policies
- [ ] Email notifications
- [ ] Backup encryption
- [ ] Remote storage (S3, FTP)
- [ ] Differential backups
- [ ] Basic authentication
- [ ] Restore functionality
- [ ] Multi-host support
- [ ] Backup verification

## Development

### Project Structure
```
BELLA/
├── app/                    # Flask application
│   ├── __init__.py        # App factory
│   ├── models.py          # Database models
│   ├── docker_manager.py  # Docker API
│   ├── backup_engine.py   # Backup logic
│   ├── scheduler.py       # APScheduler
│   ├── routes.py          # API endpoints
│   ├── static/            # CSS/JS
│   └── templates/         # HTML templates
├── config/                # Configuration
├── main.py               # Entry point
├── requirements.txt      # Dependencies
├── Dockerfile           # Container image
└── docker-compose.yml   # Orchestration
```

### Testing Locally

```bash
# Build image
docker build -t bella:dev .

# Run container
docker run -v /var/run/docker.sock:/var/run/docker.sock \
           -p 5000:5000 \
           bella:dev
```

## Contributing

Contributions are welcome! Please ensure:
- Code follows PEP 8 style guide
- Error handling is comprehensive
- Tests pass
- Documentation is updated

## License

This project is provided as-is for personal and educational use.

## Support

For issues or questions:
1. Check the logs: `docker logs bella-backup-system`
2. Verify Docker connection: `docker ps`
3. Test API endpoints: `curl http://localhost:5000/health`

## Changelog

### Version 1.0.0 (Initial Release)
- Docker container discovery
- Web dashboard
- Backup scheduling
- Backup history
- Manual backup triggers
- Volume-based backups

## Author

Bella Backup System - Automated Docker Container Backup Solution
