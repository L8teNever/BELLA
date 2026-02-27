# Bella auf Linux Server deployen

Diese Anleitung zeigt, wie du Bella auf einem Linux Server mit Docker startest.

## 📋 Voraussetzungen

- Linux Server (Ubuntu, Debian, CentOS, etc.)
- Docker installiert
- Docker Compose installiert
- Root/Sudo Zugriff (für `/var/run/docker.sock`)

### Docker & Docker Compose prüfen

```bash
docker --version
docker-compose --version
```

Falls nicht installiert:

**Ubuntu/Debian:**
```bash
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER
newgrp docker
```

## 🚀 Schnellstart (2 Optionen)

### Option A: Mit Repository klonen (Empfohlen)

```bash
# 1. Repository klonen
cd /opt/stacks  # oder ein anderes Verzeichnis
git clone https://github.com/L8teNever/BELLA.git bella-backup-system
cd bella-backup-system

# 2. Mit docker-compose starten
docker-compose up -d

# 3. Überprüfe Status
docker-compose logs -f

# 4. Öffne im Browser
# http://YOUR_SERVER_IP:5000
```

### Option B: Nur mit Docker Hub Image (Schneller)

```bash
# 1. Verzeichnis erstellen
mkdir -p /opt/stacks/bella-backup-system
cd /opt/stacks/bella-backup-system

# 2. docker-compose.yml erstellen
cat > docker-compose.yml << 'EOF'
version: '3.8'
services:
  bella:
    image: L8teNever/bella:latest
    container_name: bella-backup-system
    ports:
      - "5000:5000"
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
      - bella-db:/app/data
      - bella-backups:/backups
    environment:
      - BACKUP_DIR=/backups
      - DATABASE_PATH=/app/data/bella.db
      - BACKUP_TIME=01:00
      - TZ=Europe/Berlin
      - FLASK_ENV=production
    restart: always

volumes:
  bella-db:
    name: bella-database
  bella-backups:
    name: bella-backup-storage
EOF

# 3. Starten
docker-compose up -d

# 4. Browser öffnen
# http://YOUR_SERVER_IP:5000
```

## ✅ Überprüfung

### Container laufen?
```bash
docker ps | grep bella
```

### Logs anschauen?
```bash
docker logs -f bella-backup-system
```

### Health Check?
```bash
curl http://localhost:5000/health
```

### Web-UI erreichbar?
```bash
curl http://localhost:5000
```

## 📊 Docker Socket Permissions (wichtig!)

Das Docker Socket muss lesbar/schreibbar sein:

```bash
# Status prüfen
ls -la /var/run/docker.sock

# Falls Fehler → Docker-Gruppe hinzufügen
sudo usermod -aG docker $(whoami)
newgrp docker

# Container neu starten
docker-compose restart bella
```

## 🔧 Konfiguration anpassen

Bearbeite `docker-compose.yml` und ändere:

```yaml
environment:
  - BACKUP_TIME=02:30        # Backup-Zeit ändern
  - TZ=Europe/Amsterdam      # Zeitzone ändern
  - FLASK_ENV=development    # Debug-Mode
```

Dann neu starten:
```bash
docker-compose down
docker-compose up -d
```

## 💾 Backups Speicherort

Backups werden in Docker Volume `bella-backups` gespeichert.

### Überprüfe Speicher:
```bash
docker exec bella-backup-system du -sh /backups
```

### Kopiere Backups zum Host:
```bash
docker cp bella-backup-system:/backups ./local-backups
```

### Nutze anderes Verzeichnis:
Ändere in `docker-compose.yml`:

```yaml
volumes:
  bella-backups:
    driver: local
    driver_opts:
      type: none
      o: bind
      device: /mnt/backups  # Dein Pfad
```

## 🔄 Container verwalten

```bash
# Starten
docker-compose up -d

# Stoppen
docker-compose down

# Logs
docker-compose logs -f

# Neustart
docker-compose restart bella

# Status
docker-compose ps
```

## 🐛 Troubleshooting

### "Cannot connect to Docker daemon"
```bash
sudo usermod -aG docker $USER
newgrp docker
docker-compose restart
```

### "Port 5000 already in use"
Ändere in `docker-compose.yml`:
```yaml
ports:
  - "8080:5000"  # Nutze Port 8080 statt 5000
```

### "Docker socket permission denied"
```bash
sudo chmod 666 /var/run/docker.sock
```

### Container startet nicht
```bash
docker-compose logs bella
docker-compose up  # Ohne -d um Fehler zu sehen
```

## 🌐 Firewall öffnen

Falls Bella nicht erreichbar ist:

**UFW (Ubuntu):**
```bash
sudo ufw allow 5000/tcp
sudo ufw reload
```

**FirewallD (CentOS/RHEL):**
```bash
sudo firewall-cmd --add-port=5000/tcp --permanent
sudo firewall-cmd --reload
```

**iptables:**
```bash
sudo iptables -A INPUT -p tcp --dport 5000 -j ACCEPT
```

## 📈 Monitoring

### Container CPU/Memory:
```bash
docker stats bella-backup-system
```

### Logs filtern:
```bash
# Nur Fehler
docker logs bella-backup-system | grep ERROR

# Letzten 50 Zeilen
docker logs -n 50 bella-backup-system

# Real-time
docker logs -f bella-backup-system
```

## 🔐 Sicherheit

### Reverse Proxy mit nginx (Optional)

Erstelle `/etc/nginx/sites-available/bella`:

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://localhost:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

Enable:
```bash
sudo ln -s /etc/nginx/sites-available/bella /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

### SSL/HTTPS mit Let's Encrypt:
```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
```

## 📅 Regelmäßige Wartung

### Alte Docker Images löschen:
```bash
docker image prune -a --force
```

### Ungenutzte Volumes löschen:
```bash
docker volume prune
```

### System aufräumen:
```bash
docker system prune -a
```

## 📝 Systemd Service (Optional)

Erstelle `/etc/systemd/system/bella.service`:

```ini
[Unit]
Description=Bella Backup System
After=docker.service
Requires=docker.service

[Service]
Type=oneshot
WorkingDirectory=/opt/stacks/bella-backup-system
ExecStart=/usr/bin/docker-compose up -d
ExecStop=/usr/bin/docker-compose down
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
```

Enable:
```bash
sudo systemctl daemon-reload
sudo systemctl enable bella.service
sudo systemctl start bella.service
```

## 🎯 Next Steps

1. ✅ Starten: `docker-compose up -d`
2. ✅ Browser: `http://SERVER_IP:5000`
3. ✅ Container für Backups auswählen
4. ✅ Warten bis 1:00 Uhr für automatische Backups
5. ✅ History überprüfen

---

**Fragen?** Check die Logs: `docker logs bella-backup-system`

**Viel Erfolg!** 🚀
