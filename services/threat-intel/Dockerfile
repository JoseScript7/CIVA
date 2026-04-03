FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends curl build-essential && rm -rf /var/lib/apt/lists/*

COPY services/threat-intel/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN python -m spacy download en_core_web_sm || true

COPY shared/python /shared/python
ENV PYTHONPATH="/shared/python:${PYTHONPATH}"
COPY services/threat-intel .

RUN addgroup --gid 1000 civa && adduser --uid 1000 --gid 1000 --disabled-password civa
USER civa

EXPOSE 8005

HEALTHCHECK --interval=10s --timeout=3s --start-period=15s --retries=3 \
    CMD curl -sf http://localhost:8005/health || exit 1

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8005", "--workers", "2"]
