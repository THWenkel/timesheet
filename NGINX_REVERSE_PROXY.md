# nginx-Reverse-Proxy für timesheet.wenkel.de

Diese Anleitung ist für die Person, die den nginx-Reverse-Proxy (Docker, eigenes Git-Repository) betreut. Sie enthält alles, was dort eingetragen werden muss, damit die Timesheet-Anwendung unter **https://timesheet.wenkel.de/** aus dem Internet erreichbar ist. Die Anwendung selbst läuft weiter unter IIS.

## Überblick

``` text
Browser ──HTTPS──▶ timesheet.wenkel.de ──[nginx-Proxy]──HTTP──▶ intranet.wenkel.local (IIS)
   /assets/a.js       →  /timesheet/assets/a.js          statische Dateien (IIS)
   /api/employees/    →  /timesheet/api/employees/       IIS leitet an das Backend (localhost:8000)
   /beliebige/route   →  /timesheet/beliebige/route      IIS liefert index.html (SPA)
```

- Der Proxy macht **TLS** und **Domain-Routing**. Zum IIS geht es **per HTTP**, weil der IIS wegen der Domäne `intranet.wenkel.local` kein HTTPS kann.
- Die Anwendung liegt im IIS unter `/timesheet/`. Öffentlich steht sie an der Wurzel der Domain. Deshalb setzt der Proxy vor jeden Pfad `/timesheet/`.
- Dafür muss das Frontend mit dem Basispfad `/` gebaut sein (`npm run build:domain`, siehe Abschnitt „Gegenstücke“).

## Was im Proxy-Repository zu tun ist

1. **DNS:** `timesheet.wenkel.de` zeigt auf den Proxy.
2. **Zertifikat** für `timesheet.wenkel.de` bereitstellen (Verwaltung wie bei den anderen Domains im Proxy-Repo).
3. Die Datei `timesheet-proxy.inc` (unten) nach `/etc/nginx/snippets/timesheet-proxy.inc` legen.
4. Die Datei `timesheet.wenkel.de.conf` (unten) nach `conf.d/` legen. Sie wird in den `http`-Block geladen.
5. Die Stellen mit `<<< ANPASSEN >>>` setzen: Zertifikatspfade und die **Firmennetz-Adressbereiche** für die Administrations-Pfade.
6. Der Proxy-Container muss `intranet.wenkel.local` auflösen und Port 80 des IIS erreichen (Firewall, DNS im Container).
7. `nginx -t`, danach neu laden.

Voraussetzung: nginx ab Version 1.25.1 (wegen `http2 on;`). Bei älteren Versionen `listen 443 ssl http2;` verwenden.

Dieselben Dateien liegen im Repository der Anwendung unter `deploy/nginx-proxy/`.

## Konfiguration

### timesheet.wenkel.de.conf

