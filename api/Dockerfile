# byteTuto — service d'inscription (Python, bibliothèque standard + SQLite, aucune dépendance)
FROM python:3.13-alpine

LABEL org.opencontainers.image.title="bytetuto-api" \
      org.opencontainers.image.description="byteTuto — inscriptions « Préviens-moi du lancement »" \
      org.opencontainers.image.source="https://github.com/byteTuto/website"

RUN adduser -D -u 10001 app && mkdir /data && chown app:app /data
WORKDIR /app
COPY --chmod=644 app.py /app/app.py
USER app
ENV PYTHONUNBUFFERED=1 DB_PATH=/data/subscribers.db COUNTER_MIN=30 PORT=8000
VOLUME /data
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=2).status == 200 else 1)"

CMD ["python", "/app/app.py"]
