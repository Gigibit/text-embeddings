# syntax=docker/dockerfile:1
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app


COPY requirements.txt /app/requirements.txt
RUN pip install -r /app/requirements.txt

RUN mkdir /app/.cache 
RUN chown 1001 /app/.cache
COPY . /app

USER 1001

EXPOSE 3000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "3000", "--log-level", "debug", "--access-log"]
