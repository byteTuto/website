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
