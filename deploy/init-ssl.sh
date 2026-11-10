#!/usr/bin/env bash
# Obtient le certificat Let's Encrypt, puis bascule nginx en HTTPS.
# Pré-requis : DNS du domaine ET de www pointant vers l'EC2, port 80 ouvert, site en ligne en HTTP.
#   usage (sur EC2) : cd /opt/bytetuto
#     STAGING=1 bash deploy/init-ssl.sh   # répétition : vérifie que tout passe, n'installe rien
#     bash deploy/init-ssl.sh             # vrai certificat + bascule HTTPS
#   Sous-domaine servi par un autre dépôt (listé dans EXTRA_SITES, DNS pointant vers l'EC2) :
#     STAGING=1 bash deploy/init-ssl.sh dashboard.bytetuto.com
#     bash deploy/init-ssl.sh dashboard.bytetuto.com
#   -> certificat séparé : celui de bytetuto.com n'est pas touché.
set -euo pipefail
cd "$(dirname "$0")/.."
[ -f .env ] && set -a && . ./.env && set +a
: "${DOMAIN:?DOMAIN non défini dans .env (variable GitHub DOMAIN manquante ?)}"
: "${LETSENCRYPT_EMAIL:?LETSENCRYPT_EMAIL non défini dans .env}"

SITE="${1:-$DOMAIN}"
if [ "$SITE" = "$DOMAIN" ]; then
  names=(-d "$DOMAIN" -d "www.$DOMAIN")
else
  [[ "$SITE" =~ ^[a-z0-9]([a-z0-9.-]*[a-z0-9])?$ ]] || { echo "Nom de domaine invalide : $SITE" >&2; exit 1; }
  if ! docker compose exec -T web test -f "/etc/nginx/conf.d/extra-$SITE.conf"; then
    echo "✘ $SITE n'est pas servi par nginx : ajoute-le à EXTRA_SITES (docker-compose.yml ou .env) et redéploie." >&2
    exit 1
  fi
  names=(-d "$SITE")
fi

certbot() { docker compose --profile certbot run --rm certbot "$@"; }
args=(--webroot -w /var/www/certbot "${names[@]}"
      --email "$LETSENCRYPT_EMAIL" --agree-tos --no-eff-email --non-interactive)

if [ "${STAGING:-0}" = "1" ]; then
  # --dry-run : passe par les serveurs de test de Let's Encrypt et n'enregistre RIEN.
  certbot certonly "${args[@]}" --dry-run
  echo "✔ Répétition réussie : ${names[*]} validé(s)."
  echo "  Lance maintenant : bash deploy/init-ssl.sh${1:+ $1}"
  exit 0
fi

# Un ancien certificat de TEST (ancienne version de ce script) bloquerait le vrai : on le retire.
existing=$(certbot certificates --cert-name "$SITE" 2>/dev/null || true)
if [[ "$existing" == *TEST_CERT* ]]; then
  echo "==> Suppression de l'ancien certificat de test"
  certbot delete --cert-name "$SITE" --non-interactive
fi

certbot certonly "${args[@]}" --cert-name "$SITE" --keep-until-expiring

# Le script d'entrée nginx détecte le certificat au redémarrage
docker compose restart web
sleep 3
if [ "$SITE" = "$DOMAIN" ]; then
  curl -fsSI "https://$DOMAIN/healthz" >/dev/null && echo "✔ HTTPS actif sur https://$DOMAIN"
else
  # Le certificat est valide même si le conteneur du site n'est pas encore lancé (réponse 503).
  code=$(curl -sS -o /dev/null -w '%{http_code}' "https://$SITE/")
  echo "✔ HTTPS actif sur https://$SITE (réponse $code$([ "$code" = 503 ] && echo ' : conteneur du site pas encore lancé'))"
fi
