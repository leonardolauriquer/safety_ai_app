# Security Hardening & Melhoria de Qualidade — 2026-04-29

## Contexto
Aplicadas melhorias estruturais em segurança, resiliência, SEO e qualidade de código no **SafetyAI App** (Streamlit + FastAPI + Firebase + ChromaDB + Cloud Run).

---

## Alterações Aplicadas

### 1. CORS Restrito — `api/main.py`
**Antes**: `allow_origins=["*"]` — qualquer origem podia fazer requisições com credenciais.
**Depois**: Whitelist via `ALLOWED_ORIGINS` (env var). Default: Firebase Hosting + Cloud Run URL.

Adicionado também:
- `TrustedHostMiddleware` para prevenir Host Header Injection
- Docs da API (Swagger/ReDoc) desabilitadas em produção
- Logging configurado via `setup_logging()` centralizado

---

### 2. Admin sem Hardcode — `api/middleware/auth.py`
**Antes**: Fallback via e-mail hardcoded `"leonardo.lauriquer@gmail.com"` + `import os` ausente (erro latente).
**Depois**: Verificação exclusivamente via Firebase Custom Claims (`is_admin: true`). Para promover um admin:
```python
from firebase_admin import auth
auth.set_custom_user_claims(uid, {"is_admin": True})
```
Logging de tentativas de acesso negado adicionado.

---

### 3. Headers HTTP de Segurança — `server.py`
**Antes**: Nenhum header de segurança nas respostas HTTP.
**Depois**: Headers adicionados em todas as respostas via middleware aiohttp:
- `Content-Security-Policy` (CSP) — whitelistando Streamlit, Google, Firebase
- `Strict-Transport-Security` (HSTS) — 2 anos com preload
- `X-Frame-Options: SAMEORIGIN` — anti-clickjacking
- `X-Content-Type-Options: nosniff` — anti-MIME sniffing
- `Referrer-Policy: strict-origin-when-cross-origin`
- `Permissions-Policy` — câmera, microfone, localização desabilitados

---

### 4. Upload Seguro — `api/routers/admin.py`
**Antes**: Extensão extraída com `.split('.')[-1]` sem validação, sem limite de tamanho.
**Depois**:
- Whitelist de MIME types (`application/pdf`, `docx`, `txt`, `csv`, `xlsx`)
- Whitelist de extensões (`pdf`, `docx`, `doc`, `txt`, `csv`, `xls`, `xlsx`)
- Limite de **50MB** com HTTP 413
- Sanitização do nome do arquivo (remove path traversal, caracteres perigosos)
- Logging de auditoria com uid, tamanho e tipo
- Upload usa `io.BytesIO(content)` — conteúdo já lido evita double-read

---

### 5. Bug Crítico RAG corrigido — `rag/qa_chain.py`
**Antes**: `process_retrieved_docs` não tinha `return` explícito → retornava `None` silenciosamente, quebrando o chain.
**Depois**: Return explícito com `{"context": ..., "suggested_downloads": [...]}`.

---

### 6. Firestore com Retry Automático — `database/firestore_service.py`
**Antes**: Exceções genéricas sem retry. Uma falha transitória do Firestore causava erro silencioso.
**Depois**: `@retry` com exponential backoff (tenacity):
- 3 tentativas
- Espera: 1s → 10s (exponencial)
- Só retenta em `ServiceUnavailable` e `ResourceExhausted`
- Log de cada tentativa via `before_sleep_log`

---

### 7. SEO — Meta Tags OG + Twitter + PWA Screenshots — `pwa_support.py`
**Antes**: Sem meta tags para compartilhamento social.
**Depois**:
- `og:title`, `og:description`, `og:url`, `og:locale`, `og:site_name`
- `twitter:card`, `twitter:title`, `twitter:description`
- `meta name="description"` e `meta name="keywords"`
- `screenshots` no PWA manifest (necessário para Chrome mostrar preview antes de instalar)

---

### 8. Fontes Non-Blocking — `web_app.py`
**Antes**: Fontes Google carregadas de forma síncrona (render-blocking).
**Depois**: Técnica `media=print → onload` + `preconnect` para carregamento assíncrono das fontes Inter e Material Symbols.

---

### 9. robots.txt — `public/robots.txt`
**Criado**: Regras de indexação para SEO:
- Permite rastreamento da home
- Bloqueia `/admin`, `/settings`, `/sync`, `/api/`
- Referência ao sitemap

---

### 10. Secrets Drive Removidos — `deploy.sh`
**Removidos**: `GOOGLE_DRIVE_CENTRAL_LIBRARY_FOLDER_ID` e `GOOGLE_DRIVE_DONATION_FOLDER_ID` do script de deploy e das env vars do Cloud Run (base curada centralizada tornou esses secrets obsoletos).

---

## Impacto de Segurança

| Antes | Depois |
|---|---|
| CORS `*` com credenciais | Whitelist restrita |
| Admin por e-mail hardcoded | Apenas Firebase Custom Claims |
| Sem CSP | CSP + HSTS + X-Frame-Options |
| Upload sem validação | MIME whitelist + 50MB limit |
| Firestore sem retry | Retry com backoff automático |

## Arquivos Modificados

- `api/main.py` — CORS, TrustedHost, logging
- `api/middleware/auth.py` — import os, sem hardcode
- `api/routers/admin.py` — MIME validation, size limit, sanitize
- `rag/qa_chain.py` — return explícito
- `database/firestore_service.py` — retry decorators
- `server.py` — security headers
- `web_interface/pwa_support.py` — OG tags, screenshots
- `web_app.py` — fontes non-blocking
- `public/robots.txt` — [NOVO]
- `deploy.sh` — secrets Drive removidos
