# FRONTEND_DOCKER_COMPOSE_DEPLOY.md — Deployment mit Docker Compose

Vollständige Containerisierung der Timesheet-Applikation mit drei Containern:
Frontend (nginx), Backend (Python/Gunicorn) und Datenbank (PostgreSQL).

> **Hinweis:** Diese Anleitung verwendet **PostgreSQL** als Datenbank, da es als
> Docker-Container ohne Lizenzgebühren verfügbar ist. Am Ende wird kurz erklärt,
> wie SQL Server stattdessen verwendet werden kann.

---

## Architekturüberblick

```
Browser
    │
    ▼
┌──────────────────────────────────────────┐
│  Docker-Netzwerk: timesheet-net           │
│                                          │
│  ┌─────────────────┐                    │
│  │  frontend        │  Port 80/443       │◄── Browser
│  │  (nginx:alpine)  │                    │
│  │  - dist/ statisch│                    │
│  │  - /api/* Proxy  │──────────────────┐ │
│  └─────────────────┘                   │ │
│                                         ▼ │
│  ┌─────────────────┐                    │
│  │  backend         │  Port 8000         │
│  │  (python:3.14)   │◄───────────────────┘
│  │  gunicorn        │                    │
│  └────────┬────────┘                    │
│           │                              │
│           ▼                              │
│  ┌─────────────────┐                    │
│  │  db              │  Port 5432         │
│  │  (postgres:16)   │                    │
│  │  Volume: pg_data │                    │
│  └─────────────────┘                    │
└──────────────────────────────────────────┘
```

Alle Container kommunizieren über ein internes Docker-Netzwerk.
Nur Port 80 (und optional 443) ist von außen erreichbar.

---

## Voraussetzungen

Auf dem Server muss installiert sein:

```bash
# Docker Engine
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
# Ausloggen und wieder einloggen

# Docker Compose Plugin (bei aktuellen Docker-Versionen bereits enthalten)
docker compose version
# Ausgabe: Docker Compose version v2.x.x
```

---

## Projektstruktur für Docker

Folgende Dateien werden zusätzlich zum bestehenden Projekt angelegt:

```
timesheet/
├── Dockerfile.backend          ← Backend-Container
├── Dockerfile.frontend         ← Frontend-Container (multi-stage build)
├── docker-compose.yml          ← Alle drei Container zusammen
├── nginx.docker.conf           ← nginx-Konfiguration für den Frontend-Container
└── backend/
    └── .env.docker             ← Umgebungsvariablen für Docker (NICHT einchecken!)
```

---

## Schritt 1 — Dockerfile.backend anlegen

Erstelle `timesheet/Dockerfile.backend`:

```dockerfile
# Basis-Image: schlankes Python 3.14
FROM python:3.14-slim

# Systemabhängigkeiten und Microsoft ODBC Driver 17 installieren
# (benötigt für pyodbc / SQL Server — kann weggelassen werden bei reinem PostgreSQL)
RUN apt-get update && apt-get install -y --no-install-recommends \
        curl \
        gnupg \
        unixodbc-dev \
    && curl https://packages.microsoft.com/keys/microsoft.asc | apt-key add - \
    && curl https://packages.microsoft.com/config/debian/11/prod.list \
        > /etc/apt/sources.list.d/mssql-release.list \
    && apt-get update \
    && ACCEPT_EULA=Y apt-get install -y --no-install-recommends msodbcsql17 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Arbeitsverzeichnis im Container
WORKDIR /app

# Abhängigkeiten zuerst kopieren (Docker-Layer-Caching nutzen)
COPY backend/pyproject.toml backend/README.md* ./

# Gunicorn + alle Abhängigkeiten installieren
RUN pip install --no-cache-dir -e ".[dev]" gunicorn

# Rest des Backend-Codes kopieren
COPY backend/ .

# Backend läuft auf Port 8000 (nur intern im Docker-Netzwerk)
EXPOSE 8000

# Startbefehl: 2 Worker-Prozesse
CMD ["gunicorn", "app.main:app", \
     "-w", "2", \
     "-k", "uvicorn.workers.UvicornWorker", \
     "--bind", "0.0.0.0:8000", \
     "--access-logfile", "-", \
     "--error-logfile", "-"]
```

