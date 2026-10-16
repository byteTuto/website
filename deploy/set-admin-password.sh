#!/usr/bin/env bash
# Choisit (ou change) le mot de passe de la page https://bytetuto.com/admin/
# À lancer sur l'EC2 depuis /opt/bytetuto :   bash deploy/set-admin-password.sh
#
# Le mot de passe n'est écrit nulle part : seule son empreinte scrypt va dans .env (ADMIN_PASSWORD_HASH).
# ADMIN_SECRET (clé qui signe les sessions) est créée au premier lancement ; --deconnecter-tout la renouvelle.
set -euo pipefail
cd "$(dirname "$0")/.."

docker compose ps --status running api 2>/dev/null | grep -q bytetuto-api || {
  echo "✘ Le service api ne tourne pas. Lance d'abord un déploiement (ou : docker compose up -d api)." >&2; exit 1; }

read -rsp "Nouveau mot de passe (12 caractères minimum) : " PW1; echo
read -rsp "Encore une fois : " PW2; echo
[ "$PW1" = "$PW2" ] || { echo "✘ Les deux saisies sont différentes." >&2; exit 1; }
[ ${#PW1} -ge 12 ] || { echo "✘ Trop court : 12 caractères minimum (une phrase de 4 mots, c'est parfait)." >&2; exit 1; }

HASH=$(printf '%s\n' "$PW1" | docker compose exec -T api python app.py hash-password)
unset PW1 PW2

touch .env && chmod 600 .env
SECRET=$(grep -E '^ADMIN_SECRET=' .env | cut -d= -f2- || true)
if [ -z "$SECRET" ] || [ "${1:-}" = "--deconnecter-tout" ]; then
  SECRET=$(docker compose exec -T api python -c 'import secrets; print(secrets.token_hex(32))')
fi

grep -vE '^(ADMIN_PASSWORD_HASH|ADMIN_SECRET)=' .env > .env.tmp || true
printf 'ADMIN_PASSWORD_HASH=%s\nADMIN_SECRET=%s\n' "$HASH" "$SECRET" >> .env.tmp
mv .env.tmp .env && chmod 600 .env

docker compose up -d api >/dev/null
echo "✔ Mot de passe enregistré (empreinte seulement) et service api redémarré."
# On teste le HTTPS en vrai (le dossier certbot/conf/live appartient à root : on ne peut pas s'y fier)
DOMAIN=${DOMAIN:-$(grep -E '^DOMAIN=' .env | cut -d= -f2-)}
if [ -n "$DOMAIN" ] && curl -fsS -o /dev/null --max-time 5 "https://$DOMAIN/healthz"; then
  echo "→ Connecte-toi sur https://$DOMAIN/admin/"
else
  echo "! https://${DOMAIN:-<domaine>}/ ne répond pas : /admin/ reste fermée tant que le HTTPS n'est pas actif (deploy/init-ssl.sh)."
fi
