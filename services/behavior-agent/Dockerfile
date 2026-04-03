FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY services/behavior-agent/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy shared library

# Copy application
COPY shared/python /shared/python
ENV PYTHONPATH="/shared/python:${PYTHONPATH}"
COPY services/behavior-agent .

# Create non-root user
RUN addgroup --gid 1000 civa && \
    adduser --uid 1000 --gid 1000 --disabled-password civa
USER civa

# Model directory
RUN mkdir -p /app/models

EXPOSE 8002

HEALTHCHECK --interval=10s --timeout=3s --start-period=10s --retries=3 \
    CMD curl -sf http://localhost:8002/health || exit 1

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8002", "--workers", "4"]
