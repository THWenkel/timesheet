# nginx-Reverse-Proxy für https://cloudserver2.hopto.org/timesheet/

Diese Anleitung ist für die Person, die den nginx-Reverse-Proxy (Docker, eigenes Git-Repository) betreut. Die Timesheet-Anwendung soll unter **https://cloudserver2.hopto.org/timesheet/** aus dem Internet erreichbar sein (**Path-Routing**). Die Anwendung selbst läuft weiter unter IIS.

> Die spätere Umstellung auf eine eigene Domain (`https://timesheet.wenkel.de/`) ist in [NGINX_REVERSE_PROXY_DOMAIN.md](NGINX_REVERSE_PROXY_DOMAIN.md) beschrieben. Diese Anleitung hier gilt, solange der Proxy noch mit dem Hostnamen `cloudserver2.hopto.org` arbeitet.

## Überblick

``` text
Browser ──HTTPS──▶ cloudserver2.hopto.org/timesheet/ ──[nginx-Proxy]──HTTP──▶ intranet.wenkel.local/timesheet/ (IIS)
   /timesheet/assets/a.js    →  /timesheet/assets/a.js        statische Dateien (IIS)
   /timesheet/api/employees/ →  /timesheet/api/employees/     IIS leitet an das Backend (localhost:8000)
   /timesheet/beliebig       →  /timesheet/beliebig           IIS liefert index.html (SPA)
```

- Der Proxy macht **TLS** (das vorhandene Letsencrypt-Zertifikat von `cloudserver2.hopto.org`). Zum IIS geht es **per HTTP**, weil der IIS wegen der Domäne `intranet.wenkel.local` kein HTTPS kann.
- Öffentlicher Pfad und IIS-Pfad sind identisch (`/timesheet/…`). Der Proxy schreibt **nichts um**, er reicht den Pfad durch.
- **Kein neues Zertifikat, keine neue DNS-Adresse, kein neuer server-Block.** Es kommen nur drei Dateien dazu und eine `include`-Zeile in den bestehenden HTTPS-server-Block.
- Das Frontend wird mit `npm run build:path` gebaut (Basispfad `/timesheet/`, siehe Abschnitt „Gegenstücke“).

## Was im Proxy-Repository zu tun ist

1. Die drei Dateien (unten) nach `conf.d/` des Proxys legen, also in den Ordner, der in den Container nach `/etc/nginx/conf.d/` gemountet wird:
   - `timesheet-http.conf` wird dort automatisch geladen (Endung `.conf`, `http`-Ebene).
   - `timesheet-locations.inc` und `timesheet-proxy.inc` werden **nicht** automatisch geladen (Endung `.inc`). Sie werden nur dort verwendet, wo sie per `include` eingebunden sind.
2. Im **bestehenden** HTTPS-server-Block von `cloudserver2.hopto.org` eine Zeile ergänzen (an beliebiger Stelle zwischen den anderen `location`-Blöcken):
   ```nginx
   include /etc/nginx/conf.d/timesheet-locations.inc;
   ```
   Zertifikatspfade, Letsencrypt und alle anderen Seiten bleiben unverändert.
3. In `timesheet-locations.inc` die Stelle `<<< ANPASSEN >>>` setzen: die **Firmennetz-Adressbereiche** für die Administrations-Pfade.
4. Der Proxy-Container muss `intranet.wenkel.local` auflösen und Port 80 des IIS erreichen (Firewall, DNS im Container). Test: `docker exec <proxy> wget -S -O- http://intranet.wenkel.local/timesheet/` (erwartet: 200 und HTML).
5. `docker exec <proxy> nginx -t`, bei Erfolg `docker exec <proxy> nginx -s reload`. Bei einem Fehler im Test wird nichts geladen, die laufenden Seiten bleiben, wie sie sind.

