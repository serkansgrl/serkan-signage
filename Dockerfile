FROM python:3.12-alpine
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
RUN addgroup -S signage && adduser -S -G signage -u 10001 signage && mkdir -p /data /nas-photos && chown -R signage:signage /data
COPY app.py /app/app.py
COPY docker-entrypoint.sh /app/docker-entrypoint.sh
COPY generate_pwa.py /app/generate_pwa.py
RUN python -m py_compile /app/app.py /app/generate_pwa.py && chmod 755 /app/docker-entrypoint.sh
USER signage
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/health',timeout=3).read()" || exit 1
ENTRYPOINT ["/app/docker-entrypoint.sh"]
