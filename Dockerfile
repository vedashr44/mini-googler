# API container (FastAPI + Uvicorn)
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY mini_google_search/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY mini_google_search /app/mini_google_search

# Expose default API port
EXPOSE 8080

# Cloud Run expects listening on $PORT
ENV PORT=8080

CMD ["uvicorn", "mini_google_search.backend.api:app", "--host", "0.0.0.0", "--port", "8080"]

