# byteTuto — site

Page « coming soon » de **bytetuto.com** (tutos tech courts : code, outils, astuces — site, YouTube, TikTok).
Le nom s'écrit toujours `byteTuto`. Signature : « Apprends la tech, un byte à la fois. »

## Stack
- Site statique : `site/` (HTML + CSS inline, JS dans `site/app.js` — la CSP interdit les scripts inline).
- Serveur : nginx (image `nginx:stable-alpine`), conf dans `nginx/` ; `/api/` relayé vers le service `api/`.
- Inscriptions : `api/app.py` (Python stdlib + SQLite, volume `api-data`), image `ghcr.io/bytetuto/website-api`. Test : `api/test_api.py`.
- Pages légales : `site/mentions-legales/`, `site/confidentialite/` — à mettre à jour si on collecte d'autres données ou si le site devient professionnel (SIRET).
- Teaser : `site/media/teaser.{webm,mp4}` (rendu depuis les scripts vidéo du projet, 1280×720, 9 s).
- Conteneur : `Dockerfile`, `docker-compose.yml` (prod), `docker-compose.dev.yml` (local, port 8080).
- CI/CD : `.github/workflows/deploy.yml` → GHCR → EC2 par SSH (`deploy/deploy.sh`).
- HTTPS : Let's Encrypt via certbot (`deploy/init-ssl.sh`), renouvellement par cron.

## Skills du projet (`.claude/skills/`)
- `bytetuto-brand` : couleurs, typos, logo, ton — à suivre pour toute modif visuelle.
- `check-site` : vérification locale avant de pousser.
- `deploy-ec2` : déploiement, HTTPS, diagnostic, retour arrière.
- `site-responsive` : mobile d'abord, 320 → 1440 px, sans défilement horizontal.
- `site-seo` : head, JSON-LD, titres, URL, sitemap, Core Web Vitals.
- `site-agent-friendly` : jumeau `.md` de chaque page, `/llms.txt`, `Accept: text/markdown`.

## Règles
- Pas de script inline, pas de dépendance externe hors Google Fonts.
- Toute animation respecte `prefers-reduced-motion`.
- Textes en français, tutoiement.
- Ne jamais lire `.env`, `certbot/`, ni les clés SSH.
- Lancer le skill `check-site` après une modif de `site/`, `nginx/` ou `Dockerfile`.

## Toute page du site doit être (contrôlé en CI, bloquant)
1. **Responsive** — skill `site-responsive`, contrôle `python3 scripts/check_responsive.py`.
2. **SEO excellent** — skill `site-seo`, contrôle `python3 scripts/check_seo_agents.py`.
3. **Agent-friendly** — skill `site-agent-friendly` : créer/modifier la page `X/index.html` implique, dans le même commit,
   `X/index.md` (même contenu en Markdown), une ligne dans `site/llms.txt` et une entrée dans `site/sitemap.xml`.
