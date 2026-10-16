# Contenu du site — partagé entre la conf HTTP et la conf HTTPS
root  /usr/share/nginx/html;
index index.html;

# Santé (healthcheck Docker + vérification après déploiement)
location = /healthz {
    access_log off;
    default_type text/plain;
    return 200 "ok\n";
}

# Assets statiques : cache long (noms stables -> 7 jours, à passer en immutable si les fichiers sont versionnés)
location ~* \.(?:svg|png|jpg|jpeg|webp|ico|js|css|woff2?)$ {
    include /etc/nginx/snippets/security-headers.inc;
    add_header Cache-Control "public, max-age=604800";
    try_files $uri =404;
}

# Pages HTML : toujours revalidées (le coming soon doit changer dès le déploiement)
location / {
    include /etc/nginx/snippets/security-headers.inc;
    add_header Cache-Control "no-cache";
    try_files $uri $uri/ =404;
}

error_page 404 /404.html;
location = /404.html {
    include /etc/nginx/snippets/security-headers.inc;
    internal;
}