> **Hinweis:** `--bind 0.0.0.0:8000` (statt `127.0.0.1:8000`) ist im Container nötig,
> damit andere Container den Backend-Dienst erreichen können.
> Im Docker-Netzwerk ist der Port trotzdem nicht von außen erreichbar.

---

## Schritt 2 — nginx.docker.conf anlegen

Erstelle `timesheet/nginx.docker.conf`:

```nginx
server {
    listen 80;
    server_name _;

    root /usr/share/nginx/html;
    index index.html;

    # Statische Assets: lange Cache-Dauer
    location ~* \.(js|css|png|jpg|svg|woff2?|ico|wasm)$ {
        expires 1y;
        add_header Cache-Control "public, immutable";
        try_files $uri =404;
    }

    # API-Anfragen: Weiterleitung an den Backend-Container
    # "backend" ist der Docker-Service-Name aus docker-compose.yml
    location /api/ {
        proxy_pass         http://backend:8000;
        proxy_http_version 1.1;
        proxy_set_header   Host $host;
        proxy_set_header   X-Real-IP $remote_addr;
        proxy_set_header   X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header   X-Forwarded-Proto $scheme;
    }

    # SPA-Fallback: alle unbekannten Routen → index.html
    location / {
        try_files $uri $uri/ /index.html;
    }
}
```

---

## Schritt 3 — Dockerfile.frontend anlegen

Erstelle `timesheet/Dockerfile.frontend`:

```dockerfile
# ── Stage 1: Build ────────────────────────────────────────────────────────────
FROM node:20-alpine AS build

WORKDIR /app

# Abhängigkeiten installieren (Layer-Caching)
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm ci

# Quellcode kopieren
COPY frontend/ .

# VITE_API_URL leer lassen — nginx übernimmt die /api/-Weiterleitung
ARG VITE_API_URL=""
ENV VITE_API_URL=$VITE_API_URL

# Produktions-Build erstellen
RUN npm run build

# ── Stage 2: Serve ────────────────────────────────────────────────────────────
FROM nginx:alpine AS serve

# Build-Artefakte aus Stage 1 kopieren
COPY --from=build /app/dist /usr/share/nginx/html

# nginx-Konfiguration kopieren
COPY nginx.docker.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
```

---

## Schritt 4 — backend/.env.docker anlegen

Erstelle `timesheet/backend/.env.docker`:

```env
# Datenbankverbindung — PostgreSQL im Docker-Netzwerk
# "db" ist der Service-Name aus docker-compose.yml
DATABASE_URL=postgresql+psycopg2://timesheet_user:SICHERES_PASSWORT_HIER@db/timesheet_db

# Anwendung
DEBUG=false

# CORS — die Domain, unter der das Frontend erreichbar ist
# (nach dem Start mit dem tatsächlichen Hostnamen ersetzen)
CORS_ORIGINS=http://localhost
```

> ⚠️ **Sicherheit:** Diese Datei enthält das Datenbankpasswort.
> Sie darf **nicht** in das Git-Repository eingecheckt werden.
> Sicherstellen, dass `backend/.env.docker` in `.gitignore` eingetragen ist.

---

## Schritt 5 — docker-compose.yml anlegen

Erstelle `timesheet/docker-compose.yml`:

