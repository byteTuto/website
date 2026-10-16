#!/usr/bin/env bash
# Lancé sur EC2 par GitHub Actions (ou à la main) depuis /opt/bytetuto.
# Tire la nouvelle image, redémarre, vérifie /healthz, et revient à l'image précédente si ça échoue.
#   usage : IMAGE=ghcr.io/bytetuto/website:<sha7> bash deploy/deploy.sh
set -euo pipefail
cd "$(dirname "$0")/.."

[ -f .env ] && set -a && . ./.env && set +a
: "${IMAGE:?IMAGE non défini}"

PREV=$(cat .last_image 2>/dev/null || true)
echo "==> Déploiement de $IMAGE (précédente : ${PREV:-aucune})"

export IMAGE
docker compose pull web
docker compose up -d --remove-orphans web

healthy() {
  for i in $(seq 1 20); do
    if curl -fsS -o /dev/null http://127.0.0.1/healthz; then return 0; fi
    sleep 2
  done
  return 1
}

if healthy; then
  echo "$IMAGE" > .last_image
  docker image prune -f >/dev/null
  echo "✔ Déployé : $IMAGE"
else
  echo "✘ /healthz ne répond pas — retour arrière" >&2
  docker compose logs --tail=50 web >&2 || true
  if [ -n "$PREV" ]; then
    IMAGE="$PREV" docker compose up -d web
    echo "↩ Revenu à $PREV" >&2
  fi
  exit 1
fi
