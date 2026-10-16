#!/bin/sh
# Choisit la conf nginx au démarrage du conteneur :
#   - DOMAIN défini ET certificat présent -> HTTPS (+ redirection HTTP)
#   - sinon                              -> HTTP seul (avec défi ACME)
set -eu

DOMAIN="${DOMAIN:-}"
if [ -n "$DOMAIN" ]; then
  SERVER_NAMES="$DOMAIN www.$DOMAIN"
else
  SERVER_NAMES="_"
fi
export DOMAIN SERVER_NAMES

if [ -n "$DOMAIN" ] && [ -f "/etc/letsencrypt/live/$DOMAIN/fullchain.pem" ]; then
  tpl=/etc/nginx/bytetuto/https.conf.template
  echo "bytetuto: certificat trouvé pour $DOMAIN -> HTTPS"
else
  tpl=/etc/nginx/bytetuto/http.conf.template
  echo "bytetuto: pas de certificat (DOMAIN='${DOMAIN}') -> HTTP seul"
fi

envsubst '${DOMAIN} ${SERVER_NAMES}' < "$tpl" > /etc/nginx/conf.d/default.conf
