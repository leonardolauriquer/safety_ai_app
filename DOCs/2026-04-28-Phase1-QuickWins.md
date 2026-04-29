# 2026-04-28 — Fase 1: Quick Wins Arquiteturais

## Antes
- Dockerfile single-stage: rebuild completo (20+ min) a cada mudança de código
- Quota de chat em `session_state` (burlável por reload ou nova aba)
- `OAUTH_REDIRECT_URI` como variável de texto conflitando com Secret existente → erro 400 e FAILURE no deploy
- Sem endpoint de healthcheck → Cloud Run podia rotear tráfego para app não-inicializado
- `cloudbuild.yaml` sem cache de camadas Docker

## Depois
- **Dockerfile multi-stage** (3 stages): rebuild de código em ~3 min, `pip install` só executa quando `requirements.txt` muda
- **Quota de chat persistida no Firestore** via `auth/quota_manager.py` com transação atômica; fallback automático para `session_state`
- **`OAUTH_REDIRECT_URI` migrado para Secret Manager** via `--set-secrets`, eliminando o conflito de tipo que travava todos os deploys
- **`/healthz` endpoint** no `server.py`: Cloud Run só serve tráfego quando Streamlit interno responde
- **`HEALTHCHECK`** no Dockerfile para verificação local
- **`--min-instances=1`** no Cloud Run: elimina cold start para o primeiro usuário do dia
- **`--cache-from`** no build: reutiliza camadas Docker do build anterior

## Arquivos Alterados
| Arquivo | Mudança |
|---------|---------|
| `Dockerfile` | Multi-stage build + HEALTHCHECK |
| `server.py` | Endpoint `/healthz` adicionado |
| `cloudbuild.yaml` | OAUTH_REDIRECT_URI → set-secrets, cache-from, min-instances=1 |
| `auth/quota_manager.py` | [NOVO] Quota persistida no Firestore |
| `feature_access.py` | Integração com quota_manager (fallback para session_state) |

## Lógica Usada

### Dockerfile Multi-Stage
Docker só reexecuta os stages cujas dependências mudaram. Separando as libs pesadas (`torch`, `chromadb`) em um stage próprio, o rebuild de uma mudança de código vai diretamente para o Stage 3, pulando o `pip install`.

### Quota no Firestore
Usa transação atômica (`@firestore.transactional`) para garantir que dois requests simultâneos não burlem o limite. Cache na sessão (TTL 60s) evita uma leitura ao Firestore a cada mensagem.

### Healthcheck
O aiohttp proxy verifica se o Streamlit na porta 5001 responde antes de devolver 200. Isso garante que o Cloud Run só redireciona usuários quando o app está 100% inicializado.
