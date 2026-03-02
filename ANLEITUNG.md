# Docker Container Backup Manager - Schnellstart-Anleitung

## Schritt 1: Installation

### Linux/MacOS

```bash
# 1. Abhängigkeiten installieren
pip install -r requirements.txt

# 2. Docker-Berechtigungen (wenn nötig)
sudo usermod -aG docker $USER
newgrp docker

# 3. Verzeichnisse erstellen
mkdir -p backups logs
```

### Windows

```bash
# 1. Abhängigkeiten installieren
pip install -r requirements.txt

# 2. Docker Desktop muss laufen
# (Docker Desktop muss installiert und gestartet sein)

# 3. Verzeichnisse werden automatisch erstellt
```

## Schritt 2: Anwendung starten

### Option A: Lokal mit uvicorn

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Öffne dann: **http://localhost:8000**

### Option B: Mit Docker Compose

```bash
# Bauen und starten
docker-compose up -d

# Logs anschauen
docker-compose logs -f

# Stoppen
docker-compose down
```

### Option C: Nur Docker

```bash
# Bauen
docker build -t docker-backup-manager .

# Ausführen
docker run -it \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -v $(pwd)/backups:/app/backups \
  -v $(pwd)/logs:/app/logs \
  -p 8000:8000 \
  docker-backup-manager
```

## Schritt 3: Web-Interface öffnen

Öffne im Browser: **http://localhost:8000**

Du solltest die Hauptseite sehen mit 4 Tabs:
1. **Container** - Zeigt alle Docker-Container
2. **Backups** - Verwalte Backups
3. **Zeitpläne** - Automatische Backups planen
4. **Info** - Systeminformationen

## Schritt 4: Erstes Backup erstellen

1. Gehe zum Tab **"Container"**
   - Du solltest alle laufenden Docker-Container sehen
   - Falls keine Container sichtbar sind, überprüfe Docker-Verbindung

2. Klicke auf einen Container und dann "**Backup erstellen**"
   - Der Backup-Vorgang startet
   - Im unteren Bereich siehst du eine Benachrichtigung

3. Gehe zum Tab **"Backups"**
   - Dein neues Backup sollte in der Liste erscheinen
   - Größe, Datum und Inhalte werden angezeigt

## Schritt 5: Automatische Backups einrichten

1. Gehe zum Tab **"Zeitpläne"**
2. Klicke "**Zeitplan hinzufügen**"
3. Wähle einen Container
4. Gebe eine Cron-Expression ein, z.B.:
   - `0 2 * * *` = Täglich um 2:00 Uhr
   - `0 */4 * * *` = Alle 4 Stunden
   - `30 1 * * 0` = Sonntags um 01:30 Uhr
5. Klicke "**Erstellen**"

Der Scheduler wird automatisch zur festgelegten Zeit die Backups erstellen.

## Fehlerbehebung

### Problem: "Docker nicht verbunden"

**Lösung:**

Linux:
```bash
# Docker-Berechtigungen setzen
sudo usermod -aG docker $USER
newgrp docker

# Docker-Socket überprüfen
ls -la /var/run/docker.sock

# Docker-Service starten
sudo systemctl start docker
```

Windows:
- Docker Desktop muss laufen
- Öffne Docker Desktop Application
- Überprüfe Systemtray-Icon

### Problem: Keine Container sichtbar

```bash
# Überprüfe ob Container existieren
docker ps

# Wenn leer, starte einen Test-Container
docker run -d --name test-nginx nginx
```

### Problem: "Permission denied" beim Backup

```bash
# Überprüfe Backup-Verzeichnis-Berechtigungen
ls -la backups/

# Behebe es
chmod 755 backups/
```

### Problem: Scheduler startet nicht

```bash
# Überprüfe Logs
tail -f logs/app.log

# Neustart
# Stoppe die Anwendung (Ctrl+C) und starte neu
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## Wichtige Befehle

```bash
# Logs anschauen
tail -f logs/app.log

# Container-Liste überprüfen
docker ps

# Backup-Dateien anschauen
ls -lh backups/

# API-Health überprüfen
curl http://localhost:8000/api/health

# Alle Container-Info
curl http://localhost:8000/api/containers | python -m json.tool

# Anwendung neu starten
# Drücke Ctrl+C und starte erneut
```

## Grundlegende Konzepte

### Cron-Expressions

Format: `Minute Stunde Tag Monat Wochentag`

Beispiele:
```
0 2 * * *      → Täglich um 02:00 Uhr
*/5 * * * *    → Alle 5 Minuten
0 */6 * * *    → Alle 6 Stunden
0 0 * * 0      → Wöchentlich (Sonntag, 00:00)
0 0 1 * *      → Monatlich (1. Tag, 00:00)
```

### Backup-Inhalte

- **Volumes**: Persistente Daten des Containers
- **Config**: Container-Konfiguration und Metadaten
- **Database**: DB-Dumps (MySQL, PostgreSQL, MongoDB)
- **Image**: Container-Image (optional, große Dateien)

## Performance-Tipps

1. **Nachts backen**: Starte automatische Backups außerhalb von Spitzenlastzeiten
2. **Speicher überwachen**: `df -h` zeigt verfügbaren Speicher
3. **Alte Backups löschen**: Nutze Backup-Retention in der Config
4. **DB-Dumps separieren**: Backup nur Datenbank, nicht ganzer Container

## Web-Interface Tipps

- **Tab-Reiter**: Mit Pfeilen navigierst du zwischen Container, Backups, Zeitpläne, Info
- **Auto-Refresh**: Seite aktualisiert sich automatisch alle 30 Sekunden
- **Manuelle Aktualisierung**: Klick auf "Aktualisieren" Button
- **Drag & Drop**: Ziehe ZIP-Dateien per Drag & Drop in Upload-Bereich
- **Responsive Design**: Funktioniert auch auf Mobilgeräten

## Produktives Setup

Für eine produktive Nutzung:

```bash
# 1. Erstelle .env Datei
cp .env.example .env
# Bearbeite .env mit Deinen Settings

# 2. Starte mit Docker Compose
docker-compose up -d

# 3. Überprüfe Health
docker-compose ps

# 4. Sieh dir Logs an
docker-compose logs -f

# 5. Öffne Browser
# http://localhost:8000
```

## Nächste Schritte

1. ✅ Anwendung gestartet
2. ✅ Erstes Backup erstellt
3. ✅ Zeitplan konfiguriert
4. Backups regelmäßig überprüfen
5. Alte Backups archivieren/löschen

## Hilfe & Support

- Überprüfe `logs/app.log` für Fehler
- Siehe `README.md` für detaillierte Dokumentation
- Überprüfe Docker-Verbindung: `docker ps`

---

**Viel Erfolg mit Docker Container Backup Manager!** 🐳💾