Falls `conf.d/` bei dir nicht gemountet ist, sondern die Konfiguration im Image steckt: die Dateien an den Ort legen, der gemountet ist, und die drei Pfade `/etc/nginx/conf.d/…` in `timesheet-locations.inc` und der `include`-Zeile entsprechend anpassen.

Die Dateien liegen auch im Repository der Anwendung unter `deploy/nginx-proxy/`.

## Konfiguration

### timesheet-http.conf

```nginx
# =============================================================================
# timesheet-http.conf
#
# Teil 1 von 3 fuer https://cloudserver2.hopto.org/timesheet/ (Path-Routing).
# Diese Datei liegt in conf.d/ des Proxys und wird dadurch im http-Block geladen.
# Sie enthaelt nur Definitionen, die auf http-Ebene stehen muessen. Sie aendert
# nichts an bestehenden Seiten.
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
```

### timesheet-locations.inc

```nginx
# =============================================================================
# timesheet-locations.inc
#
# Teil 2 von 3 fuer https://cloudserver2.hopto.org/timesheet/ (Path-Routing).
#
#   Browser --HTTPS--> cloudserver2.hopto.org/timesheet/ --[Proxy]--HTTP--> IIS
#                                                     intranet.wenkel.local/timesheet/
#
# Diese Datei wird INNERHALB des bestehenden HTTPS-server-Blocks von
# cloudserver2.hopto.org eingebunden (Zertifikat und Letsencrypt bleiben unveraendert):
#
#     server {
#         listen 443 ssl;
#         server_name cloudserver2.hopto.org;
#         ...
#         include /etc/nginx/conf.d/timesheet-locations.inc;     # <-- diese Zeile ergaenzen
#     }
#
# Sie liegt bewusst in conf.d/, hat aber die Endung .inc: Die Zeile "include conf.d/*.conf"
# laedt sie deshalb nicht von selbst als eigene Konfiguration.
# Der Pfad bleibt gleich: /timesheet/... oeffentlich = /timesheet/... im IIS (kein Umschreiben).
# =============================================================================

# /timesheet ohne Schraegstrich -> mit Schraegstrich
location = /timesheet {
    return 301 https://$host/timesheet/;
}

# "^~" sorgt dafuer, dass keine Regex-Location des bestehenden server-Blocks (z. B. fuer
# Dateiendungen wie .js/.css) die Anfragen an /timesheet/ abfaengt.
location ^~ /timesheet/ {
    include /etc/nginx/conf.d/timesheet-proxy.inc;

    # Administrations-Pfade (nur vom Admin-Tool genutzt): nur aus dem Firmennetz.
    # Zusaetzliche Schicht. Der Login mit Administrator-Recht ist weiterhin Pflicht.
    location ~ ^/timesheet/api/(backup|projects|customers|employees/admin|auth/admin)(/|$) {
        # <<< ANPASSEN >>> eigene Firmennetz-Adressbereiche eintragen (Quelladresse, wie sie
        # beim Proxy ankommt, siehe NGINX_REVERSE_PROXY.md "Fallstricke")
        allow 10.0.0.0/8;
        allow 172.16.0.0/12;
        allow 192.168.0.0/16;
        deny  all;

        include /etc/nginx/conf.d/timesheet-proxy.inc;
    }

    # Login mit Bremse pro IP
    location = /timesheet/api/auth/login {
        limit_req zone=timesheet_login burst=10 nodelay;
        limit_req_status 429;

        include /etc/nginx/conf.d/timesheet-proxy.inc;
    }
}
```

### timesheet-proxy.inc

