#!/usr/bin/env bash
# Lancé sur EC2 par GitHub Actions (ou à la main) depuis /opt/bytetuto.
# Tire les nouvelles images (site + service d'inscription), redémarre, vérifie /healthz et la santé de l'API,
# et revient aux images précédentes si ça échoue. La base des inscrits (volume Docker api-data) n'est jamais touchée.
#   usage : IMAGE=ghcr.io/bytetuto/website:<sha7> API_IMAGE=ghcr.io/bytetuto/website-api:<sha7> bash deploy/deploy.sh
set -euo pipefail
cd "$(dirname "$0")/.."

[ -f .env ] && set -a && . ./.env && set +a
: "${IMAGE:?IMAGE non défini}"

API_IMAGE=${API_IMAGE:-ghcr.io/bytetuto/website-api:latest}
PREV=$(cat .last_image 2>/dev/null || true)
PREV_API=$(cat .last_api_image 2>/dev/null || true)
echo "==> Déploiement de $IMAGE + $API_IMAGE (précédentes : ${PREV:-aucune} / ${PREV_API:-aucune})"

export IMAGE API_IMAGE
docker compose pull web api
docker compose up -d --remove-orphans web api

api_healthy() {
  [ "$(docker inspect --format '{{.State.Health.Status}}' bytetuto-api 2>/dev/null)" = "healthy" ]
}

healthy() {
  for i in $(seq 1 30); do
    if curl -fsS -o /dev/null http://127.0.0.1/healthz && api_healthy; then return 0; fi
    sleep 2
  done
  return 1
}

if healthy; then
  echo "$IMAGE" > .last_image
  echo "$API_IMAGE" > .last_api_image
  docker image prune -f >/dev/null
  echo "✔ Déployé : $IMAGE + $API_IMAGE"
else
  echo "✘ /healthz ou l'API ne répond pas — retour arrière" >&2
  docker compose logs --tail=50 web api >&2 || true
  if [ -n "$PREV" ]; then
    IMAGE="$PREV" docker compose up -d web
    echo "↩ Site revenu à $PREV" >&2
  fi
  if [ -n "$PREV_API" ]; then
    API_IMAGE="$PREV_API" docker compose up -d api
    echo "↩ API revenue à $PREV_API" >&2
  else
    docker compose stop api || true   # premier déploiement de l'API : le site reste en ligne sans elle
  fi
  exit 1
fi
