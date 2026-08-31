# FRONTEND_GENERIC_DEPLOY.md — Deployment auf Linux (nginx / Apache)

Schritt-für-Schritt-Anleitung für den Betrieb der Timesheet-Applikation
auf einem Linux-Server (Ubuntu 22.04 LTS oder Debian 12).

Zwei Varianten werden beschrieben:

- **Variante A**: nginx (empfohlen — einfacher, performanter)
- **Variante B**: Apache (falls bereits im Einsatz)

Außerdem: PostgreSQL als Alternative zu Microsoft SQL Server.

---

## Architekturüberblick

``` structure
Browser
    │
    ▼
nginx / Apache (Port 80 / 443)
  ├── /                    → statische React-Dateien (dist/)
  └── /api/*               → Reverse Proxy → 127.0.0.1:8000 (FastAPI)

Python-Prozess (systemd-Dienst)
  gunicorn + uvicorn.workers.UvicornWorker
  Port 8000 (nur localhost — kein externer Zugriff)
    │
    ▼
Datenbank: SQL Server 2012 (dbserver01)
       oder: PostgreSQL (lokal auf demselben Server)
```

---

## Voraussetzungen auf dem Linux-Server

```bash
# Systempakete aktualisieren
sudo apt update && sudo apt upgrade -y

# Basiswerkzeuge
sudo apt install -y git curl wget build-essential
```

---

## Variante A: nginx (empfohlen)

### A.1 — Python 3.14 installieren

Ubuntu 22.04 / Debian 12 liefern standardmäßig Python 3.10/3.11.
Für Python 3.14 das **deadsnakes-PPA** verwenden:

```bash
sudo apt install -y software-properties-common
sudo add-apt-repository ppa:deadsnakes/ppa
sudo apt update
sudo apt install -y python3.14 python3.14-venv python3.14-dev
```

Prüfen:

```bash
python3.14 --version
# Ausgabe: Python 3.14.x
```

### A.2 — ODBC Driver 17 for SQL Server installieren

> **Hinweis:** Dieser Schritt ist nur nötig, wenn du SQL Server als Datenbank verwendest.
> Bei PostgreSQL (siehe Variante C am Ende) kann er übersprungen werden.

```bash
# Microsoft-Paketquelle hinzufügen (für Ubuntu 22.04)
curl https://packages.microsoft.com/keys/microsoft.asc | sudo apt-key add -
curl https://packages.microsoft.com/config/ubuntu/22.04/prod.list \
    | sudo tee /etc/apt/sources.list.d/mssql-release.list

sudo apt update
sudo ACCEPT_EULA=Y apt install -y msodbcsql17

# unixODBC-Entwicklungspakete (für pyodbc)
sudo apt install -y unixodbc-dev
```

### A.3 — Quellcode auf den Server kopieren

```bash
# Empfohlener Zielordner
sudo mkdir -p /opt/timesheet
sudo chown $USER:$USER /opt/timesheet

# Via Git
git clone <repository-url> /opt/timesheet

# Oder: Ordner per SCP vom Entwicklungsrechner kopieren
# scp -r /lokaler/pfad/timesheet user@server:/opt/timesheet
```

### A.4 — Python-Umgebung und Backend einrichten

```bash
cd /opt/timesheet/backend

# Virtuelle Umgebung erstellen
python3.14 -m venv .venv

# Aktivieren
source .venv/bin/activate

# Alle Abhängigkeiten installieren
pip install -e ".[dev]"

# Gunicorn für Produktion
pip install gunicorn
```

### A.5 — Umgebungsvariablen konfigurieren

```bash
# .env-Datei anlegen
nano /opt/timesheet/backend/.env
```

Inhalt:

```env
# Datenbankverbindung (SQL Server)
DB_SERVER=dbserver01
DB_NAME=WiTERP
DB_USER=sa
DB_PASSWORD=DEIN_ECHTES_PASSWORT_HIER

# SQL Server 2012 — kein TLS
DB_ENCRYPT=no

# Anwendung
DEBUG=false
```

Dateiberechtigungen einschränken:

```bash
chmod 600 /opt/timesheet/backend/.env
```

### A.6 — CORS einschränken

Öffne `backend/app/main.py` und ändere:

```python
# VORHER:
allow_origins=["*"],

# NACHHER (deine Produktionsdomain eintragen):
allow_origins=["https://timesheet.deinefirma.de"],
```

### A.7 — Backend manuell testen

```bash
cd /opt/timesheet/backend
source .venv/bin/activate

gunicorn app.main:app -w 2 -k uvicorn.workers.UvicornWorker --bind 127.0.0.1:8000
```

In einem zweiten Terminal:

```bash
curl http://localhost:8000/health
# Erwartete Antwort: {"status":"ok","version":"0.1.0","database":"ok"}
```

Mit `Ctrl+C` stoppen.

### A.8 — systemd-Dienst einrichten

```bash
sudo nano /etc/systemd/system/timesheet-backend.service
```

