#!/usr/bin/env bash
# À lancer UNE FOIS sur l'instance EC2 (Amazon Linux 2023 ou Ubuntu 22.04/24.04) :
#   curl -fsSL https://raw.githubusercontent.com/<owner>/bytetuto-site/main/deploy/ec2-setup.sh | sudo bash
#   (ou scp ce fichier puis : sudo bash ec2-setup.sh)
# Installe Docker + Compose, prépare /opt/bytetuto et le cron de renouvellement SSL.
set -euo pipefail

APP_DIR=/opt/bytetuto
DEPLOY_USER="${SUDO_USER:-${DEPLOY_USER:-ec2-user}}"

[ "$(id -u)" -eq 0 ] || { echo "Lance ce script avec sudo." >&2; exit 1; }

. /etc/os-release
echo "==> Système : $PRETTY_NAME — utilisateur de déploiement : $DEPLOY_USER"

if ! command -v docker >/dev/null 2>&1; then
  case "$ID" in
    amzn)
      dnf install -y docker cronie
      systemctl enable --now crond
      ;;
    ubuntu|debian)
      apt-get update -y
      apt-get install -y ca-certificates curl cron
      curl -fsSL https://get.docker.com | sh
      ;;
    *) echo "Distribution non gérée : $ID" >&2; exit 1 ;;
  esac
fi
systemctl enable --now docker

# Plugin docker compose (absent des dépôts Amazon Linux)
if ! docker compose version >/dev/null 2>&1; then
  echo "==> Installation de docker compose"
  ARCH=$(uname -m); [ "$ARCH" = "aarch64" ] && ARCH=aarch64 || ARCH=x86_64
  mkdir -p /usr/local/lib/docker/cli-plugins
  curl -fsSL "https://github.com/docker/compose/releases/latest/download/docker-compose-linux-${ARCH}" \
    -o /usr/local/lib/docker/cli-plugins/docker-compose
  chmod +x /usr/local/lib/docker/cli-plugins/docker-compose
fi
docker compose version

# Buildx n'est pas nécessaire : l'image est construite par GitHub Actions et tirée depuis GHCR.

usermod -aG docker "$DEPLOY_USER"
mkdir -p "$APP_DIR/certbot/www" "$APP_DIR/certbot/conf"
chown -R "$DEPLOY_USER":"$DEPLOY_USER" "$APP_DIR"

# Renouvellement Let's Encrypt : 2 fois par jour (certbot ne renouvelle qu'à < 30 jours)
cat > /etc/cron.d/bytetuto-certbot <<CRON
SHELL=/bin/bash
17 3,15 * * * $DEPLOY_USER cd $APP_DIR && ( docker compose --profile certbot run --rm certbot renew --webroot -w /var/www/certbot --quiet && docker compose exec -T web nginx -s reload ) >> $APP_DIR/certbot-renew.log 2>&1
CRON
chmod 644 /etc/cron.d/bytetuto-certbot

# Petit swap si l'instance a peu de RAM (t2/t3.micro)
if [ "$(free -m | awk '/Mem:/ {print $2}')" -lt 1500 ] && ! swapon --show | grep -q swapfile; then
  echo "==> Ajout de 1 Go de swap"
  fallocate -l 1G /swapfile && chmod 600 /swapfile && mkswap /swapfile && swapon /swapfile
  echo '/swapfile none swap sw 0 0' >> /etc/fstab
fi

cat <<MSG

✔ Serveur prêt.
  Dossier de l'app : $APP_DIR
  Prochaines étapes :
    1. Security Group EC2 : ouvrir 22 (ton IP), 80 et 443 (0.0.0.0/0, ::/0).
    2. DNS : enregistrement A bytetuto.com et www.bytetuto.com -> IP élastique de l'instance.
    3. Ajouter les secrets GitHub (voir README) puis pousser sur main.
    4. Une fois le site en ligne en HTTP : bash $APP_DIR/deploy/init-ssl.sh
  (Déconnecte-toi / reconnecte-toi pour que le groupe docker s'applique à $DEPLOY_USER.)
MSG
