# INSTALL_IIS_INTRANET.md — Deployment auf Windows Server 2019 IIS

Schritt-für-Schritt-Anleitung, um die Timesheet-Applikation in die bestehende
IIS-Website `intranet.wenkel.local` (Port 80) einzubinden.

**Ziel-URL nach Abschluss:** `http://intranet.wenkel.local/timesheet`

---

## Architekturüberblick

```
Browser im Intranet
        │
        ▼
IIS auf Windows Server 2019 (Port 80)
  ├── /                    → bestehende Intranet-Website (unverändert)
  └── /timesheet           → statische React-Dateien (dist/)
        └── /api/*         → ARR Reverse Proxy → localhost:8000 (FastAPI)

Python-Prozess (NSSM-Dienst)
  gunicorn + uvicorn.workers.UvicornWorker
  Port 8000 (nur lokal — kein externer Zugriff)
        │
        ▼
Microsoft SQL Server 2012 (dbserver01)
```

> **Wichtig:** Der Python-Backend-Prozess (Port 8000) ist **nicht** direkt aus dem Netzwerk
> erreichbar. Alle API-Anfragen laufen über den IIS-Proxy.

---

## Voraussetzungen

### Benötigte Software (auf dem IIS-Server installieren)

| Software | Zweck | Download |
|----------|-------|---------|
| Python 3.14 (64-bit) | Backend-Laufzeit | https://www.python.org/downloads/ |
| ODBC Driver 17 for SQL Server | Datenbankverbindung | https://aka.ms/odbc17 |
| IIS URL Rewrite Module 2.1 | SPA-Routing + Weiterleitungen | https://www.iis.net/downloads/microsoft/url-rewrite |
| IIS ARR (Application Request Routing) 3.0 | Reverse Proxy `/api/*` → Python | https://www.iis.net/downloads/microsoft/application-request-routing |
| NSSM 2.24 | Python-Prozess als Windows-Dienst | https://nssm.cc/download |
| Node.js >= 20 LTS | **Nur für den Frontend-Build** — danach nicht mehr nötig | https://nodejs.org/ |

> **Tipp:** Node.js muss **nicht** dauerhaft auf dem Produktionsserver installiert bleiben.
> Es wird nur einmalig (oder bei Updates) für `npm run build` benötigt.
> Alternativ kann der Build auf einem Entwicklungsrechner erstellt und nur `dist/` kopiert werden
> — das ist die **empfohlene Variante**.

---

## Schritt 1 — IIS-Features aktivieren

Öffne **PowerShell als Administrator** auf dem Server:

```powershell
Enable-WindowsOptionalFeature -Online -FeatureName `
    IIS-WebServerRole, IIS-WebServer, IIS-CommonHttpFeatures, `
    IIS-StaticContent, IIS-DefaultDocument, IIS-HttpErrors, `
    IIS-HttpRedirect, IIS-HttpCompressionStatic, IIS-HttpCompressionDynamic, `
    IIS-Security, IIS-RequestFiltering, IIS-ManagementConsole -All
```

Danach **URL Rewrite** und **ARR** per Installer installieren (Download-Links oben).

**ARR als Reverse Proxy aktivieren:**

1. IIS-Manager öffnen (`inetmgr` in der Suche)
2. Auf den **Server-Knoten** (ganz oben, nicht die Website) klicken
3. Doppelklick auf **Application Request Routing Cache**
4. Rechts auf **Server Proxy Settings** klicken
5. Checkbox **Enable proxy** aktivieren → **Apply**

---

## Schritt 2 — Quellcode auf den Server kopieren

```powershell
# Empfohlener Zielordner für die Applikation
New-Item -ItemType Directory -Path "C:\Apps\timesheet" -Force

# Via Git (wenn Git installiert ist)
cd C:\Apps
git clone <repository-url> timesheet
```

Alternativ den Projektordner per ZIP oder Netzlaufwerk auf den Server kopieren.

---

## Schritt 3 — Backend einrichten

### 3.1 Virtuelle Python-Umgebung erstellen

```powershell
cd C:\Apps\timesheet\backend

# Virtuelle Umgebung erstellen
python -m venv .venv

# Aktivieren
.\.venv\Scripts\Activate.ps1

# Alle Abhängigkeiten installieren
pip install -e ".[dev]"

# Gunicorn für Produktion installieren (mehrere Worker-Prozesse)
pip install gunicorn
```

> **Warum Gunicorn?**
> Das bare `uvicorn` läuft in einem einzigen Prozess. `gunicorn` mit `uvicorn`-Workern
> startet mehrere parallele Prozesse, startet abgestürzte Worker automatisch neu,
> und ist der empfohlene Produktions-Stack für FastAPI.

