# syntax=docker/dockerfile:1
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app


COPY requirements.txt /app/requirements.txt
RUN pip install -r /app/requirements.txt


# (both the HF-safe files and any tokenizer/config weights)
RUN python - <<'PY'
from sentence_transformers import SentenceTransformer
# Will populate HF cache under /opt/hf
SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
PY

# Make the cache readable at runtime by non-root if you drop privileges later
RUN chmod -R a+rX /opt/hf

COPY . /app

USER 1001

EXPOSE 3000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "3000", "--log-level", "debug", "--access-log"]
