FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt requirements-services.txt ./
RUN pip install --no-cache-dir -r requirements-services.txt

COPY whisperforge_core ./whisperforge_core
COPY shared ./shared
COPY services/storage/service.py ./service.py

ENV PYTHONPATH=/app \
    PYTHONUNBUFFERED=1

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=5 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "service:app", "--host", "0.0.0.0", "--port", "8000"]
