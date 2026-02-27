# Bella - Quick Start Guide

## ⚡ Quick Start

### 1. Prerequisites
- Docker und Docker Compose installiert
- Linux, macOS, oder Windows mit Docker Desktop

### 2. Start Bella

```bash
cd /path/to/BELLA
docker-compose up -d
```

Wait 30-60 seconds for the container to start.

### 3. Access the Dashboard

Open your browser:
```
http://localhost:5000
```

## 📊 First Steps

### Step 1: View Containers
- Dashboard automatically lists all Docker containers
- You'll see: Container name, image, status, volumes

### Step 2: Enable Backups
- Toggle the checkbox for containers you want to backup
- Green = backup enabled, disabled = no backup

### Step 3: Manual Backup (Optional)
- Click the "Backup" button to backup a container immediately
- Container will be stopped, backed up, and restarted

### Step 4: Verify Backups
- Go to "History" tab
- View all backup operations
- Check for successful backups (green status)

## 🕐 Automatic Backups

Backups run **automatically at 1:00 AM** (default) every day.

To check if backups ran:
1. Go to "History" tab
2. Look for entries at 1:00 AM
3. Check status (green = success, red = failed)

## 📁 Backup Storage

Backups are stored in `/backups` inside the container, which is mounted to a Docker volume.

To access backups:
```bash
# List backups
docker exec bella-backup-system ls -lh /backups/

# Copy a backup to your computer
docker cp bella-backup-system:/backups/your-backup.tar.gz ./
```

## 🐛 Troubleshooting

### "No containers showing"
```bash
docker logs bella-backup-system
```

Check for Docker socket permission issues:
```bash
docker exec bella-backup-system ls -la /var/run/docker.sock
```

### "Backup failed"
1. Check the error message in History tab
2. View logs: `docker logs bella-backup-system`
3. Verify container volumes are accessible

### "Can't access web interface"
```bash
# Check if container is running
docker ps | grep bella

# Check logs
docker logs bella-backup-system

# Try port 5000
http://localhost:5000
```

## 🔧 Configuration

### Change Backup Time

Edit `docker-compose.yml`:
```yaml
environment:
  - BACKUP_TIME=02:30  # Change to 2:30 AM
  - TZ=Europe/Berlin   # Set your timezone
```

Then restart:
```bash
docker-compose restart
```

### Change Backup Directory

Backup directory is mounted as `bella-backups` Docker volume. To use a local directory instead, modify `docker-compose.yml`:

```yaml
volumes:
  bella:
    driver: local
    driver_opts:
      type: none
      o: bind
      device: /path/to/local/backups  # Your path here
```

## 📊 API Examples

### Get all containers
```bash
curl http://localhost:5000/api/containers
```

### Get backup statistics
```bash
curl http://localhost:5000/api/stats
```

### Get backup history
```bash
curl http://localhost:5000/api/backups
```

### Enable backup for container ID 1
```bash
curl -X POST http://localhost:5000/api/container/1/enable
```

### Trigger manual backup for container ID 1
```bash
curl -X POST http://localhost:5000/api/container/1/backup
```

## 🧹 Maintenance

### View Logs
```bash
docker logs -f bella-backup-system
```

### Stop Bella
```bash
docker-compose down
```

### Remove all data (WARNING: Deletes backups!)
```bash
docker-compose down -v
```

### Update Bella
```bash
docker-compose pull
docker-compose up -d
```

## ⚙️ Environment Variables

Set in `docker-compose.yml`:

| Variable | Default | Purpose |
|----------|---------|---------|
| `BACKUP_TIME` | `01:00` | Time for automatic backups (HH:MM) |
| `BACKUP_DIR` | `/backups` | Directory to store backups |
| `TZ` | `Europe/Berlin` | Timezone for scheduling |
| `FLASK_ENV` | `production` | Flask environment mode |
| `DATABASE_PATH` | `/app/data/bella.db` | Database file location |

## 📝 Backup Filename Format

Backups are named:
```
{container_name}_{volume_name}_{timestamp}.tar.gz
```

Example:
```
postgres_data_20240227_011234.tar.gz
redis_config_20240227_011234.tar.gz
```

## ✅ Next Steps

1. **Monitor First Backup**: Wait until 1:00 AM and check if backups ran
2. **Test Manual Backup**: Click backup button to test immediately
3. **Check Backup Integrity**: Extract and verify a backup file
4. **Setup Retention**: Consider setting up automatic cleanup for old backups
5. **Plan Restore**: Document your restore procedure

## 🆘 Getting Help

1. Check logs: `docker logs bella-backup-system`
2. Read README.md for detailed information
3. Check API health: `curl http://localhost:5000/health`
4. Verify Docker: `docker ps` and `docker volume ls`

## 🎯 Pro Tips

- 💾 Regularly download and store backups off-site
- 🔔 Set calendar reminders to verify backups are running
- 📊 Monitor backup size and adjust retention if needed
- 🔒 Keep backup files in a secure location
- 📱 Consider backing up the backup location itself!

## 🚀 Advanced

### Custom Backup Time per Container
- Currently all containers backup at same time
- Feature for individual schedules can be added

### Incremental Backups
- Current backups are full (not incremental)
- Future enhancement: differential backup support

### Backup Encryption
- Backups are currently unencrypted
- You can manually encrypt via: `gpg -c backup.tar.gz`

### Remote Storage
- Currently backups stored locally
- Future: S3, FTP, or cloud storage support

---

**Bella v1.0** - Happy Backing Up! 🎉
