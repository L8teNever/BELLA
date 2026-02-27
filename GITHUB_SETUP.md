# GitHub Setup für Bella

Diese Anleitung zeigt dir, wie du Bella auf GitHub hochlädst und automatische Docker Builds einrichtest.

## 📋 Voraussetzungen

- GitHub Account (kostenlos auf [github.com](https://github.com))
- Docker Hub Account (kostenlos auf [hub.docker.com](https://hub.docker.com))
- Git installiert auf deinem Computer

## 🚀 Schritt 1: GitHub Repository erstellen

### 1.1 Auf GitHub anmelden
Gehe zu [github.com](https://github.com) und melde dich an.

### 1.2 Neues Repository erstellen
1. Klicke **"+"** oben rechts
2. Wähle **"New repository"**
3. Gib folgende Daten ein:
   - **Repository name:** `bella` (oder nach Wunsch)
   - **Description:** "Docker Container Backup System"
   - **Visibility:** Public (damit Docker Hub kann bauen)
   - **Initialize:** NICHT ankreuzen (wir pushen lokal)
4. Klicke **"Create repository"**

### 1.3 Du erhältst eine URL
```
https://github.com/DEIN_USERNAME/bella.git
```

## 🔑 Schritt 2: Docker Hub API Token erstellen

### 2.1 Auf Docker Hub anmelden
Gehe zu [hub.docker.com](https://hub.docker.com)

### 2.2 Access Token erstellen
1. Klicke auf dein **Profil-Icon** oben rechts
2. Wähle **"Account Settings"**
3. Gehe zu **"Security"** tab
4. Klicke **"New Access Token"**
5. Gib einen Namen ein: `github-bella` (oder ähnlich)
6. **Read, Write, Delete** permissions wählen
7. Klicke **"Generate"**
8. **Kopiere den Token sofort!** (später nicht mehr sichtbar)

Du brauchst:
- **Docker Hub Username** (z.B. `deinname`)
- **Docker Hub Access Token** (der lange Code)

## 🔐 Schritt 3: GitHub Secrets einrichten

Diese sind erforderlich damit GitHub Actions Docker Images zu Docker Hub pushen kann.

### 3.1 Gehe zum Repository
1. Gehe auf GitHub zu deinem `bella` Repository
2. Klicke **"Settings"** (oben)
3. Wähle **"Secrets and variables"** → **"Actions"** (links)

### 3.2 Secrets hinzufügen
Klicke **"New repository secret"** und füge hinzu:

**Secret 1: DOCKER_HUB_USERNAME**
- Name: `DOCKER_HUB_USERNAME`
- Value: `dein_docker_hub_username` (z.B. `simonxy`)
- Klick **"Add secret"**

**Secret 2: DOCKER_HUB_ACCESS_TOKEN**
- Name: `DOCKER_HUB_ACCESS_TOKEN`
- Value: `der_token_den_du_oben_kopiert_hast`
- Klick **"Add secret"**

✅ Jetzt sollten beide Secrets in der Liste erscheinen!

## 📤 Schritt 4: Code zu GitHub pushen

Öffne Terminal/PowerShell im `BELLA` Verzeichnis und führe aus:

```bash
# Navigiere zum BELLA Verzeichnis
cd C:\Users\simon\Videos\BELLA

# Initialisiere Git Repository lokal
git init

# Konfiguriere Git (ersetze durch deine Daten)
git config user.email "deine@email.com"
git config user.name "Dein Name"

# Füge alle Dateien hinzu
git add .

# Erstelle ersten Commit
git commit -m "Initial commit: Bella backup system"

# Verbinde mit GitHub Repository
git remote add origin https://github.com/DEIN_USERNAME/bella.git

# Pushe zum GitHub (main branch)
git branch -M main
git push -u origin main
```

Wenn du gefragt wirst nach Anmeldedaten:
- **Username:** Dein GitHub Username
- **Password:** Dein GitHub Personal Access Token (siehe unten)

### GitHub Personal Access Token erstellen (falls nötig)
Falls du kein Token hast:
1. Gehe zu GitHub → **Settings** → **Developer settings** → **Personal access tokens** → **Tokens (classic)**
2. Klicke **"Generate new token"** → **"Generate new token (classic)"**
3. Gib Namen ein: `github-bella`
4. Wähle Scopes: `repo`, `workflow`
5. Klicke **"Generate token"**
6. **Kopiere sofort!** (später nicht mehr sichtbar)
7. Nutze diesen Token als "password" beim `git push`

## ✅ Schritt 5: Workflows verifizieren

Nach dem `git push`:

1. Gehe auf GitHub zu deinem Repository
2. Klicke **"Actions"** (oben)
3. Du solltest sehen:
   - **"Build and Push Docker Image to Docker Hub"** - läuft
   - **"Python Syntax & Quality Tests"** - läuft

Die Workflows sollten in **~2-3 Minuten** fertig sein.

## 📊 Was passiert automatisch:

### Beim Push zu main:
1. ✅ **Python Tests** laufen
   - Syntax-Checks
   - Import-Verification
   - Projektstruktur-Validierung

2. ✅ **Docker Build & Push**
   - Docker Image wird gebaut
   - Image wird zu Docker Hub gepusht
   - Tags: `latest`, Branch-Name, Git-SHA

### Docker Hub Image URLs:

Nach erfolgreichem Build:
```
docker pull dein_username/bella:latest
docker pull dein_username/bella:main
docker pull dein_username/bella:v1.0.0  (bei Tags)
```

## 🔄 Zukünftige Updates

Jedes Mal wenn du Code pushst:

```bash
# Nach einer Änderung
git add .
git commit -m "Beschreibung der Änderung"
git push

# Automatisch:
# 1. Tests laufen
# 2. Docker Image wird gebaut
# 3. Image wird zu Docker Hub gepusht
```

## 🐳 Mit gepushtem Image starten

Sobald das Image auf Docker Hub ist, kannst du es überall nutzen:

```bash
# Ziehe das Image
docker pull dein_username/bella:latest

# Starte mit docker-compose (lokal)
docker run -d \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -p 5000:5000 \
  dein_username/bella:latest
```

## 📝 Release erstellen (Tags)

Um eine offizielle Version zu releasen:

```bash
# Erstelle einen Git Tag
git tag -a v1.0.0 -m "Version 1.0.0: Initial Release"

# Pushe den Tag
git push origin v1.0.0

# Automatisch:
# - Docker Image wird gebaut
# - Tag `v1.0.0` wird zu Docker Hub gepusht
```

## 🐛 Troubleshooting

### GitHub Actions zeigt Fehler

1. Gehe zu **Actions** im Repository
2. Klicke auf den fehlgeschlagenen Workflow
3. Klicke auf den Job um Details zu sehen
4. **"Docker login failed"?** → Überprüfe die Secrets (DOCKER_HUB_USERNAME, DOCKER_HUB_ACCESS_TOKEN)

### Docker Hub Push schlägt fehl

```bash
# Überprüfe local
docker login
# Gib Username und Access Token ein

# Dann:
docker build -t dein_username/bella:latest .
docker push dein_username/bella:latest
```

### Workflow lädt nicht los

1. Überprüfe dass `.github/workflows/docker-build.yml` existiert
2. Stelle sicher dass du zu **main** branch gepusht hast
3. Warte 1-2 Minuten, dann refresh GitHub

## 🎯 Best Practices

1. **Committen vor Updates:**
   ```bash
   git status  # Überprüfe was geändert wurde
   ```

2. **Commits mit aussagekräftigen Messages:**
   ```bash
   git commit -m "Fix backup scheduler timing"
   ```

3. **Regelmäßig pullen** (wenn du von mehreren Orten arbeitest):
   ```bash
   git pull origin main
   ```

4. **Tags für Releases:**
   ```bash
   git tag v1.0.0
   git push --tags
   ```

## 📚 Weitere Ressourcen

- [Git Dokumentation](https://git-scm.com/doc)
- [GitHub Dokumentation](https://docs.github.com)
- [GitHub Actions](https://docs.github.com/actions)
- [Docker Hub](https://hub.docker.com)

---

**Alles fertig?** 🎉

Jetzt hast du:
- ✅ Bella auf GitHub
- ✅ Automatische Docker Builds
- ✅ Images auf Docker Hub verfügbar

Viel Erfolg! 🚀
