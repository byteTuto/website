#!/usr/bin/env bash
# Obtient le certificat Let's Encrypt (une seule fois), puis bascule nginx en HTTPS.
# Pré-requis : DNS du domaine (et www) pointant vers l'EC2, port 80 ouvert, site en ligne en HTTP.
#   usage (sur EC2) : cd /opt/bytetuto && bash deploy/init-ssl.sh
set -euo pipefail
cd "$(dirname "$0")/.."
[ -f .env ] && set -a && . ./.env && set +a
: "${DOMAIN:?DOMAIN non défini dans .env}"
: "${LETSENCRYPT_EMAIL:?LETSENCRYPT_EMAIL non défini dans .env}"

STAGING=${STAGING:-0}   # STAGING=1 pour tester sans toucher aux quotas Let's Encrypt
extra=""; [ "$STAGING" = "1" ] && extra="--staging"

docker compose --profile certbot run --rm certbot certonly \
  --webroot -w /var/www/certbot \
  -d "$DOMAIN" -d "www.$DOMAIN" \
  --email "$LETSENCRYPT_EMAIL" --agree-tos --no-eff-email --non-interactive $extra

# Le script d'entrée nginx détecte le certificat au redémarrage
docker compose restart web
sleep 2
curl -fsSI "https://$DOMAIN/healthz" && echo "✔ HTTPS actif sur https://$DOMAIN"
