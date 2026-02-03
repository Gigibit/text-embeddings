# syntax=docker/dockerfile:1
FROM python:3.11-slim AS base
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    HF_HUB_DISABLE_TELEMETRY=1

WORKDIR /app

# --- Dipendenze ---
COPY requirements.txt /app/requirements.txt
RUN apt-get update \
 && apt-get install -y --no-install-recommends ca-certificates curl git \
 && pip install -r /app/requirements.txt \
 && rm -rf /var/lib/apt/lists/*

# --- Scarico il modello a build-time ---
# Variabili parametrizzabili dalla pipeline
ARG MODEL_ID="sentence-transformers/all-MiniLM-L6-v2"
ARG MODEL_DIR="/models"
# Se usi huggingface_hub:
RUN python - <<'PY'
import os
from huggingface_hub import snapshot_download
model_id = os.environ.get("MODEL_ID", "sentence-transformers/all-MiniLM-L6-v2")
local_dir = os.environ.get("MODEL_DIR", "/models")
snapshot_download(repo_id=model_id, local_dir=local_dir, local_dir_use_symlinks=False)
PY

# In alternativa (air-gapped) scarica da Artifactory/risorsa interna:
# RUN mkdir -p /models/my-emb \
#  && curl -fSL https://artifactory.<dominio>/models/my-emb.tar.gz | tar -xz -C /models/my-emb

# --- App ---
COPY . /app

# (opzionale) utente non root
RUN useradd -u 1001 -m appuser && chown -R 1001:1001 /app /models
USER 1001

EXPOSE 3000
ENV MODEL_PATH=/models \
    EMBEDDING_BACKEND=local

# Avvio: il tuo summon + uvicorn (immutato)
CMD ["sh","-c","exec summon -f /deployments/config/secrets.yml uvicorn main:app --host 0.0.0.0 --port 3000 --log-level debug --access-log"]
