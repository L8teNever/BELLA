# Docker Container Backup Manager

Eine webbasierte Python-Anwendung zur Verwaltung von Docker-Container-Backups mit automatischer Zeitplanung.

## Features

- **Container-Management**: Anzeige aller laufenden Docker-Container mit detaillierten Informationen
- **Manuelle Backups**: Erstelle Backups einzelner Container mit Klick auf einen Button
- **Automatische Backups**: Zeitgesteuerte Backups mit Cron-Expressions
- **Backup-Verwaltung**: Download, Upload und Wiederherstellung von Backups
- **Flexible Backup-Optionen**: Wähle, was du sichern möchtest:
  - Container Volumes
  - Container-Konfiguration
  - Datenbanken (MySQL, PostgreSQL, MongoDB)
  - Container-Images
- **ZIP-Archive**: Alle Backups werden als komprimierte ZIP-Dateien gespeichert
- **Wiederherstellung**: Backups mit individuellen Pfad-Einstellungen wiederherstellen
- **Responsive Web-Interface**: Funktioniert auf Desktop, Tablet und Mobilgeräten

## Installation

### Voraussetzungen

- Python 3.8+
- Docker und Docker-Socket Zugriff
- pip (Python Package Manager)

### Setup

1. **Abhängigkeiten installieren**:
```bash
pip install -r requirements.txt
```

2. **Docker-Socket-Berechtigungen** (Linux):
```bash
# Der Benutzer muss Docker-Berechtigungen haben
sudo usermod -aG docker $USER
newgrp docker
```

### Starten der Anwendung

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Öffne dann im Browser: **http://localhost:8000**

### Mit Docker ausführen

```dockerfile
docker run -it \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -v $(pwd)/backups:/app/backups \
  -p 8000:8000 \
  docker-backup-manager
```

## Verwendung

### Container anzeigen

Im Tab **"Container"** werden alle laufenden Docker-Container angezeigt mit:
- Container-Name und ID
- Aktueller Status (Running, Exited, etc.)
- Container-Image
- Volumes
- Erstellungsdatum

### Manuelles Backup erstellen

1. Gehe zum Tab **"Container"**
2. Wähle einen Container
3. Klicke "**Backup erstellen**"
4. Das Backup wird sofort erstellt und als ZIP gespeichert

### Automatische Backups planen

1. Gehe zum Tab **"Zeitpläne"**
2. Klicke "**Zeitplan hinzufügen**"
3. Wähle einen Container und gebe eine Cron-Expression ein
4. Beispiele:
   - `0 2 * * *` = Täglich um 2:00 Uhr
   - `0 */6 * * *` = Alle 6 Stunden
   - `0 0 * * 0` = Sonntags um 00:00 Uhr
5. Wähle, was gebackupt werden soll
6. Speichern

### Backups verwalten

Im Tab **"Backups"** kannst du:

- **Statistiken sehen**: Anzahl Backups, Gesamtgröße, ältestes und neustes Backup
- **Download**: Backup-ZIP herunterladen
- **Restore**: Backup wiederherstellen mit Pfad-Auswahl
- **Löschen**: Alte Backups entfernen
- **Hochladen**: Neue Backup-Dateien hochladen

### Backup wiederherstellen

1. Im Tab **"Backups"** auf "**Restore**" klicken
2. Zielverzeichnis eingeben (z.B. `/data/restored`)
3. Wählen, was wiederhergestellt werden soll
4. Auf "**Wiederherstellen**" klicken

## Konfiguration

Die Konfiguration erfolgt in `app/config.py`:

```python
# Backup-Speicherort
backup_dir = Path("backups")

# Maximale Backup-Größe (10GB)
max_backup_size = 10 * 1024 * 1024 * 1024

# Aufbewahrungsdauer in Tagen (alte Backups automatisch löschen)
backup_retention_days = 30

# Kompressionslevel (0-9, 6 ist Standard)
compress_level = 6
```

Oder mit Umgebungsvariablen in `.env`:
```
BACKUP_DIR=/path/to/backups
BACKUP_RETENTION_DAYS=30
```

## API-Endpunkte

### Container

```
GET  /api/containers              # Alle Container auflisten
GET  /api/containers/{id}         # Container-Details
GET  /api/containers/{id}/logs    # Container-Logs
```

