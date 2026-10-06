FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY . .
RUN python -m pip install --no-cache-dir . \
    && mkdir -p /app/data \
    && addgroup --system frontiere \
    && adduser --system --ingroup frontiere frontiere \
    && chown -R frontiere:frontiere /app/data

USER frontiere

ENV FRONTIERE_DATABASE_URL=sqlite:////app/data/frontiere.db

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=2)"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
