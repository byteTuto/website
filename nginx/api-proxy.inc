# Proxy vers le service d'inscription (inclus par les locations /api/ de site.inc)
resolver 127.0.0.11 valid=10s ipv6=off;
set $bytetuto_api http://api:8000;
proxy_pass $bytetuto_api;
proxy_http_version 1.1;
proxy_set_header Host $host;
proxy_set_header X-Real-IP $remote_addr;      # écrase toute valeur envoyée par le client
proxy_set_header Connection "";
proxy_connect_timeout 3s;
proxy_read_timeout 10s;
client_max_body_size 4k;
include /etc/nginx/snippets/security-headers.inc;
add_header Cache-Control "no-store" always;