```nginx
# =============================================================================
# timesheet.wenkel.de.conf
#
# nginx-Reverse-Proxy fuer die Timesheet-Anwendung (Domain-Routing).
#
#   Browser --HTTPS--> timesheet.wenkel.de --[dieser Proxy]--HTTP--> IIS
#                                                     intranet.wenkel.local/timesheet/
#
# Einbinden: Datei in conf.d/ des Proxys legen (wird in den http-Block geladen) und
# die gemeinsamen Direktiven nach /etc/nginx/snippets/timesheet-proxy.inc kopieren.
# Stellen mit  <<< ANPASSEN >>>  muessen auf die eigene Umgebung gesetzt werden.
# nginx >= 1.25.1 (Direktive "http2 on;"). Bei aelteren Versionen: "listen 443 ssl http2;".
# =============================================================================

# Der IIS spricht nur HTTP (Domaene intranet.wenkel.local, kein HTTPS im Firmennetz).
# nginx loest den Namen beim Start auf. Aendert sich die IP, nginx neu laden oder
# "extra_hosts" / eine feste IP verwenden.
upstream timesheet_iis {
    server intranet.wenkel.local:80;
    keepalive 16;
}

# Bremse gegen Passwort-Raten pro IP-Adresse. Sie ergaenzt die Kontosperre der App
# (5 Fehlversuche -> 15 Minuten). Grosszuegig, weil viele Nutzer hinter einem
# Firmen-NAT dieselbe Adresse haben koennen.
limit_req_zone $binary_remote_addr zone=timesheet_login:10m rate=30r/m;
limit_req_status 429;

# --- HTTP -> HTTPS ------------------------------------------------------------
server {
    listen 80;
    listen [::]:80;
    server_name timesheet.wenkel.de;

    return 301 https://$host$request_uri;
}

# --- HTTPS --------------------------------------------------------------------
server {
    listen 443 ssl;
    listen [::]:443 ssl;
    http2 on;
    server_name timesheet.wenkel.de;

    # <<< ANPASSEN >>> Zertifikat fuer timesheet.wenkel.de (Verwaltung im Proxy-Repo)
    ssl_certificate     /etc/nginx/certs/timesheet.wenkel.de/fullchain.pem;
    ssl_certificate_key /etc/nginx/certs/timesheet.wenkel.de/privkey.pem;
    ssl_protocols       TLSv1.2 TLSv1.3;

    server_tokens off;

    add_header Strict-Transport-Security "max-age=31536000" always;
    add_header X-Content-Type-Options    "nosniff"          always;
    add_header Referrer-Policy           "same-origin"      always;
    add_header X-Frame-Options           "SAMEORIGIN"       always;

    # Administrations-Pfade (nur vom Admin-Tool genutzt): nur aus dem Firmennetz.
    # Zusaetzliche Schicht. Der Login mit Administrator-Recht ist weiterhin Pflicht.
    location ~ ^/api/(backup|projects|customers|employees/admin|auth/admin)(/|$) {
        # <<< ANPASSEN >>> eigene Firmennetz-Adressbereiche eintragen (Quelladresse, wie sie
        # beim Proxy ankommt, siehe NGINX_REVERSE_PROXY.md "Fallstricke")
        allow 10.0.0.0/8;
        allow 172.16.0.0/12;
        allow 192.168.0.0/16;
        deny  all;

        include /etc/nginx/snippets/timesheet-proxy.inc;
    }

    # Login mit Bremse pro IP
    location = /api/auth/login {
        limit_req zone=timesheet_login burst=10 nodelay;

        include /etc/nginx/snippets/timesheet-proxy.inc;
    }

    # Alles andere: Web-App und uebrige API
    location / {
        include /etc/nginx/snippets/timesheet-proxy.inc;
    }
}
```

### timesheet-proxy.inc

```nginx
# =============================================================================
# timesheet-proxy.inc
#
# Gemeinsame Proxy-Direktiven fuer timesheet.wenkel.de. Wird in jede location
# von timesheet.wenkel.de.conf eingebunden:
#     include /etc/nginx/snippets/timesheet-proxy.inc;
# =============================================================================

# Die App liegt im IIS unter /timesheet/. Oeffentlich steht sie an der Wurzel der
# Domain, deshalb kommt vor jeden Pfad /timesheet/ (Query-String bleibt erhalten).
#   /assets/a.js    -> /timesheet/assets/a.js
#   /api/employees/ -> /timesheet/api/employees/   (IIS leitet an das Backend weiter)
rewrite ^/(.*)$ /timesheet/$1 break;
proxy_pass http://timesheet_iis;

proxy_http_version 1.1;
proxy_set_header Connection "";

# WICHTIG: Die IIS-Site ist an diesen Hostnamen gebunden. Mit dem oeffentlichen Namen
# wuerde der IIS die falsche Site treffen. Den oeffentlichen Namen bekommt die App in
# X-Forwarded-Host.
proxy_set_header Host              intranet.wenkel.local;
proxy_set_header X-Forwarded-Host  $host;
proxy_set_header X-Forwarded-Proto $scheme;
proxy_set_header X-Forwarded-For   $proxy_add_x_forwarded_for;
proxy_set_header X-Real-IP         $remote_addr;

# Falls der IIS doch einmal mit seinem internen Namen umleitet.
proxy_redirect http://intranet.wenkel.local/timesheet/ https://$host/;

# Das Backend sendet bei COOKIE_SECURE=true selbst einen HSTS-Header. Der Proxy setzt
# ihn im server-Block, damit er nur einmal in der Antwort steht.
proxy_hide_header Strict-Transport-Security;

# PDF-/Excel-Export und Restore-Import koennen dauern bzw. gross sein.
proxy_read_timeout  120s;
proxy_send_timeout  120s;
client_max_body_size 25m;
```

### Was die einzelnen Teile bewirken

