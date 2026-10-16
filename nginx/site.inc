# Contenu du site — partagé entre la conf HTTP et la conf HTTPS
root  /usr/share/nginx/html;
index index.html;

# Santé (healthcheck Docker + vérification après déploiement)
location = /healthz {
    access_log off;
    default_type text/plain;
    return 200 "ok\n";
}

# Service d'inscription (conteneur « api », voir api/). Résolu à chaque requête par le DNS de Docker :
# nginx démarre même si l'API est absente (elle répond alors 502, la page affiche un message d'erreur).
location = /api/subscribe {
    limit_req zone=api_subscribe burst=10 nodelay;
    include /etc/nginx/snippets/api-proxy.inc;
}
location /api/ {
    limit_except GET HEAD { deny all; }
    include /etc/nginx/snippets/api-proxy.inc;
}

# Vidéos : cache long, lecture par morceaux (Range) gérée par nginx
location ~* \.(?:mp4|webm)$ {
    include /etc/nginx/snippets/security-headers.inc;
    add_header Cache-Control "public, max-age=604800";
    try_files $uri =404;
}

# Assets statiques : cache long (noms stables -> 7 jours, à passer en immutable si les fichiers sont versionnés)
location ~* \.(?:svg|png|jpg|jpeg|webp|ico|js|css|woff2?)$ {
    include /etc/nginx/snippets/security-headers.inc;
    add_header Cache-Control "public, max-age=604800";
    try_files $uri =404;
}

# Versions Markdown des pages (agents IA) : text/markdown, jamais indexées par Google (doublon du HTML)
location ~* \.md$ {
    default_type text/markdown;
    types { }
    include /etc/nginx/snippets/security-headers.inc;
    add_header Cache-Control "no-cache";
    add_header X-Robots-Tag "noindex" always;
    add_header Vary "Accept";
    try_files $uri =404;
}

# Pages HTML : toujours revalidées (le coming soon doit changer dès le déploiement)
location / {
    # Négociation de contenu : « Accept: text/markdown » sur une page -> son index.md
    if ($wants_markdown) {
        rewrite ^(.*)/$ $1/index.md last;
    }
    include /etc/nginx/snippets/security-headers.inc;
    add_header Cache-Control "no-cache";
    add_header Vary "Accept";
    try_files $uri $uri/ =404;
}

error_page 404 /404.html;
location = /404.html {
    include /etc/nginx/snippets/security-headers.inc;
    internal;
}
