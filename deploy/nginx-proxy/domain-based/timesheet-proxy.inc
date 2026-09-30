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