```yaml
services:

  # ── Frontend: React-App via nginx ────────────────────────────────────────────
  frontend:
    build:
      context: .
      dockerfile: Dockerfile.frontend
    ports:
      - "80:80"
    depends_on:
      backend:
        condition: service_healthy
    restart: unless-stopped
    networks:
      - timesheet-net

  # ── Backend: FastAPI via Gunicorn ────────────────────────────────────────────
  backend:
    build:
      context: .
      dockerfile: Dockerfile.backend
    env_file:
      - backend/.env.docker
    depends_on:
      db:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 5
      start_period: 15s
    restart: unless-stopped
    networks:
      - timesheet-net
    # Port 8000 ist NICHT nach außen freigegeben — nur intern im Docker-Netzwerk

  # ── Datenbank: PostgreSQL ─────────────────────────────────────────────────────
  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: timesheet_db
      POSTGRES_USER: timesheet_user
      POSTGRES_PASSWORD: SICHERES_PASSWORT_HIER   # gleiches Passwort wie in .env.docker
    volumes:
      - pg_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U timesheet_user -d timesheet_db"]
      interval: 10s
      timeout: 5s
      retries: 10
      start_period: 10s
    restart: unless-stopped
    networks:
      - timesheet-net
    # Port 5432 ist NICHT nach außen freigegeben

volumes:
  pg_data:   # PostgreSQL-Daten überleben Container-Neustarts

networks:
  timesheet-net:
    driver: bridge
```

> **Wichtig:** Das Passwort in `POSTGRES_PASSWORD` muss exakt dasselbe sein wie
> in der `DATABASE_URL` in `backend/.env.docker`.

---

## Schritt 6 — Backend für PostgreSQL vorbereiten

Da der Docker-Compose-Stack PostgreSQL statt SQL Server verwendet, müssen
zwei kleine Anpassungen im Backend vorgenommen werden:

### 6.1 psycopg2 als Abhängigkeit hinzufügen

Öffne `backend/pyproject.toml` und ergänze `psycopg2-binary` in den Abhängigkeiten:

```toml
dependencies = [
    # ... bestehende Abhängigkeiten ...
    "psycopg2-binary>=2.9",
]
```

### 6.2 CORS-Konfiguration aus Umgebungsvariable lesen

Damit die CORS-Einstellung ohne Code-Änderung konfigurierbar ist, prüfe
`backend/app/main.py`. Falls `allow_origins` noch hartcodiert ist, ändere auf:

```python
import os
# ...
allow_origins=os.environ.get("CORS_ORIGINS", "http://localhost").split(","),
```

---

## Schritt 7 — Alles starten

```bash
# Im Projektroot (dort, wo docker-compose.yml liegt)
cd /opt/timesheet

# Images bauen und alle Container starten
docker compose up --build -d

# Status aller Container prüfen
docker compose ps
```

Erwartete Ausgabe (alle Container `running`):

```
NAME                    STATUS          PORTS
timesheet-frontend-1    Up (healthy)    0.0.0.0:80->80/tcp
timesheet-backend-1     Up (healthy)
timesheet-db-1          Up (healthy)
```

---

## Schritt 8 — Datenbankmigrationen ausführen

Direkt nach dem ersten Start:

```bash
docker compose exec backend alembic upgrade head
```

Dieser Befehl erstellt alle Tabellen in der PostgreSQL-Datenbank.
Bei späteren Updates muss dieser Befehl erneut ausgeführt werden.

---

## Schritt 9 — Logs ansehen

```bash
# Alle Container-Logs live verfolgen
docker compose logs -f

# Nur Backend-Logs
docker compose logs -f backend

# Nur die letzten 100 Zeilen
docker compose logs --tail=100 backend
```

---

## Schritt 10 — Update-Prozess

```bash
# 1. Neuen Code holen
cd /opt/timesheet
git pull

# 2. Images neu bauen und Container neu starten
docker compose up --build -d

# 3. Datenbankmigrationen anwenden
docker compose exec backend alembic upgrade head
```

Docker ersetzt automatisch nur die Container, deren Images sich geändert haben.
Laufende Verbindungen werden dabei kurz unterbrochen.

---

## Datensicherung (PostgreSQL-Volume)

Die Datenbankdaten liegen im Docker-Volume `pg_data`. So erstellst du ein Backup:

