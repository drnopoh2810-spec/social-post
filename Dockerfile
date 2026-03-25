FROM python:3.11-slim

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    libjpeg-dev libpng-dev libwebp-dev curl \
    && rm -rf /var/lib/apt/lists/*

# Non-root user
RUN useradd -m -u 1000 appuser

WORKDIR /app

# Dependencies (cached layer)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# App code
COPY --chown=appuser:appuser . .

# Data directory for SQLite
RUN mkdir -p /app/data && chown appuser:appuser /app/data

USER appuser

ENV PORT=7860
ENV FLASK_ENV=production
ENV DATABASE_URL=sqlite:////app/data/social_post.db

EXPOSE 7860

HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:${PORT}/health || exit 1

CMD ["gunicorn", "wsgi:application", "-c", "gunicorn.conf.py"]
