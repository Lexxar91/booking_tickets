FROM python:3.12-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
COPY wheels/ ./wheels/

RUN pip install --no-cache-dir --no-index --find-links=./wheels -r requirements.txt


FROM python:3.12-slim AS final

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN addgroup --system appgroup && adduser --system --ingroup appgroup appuser

COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

COPY ./src ./src

RUN chown -R appuser:appgroup /app

USER appuser


CMD ["celery", "-A", "src.worker", "worker", "--loglevel=info", "--concurrency=2"]