| Teil | Zweck |
| --- | --- |
| `rewrite ^/(.*)$ /timesheet/$1 break;` | setzt `/timesheet/` vor jeden Pfad, der Query-String bleibt erhalten |
| `proxy_set_header Host intranet.wenkel.local;` | die IIS-Site ist an diesen Hostnamen gebunden, mit dem öffentlichen Namen würde der IIS die falsche Site treffen |
| `X-Forwarded-Host/-Proto/-For`, `X-Real-IP` | der Backend-Stack erfährt Originalname, Protokoll und Client-Adresse |
| `proxy_redirect` | schreibt Weiterleitungen des IIS (z. B. Verzeichnis ohne Schrägstrich) auf die öffentliche Adresse um |
| `proxy_hide_header Strict-Transport-Security` plus eigenes `add_header` | der HSTS-Header steht genau einmal in der Antwort |
| `client_max_body_size 25m` | der Restore-Import der Datensicherung schickt den Dateiinhalt im JSON-Body, die Standardgrenze von 1 MB reicht nicht |
| `proxy_read_timeout 120s` | PDF- und Excel-Export können dauern |
| Regex-Location für Administrations-Pfade | `/api/backup`, `/api/projects`, `/api/customers`, `/api/employees/admin`, `/api/auth/admin` nur aus dem Firmennetz. Das ist eine zweite Schicht **zusätzlich** zum Login mit Administrator-Recht |
| `limit_req` auf `/api/auth/login` | Bremse gegen Passwort-Raten pro IP. Ergänzt die Kontosperre der Anwendung (5 Fehlversuche, 15 Minuten) |

Ein `proxy_cookie_path` ist **nicht** nötig: Die Domain gehört nur dieser Anwendung, Cookies mit `Path=/` sind richtig.

## Gegenstücke auf der Anwendungsseite (IIS-Server)

1. **Frontend für die Domain bauen** und in denselben IIS-Ordner kopieren wie bisher:
   ```powershell
   cd C:\Develop\timesheet\frontend
   npm run build:domain
   Copy-Item -Path "dist\*" -Destination "C:\inetpub\wwwroot\intranet.wenkel.local\timesheet" -Recurse -Force
   ```
   `build:domain` setzt den Basispfad auf `/` und ignoriert `VITE_API_URL` aus `frontend/.env` (`frontend/.env.domain`). Der normale `npm run build` baut weiter für `/timesheet/`.
   Mit diesem Build funktioniert der **direkte** Aufruf `http://intranet.wenkel.local/timesheet/` nicht mehr, weil die Dateien unter `/assets/…` angefordert werden. Das ist gewollt: Alle Nutzer gehen über `https://timesheet.wenkel.de/`.
2. **`backend/.env`** auf dem IIS-Server:
   ```
   AUTH_ENABLED=true
   SECRET_KEY=<mindestens 32 Zeichen, z. B. python -c "import secrets; print(secrets.token_hex(32))">
   COOKIE_SECURE=true
   CORS_ORIGINS=["https://timesheet.wenkel.de"]
   ```
   `COOKIE_SECURE=true` passt, weil der Browser ausschließlich HTTPS sieht. Backend danach neu starten (Dienst `TimesheetBackend`).
3. **Im IIS keine http→https-Umleitung einrichten.** Der Proxy spricht HTTP mit dem IIS, eine solche Regel würde eine Endlosschleife erzeugen. (Die Anleitung `INSTALL_IIS_INTRANET.md` Schritt 8 gilt für diesen Betrieb nicht.)
4. **Windows-Admin-Tool:** Umgebungsvariable `TIMESHEET_API_URL=https://timesheet.wenkel.de/` (mit Schrägstrich am Ende). Bei einem Zertifikat einer öffentlichen CA braucht der PC nichts weiter. Die Administrations-Pfade funktionieren nur von Adressen aus der Freigabeliste (siehe Fallstricke).

## Prüfliste

Von einem beliebigen Rechner (`-i` zeigt die Header):

