# byteTuto — site statique servi par nginx
FROM nginx:stable-alpine

LABEL org.opencontainers.image.title="bytetuto-site" \
      org.opencontainers.image.description="byteTuto — page coming soon (nginx)" \
      org.opencontainers.image.source="https://github.com/byteTuto/website"

# Conf nginx
RUN rm -f /etc/nginx/conf.d/default.conf && mkdir -p /etc/nginx/bytetuto /etc/nginx/snippets /var/www/certbot
COPY nginx/nginx.conf               /etc/nginx/nginx.conf
COPY nginx/*.inc                    /etc/nginx/snippets/
COPY nginx/*.conf.template          /etc/nginx/bytetuto/
COPY --chmod=755 nginx/40-bytetuto-ssl.sh /docker-entrypoint.d/40-bytetuto-ssl.sh

# Site
COPY site/ /usr/share/nginx/html/

EXPOSE 80 443

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD wget -q -O /dev/null http://127.0.0.1/healthz || exit 1
