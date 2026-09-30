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
