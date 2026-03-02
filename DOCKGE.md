# Docker Container Backup Manager in Dockge einrichten

## Was ist Dockge?

Dockge ist ein einfaches, modernes Docker Management Interface. Mit Dockge kannst du:
- Docker Container verwalten
- Docker Compose Projekte starten/stoppen
- Logs anschauen
- Container-Status überwachen

## Installation in Dockge

### Schritt 1: Dockge öffnen

Öffne dein Dockge Interface:
- URL: `http://localhost:5001` (oder deine Dockge-IP)

### Schritt 2: Neues Compose Projekt erstellen

1. Klicke auf **"Compose"** oder **"New Project"**
2. Gib einen Namen ein: `bella` oder `docker-backup-manager`
3. Wähle **"From URL"** oder **"From File"**

### Option A: From GitHub (EINFACHSTE VARIANTE)

1. Klicke auf **"From URL"** oder **"Import from URL"**
2. Gib diese URL ein:
```
https://raw.githubusercontent.com/L8teNever/BELLA/main/docker-compose.yml
```
3. Klicke **"Create"**
4. Das Projekt wird automatisch erstellt und gestartet

### Option B: Manuell einfügen

1. Klicke auf **"Create Compose Project"**
2. Wähle **"Compose String"** oder Editor
3. Kopiere diesen Code:

```yaml
services:
  docker-backup-manager:
    image: ghcr.io/l8tenever/bella:latest
    container_name: docker-backup-manager
    ports:
      - "8000:8000"
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock:ro
      - backup-data:/app/backups
      - log-data:/app/logs
    environment:
      - DEBUG=False
      - BACKUP_RETENTION_DAYS=30
      - SCHEDULER_TIMEZONE=UTC
      - MAX_BACKUP_SIZE=10737418240
      - COMPRESS_LEVEL=6
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/api/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 5s

volumes:
  backup-data:
    driver: local
  log-data:
    driver: local
```

4. Klicke **"Create & Deploy"** oder **"Save & Deploy"**

## Schritt 3: Container starten

Dockge wird den Container automatisch starten:
1. Warte ~10 Sekunden bis der Container hochfährt
2. Der Status sollte **"Running"** anzeigen (grün)
3. Health Check sollte bestanden sein ✅

## Schritt 4: Auf die Anwendung zugreifen

Öffne im Browser:
```
http://localhost:8000
```

oder

```
http://<dein-server>:8000
```

Du solltest jetzt das Docker Backup Manager Interface sehen!

## Dockge Integration

In Dockge kannst du nun:

### Container verwalten
- ✅ Start/Stop/Restart Button
- ✅ Logs anschauen (Klick auf "Logs" Tab)
- ✅ Ressourcen-Überwachung (CPU, RAM)
- ✅ Container-Details

### Probleme beheben

**Container startet nicht?**
1. Gehe zum **"Logs"** Tab in Dockge
2. Schau nach Fehlern
3. Überprüfe Docker Socket: `docker ps`

**Health Check Failed?**
```bash
# Von außerhalb in Dockge Logs überprüfen
docker logs docker-backup-manager
```

**Port 8000 nicht erreichbar?**
```bash
# In Dockge: Gehe zu Container → Ports → überprüfe ob 8000 gemappt ist
```

## Dockge Commands (falls nötig)

Wenn du in der Command Line arbeiten willst:

```bash
# Projekt Status in Dockge
dockge ps

# Logs anschauen
dockge logs docker-backup-manager

# Neu starten
dockge restart docker-backup-manager

# Image updaten (neue Version)
dockge pull docker-backup-manager
dockge restart docker-backup-manager
```

## Updates durchführen

Wenn es ein neues Update gibt:

### In Dockge UI:
1. Gehe zum Projekt
2. Klick auf **"Pull"** oder **"Update Image"**
3. Container wird automatisch neu gestartet