Inhalt:

```ini
[Unit]
Description=Timesheet Backend (FastAPI / Gunicorn)
After=network.target

[Service]
Type=exec
User=www-data
Group=www-data
WorkingDirectory=/opt/timesheet/backend
Environment="PATH=/opt/timesheet/backend/.venv/bin"
EnvironmentFile=/opt/timesheet/backend/.env
ExecStart=/opt/timesheet/backend/.venv/bin/gunicorn \
    app.main:app \
    -w 2 \
    -k uvicorn.workers.UvicornWorker \
    --bind 127.0.0.1:8000 \
    --access-logfile /var/log/timesheet/access.log \
    --error-logfile /var/log/timesheet/error.log

Restart=on-failure
RestartSec=5s

[Install]
WantedBy=multi-user.target
```

```bash
# Log-Ordner anlegen
sudo mkdir -p /var/log/timesheet
sudo chown www-data:www-data /var/log/timesheet

# Eigentumsrecht auf /opt/timesheet für www-data setzen
sudo chown -R www-data:www-data /opt/timesheet

# Dienst aktivieren und starten
sudo systemctl daemon-reload
sudo systemctl enable timesheet-backend
sudo systemctl start timesheet-backend

# Status prüfen
sudo systemctl status timesheet-backend
```

### A.9 — Log-Rotation einrichten

```bash
sudo nano /etc/logrotate.d/timesheet
```

Inhalt:

``` structure
/var/log/timesheet/*.log {
    daily
    missingok
    rotate 14
    compress
    delaycompress
    notifempty
    sharedscripts
    postrotate
        systemctl reload timesheet-backend > /dev/null 2>&1 || true
    endscript
}
```

### A.10 — Frontend bauen

> **Empfehlung:** Build auf dem Entwicklungsrechner ausführen, dann nur `dist/` kopieren.

```bash
# Auf dem Entwicklungsrechner:
cd /pfad/zu/timesheet/frontend
npm install

# VITE_API_URL muss leer sein!
# nginx übernimmt die Weiterleitung von /api/* zum Backend.
# In frontend/.env sicherstellen:
#   VITE_API_URL=

npm run build
# Erzeugt: frontend/dist/
```

`dist/`-Ordner auf den Server kopieren:

```bash
# Auf dem Server: Zielordner anlegen
sudo mkdir -p /var/www/timesheet
sudo chown www-data:www-data /var/www/timesheet

# Von Entwicklungsrechner auf den Server kopieren
scp -r frontend/dist/* user@server:/var/www/timesheet/
```

### A.11 — nginx konfigurieren

nginx installieren:

```bash
sudo apt install -y nginx
```

Neue Site-Konfiguration erstellen:

```bash
sudo nano /etc/nginx/sites-available/timesheet
```

Inhalt (Platzhalter `timesheet.deinefirma.de` anpassen):

```nginx
server {
    listen 80;
    server_name timesheet.deinefirma.de;

    root /var/www/timesheet;
    index index.html;

    # Statische Assets: lange Cache-Dauer (Vite generiert eindeutige Dateinamen)
    location ~* \.(js|css|png|jpg|svg|woff2?|ico)$ {
        expires 1y;
        add_header Cache-Control "public, immutable";
        try_files $uri =404;
    }

    # API-Anfragen: Reverse Proxy zum Python-Backend
    location /api/ {
        proxy_pass         http://127.0.0.1:8000;
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

Site aktivieren und nginx testen:

```bash
sudo ln -s /etc/nginx/sites-available/timesheet /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

---

## Variante B: Apache

> Nutze diese Variante, wenn Apache bereits auf dem Server läuft.

### B.1 — Benötigte Module aktivieren

```bash
sudo a2enmod rewrite proxy proxy_http headers
sudo systemctl restart apache2
```

### B.2 — VirtualHost konfigurieren

```bash
sudo nano /etc/apache2/sites-available/timesheet.conf
```

Inhalt (Platzhalter anpassen):

```apache
<VirtualHost *:80>
    ServerName timesheet.deinefirma.de

    DocumentRoot /var/www/timesheet

    <Directory /var/www/timesheet>
        Options -Indexes +FollowSymLinks
        AllowOverride All
        Require all granted

        # SPA-Fallback: alle Anfragen ohne echte Datei → index.html
        RewriteEngine On
        RewriteCond %{REQUEST_FILENAME} !-f
        RewriteCond %{REQUEST_FILENAME} !-d
        RewriteRule ^ /index.html [L]
    </Directory>

    # API-Anfragen: Reverse Proxy zum Python-Backend
    ProxyPreserveHost On
    ProxyPass        /api/ http://127.0.0.1:8000/api/
    ProxyPassReverse /api/ http://127.0.0.1:8000/api/

    ErrorLog ${APACHE_LOG_DIR}/timesheet-error.log
    CustomLog ${APACHE_LOG_DIR}/timesheet-access.log combined
</VirtualHost>
```