```nginx
# =============================================================================
# timesheet-proxy.inc
#
# Teil 3 von 3 fuer https://cloudserver2.hopto.org/timesheet/ (Path-Routing).
# Gemeinsame Proxy-Direktiven, eingebunden in jede location von timesheet-locations.inc:
#     include /etc/nginx/conf.d/timesheet-proxy.inc;
# =============================================================================

# Kein Umschreiben: Die App liegt im IIS unter /timesheet/ und oeffentlich ebenfalls.
# Ohne URI hinter proxy_pass reicht nginx den Pfad samt Query-String unveraendert durch.
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

# Falls der IIS mit seinem internen Namen umleitet (z. B. Verzeichnis ohne Schraegstrich).
proxy_redirect http://intranet.wenkel.local/ https://$host/;

# Der Host cloudserver2.hopto.org bedient auch andere Anwendungen. Das Session-Cookie
# der App (Path=/) wird deshalb auf /timesheet/ beschraenkt und wird nur dorthin gesendet.
proxy_cookie_path / /timesheet/;

# Das Backend sendet bei COOKIE_SECURE=true selbst einen HSTS-Header. Ob und wie HSTS
# fuer den Host gesetzt wird, entscheidet der bestehende server-Block, nicht die App.
proxy_hide_header Strict-Transport-Security;

# PDF-/Excel-Export und Restore-Import koennen dauern bzw. gross sein.
proxy_read_timeout  120s;
proxy_send_timeout  120s;
client_max_body_size 25m;
```

### Was die einzelnen Teile bewirken

| Teil | Zweck |
| --- | --- |
| `proxy_pass http://timesheet_iis;` (ohne URI) | reicht Pfad und Query-String unverändert an den IIS durch |
| `location ^~ /timesheet/` | hat Vorrang vor Regex-Locations des bestehenden Servers, z. B. `location ~* \.(js\|css)$`. Ohne `^~` würden solche Regeln die Dateien der App abfangen |
| `proxy_set_header Host intranet.wenkel.local;` | die IIS-Site ist an diesen Hostnamen gebunden, mit dem öffentlichen Namen würde der IIS die falsche Site treffen |
| `X-Forwarded-Host/-Proto/-For`, `X-Real-IP` | der Backend-Stack erfährt Originalname, Protokoll und Client-Adresse |
| `proxy_redirect` | schreibt Weiterleitungen des IIS (z. B. Verzeichnis ohne Schrägstrich) auf die öffentliche Adresse um |
| `proxy_cookie_path / /timesheet/;` | der Host bedient auch andere Anwendungen. Das Session-Cookie der App wird auf `/timesheet/` beschränkt und nur dorthin gesendet |
| `proxy_hide_header Strict-Transport-Security` | das Backend sendet bei `COOKIE_SECURE=true` selbst HSTS. Ob und wie HSTS für den Host gesetzt wird, entscheidet der bestehende server-Block |
| `client_max_body_size 25m` | der Restore-Import der Datensicherung schickt den Dateiinhalt im JSON-Body, die Standardgrenze von 1 MB reicht nicht |
| `proxy_read_timeout 120s` | PDF- und Excel-Export können dauern |
| verschachtelte Regex-Location für Administrations-Pfade | `/timesheet/api/backup`, `projects`, `customers`, `employees/admin`, `auth/admin` nur aus dem Firmennetz. Das ist eine zweite Schicht **zusätzlich** zum Login mit Administrator-Recht |
| `limit_req` auf `/timesheet/api/auth/login` | Bremse gegen Passwort-Raten pro IP. Ergänzt die Kontosperre der Anwendung (5 Fehlversuche, 15 Minuten) |

## Gegenstücke auf der Anwendungsseite (IIS-Server)

1. **Frontend bauen** und in den IIS-Ordner kopieren:
   ```powershell
   cd C:\Develop\timesheet\frontend
   npm run build:path
   Copy-Item -Path "dist\*" -Destination "C:\inetpub\wwwroot\intranet.wenkel.local\timesheet" -Recurse -Force
   ```
   `build:path` nutzt `frontend/.env.proxypath`: Basispfad `/timesheet/`, API-Aufrufe an `/timesheet/api/…`, und der Wert `VITE_API_URL` aus `frontend/.env` (`http://localhost:8000`) wird überschrieben. **Ein normaler `npm run build` mit vorhandener `.env` brennt `localhost:8000` ins Bundle und darf hier nicht verwendet werden.**
   Dieser Build läuft sowohl über den Proxy als auch beim direkten Aufruf von `http://intranet.wenkel.local/timesheet/` (Anmeldung dort siehe Punkt 2).