### Oder manuell:
```bash
dockge pull ghcr.io/l8tenever/bella:latest
dockge restart docker-backup-manager
```

## Backup der Daten

### In Dockge:

Die Daten werden in Named Volumes gespeichert:
- `backup-data` → Alle Backups
- `log-data` → Alle Logs

Du kannst diese in Dockge sehen unter:
- **Volumes** Tab

### Backup exportieren:

```bash
# Backup-Daten exportieren
docker run --rm -v backup-data:/data -v $(pwd):/backup \
  alpine tar czf /backup/bella-backups.tar.gz -C /data .

# Log-Daten exportieren
docker run --rm -v log-data:/data -v $(pwd):/backup \
  alpine tar czf /backup/bella-logs.tar.gz -C /data .
```

## Troubleshooting

### Problem: Image kann nicht gepullt werden

**Lösung:**
```bash
# Docker Login zu GitHub Container Registry
docker login ghcr.io

# Username: dein-github-username
# Password: dein-github-token (mit read:packages permission)

# Dann nochmal in Dockge versuchen
```

### Problem: Docker Socket nicht erreichbar

**In Dockge Logs:**
```
Cannot connect to Docker daemon
```

**Lösung:**
```bash
# Überprüfe Docker Status
docker ps

# Falls nicht läuft
sudo systemctl start docker

# Überprüfe Socket
ls -la /var/run/docker.sock
```

### Problem: Port 8000 schon vergeben

**Lösung in Dockge:**
1. Gehe zum Container
2. Klick auf **"Edit"**
3. Ändere Port: `"8001:8000"` statt `"8000:8000"`
4. Save & Deploy
5. Öffne dann `http://localhost:8001`

## Automatische Updates mit Dockge

Dockge kann automatisch Updates durchführen:

1. In Dockge: **Settings** → **Auto Update**
2. Aktiviere: **"Auto Update Image"**
3. Setz Interval: **Daily** oder **Weekly**
4. Speichern

Dann wird Dockge automatisch neue Images pullen und Container neu starten!

## Tipps & Tricks

### 1. Compose File im GitHub speichern

Dein docker-compose.yml ist bereits im GitHub:
```
https://github.com/L8teNever/BELLA/blob/main/docker-compose.yml
```

### 2. Mehrere Services mit Dockge

Du kannst mehrere Services (z.B. Datenbanken) zusammen starten:

```yaml
services:
  docker-backup-manager:
    image: ghcr.io/l8tenever/bella:latest
    # ... (siehe oben)

  # Optional: Wenn du auch Daten-Backups machen willst
  backup-scheduler:
    image: ghcr.io/l8tenever/bella:latest
    # ... weitere Config
```

### 3. Environment Variablen anpassen

In Dockge kannst du Environment Variablen direkt im UI ändern:
1. Container → Edit
2. Environment Variablen bearbeiten
3. Container wird neu gestartet

## Health Check Status

Der Container hat einen Health Check. Du sehen kannst in Dockge:

- 🟢 **Healthy** = Alles funktioniert
- 🟡 **Starting** = Container startet gerade auf
- 🔴 **Unhealthy** = Fehler vorhanden

Wenn Unhealthy: Schau in die Logs!

## Zusammenfassung

**Schnellstart in Dockge:**

1. Öffne Dockge UI (`http://localhost:5001`)
2. Klick **"New Project"** → **"From URL"**
3. URL eingeben:
   ```
   https://raw.githubusercontent.com/L8teNever/BELLA/main/docker-compose.yml
   ```
4. Klick **"Create & Deploy"**
5. Warte 10 Sekunden
6. Öffne `http://localhost:8000` in Browser
7. Fertig! 🎉

---

**Weitere Hilfe:**
- Dockge Docs: https://dockge.kuma.pet/
- BELLA GitHub: https://github.com/L8teNever/BELLA
- Deployment Guide: Siehe DEPLOYMENT.md im Repo
