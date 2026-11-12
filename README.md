# byteTuto — site (coming soon)

Page « Coming soon / site en construction » de **bytetuto.com**, avec fond animé (trame de points, pistes de circuit et impulsions néon), servie par **nginx dans Docker**, déployée automatiquement sur **Amazon EC2** à chaque push sur `main`.

```
.
├── site/                    # le site (index.html, app.js, 404.html, favicon.svg…)
├── nginx/                   # conf nginx : HTTP seul ou HTTPS choisi au démarrage
├── Dockerfile
├── docker-compose.yml       # production (EC2) : web + certbot
├── docker-compose.dev.yml   # local : http://localhost:8080, site/ monté en direct
├── deploy/
│   ├── ec2-setup.sh         # préparation du serveur (une fois)
│   ├── deploy.sh            # pull + redémarrage + healthcheck + retour arrière auto
│   └── init-ssl.sh          # certificat Let's Encrypt (une fois)
├── .github/workflows/deploy.yml
├── .claude/                 # config Claude Code : settings + skills du projet
└── CLAUDE.md
```

## 1. En local

```bash
docker compose -f docker-compose.dev.yml up --build
# → http://localhost:8080  (modifie site/index.html et rafraîchis)
```

## 2. Préparer l'EC2 (une fois)

1. **Lancer une instance** : Amazon Linux 2023 ou Ubuntu 24.04, `t3.micro` / `t4g.micro` suffit.
2. **Security Group** : 22 (ton IP uniquement), 80 et 443 (tout le monde).
3. **IP élastique** associée à l'instance.
4. **DNS** chez ton registrar : `A bytetuto.com` et `A www.bytetuto.com` → l'IP élastique.
5. Sur l'instance :
   ```bash
   scp -i ma-cle.pem deploy/ec2-setup.sh ec2-user@<IP>:~
   ssh -i ma-cle.pem ec2-user@<IP> "sudo bash ec2-setup.sh"
   ```
   (installe Docker + Compose, crée `/opt/bytetuto`, le cron de renouvellement SSL, un peu de swap.)

## 3. Configurer GitHub

Pousse ce dossier dans un dépôt GitHub, puis **Settings → Secrets and variables → Actions** :

| Type | Nom | Valeur |
| --- | --- | --- |
| Secret | `EC2_HOST` | IP élastique (ou bytetuto.com) |
| Secret | `EC2_USER` | `ec2-user` (Amazon Linux) ou `ubuntu` |
| Secret | `EC2_SSH_KEY` | contenu complet de la clé privée `.pem` |
| Secret | `EC2_KNOWN_HOSTS` | recommandé : sortie de `ssh-keyscan -H <IP>` |
| Variable | `DOMAIN` | `bytetuto.com` |
| Variable | `LETSENCRYPT_EMAIL` | `contact@bytetuto.com` |

Optionnel : **Settings → Environments → production** → « Required reviewers » pour valider chaque mise en prod.

## 4. Déployer

```bash
git push origin main
```

Le workflow : **test** (build, `nginx -t`, test de fumée) → **publish** (image `ghcr.io/bytetuto/website`, amd64 + arm64) → **deploy** (SSH, `deploy.sh`, vérification `/healthz`). Si le nouveau conteneur ne répond pas, `deploy.sh` revient tout seul à la version précédente.

Les pull requests ne lancent que les tests.

## 5. Activer le HTTPS (une fois, après le premier déploiement)

```bash
ssh ec2-user@<IP>
cd /opt/bytetuto
STAGING=1 bash deploy/init-ssl.sh   # répétition, n'installe rien
bash deploy/init-ssl.sh             # vrai certificat
```

nginx détecte le certificat au redémarrage et bascule seul en HTTPS (HTTP → HTTPS, www → domaine nu, HSTS). Renouvellement automatique par cron.

## 6. Inscriptions « Préviens-moi du lancement »

Le formulaire de l'accueil (et la commande `inscris` du terminal) envoie l'email au petit service `api/`
(Python, bibliothèque standard + SQLite, conteneur `bytetuto-api`). nginx le relaie sur `/api/`.

| Route | Rôle |
| --- | --- |
| `POST /api/subscribe` | inscription (JSON, ou formulaire classique sans JavaScript → `/#merci`) |
| `GET /api/count` | nombre d'inscrits ; `show` passe à `true` à partir de `COUNTER_MIN` (30 par défaut) |
| `GET /api/health` | santé (healthcheck Docker) |

Protections : pot de miel anti-robot, 5 inscriptions / 10 min par IP dans l'API et 10 / min dans nginx, emails normalisés,
réponse identique pour un email déjà inscrit. L'adresse IP n'est pas stockée avec l'email.

Sur l'EC2, depuis `/opt/bytetuto` :

```bash
docker compose exec api python app.py count                    # nombre d'inscrits
docker compose exec -T api python app.py export > inscrits.csv    # pour l'email de lancement / l'outil de newsletter
docker compose exec api python app.py delete toi@exemple.fr    # demande de suppression (RGPD)
# sauvegarde de la base (volume Docker api-data)
docker run --rm -v bytetuto_api-data:/data -v "$PWD":/out alpine cp /data/subscribers.db /out/inscrits-$(date +%F).db
```

### Page admin : https://bytetuto.com/admin/