### 3.2 Umgebungsvariablen konfigurieren

Erstelle die Datei `C:\Apps\timesheet\backend\.env` mit folgendem Inhalt.
In der Kommandozeile am einfachsten so:

```powershell
notepad C:\Apps\timesheet\backend\.env
```

Inhalt:

```env
# Datenbankverbindung
DB_SERVER=dbserver01
DB_NAME=WiTERP
DB_USER=sa
DB_PASSWORD=DEIN_ECHTES_PASSWORT_HIER

# SQL Server 2012 benötigt Encrypt=no (kein TLS-Zertifikat vorhanden)
DB_ENCRYPT=no

# Anwendung
DEBUG=false
```

Dateiberechtigungen einschränken (Passwort schützen):

```powershell
icacls "C:\Apps\timesheet\backend\.env" /inheritance:r `
    /grant "SYSTEM:R" /grant "Administratoren:R"
```

### 3.3 CORS auf die Intranet-Domain einschränken

Öffne `C:\Apps\timesheet\backend\app\main.py` in einem Texteditor (z. B. Notepad)
und suche nach der Zeile `allow_origins`. Ändere:

```python
# VORHER — erlaubt alle Origins (nur für Entwicklung geeignet):
allow_origins=["*"],

# NACHHER — nur die eigene Intranet-Domain:
allow_origins=["http://intranet.wenkel.local"],
```

Speichern und schließen.

### 3.4 Backend manuell testen

```powershell
cd C:\Apps\timesheet\backend
.\.venv\Scripts\Activate.ps1

# Backend starten
gunicorn app.main:app -w 2 -k uvicorn.workers.UvicornWorker --bind 127.0.0.1:8000
```

In einem **zweiten PowerShell-Fenster** prüfen:

```powershell
Invoke-RestMethod -Uri "http://localhost:8000/health"
# Erwartete Antwort: {"status":"ok","version":"0.1.0","database":"ok"}
```

Mit `Ctrl+C` im ersten Fenster stoppen — als Dienst wird das Backend im nächsten Schritt eingerichtet.

---

## Schritt 4 — Backend als Windows-Dienst (NSSM)

NSSM herunterladen und z. B. nach `C:\Tools\nssm\` entpacken.

```powershell
# Log-Ordner anlegen
New-Item -ItemType Directory -Path "C:\Logs\timesheet" -Force

# Dienst registrieren
C:\Tools\nssm\win64\nssm.exe install TimesheetBackend `
    "C:\Apps\timesheet\backend\.venv\Scripts\python.exe"

# Arbeitsverzeichnis setzen
C:\Tools\nssm\win64\nssm.exe set TimesheetBackend AppDirectory `
    "C:\Apps\timesheet\backend"

# Startparameter: 2 Worker-Prozesse, bindet nur an localhost
C:\Tools\nssm\win64\nssm.exe set TimesheetBackend AppParameters `
    "-m gunicorn app.main:app -w 2 -k uvicorn.workers.UvicornWorker --bind 127.0.0.1:8000"

# Log-Dateien mit automatischer Rotation (max. 10 MB pro Datei)
C:\Tools\nssm\win64\nssm.exe set TimesheetBackend AppStdout `
    "C:\Logs\timesheet\backend.log"
C:\Tools\nssm\win64\nssm.exe set TimesheetBackend AppStderr `
    "C:\Logs\timesheet\backend-error.log"
C:\Tools\nssm\win64\nssm.exe set TimesheetBackend AppRotateFiles 1
C:\Tools\nssm\win64\nssm.exe set TimesheetBackend AppRotateOnline 1
C:\Tools\nssm\win64\nssm.exe set TimesheetBackend AppRotateBytes 10485760

# Automatischen Start beim Hochfahren des Servers aktivieren
C:\Tools\nssm\win64\nssm.exe set TimesheetBackend Start SERVICE_AUTO_START

# Dienst starten
net start TimesheetBackend

# Status prüfen
Get-Service -Name TimesheetBackend
```

Der Dienst startet jetzt automatisch bei jedem Server-Neustart.
Logs findest du unter `C:\Logs\timesheet\`.

---

## Schritt 5 — Frontend bauen

> **Empfehlung:** Den Build auf einem **Entwicklungsrechner** ausführen
> und nur den fertigen `dist/`-Ordner auf den Server kopieren.
> Der Produktionsserver braucht dann kein Node.js.

```powershell
# Auf dem Entwicklungsrechner (z. B. deinem Büro-PC):
cd C:\Develop\timesheet\frontend

