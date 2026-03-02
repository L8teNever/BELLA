# Docker Container Backup Manager - Deployment Guide

## Lokale Entwicklung

```bash
# Mit lokalem Dockerfile Build
docker-compose -f docker-compose.dev.yml up -d

# Logs
docker-compose -f docker-compose.dev.yml logs -f

# Stoppen
docker-compose -f docker-compose.dev.yml down
```

## Production Deployment

### Variante 1: Von GitHub Container Registry (EMPFOHLEN)

```bash
# Gehe in das korrekte Verzeichnis
cd /path/to/BELLA

# Verwende die Production Compose Datei
docker-compose -f docker-compose.prod.yml up -d

# Oder vereinfacht (wenn du im Projekt-Root bist)
docker pull ghcr.io/l8tenever/bella:latest
docker-compose up -d
```

**Vorteile:**
- ✅ Keine Abhängigkeit vom lokalen Dockerfile
- ✅ Schneller (vorgefertigtes Image)
- ✅ Einfaches Update: `docker-compose pull && docker-compose up -d`

### Variante 2: Lokaler Build (wenn sich die Datei im Verzeichnis befindet)

```bash
# Stelle sicher, dass du im richtigen Verzeichnis bist
pwd
# Output: /path/to/BELLA

# Build und Start
docker-compose build
docker-compose up -d
```

### Variante 3: Manueller Build für einen anderen Speicherort

```bash
# Wenn docker-compose von einem anderen Ort aus läuft:
cd /path/to/BELLA
docker build -t docker-backup-manager:latest .
docker run -d \
  --name docker-backup-manager \
  -p 8000:8000 \
  -v /var/run/docker.sock:/var/run/docker.sock:ro \
  -v backup-data:/app/backups \
  -v log-data:/app/logs \
  docker-backup-manager:latest
```

## Dein Fehler beheben

Du bekommst: `failed to read dockerfile: open Dockerfile: no such file or directory`

**Lösung:**

1. **Überprüfe dein aktuelles Verzeichnis:**
```bash
pwd
ls -la | grep -E "Dockerfile|docker-compose"
```

2. **Falls die Datei nicht dort ist:**
```bash
# Gehe zum Projekt-Root
cd /path/to/BELLA

# Überprüfe dass alles da ist
ls -la Dockerfile docker-compose*.yml
```

3. **Verwende die richtige Compose-Datei:**
```bash
# Production (mit GitHub Image, kein lokaler Build nötig)
docker-compose -f docker-compose.prod.yml up -d

# ODER du kannst die Standard-Datei umbenennen:
cp docker-compose.prod.yml docker-compose.yml
docker-compose up -d
```

## Systemd Service (Linux)

Erstelle `/etc/systemd/system/bella-docker.service`:

```ini
[Unit]
Description=BELLA Docker Container Backup Manager
After=docker.service
Requires=docker.service

[Service]
Type=oneshot
WorkingDirectory=/path/to/BELLA
ExecStart=/usr/bin/docker-compose -f docker-compose.prod.yml up -d
ExecStop=/usr/bin/docker-compose -f docker-compose.prod.yml down
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
```

```bash
# Aktivieren und starten
sudo systemctl daemon-reload
sudo systemctl enable bella-docker
sudo systemctl start bella-docker

# Status überprüfen
sudo systemctl status bella-docker
```

## Häufige Probleme

### Problem: "Dockerfile: No such file or directory"

**Ursache:** docker-compose läuft vom falschen Ort aus

**Lösung:**
```bash
# Variante 1: Zum Projekt-Root wechseln
cd /path/to/BELLA
docker-compose up -d

# Variante 2: Absoluter Pfad in compose.yml
# services:
#   docker-backup-manager:
#     build:
#       context: /path/to/BELLA
#       dockerfile: /path/to/BELLA/Dockerfile

# Variante 3: Image statt Build verwenden (EMPFOHLEN)
docker-compose -f docker-compose.prod.yml up -d
```

### Problem: Docker-Socket nicht zugänglich

```bash
# Überprüfe Socket-Berechtigungen
ls -la /var/run/docker.sock

# Add user to docker group
sudo usermod -aG docker $USER
newgrp docker

# Oder nutze sudo
sudo docker-compose up -d
```

### Problem: Port 8000 schon in Verwendung

```bash
# Finde Prozess auf Port 8000
lsof -i :8000

# Oder ändere den Port in docker-compose.yml
# ports:
#   - "9000:8000"
```

### Problem: Volumen-Berechtigungen

```bash
# Überprüfe Volumen
docker volume ls
docker volume inspect backup-data

# Räume auf Backups auf (falls nötig)
docker volume rm backup-data log-data
```

## Monitoring

```bash
# Container Status
docker ps | grep docker-backup-manager

# Logs Live
docker logs -f docker-backup-manager

# Ressourcen-Verwendung
docker stats docker-backup-manager

# Health Check
curl http://localhost:8000/api/health
```

## Backups

Die Daten werden in Named Volumes gespeichert:
```bash
# Backup exportieren
docker run --rm -v backup-data:/data -v $(pwd):/backup \
  alpine tar czf /backup/backup-data.tar.gz -C /data .

# Backup wiederherstellen
docker run --rm -v backup-data:/data -v $(pwd):/backup \
  alpine tar xzf /backup/backup-data.tar.gz -C /data
```

## Update durchführen

```bash
# Neue Version pullen
docker-compose pull

# Stoppen und neustarten
docker-compose up -d

# Oder alles auf einmal
docker-compose pull && docker-compose up -d
```

## Zusammenfassung

**EMPFOHLENE PRODUCTION-SETUP:**

```bash
cd /path/to/BELLA
docker-compose -f docker-compose.prod.yml up -d
```

Das ist am sichersten, da es:
- ✅ Kein lokales Build braucht
- ✅ Konsistent funktioniert
- ✅ Schnell ist
- ✅ Einfach zu updaten ist