Liste des inscrits, recherche, téléchargement du CSV (s'ouvre dans Excel) et suppression avec confirmation.

- **Ouverte uniquement en HTTPS** : en HTTP seul, `/admin/` répond 404 (le mot de passe ne circule jamais en clair).
- **Choisir ou changer le mot de passe** (sur l'EC2, dans `/opt/bytetuto`) : `bash deploy/set-admin-password.sh`.
  Le script demande le mot de passe deux fois et n'écrit dans `.env` que son **empreinte scrypt** (`ADMIN_PASSWORD_HASH`)
  et la clé qui signe les sessions (`ADMIN_SECRET`). Le mot de passe lui-même n'est stocké nulle part.
- `bash deploy/set-admin-password.sh --deconnecter-tout` : change aussi la clé, ce qui ferme toutes les sessions ouvertes.
- Session de 4 h (cookie HttpOnly, Secure, SameSite=Strict), jeton anti-CSRF sur chaque bouton,
  5 mauvais mots de passe par IP → blocage 15 min. Page non indexée.
- Les déploiements ne réécrivent plus tout le `.env` : `ADMIN_*` et `COUNTER_MIN` sont conservés.

Le seuil d'affichage du compteur se change avec `COUNTER_MIN=…` dans `.env`, puis `docker compose up -d api`.
En local, `docker compose -f docker-compose.dev.yml up --build` lance aussi l'API (compteur visible dès 3 inscrits).
Test de bout en bout : `python3 api/test_api.py http://localhost:8080` (API lancée avec `RATE_MAX=8`, base vide).

## 7. Ajouter un autre site sur l'EC2 (dashboard.bytetuto.com, synko.bytetuto.com)

Chaque site supplémentaire a **son propre dépôt** et son propre conteneur. Le nginx de ce dépôt reste le seul
à écouter sur 80/443 : il reconnaît le sous-domaine et relaie vers le conteneur, sur le réseau Docker partagé
`bytetuto-sites`. L'API des inscrits n'est pas sur ce réseau, donc les autres sites ne peuvent pas la joindre.

```
visiteur ──▶ nginx (bytetuto-web, 80/443) ──┬──▶ site byteTuto (même conteneur)
                                            ├──▶ bytetuto-dashboard:8080 (dépôt dashboard)
                                            └──▶ bytetuto-synko:8080     (dépôt synko)
```

| Sous-domaine | Dépôt | Conteneur | Dossier sur l'EC2 |
| --- | --- | --- | --- |
| dashboard.bytetuto.com | [byteTuto/dashboard](https://github.com/byteTuto/dashboard) | `bytetuto-dashboard:8080` | `/opt/dashboard` |
| synko.bytetuto.com | [byteTuto/synko](https://github.com/byteTuto/synko) | `bytetuto-synko:8080` | `/opt/synko` |

**Déclarer le site** : variable `EXTRA_SITES` du service `web` dans `docker-compose.yml`
(déjà réglée sur les deux sites ci-dessus). Plusieurs sites : entrées `hote=http://conteneur:port` séparées par des espaces.
Pour tout désactiver sans modifier le dépôt : `EXTRA_SITES=` dans le `.env` de l'EC2, puis `docker compose up -d web`.
⚠ Si `EXTRA_SITES` est défini dans le `.env` de l'EC2, c'est lui qui compte : y ajouter le nouveau site.

**Mise en ligne d'un nouveau sous-domaine, une fois (ex. synko) :**
1. DNS : `A synko.bytetuto.com` → la même IP élastique.
2. Déployer ce dépôt (push sur `main`) : crée le réseau `bytetuto-sites` et le bloc nginx du sous-domaine (en HTTP).
3. Sur l'EC2, dans `/opt/bytetuto` : `STAGING=1 bash deploy/init-ssl.sh synko.bytetuto.com` (répétition), puis
   `bash deploy/init-ssl.sh synko.bytetuto.com`. C'est un **certificat séparé** : ceux des autres sites ne sont pas touchés.
   Le cron existant renouvelle tous les certificats.
4. Déployer le site depuis son dépôt (dans son propre dossier, ex. `/opt/synko`), avec un `docker-compose.yml` de ce type :

```yaml
services:
  synko:
    image: ghcr.io/bytetuto/synko:latest
    container_name: bytetuto-synko       # nom utilisé dans EXTRA_SITES
    restart: unless-stopped
    expose: ["8080"]                     # pas de « ports: » : seul nginx le joint
    networks: [sites]

networks:
  sites:
    name: bytetuto-sites
    external: true
```

Tant que le conteneur d'un site n'est pas lancé, son sous-domaine répond 503 (« site momentanément indisponible »),
et bytetuto.com comme les autres sites restent en ligne. nginx transmet `X-Forwarded-Proto`, `X-Real-IP`, les WebSocket
et les flux temps réel (SSE : l'application envoie `X-Accel-Buffering: no` et un battement toutes les 25 s, sous le
`proxy_read_timeout` de 60 s). Les en-têtes CSP et anti-iframe sont laissés à chaque application. Taille maximale d'un
envoi : 10 Mo (`nginx/extra-site.inc`).

## À personnaliser

- Liens YouTube / TikTok dans `site/index.html` (`@bytetuto` par défaut).
- `og-image.png` (aperçu de partage 1200×630) et `apple-touch-icon.png` sont fournis ; remplace-les si tu changes le visuel.
- `org.opencontainers.image.source` dans le `Dockerfile` : l'URL de ton dépôt (relie l'image GHCR au dépôt).

## Claude Code

Le dossier `.claude/` contient :
- `settings.json` : permissions partagées (docker/curl/git autorisés, push/ssh/scp sur confirmation, `.env` et clés interdits en lecture).
- `skills/bytetuto-brand` : la charte (couleurs, typos, logo, ton).
- `skills/check-site` : vérification locale avant push.
- `skills/deploy-ec2` : déploiement, HTTPS, diagnostic, retour arrière.

Tes réglages perso vont dans `.claude/settings.local.json` (ignoré par git).