2. **`backend/.env`** auf dem IIS-Server:
   ```
   AUTH_ENABLED=true
   SECRET_KEY=<mindestens 32 Zeichen, z. B. python -c "import secrets; print(secrets.token_hex(32))">
   COOKIE_SECURE=true
   CORS_ORIGINS=["https://cloudserver2.hopto.org"]
   ```
   `COOKIE_SECURE=true` passt, weil der Browser ausschließlich HTTPS sieht. Backend danach neu starten (Dienst `TimesheetBackend`). **Folge:** Die Anmeldung über `http://intranet.wenkel.local/timesheet/` funktioniert damit nicht mehr, weil der Browser ein `Secure`-Cookie nicht über HTTP speichert. Alle Nutzer gehen über die öffentliche Adresse.
3. **Im IIS keine http→https-Umleitung einrichten.** Der Proxy spricht HTTP mit dem IIS, eine solche Regel würde eine Endlosschleife erzeugen. (Die Anleitung `INSTALL_IIS_INTRANET.md` Schritt 8 gilt für diesen Betrieb nicht.)
4. **Windows-Admin-Tool:** Umgebungsvariable `TIMESHEET_API_URL=https://cloudserver2.hopto.org/timesheet/` (mit Schrägstrich am Ende, sonst geht der Pfad `/timesheet` verloren). Bei einem Zertifikat einer öffentlichen CA braucht der PC nichts weiter. Die Administrations-Pfade funktionieren nur von Adressen aus der Freigabeliste (siehe Fallstricke).

## Prüfliste

Von einem beliebigen Rechner (`-i` zeigt die Header):

```bash
H=https://cloudserver2.hopto.org

# 1. Die App wird ausgeliefert, /timesheet wird zu /timesheet/
curl -sI $H/timesheet  | head -3                                               # 301 -> /timesheet/
curl -sI $H/timesheet/ | head -1                                               # 200

# 2. Die anderen Seiten auf diesem Host sind unberührt
curl -sI $H/ | head -1                                                         # wie vorher

# 3. Statische Dateien und API laufen über den Proxy
curl -s  $H/timesheet/api/auth/config                                          # {"auth_enabled":true}
curl -so /dev/null -w "%{http_code}\n" $H/timesheet/api/employees/             # 401 ohne Login

# 4. Cookie-Attribute nach dem Login (Benutzername und Passwort einsetzen)
curl -si -X POST $H/timesheet/api/auth/login \
  -H 'content-type: application/json' -d '{"username":"...","password":"..."}' | grep -i set-cookie
#    erwartet: ts_session ... Path=/timesheet/; HttpOnly; Secure; SameSite=lax   und   ts_csrf ... Path=/timesheet/; Secure

# 5. Administrations-Pfade sind aus dem Internet gesperrt (von einer Adresse außerhalb der Freigabe)
curl -so /dev/null -w "%{http_code}\n" $H/timesheet/api/backup/tables          # erwartet: 403

# 6. Weiterleitungen des IIS zeigen auf die öffentliche Adresse
curl -sI $H/timesheet/assets | grep -i location                                # erwartet: https://cloudserver2.hopto.org/timesheet/assets/
```

Im Browser: `https://cloudserver2.hopto.org/timesheet/` öffnen, anmelden, Zeit erfassen, Export als PDF laden, abmelden.

## Fallstricke