```bash
# Backup erstellen
docker compose exec db pg_dump \
    -U timesheet_user \
    -d timesheet_db \
    -F c \
    -f /tmp/timesheet_backup.dump

# Backup-Datei aus dem Container kopieren
docker compose cp db:/tmp/timesheet_backup.dump \
    ./backups/timesheet_$(date +%Y%m%d_%H%M%S).dump

# Backup wiederherstellen
docker compose exec -T db pg_restore \
    -U timesheet_user \
    -d timesheet_db \
    -c /tmp/timesheet_backup.dump
```

**Automatisches tägliches Backup** (Cron-Job):

```bash
# crontab -e
0 2 * * * cd /opt/timesheet && docker compose exec db pg_dump \
    -U timesheet_user -d timesheet_db -F c \
    > /opt/backups/timesheet_$(date +\%Y\%m\%d).dump 2>&1
```

---

## HTTPS mit nginx (Produktionsumgebung)

Für HTTPS gibt es zwei einfache Wege:

### Option A: Certbot-Companion (Let's Encrypt — automatisch)

```yaml
# Ergänzung in docker-compose.yml:
services:
  certbot:
    image: certbot/certbot
    volumes:
      - ./certbot/conf:/etc/letsencrypt
      - ./certbot/www:/var/www/certbot
    entrypoint: >
      sh -c "trap exit TERM; while :; do certbot renew; sleep 12h & wait $${!}; done"
```

### Option B: Reverse Proxy vorschalten (Traefik oder Caddy)

Traefik und Caddy sind moderne Reverse-Proxys, die HTTPS-Zertifikate vollautomatisch
verwalten. Sie werden als zusätzlicher Container vor das Frontend geschaltet:

```bash
# Einfachstes Beispiel mit Caddy:
# Caddyfile:
#   timesheet.deinefirma.de {
#       reverse_proxy frontend:80
#   }
```

---

## SQL Server statt PostgreSQL (optional)

Falls der vorhandene SQL Server 2012 auch im Docker-Betrieb verwendet werden soll:

- **Kein SQL-Server-Container nötig** — die bestehende Instanz auf `dbserver01` wird weiter verwendet
- In `backend/.env.docker` die PostgreSQL-`DATABASE_URL` durch die SQL-Server-Verbindung ersetzen:

```env
# SQL Server Verbindung (statt PostgreSQL):
DB_SERVER=dbserver01
DB_NAME=WiTERP
DB_USER=sa
DB_PASSWORD=DEIN_PASSWORT
DB_ENCRYPT=no
```

- `psycopg2-binary` aus `pyproject.toml` entfernen (nicht eintragen)
- Das `Dockerfile.backend` enthält bereits ODBC Driver 17 — kein weiterer Eingriff nötig

> **Lizenz-Hinweis:** Microsoft stellt unter `mcr.microsoft.com/mssql/server` ein offizielles
> SQL-Server-Docker-Image bereit (SQL Server 2022 Developer/Express: kostenlos;
> Standard/Enterprise: Lizenz erforderlich). SQL Server 2012 ist als Docker-Image nicht verfügbar.

---

## Vollständige Dateiübersicht

Nach Abschluss liegen folgende neue Dateien im Projekt:

```
timesheet/
├── Dockerfile.backend
├── Dockerfile.frontend
├── docker-compose.yml
├── nginx.docker.conf
└── backend/
    └── .env.docker          ← NICHT in Git einchecken!
```

Stelle sicher, dass `backend/.env.docker` in `.gitignore` eingetragen ist:

```
# In .gitignore hinzufügen:
backend/.env.docker
```

---

## Test-Checkliste

```
[ ] docker compose ps  →  alle 3 Container "Up (healthy)"
[ ] docker compose logs backend  →  kein Fehler, gunicorn gestartet
[ ] http://localhost/ lädt die React-Anwendung
[ ] Mitarbeiter-Dropdown lädt (API-Proxy über nginx funktioniert)
[ ] Ein Zeiteintrag kann erstellt und gespeichert werden
[ ] docker compose restart backend  →  App bleibt erreichbar (DB-Volume persistent)
[ ] Backup-Befehl erstellt .dump-Datei
```