# Node-Abhängigkeiten installieren
npm install

# WICHTIG: VITE_API_URL muss leer sein (kein Wert)
# Der IIS-Proxy übernimmt die Weiterleitung von /api/* zum Backend.
# Öffne frontend\.env und stelle sicher, dass dort steht:
#   VITE_API_URL=
# (oder die Datei enthält die Zeile einfach nicht)

# Produktions-Build erstellen
npm run build
# Erzeugt den Ordner: frontend\dist\
```

`dist/`-Ordner auf den Server kopieren:

```powershell
# Auf dem Server: Zielordner anlegen
$webRoot = "C:\inetpub\wwwroot\intranet.wenkel.local\timesheet"
New-Item -ItemType Directory -Path $webRoot -Force

# dist/-Inhalt auf den Server kopieren
# (passe den Quellpfad an — z. B. via Netzlaufwerk oder zuvor per RDP kopiert)
Copy-Item -Path "C:\Develop\timesheet\frontend\dist\*" `
          -Destination $webRoot -Recurse -Force
```

---

## Schritt 6 — IIS konfigurieren

### 6.1 Virtuelle Applikation anlegen

Führe auf dem Server in PowerShell (Administrator) aus:

```powershell
New-WebApplication `
    -Site "intranet.wenkel.local" `
    -Name "timesheet" `
    -PhysicalPath "C:\inetpub\wwwroot\intranet.wenkel.local\timesheet"
```

Oder im **IIS-Manager** manuell:
1. Website `intranet.wenkel.local` aufklappen
2. Rechtsklick → **Anwendung hinzufügen**
3. Alias: `timesheet`
4. Physischer Pfad: `C:\inetpub\wwwroot\intranet.wenkel.local\timesheet`
5. OK klicken

### 6.2 web.config anlegen

Erstelle die Datei `C:\inetpub\wwwroot\intranet.wenkel.local\timesheet\web.config`
mit folgendem Inhalt:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<configuration>
  <system.webServer>

    <rewrite>
      <rules>

        <!--
          Regel 1: Anfragen an /timesheet/api/* werden als Reverse Proxy
          an das Python-Backend auf Port 8000 weitergeleitet.
          Beispiel: /timesheet/api/employees → http://localhost:8000/api/employees
        -->
        <rule name="API Proxy" stopProcessing="true">
          <match url="^api/(.*)" />
          <action type="Rewrite" url="http://localhost:8000/api/{R:1}" />
        </rule>

        <!--
          Regel 2: Wenn die angeforderte Datei tatsächlich existiert
          (JS, CSS, Bilder, Fonts), wird sie direkt ausgeliefert.
        -->
        <rule name="Static Files" stopProcessing="true">
          <match url=".*" />
          <conditions>
            <add input="{REQUEST_FILENAME}" matchType="IsFile" />
          </conditions>
          <action type="None" />
        </rule>

        <!--
          Regel 3: Alle anderen Routen liefern index.html aus.
          React Router übernimmt dann das client-seitige Routing.
        -->
        <rule name="SPA Fallback" stopProcessing="true">
          <match url=".*" />
          <action type="Rewrite" url="/timesheet/index.html" />
        </rule>

      </rules>
    </rewrite>

    <!-- Standard-Startdatei -->
    <defaultDocument>
      <files>
        <add value="index.html" />
      </files>
    </defaultDocument>

    <!-- Komprimierung aktivieren (spart Bandbreite) -->
    <urlCompression doStaticCompression="true" doDynamicCompression="true" />

    <staticContent>
      <!--
        Lange Cache-Dauer für statische Assets:
        Vite generiert bei jedem Build eindeutige Dateinamen (z. B. main-a3f1b2.js),
        sodass Browser immer die aktuelle Version laden.
      -->
      <clientCache cacheControlMode="UseMaxAge" cacheControlMaxAge="365.00:00:00" />

      <!-- WebAssembly-MIME-Type (für zukünftige Erweiterungen) -->
      <mimeMap fileExtension=".wasm" mimeType="application/wasm" />
    </staticContent>

  </system.webServer>
</configuration>
```

### 6.3 IIS neu starten

```powershell
iisreset /restart
```

---

## Schritt 7 — Firewall absichern

Port 8000 soll **nicht** direkt aus dem Netzwerk erreichbar sein —
der Zugriff läuft ausschließlich über den IIS-Proxy:

```powershell
New-NetFirewallRule `
    -DisplayName "Block Timesheet Backend Direct Access" `
    -Direction Inbound `
    -Protocol TCP `
    -LocalPort 8000 `
    -RemoteAddress "LocalSubnet" `
    -Action Block
```

