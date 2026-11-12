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

# Sites supplémentaires (ex. dashboard.bytetuto.com, synko.bytetuto.com), chacun dans son propre conteneur.
#   EXTRA_SITES="dashboard.bytetuto.com=http://bytetuto-dashboard:8080 synko.bytetuto.com=http://bytetuto-synko:8080"
# Une entrée invalide est ignorée (avertissement) : le site principal démarre toujours.
rm -f /etc/nginx/conf.d/extra-*.conf
for entry in ${EXTRA_SITES:-}; do
  SITE_HOST="${entry%%=*}"
  SITE_UPSTREAM="${entry#*=}"
  if ! printf '%s' "$SITE_HOST" | grep -Eq '^[a-z0-9]([a-z0-9-]*[a-z0-9])?(\.[a-z0-9]([a-z0-9-]*[a-z0-9])?)+$' \
     || ! printf '%s' "$SITE_UPSTREAM" | grep -Eq '^http://[A-Za-z0-9._-]+(:[0-9]{1,5})?$' \
     || [ "$SITE_HOST" = "$DOMAIN" ] || [ "$SITE_HOST" = "www.$DOMAIN" ]; then
    echo "bytetuto: entrée EXTRA_SITES ignorée (attendu hote=http://conteneur:port) : $entry" >&2
    continue
  fi
  if [ -f "/etc/letsencrypt/live/$SITE_HOST/fullchain.pem" ]; then
    xtpl=/etc/nginx/bytetuto/extra-https.conf.template
    echo "bytetuto: site $SITE_HOST -> $SITE_UPSTREAM (HTTPS)"
  else
    xtpl=/etc/nginx/bytetuto/extra-http.conf.template
    echo "bytetuto: site $SITE_HOST -> $SITE_UPSTREAM (HTTP seul, pas de certificat)"
  fi
  export SITE_HOST SITE_UPSTREAM
  envsubst '${SITE_HOST} ${SITE_UPSTREAM}' < "$xtpl" > "/etc/nginx/conf.d/extra-$SITE_HOST.conf"
done
