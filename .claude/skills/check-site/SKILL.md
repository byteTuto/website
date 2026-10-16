---
name: check-site
description: Vérifier le site byteTuto en local avant de pousser — build Docker, conf nginx, test de fumée, en-têtes de sécurité. À utiliser après toute modification de site/, nginx/ ou Dockerfile.
---

# Vérification locale

Lancer dans l'ordre, s'arrêter à la première erreur et la corriger :

```bash
docker build -t bytetuto-site:local .
docker run --rm bytetuto-site:local nginx -t
docker rm -f bt-check 2>/dev/null; docker run -d --name bt-check -p 8088:80 bytetuto-site:local
sleep 2
curl -fsS http://localhost:8088/healthz                       # -> ok
curl -fsS http://localhost:8088/ | grep -c byteTuto           # > 0
curl -s -o /dev/null -w '%{http_code}\n' http://localhost:8088/x   # -> 404
curl -sI http://localhost:8088/ | grep -iE 'content-security|x-frame|cache-control'
docker rm -f bt-check
```

Scripts shell : `bash -n deploy/*.sh nginx/*.sh` (et `shellcheck` s'il est installé).

## Points à contrôler à l'œil (dev : `docker compose -f docker-compose.dev.yml up` → http://localhost:8080)
- L'animation du fond tourne sans saccade, et s'arrête avec « réduire les animations » activé.
- Pas d'erreur dans la console (la CSP bloque tout script inline : le JS va dans `site/app.js`).
- Rendu mobile à 375 px : pas de défilement horizontal.
- Charte respectée (voir skill `bytetuto-brand`).
