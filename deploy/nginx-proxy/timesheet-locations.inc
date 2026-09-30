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
