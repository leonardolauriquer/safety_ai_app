FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-por \
    poppler-utils \
    libgl1 \
    libglib2.0-0 \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY safety_ai_app/requirements.txt ./requirements.txt

RUN pip install --no-cache-dir -r requirements.txt

COPY safety_ai_app/src ./src
COPY safety_ai_app/data ./data
COPY safety_ai_app/assets ./assets

EXPOSE 8080

ENV PORT=8080 \
    PYTHONPATH=/app/src

CMD streamlit run src/safety_ai_app/web_app.py \
    --server.port=$PORT \
    --server.address=0.0.0.0 \
    --server.headless=true \
    --server.enableCORS=false \
    --server.enableXsrfProtection=false