---

## Schritt 8 — HTTPS einrichten (empfohlen)

Auch im Intranet schützt HTTPS vor Mitlesen im Netzwerk (z. B. Passwörter, Arbeitszeiten).

### Option A: Internes Zertifikat via Windows-CA (Active Directory Certificate Services)

Falls im Intranet eine Windows-Zertifizierungsstelle (AD CS) vorhanden ist:

1. **IIS-Manager** öffnen → Auf den Server-Knoten klicken → **Server-Zertifikate**
2. Rechts: **Domänenzertifikat anfordern...**
3. Allgemeiner Name (Common Name): `intranet.wenkel.local`
4. Zertifikat fertigstellen und der Zertifizierungsstelle zuweisen lassen
5. Website `intranet.wenkel.local` → **Bindungen** → Neue Bindung: `https`, Port `443`, Zertifikat auswählen
6. HTTP-zu-HTTPS-Umleitung in `web.config` ergänzen — folgende Regel **ganz oben** in `<rules>` einfügen:

```xml
<rule name="HTTP to HTTPS" stopProcessing="true">
  <match url="(.*)" />
  <conditions>
    <add input="{HTTPS}" pattern="^OFF$" />
  </conditions>
  <action type="Redirect" url="https://{HTTP_HOST}/{R:0}" redirectType="Permanent" />
</rule>
```

7. Nach HTTPS-Umstellung: CORS in `backend\app\main.py` anpassen:
   ```python
   allow_origins=["https://intranet.wenkel.local"],
   ```

### Option B: Selbst signiertes Zertifikat (ohne CA)

```powershell
# Im IIS-Manager: Server-Zertifikate → "Selbst signiertes Zertifikat erstellen"
# Name: intranet.wenkel.local
```

Achtung: Browser zeigen dann eine Sicherheitswarnung. Das Zertifikat muss
auf den Client-Rechnern als vertrauenswürdig importiert werden.

---

## Schritt 9 — Datenbankmigrationen

Falls die Tabellen in der WiTERP-Datenbank noch nicht existieren:

```powershell
cd C:\Apps\timesheet\backend
.\.venv\Scripts\Activate.ps1

# Alle Tabellen erstellen (empfohlen — ORM-basiert via Alembic)
alembic upgrade head

# Alternativ: Raw SQL Script direkt gegen SQL Server ausführen
python cli.py --password DEIN_PASSWORT migrate
```

---

## Test-Checkliste

Nach Abschluss aller Schritte folgendes überprüfen:

```
[ ] http://localhost:8000/health gibt {"status":"ok","database":"ok"} zurück
[ ] Windows-Dienst "TimesheetBackend" hat Status "Running" (services.msc)
[ ] http://intranet.wenkel.local/timesheet/ lädt die React-Anwendung im Browser
[ ] Das Mitarbeiter-Dropdown lädt (API-Verbindung über IIS-Proxy funktioniert)
[ ] Ein Zeiteintrag kann erstellt und gespeichert werden
[ ] Nach Server-Neustart startet der Backend-Dienst automatisch
[ ] Browser-Konsole (F12 → Console) zeigt keine Fehler
```

---

## Update-Prozess (für künftige Versionen)

```powershell
# 1. Neuen Code holen
cd C:\Apps\timesheet
git pull

# 2. Python-Pakete aktualisieren
cd backend
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
pip install --upgrade gunicorn

# 3. Datenbankmigrationen anwenden
alembic upgrade head

# 4. Backend-Dienst neu starten
net stop TimesheetBackend
net start TimesheetBackend

# 5. Frontend neu bauen (auf dem Entwicklungsrechner)
#    cd C:\Develop\timesheet\frontend
#    npm install && npm run build

# 6. Neuen dist/-Inhalt auf den Server kopieren
Copy-Item -Path "C:\Develop\timesheet\frontend\dist\*" `
    -Destination "C:\inetpub\wwwroot\intranet.wenkel.local\timesheet" `
    -Recurse -Force
```

---

## Hinweis: SQL Server 2012

SQL Server 2012 erhält seit Juli 2022 keine Sicherheitsupdates mehr (End of Extended Support).
Die Verbindung läuft mit `DB_ENCRYPT=no`, da SQL Server 2012 standardmäßig kein TLS-Zertifikat
für verschlüsselte Verbindungen voraussetzt. Für ein internes Intranet mit kontrolliertem
Netzwerkzugang ist das akzeptabel. Eine langfristige Migration auf einen aktuelleren SQL Server
(2019 oder 2022) wird empfohlen.
