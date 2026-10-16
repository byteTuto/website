# Page admin des inscrits : incluse UNIQUEMENT dans le serveur HTTPS (https.conf.template).
# En HTTP seul, /admin/ n'existe pas (404) : le mot de passe ne circule jamais en clair.
location = /admin {
    return 301 /admin/;
}
location /admin/ {
    limit_req zone=admin burst=30 nodelay;
    limit_except GET POST { deny all; }
    include /etc/nginx/snippets/api-proxy.inc;
    proxy_set_header X-Forwarded-Proto https;
}
