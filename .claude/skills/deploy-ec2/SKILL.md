---
name: deploy-ec2
description: Déployer, vérifier, diagnostiquer ou revenir en arrière sur le site byteTuto hébergé sur Amazon EC2 (Docker + nginx, GitHub Actions, GHCR, Let's Encrypt). À utiliser pour toute question de mise en ligne, de HTTPS, de serveur ou de pipeline CI/CD.
---

# Déploiement byteTuto sur EC2

## Chaîne de déploiement
1. `git push` sur `main` → `.github/workflows/deploy.yml`
2. Job **test** : `docker build`, `nginx -t`, test de fumée (`/healthz`, page d'accueil, 404, en-tête CSP).
3. Job **publish** : image multi-arch (amd64 + arm64) poussée sur `ghcr.io/<owner>/bytetuto-site:<sha7>` et `:latest`.
4. Job **deploy** : SSH vers EC2, écrit `/opt/bytetuto/.env`, copie `docker-compose.yml` + `deploy/*.sh`, lance `deploy/deploy.sh`.
5. `deploy.sh` : pull, `up -d`, attend `/healthz` (40 s max). Échec → retour automatique à l'image de `.last_image`.

Les PR ne font que le job test.

## Secrets / variables GitHub (Settings → Secrets and variables → Actions)
- Secrets : `EC2_HOST`, `EC2_USER` (ec2-user ou ubuntu), `EC2_SSH_KEY` (clé privée complète), `EC2_KNOWN_HOSTS` (recommandé : sortie de `ssh-keyscan -H <ip>`).
- Variables : `DOMAIN` (ex. bytetuto.com), `LETSENCRYPT_EMAIL`.
- Environnement GitHub `production` (peut exiger une approbation manuelle).

## Commandes utiles (sur l'EC2, dans /opt/bytetuto)
- État : `docker compose ps` · logs : `docker compose logs -f web`
- Santé : `curl -fsS http://127.0.0.1/healthz`
- Redéployer une version précise : `IMAGE=ghcr.io/<owner>/bytetuto-site:<sha7> bash deploy/deploy.sh`
- Retour arrière manuel : relancer `deploy.sh` avec l'ancien tag (visible dans l'onglet Packages de GitHub).
- HTTPS (une fois, après DNS OK) : `bash deploy/init-ssl.sh` (tester d'abord avec `STAGING=1`).
- Renouvellement : cron `/etc/cron.d/bytetuto-certbot` (2×/jour), log dans `certbot-renew.log`.

## Comment nginx choisit HTTP ou HTTPS
`nginx/40-bytetuto-ssl.sh` s'exécute au démarrage du conteneur :
certificat présent pour `$DOMAIN` → `https.conf.template`, sinon → `http.conf.template`.
Après `init-ssl.sh`, un simple `docker compose restart web` suffit.

## Diagnostic rapide
| Symptôme | Piste |
| --- | --- |
| Job deploy : `Permission denied (publickey)` | `EC2_SSH_KEY` / `EC2_USER` incorrects |
| `docker: permission denied` | l'utilisateur n'est pas dans le groupe docker → se reconnecter après `ec2-setup.sh` |
| `pull access denied` | package GHCR privé et login raté, ou rendre le package public |
| Timeout HTTP depuis l'extérieur | Security Group : ports 80/443 non ouverts |
| certbot échoue | DNS pas encore propagé, ou port 80 fermé |
| `exec format error` | architecture : vérifier que l'image est bien multi-arch |

## Règles
- Ne jamais lire ni afficher `.env`, les clés SSH ou `certbot/`.
- Demander confirmation avant `git push`, `ssh`, `scp` ou toute modification de `deploy/` et du workflow.
