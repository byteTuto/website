#!/usr/bin/env bash
# Obtient le certificat Let's Encrypt, puis bascule nginx en HTTPS.
# Pré-requis : DNS du domaine ET de www pointant vers l'EC2, port 80 ouvert, site en ligne en HTTP.
#   usage (sur EC2) : cd /opt/bytetuto
#     STAGING=1 bash deploy/init-ssl.sh   # répétition : vérifie que tout passe, n'installe rien
#     bash deploy/init-ssl.sh             # vrai certificat + bascule HTTPS
set -euo pipefail
cd "$(dirname "$0")/.."
[ -f .env ] && set -a && . ./.env && set +a
: "${DOMAIN:?DOMAIN non défini dans .env (variable GitHub DOMAIN manquante ?)}"
: "${LETSENCRYPT_EMAIL:?LETSENCRYPT_EMAIL non défini dans .env}"

certbot() { docker compose --profile certbot run --rm certbot "$@"; }
args=(--webroot -w /var/www/certbot -d "$DOMAIN" -d "www.$DOMAIN"
      --email "$LETSENCRYPT_EMAIL" --agree-tos --no-eff-email --non-interactive)

if [ "${STAGING:-0}" = "1" ]; then
  # --dry-run : passe par les serveurs de test de Let's Encrypt et n'enregistre RIEN.
  certbot certonly "${args[@]}" --dry-run
  echo "✔ Répétition réussie : les deux domaines sont validés."
  echo "  Lance maintenant : bash deploy/init-ssl.sh"
  exit 0
fi

# Un ancien certificat de TEST (ancienne version de ce script) bloquerait le vrai : on le retire.
existing=$(certbot certificates --cert-name "$DOMAIN" 2>/dev/null || true)
if [[ "$existing" == *TEST_CERT* ]]; then
  echo "==> Suppression de l'ancien certificat de test"
  certbot delete --cert-name "$DOMAIN" --non-interactive
fi

certbot certonly "${args[@]}" --cert-name "$DOMAIN" --keep-until-expiring

# Le script d'entrée nginx détecte le certificat au redémarrage
docker compose restart web
sleep 3
curl -fsSI "https://$DOMAIN/healthz" >/dev/null && echo "✔ HTTPS actif sur https://$DOMAIN"