```bash
# 1. HTTP wird auf HTTPS umgeleitet (Pfad bleibt erhalten)
curl -sI http://timesheet.wenkel.de/foo | head -3

# 2. Die App wird ausgeliefert, HSTS kommt genau einmal
curl -sI https://timesheet.wenkel.de/ | grep -ci strict-transport-security      # erwartet: 1

# 3. Statische Dateien und API laufen über den Proxy
curl -s  https://timesheet.wenkel.de/api/auth/config                            # {"auth_enabled":true}
curl -so /dev/null -w "%{http_code}\n" https://timesheet.wenkel.de/api/employees/   # 401 ohne Login

# 4. Cookie-Attribute nach dem Login (Benutzername und Passwort einsetzen)
curl -si -X POST https://timesheet.wenkel.de/api/auth/login \
  -H 'content-type: application/json' -d '{"username":"...","password":"..."}' | grep -i set-cookie
#    erwartet: ts_session ... Path=/; HttpOnly; Secure; SameSite=lax   und   ts_csrf ... Path=/; Secure

# 5. Administrations-Pfade sind aus dem Internet gesperrt (von einer Adresse außerhalb der Freigabe)
curl -so /dev/null -w "%{http_code}\n" https://timesheet.wenkel.de/api/backup/tables   # erwartet: 403

# 6. Weiterleitungen des IIS zeigen auf die öffentliche Adresse
curl -sI https://timesheet.wenkel.de/assets | grep -i location   # erwartet: https://timesheet.wenkel.de/assets/
```

Im Browser: `https://timesheet.wenkel.de/` öffnen, anmelden, Zeit erfassen, Export als PDF laden, abmelden.

## Fallstricke

1. **Client-Adresse im Docker.** Die Freigabeliste und die Login-Bremse arbeiten mit `$remote_addr`. Läuft der Proxy im Docker-Bridge-Netz, steht dort unter Umständen nur das Gateway (`172.x`) statt der echten Adresse. Dann wirkt die Freigabe für alle oder für keinen. Abhilfe: `network_mode: host` oder `"userland-proxy": false` in der Docker-Konfiguration. Mit `curl` aus dem Internet (Prüfpunkt 5) kontrollieren.
2. **Interne Nutzer und das Admin-Tool gehen über `timesheet.wenkel.de`.** Löst der interne DNS den Namen auf die öffentliche Adresse auf, kann die Quelladresse durch NAT am Firewall-Rand erscheinen und die Freigabeliste verfehlen. Abhilfe: interner DNS (Split-DNS) auf die interne Adresse des Proxys, oder die Adresse der Firewall in die Freigabe aufnehmen.
3. **Klartext zwischen Proxy und IIS.** Sitzungs-Cookie und Passwörter laufen auf dieser Strecke unverschlüsselt. Das ist nur im abgeschotteten Serversegment des Firmennetzes vertretbar. Sobald der IIS HTTPS kann: `proxy_pass https://…`, `proxy_ssl_server_name on`, `proxy_ssl_name intranet.wenkel.local` und `proxy_ssl_verify on` mit der Firmen-CA ergänzen.
4. **`.local`-Namen in Containern.** `intranet.wenkel.local` wird über das DNS des Docker-Hosts aufgelöst. Funktioniert das nicht, `extra_hosts: ["intranet.wenkel.local:<IP>"]` setzen. nginx löst den Namen nur beim Start auf: Ändert sich die IP des IIS, nginx neu laden.
5. **Zertifikatsablauf** beobachten. Das Admin-Tool meldet bei einem abgelaufenen Zertifikat einen TLS-Fehler.
6. **Grenzen der Bremse.** `limit_req` zählt pro Adresse. Hinter einem gemeinsamen Firmen-NAT teilen sich viele Nutzer eine Adresse, deshalb ist die Grenze großzügig (30 pro Minute, Burst 10).
7. **Nicht durchgereicht:** `/docs`, `/redoc` und `/openapi.json` der API. Der IIS leitet nur `/timesheet/api/*` an das Backend weiter, die Dokumentation ist von außen nicht erreichbar.

## Was getestet wurde

Die Konfiguration wurde lokal mit Docker gegen eine Attrappe des IIS geprüft (nginx 1.31, selbstsigniertes Zertifikat nur für den Test): Syntax (`nginx -t`), HTTP→HTTPS, Umschreiben der Pfade inklusive Query-String, Host-Header `intranet.wenkel.local`, `X-Forwarded-*`, HSTS genau einmal, Weiterleitungen des IIS, Sperre und Freigabe der Administrations-Pfade nach Quelladresse, Upload-Grenze (26 MB → 413), Login-Bremse (429).

**Nicht getestet:** der echte IIS (insbesondere sein SPA-Fallback und die Backend-Weiterleitung mit dem neuen Build), das Zertifikat und das Verhalten von `$remote_addr` im echten Proxy-Container. Dafür gilt die Prüfliste oben.