### Backups

```
GET    /api/backups                              # Alle Backups
GET    /api/backups/stats                        # Backup-Statistiken
POST   /api/containers/{id}/backup               # Backup erstellen
GET    /api/backups/{filename}/download          # Backup herunterladen
POST   /api/backups/upload                       # Backup hochladen
POST   /api/backups/{filename}/restore           # Backup wiederherstellen
DELETE /api/backups/{filename}                   # Backup löschen
POST   /api/backups/{filename}/validate          # Backup validieren
```

### Zeitpläne

```
GET    /api/schedules                # Alle Zeitpläne
POST   /api/schedules                # Zeitplan erstellen
GET    /api/schedules/{id}           # Zeitplan-Details
POST   /api/schedules/{id}/trigger   # Zeitplan manuell auslösen
DELETE /api/schedules/{id}           # Zeitplan löschen
```

### System

```
GET /api/info     # Systeminformationen
GET /api/health   # Health Check
```

## Backup-Format

Jedes Backup ist eine ZIP-Datei mit folgendem Aufbau:

```
backup_containername_20260302_143022.zip
├── metadata.json           # Backup-Metadaten
├── volumes/
│   ├── volume1.tar
│   └── volume2.tar
├── config/
│   ├── container_inspect.json
│   └── docker-compose.yml
├── database/
│   └── db_dump.sql
└── image/
    └── container_image.tar
```

## Logging

Logs werden in `logs/app.log` gespeichert und zeigen:
- Backup-Vorgänge
- Docker-Verbindung
- API-Requests
- Fehler und Warnungen

```bash
# Logs anschauen
tail -f logs/app.log

# Log-Größe limitieren (Windows)
Get-ChildItem logs/app.log | Select-Object -ExpandProperty Length
```

## Fehlerbehandlung

### Docker nicht verbunden

- Überprüfe, ob Docker läuft: `docker ps`
- Überprüfe Docker-Socket-Berechtigungen: `ls -la /var/run/docker.sock`
- Füge Benutzer zu Docker-Gruppe hinzu: `sudo usermod -aG docker $USER`

### Backup-Fehler

- Überprüfe Speicherplatz: `df -h`
- Überprüfe Backup-Verzeichnis-Berechtigungen
- Überprüfe Container-Status: `docker inspect <container-id>`

### Wiederherstellungs-Fehler

- Stelle sicher, dass das Zielverzeichnis existiert
- Überprüfe Schreibberechtigungen für das Zielverzeichnis
- Validiere das Backup: `/api/backups/{filename}/validate`

## Performance-Tipps

1. **Große Backups**: Starte Backups nachts außerhalb von Spitzenlastzeiten
2. **Speicher**: Überwache `backup_retention_days` und räume alte Backups auf
3. **Netzwerk**: Bei großen Backups erhöhe das Upload-Limit in `config.py`
4. **Datenbanken**: Nutze native DB-Dumps statt komplette Container-Volumes

## Sicherheit

- Der Docker-Socket sollte nur dem Anwendungsbenutzer zugänglich sein
- Backups enthalten sensible Daten - sicher den Backup-Speicher!
- Verwende HTTPS in Produktionsumgebungen (nginx-Reverse-Proxy)
- Schränke API-Zugriff mit Authentifizierung ein (zukünftige Erweiterung)

## Zukünftige Verbesserungen

- [ ] Benutzer-Authentifizierung und Autorisierung
- [ ] Backup-Verschlüsselung
- [ ] Cloud-Storage-Integration (S3, Azure)
- [ ] Email-Benachrichtigungen
- [ ] Backup-Vergleich und Versionierung
- [ ] Inkrementelle Backups
- [ ] Multi-Container Backups
- [ ] Backup-Vorschau

## Lizenz

MIT

## Support

Bei Fragen oder Problemen, überprüfe:
1. Logs in `logs/app.log`
2. Browser-Konsole (F12) auf JavaScript-Fehler
3. Docker-Verbindung: `docker ps`
4. API-Erreichbarkeit: `curl http://localhost:8000/api/health`

---

**Version**: 1.0.0
**Letztes Update**: 2026-03-02
