# ============================================================
# Stage 1: Dependências pesadas de sistema (cache longo)
# Apenas muda se o SO ou as libs de sistema mudarem
# ============================================================
FROM python:3.12-slim AS system-deps

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

# ============================================================
# Stage 2: Dependências Python pesadas (cache longo)
# Apenas muda se requirements.txt mudar — não recopia o código
# ============================================================
FROM system-deps AS python-deps

WORKDIR /app

# Copiamos APENAS o requirements.txt para maximizar o cache do Docker.
# Se o código do app mudar mas as dependências não, esse stage não é reexecutado.
COPY safety_ai_app/requirements.txt ./requirements.txt

RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# ============================================================
# Stage 3: Código do app (rebuild rápido)
# Apenas esse stage é reexecutado quando o código muda
# ============================================================
FROM python-deps AS app

WORKDIR /app

# Copia apenas o necessário para rodar o app
COPY safety_ai_app/src ./src
COPY safety_ai_app/data ./data
COPY safety_ai_app/assets ./assets

EXPOSE 8080

ENV PORT=8080 \
    PYTHONPATH=/app/src

# Healthcheck: verifica se o proxy HTTP responde em até 30s
# O Cloud Run só manda tráfego quando esse check passa
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:${PORT}/healthz || exit 1

CMD ["python", "-m", "safety_ai_app.server"]
