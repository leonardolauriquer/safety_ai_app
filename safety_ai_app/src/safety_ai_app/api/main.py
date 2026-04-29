import logging
import os
from fastapi import FastAPI, Depends, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from safety_ai_app.logging_config import setup_logging

# Configure logging via módulo centralizado
setup_logging()
logger = logging.getLogger("safety_ai_api")

app = FastAPI(
    title="Safety AI API",
    description="Backend API para o ecossistema Safety AI (SST)",
    version="1.0.0",
    # Desabilita docs em produção
    docs_url=None if os.environ.get("ENV", "production") == "production" else "/docs",
    redoc_url=None if os.environ.get("ENV", "production") == "production" else "/redoc",
)

# CORS — Origens autorizadas via variável de ambiente
_DEFAULT_ORIGINS = (
    "https://safetyai-472110.web.app,"
    "https://safety-ai-app-o5e7fadxoq-uc.a.run.app,"
    "http://localhost:8080,"
    "http://127.0.0.1:8080"
)
_ALLOWED_ORIGINS = [
    o.strip()
    for o in os.environ.get("ALLOWED_ORIGINS", _DEFAULT_ORIGINS).split(",")
    if o.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
    max_age=600,
)

# Hosts confiáveis — bloqueia Host Header Injection
_TRUSTED_HOSTS = os.environ.get(
    "TRUSTED_HOSTS",
    "safetyai-472110.web.app,safety-ai-app-o5e7fadxoq-uc.a.run.app,localhost,127.0.0.1"
).split(",")
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=[h.strip() for h in _TRUSTED_HOSTS],
)

@app.get("/healthz")
async def health_check():
    """Healthcheck endpoint."""
    return {"status": "ok", "service": "Safety AI API"}

@app.get("/")
async def root():
    return {"message": "Welcome to Safety AI API", "docs": "/docs"}

# Import and include routers
from safety_ai_app.api.routers import chat, documents, admin
app.include_router(chat.router, prefix="/api/v1/chat", tags=["IA Chat"])
app.include_router(documents.router, prefix="/api/v1/documents", tags=["Documents"])
app.include_router(admin.router, prefix="/api/v1/admin", tags=["Admin"])

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
