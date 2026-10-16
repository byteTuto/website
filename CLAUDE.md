# byteTuto — site

Page « coming soon » de **bytetuto.com** (tutos tech courts : code, outils, astuces — site, YouTube, TikTok).
Le nom s'écrit toujours `byteTuto`. Signature : « Apprends la tech, un byte à la fois. »

## Stack
- Site statique : `site/` (HTML + CSS inline, JS dans `site/app.js` — la CSP interdit les scripts inline).
- Serveur : nginx (image `nginx:stable-alpine`), conf dans `nginx/`.
- Conteneur : `Dockerfile`, `docker-compose.yml` (prod), `docker-compose.dev.yml` (local, port 8080).
- CI/CD : `.github/workflows/deploy.yml` → GHCR → EC2 par SSH (`deploy/deploy.sh`).
- HTTPS : Let's Encrypt via certbot (`deploy/init-ssl.sh`), renouvellement par cron.

## Skills du projet (`.claude/skills/`)
- `bytetuto-brand` : couleurs, typos, logo, ton — à suivre pour toute modif visuelle.
- `check-site` : vérification locale avant de pousser.
- `deploy-ec2` : déploiement, HTTPS, diagnostic, retour arrière.

## Règles
- Pas de script inline, pas de dépendance externe hors Google Fonts.
- Toute animation respecte `prefers-reduced-motion`.
- Textes en français, tutoiement.
- Ne jamais lire `.env`, `certbot/`, ni les clés SSH.
- Lancer le skill `check-site` après une modif de `site/`, `nginx/` ou `Dockerfile`.
