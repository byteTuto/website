# Relais vers un site supplémentaire (dashboard…) qui tourne dans son propre conteneur,
# sur le réseau Docker partagé « bytetuto-sites ». $site_upstream est fixé par le bloc server.
# Résolu à chaque requête : nginx démarre même si le conteneur du site est absent
# (le visiteur voit alors « site momentanément indisponible », bytetuto.com n'est pas touché).
# Les en-têtes CSP / X-Frame-Options sont laissés à l'application elle-même.
location / {
    resolver 127.0.0.11 valid=10s ipv6=off;
    proxy_pass $site_upstream;
    proxy_http_version 1.1;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;           # écrase toute valeur envoyée par le client
    proxy_set_header X-Forwarded-For $remote_addr;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_set_header X-Forwarded-Host $host;
    proxy_set_header Upgrade $http_upgrade;            # WebSocket (graphiques en temps réel…)
    proxy_set_header Connection $connection_upgrade;
    proxy_connect_timeout 3s;
    proxy_read_timeout 60s;
    client_max_body_size 10m;

    add_header X-Content-Type-Options "nosniff" always;
    add_header Strict-Transport-Security $hsts always;   # vide en HTTP -> non envoyé
}

error_page 502 503 504 = @site_indisponible;
location @site_indisponible {
    default_type text/plain;
    add_header Retry-After "30" always;
    add_header Cache-Control "no-store" always;
    return 503 "Site momentanément indisponible, réessaie dans quelques instants.\n";
}