1. **Client-Adresse im Docker.** Die Freigabeliste und die Login-Bremse arbeiten mit `$remote_addr`. Läuft der Proxy im Docker-Bridge-Netz, steht dort unter Umständen nur das Gateway (`172.x`) statt der echten Adresse. Dann wirkt die Freigabe für alle oder für keinen. Abhilfe: `network_mode: host` oder `"userland-proxy": false` in der Docker-Konfiguration. Mit `curl` aus dem Internet (Prüfpunkt 5) kontrollieren.
2. **Interne Nutzer und das Admin-Tool gehen ebenfalls über `cloudserver2.hopto.org`.** Löst der interne DNS den Namen auf die öffentliche Adresse auf, kann die Quelladresse durch NAT am Firewall-Rand erscheinen und die Freigabeliste verfehlen. Abhilfe: interner DNS (Split-DNS) auf die interne Adresse des Proxys, oder die Adresse der Firewall in die Freigabe aufnehmen.
3. **Klartext zwischen Proxy und IIS.** Sitzungs-Cookie und Passwörter laufen auf dieser Strecke unverschlüsselt. Das ist nur im abgeschotteten Serversegment des Firmennetzes vertretbar. Sobald der IIS HTTPS kann: `proxy_pass https://…`, `proxy_ssl_server_name on`, `proxy_ssl_name intranet.wenkel.local` und `proxy_ssl_verify on` mit der Firmen-CA ergänzen.
4. **`.local`-Namen in Containern.** `intranet.wenkel.local` wird über das DNS des Docker-Hosts aufgelöst. Funktioniert das nicht, `extra_hosts: ["intranet.wenkel.local:<IP>"]` setzen. nginx löst den Namen nur beim Start auf: Ändert sich die IP des IIS, nginx neu laden.
5. **Zertifikat:** Es bleibt das vorhandene Letsencrypt-Zertifikat von `cloudserver2.hopto.org`, dafür ist nichts zu tun. Das Admin-Tool meldet bei einem abgelaufenen Zertifikat einen TLS-Fehler.
6. **Geteilter Host.** Andere Anwendungen auf `cloudserver2.hopto.org` teilen sich mit der App Hostname und damit auch HSTS. Das Cookie der App ist auf `/timesheet/` beschränkt (`proxy_cookie_path`), damit es nicht an andere Pfade gesendet wird.
7. **Grenzen der Bremse.** `limit_req` zählt pro Adresse. Hinter einem gemeinsamen Firmen-NAT teilen sich viele Nutzer eine Adresse, deshalb ist die Grenze großzügig (30 pro Minute, Burst 10).
8. **Nicht durchgereicht:** `/docs`, `/redoc` und `/openapi.json` der API. Der IIS leitet nur `/timesheet/api/*` an das Backend weiter, die Dokumentation ist von außen nicht erreichbar.

## Was getestet wurde

Die Konfiguration wurde lokal mit Docker gegen eine Attrappe des IIS geprüft (nginx, selbstsigniertes Zertifikat nur für den Test), eingebunden in einen nachgebauten „bestehenden“ server-Block mit einer fremden Anwendung und einer Regex-Location für `.js`/`.css` (38 Prüfungen): Syntax (`nginx -t`), Pfad und Query-String unverändert durchgereicht, die andere Anwendung und ihre Regeln unberührt, Vorrang vor der Regex-Location (`^~`), Host-Header `intranet.wenkel.local`, `X-Forwarded-*`, HSTS genau einmal, Cookie-Pfad `/timesheet/`, Weiterleitungen des IIS, Sperre und Freigabe der Administrations-Pfade nach Quelladresse, Upload-Grenze (26 MB → 413), Login-Bremse (429).

Zusätzlich: Der Build `npm run build:path` enthält `/timesheet/assets/…` und den API-Pfad `/timesheet`, aber kein `localhost:8000`.

**Nicht getestet:** der echte IIS (insbesondere sein SPA-Fallback und die Backend-Weiterleitung mit dem neuen Build), das echte Letsencrypt-Zertifikat, das Zusammenspiel mit dem bestehenden server-Block und das Verhalten von `$remote_addr` im echten Proxy-Container. Dafür gilt die Prüfliste oben.