```bash
sudo a2ensite timesheet
sudo apache2ctl configtest
sudo systemctl reload apache2
```

> Der systemd-Backend-Dienst (Schritt A.8) bleibt identisch für Variante B.
> Nur der Webserver-Teil unterscheidet sich.

---

## SSL mit Let's Encrypt (für öffentlich erreichbare Server)

Für Domains, die aus dem Internet erreichbar sind, kann ein kostenloses
SSL-Zertifikat über Let's Encrypt automatisch ausgestellt werden:

```bash
# Certbot installieren
sudo apt install -y certbot python3-certbot-nginx
# (für Apache: python3-certbot-apache statt python3-certbot-nginx)

# Zertifikat ausstellen und nginx automatisch konfigurieren
sudo certbot --nginx -d timesheet.deinefirma.de

# Automatische Erneuerung testen
sudo certbot renew --dry-run
```

Nach der Zertifikatsausstellung: CORS in `main.py` auf `https://...` anpassen.

---

## PostgreSQL als Alternative zu SQL Server

Wenn kein Windows-SQL-Server verfügbar ist oder ein vollständig Linux-basiertes
Deployment gewünscht wird, kann PostgreSQL als Datenbank verwendet werden.

### PostgreSQL installieren

```bash
sudo apt install -y postgresql postgresql-contrib

# PostgreSQL-Dienst starten
sudo systemctl enable postgresql
sudo systemctl start postgresql
```

### Datenbank und Benutzer anlegen

```bash
sudo -u postgres psql
```

Im psql-Prompt:

```sql
CREATE USER timesheet_user WITH PASSWORD 'SICHERES_PASSWORT_HIER';
CREATE DATABASE timesheet_db OWNER timesheet_user;
GRANT ALL PRIVILEGES ON DATABASE timesheet_db TO timesheet_user;
\q
```

### Python-Treiber tauschen

```bash
cd /opt/timesheet/backend
source .venv/bin/activate

# pyodbc (SQL Server) entfernen, psycopg2 (PostgreSQL) installieren
pip uninstall pyodbc
pip install psycopg2-binary
```

### .env für PostgreSQL anpassen

Ersetze die `DB_*`-Variablen in `backend/.env`:

```env
# PostgreSQL-Verbindung
DATABASE_URL=postgresql+psycopg2://timesheet_user:SICHERES_PASSWORT_HIER@localhost/timesheet_db

DEBUG=false
```

### SQLAlchemy-Verbindung umstellen

Öffne `backend/app/db/session.py` und ersetze die Engine-Erstellung:

```python
# VORHER (SQL Server via pyodbc):
# engine = create_engine(...)  — pyodbc-basiert

# NACHHER (PostgreSQL):
from sqlalchemy import create_engine
import os

DATABASE_URL = os.environ["DATABASE_URL"]
engine = create_engine(DATABASE_URL, pool_pre_ping=True)
```

> **Hinweis:** Je nach aktueller Implementierung in `session.py` kann die
> genaue Änderung abweichen. Die `DATABASE_URL` aus der `.env` wird direkt übergeben.

### Alembic-Konfiguration anpassen

Öffne `backend/alembic.ini` und setze:

```ini
sqlalchemy.url = postgresql+psycopg2://timesheet_user:PASSWORT@localhost/timesheet_db
```

Oder besser: die URL aus der `.env` lesen (bereits in `backend/alembic/env.py` konfiguriert,
falls `DATABASE_URL` gesetzt ist).

### Datenbanktabellen erstellen

```bash
cd /opt/timesheet/backend
source .venv/bin/activate
alembic upgrade head
```

---

## Test-Checkliste

``` todo list
[ ] sudo systemctl status timesheet-backend  →  "active (running)"
[ ] curl http://localhost:8000/health  →  {"status":"ok","database":"ok"}
[ ] http://timesheet.deinefirma.de/ lädt die React-Anwendung
[ ] Mitarbeiter-Dropdown lädt (API-Proxy funktioniert)
[ ] Ein Zeiteintrag kann erstellt und gespeichert werden
[ ] Nach Server-Neustart startet der Backend-Dienst automatisch
[ ] Browser-Konsole (F12) zeigt keine Fehler
```

---

## Update-Prozess

```bash
# 1. Neuen Code holen
cd /opt/timesheet
git pull

# 2. Python-Pakete aktualisieren
cd backend
source .venv/bin/activate
pip install -e ".[dev]"
pip install --upgrade gunicorn

# 3. Datenbankmigrationen anwenden
alembic upgrade head

# 4. Backend-Dienst neu starten
sudo systemctl restart timesheet-backend

# 5. Frontend neu bauen (auf Entwicklungsrechner)
#    cd /pfad/frontend && npm install && npm run build

# 6. Neue dist/-Dateien auf den Server kopieren
sudo cp -r /pfad/zu/dist/* /var/www/timesheet/
sudo chown -R www-data:www-data /var/www/timesheet/
```
