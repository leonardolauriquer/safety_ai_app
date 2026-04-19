# SafetyAI App — Documentação Técnica

## Overview

SafetyAI App is an intelligent assistant designed for Occupational Safety and Health (OSH) professionals in Brazil. It leverages generative AI with RAG (Retrieval-Augmented Generation) for querying Brazilian Regulatory Standards (NRs), alongside tools for dimensioning safety teams, generating essential documents, and providing educational content in workplace safety. The project aims to streamline compliance and enhance safety management through AI-powered solutions.

## User Preferences

Communication style: Simples, linguagem do dia-a-dia.

## System Architecture

### Frontend Architecture

The application features a "Cyber-Neon Glass" design system across all 24 pages, characterized by glassmorphism effects, a neon color palette (purple, cyan, green on a dark background), and "Orbitron" and "Inter" typography. Navigation and routing are managed via `st.session_state` in `web_app.py`, implementing a 3-phase authentication flow (Google OAuth, Drive synchronization, main app access).

Key pages include:
- **AI Chat:** RAG interface with token streaming.
- **Knowledge Base:** Document upload, indexing, and management.
- **Quick Queries:** Hub for CBO, CID-10/ICD-11, CNAE, CA/EPI, and NR Fines.
- **Sizing Tools:** CIPA, SESMT, and Emergency Brigade dimensioning.
- **Document Generators:** APR (Preliminary Risk Analysis) and ATA (CIPA Meeting Minutes).
- **Educational Games:** Quiz and Crosswords on OSH topics.
- **Jobs Board:** OSH vacancies.
- **News Feed:** RSS-based OSH news.
- **Admin Panel:** Comprehensive administration and RAG pipeline evaluation.

### Server Entry Point

The application uses a thin `aiohttp` reverse proxy (`server.py`) that listens on port 5000 and forwards all traffic to Streamlit on port 5001. The proxy adds two additional endpoints:
- `GET /sw.js` — serves the service worker with `Service-Worker-Allowed: /` HTTP header so the SW can claim full-origin scope (`/`) for offline navigation support.
- `GET /_safetyai_offline` — serves the inline offline fallback HTML page.

This architecture is required because Streamlit's static file server cannot set custom HTTP headers or serve files at the root path `/`.

### Backend Architecture

The core is a RAG pipeline (`nr_rag_qa.py`) built with LangChain, utilizing a persistent ChromaDB for NR indexing and Sentence Transformers for embeddings. OpenRouter serves as the LLM provider, with configurable models and dynamic temperature. The retriever combines BM25 and semantic search (ensemble 30/70). Features include historical chat compression, Chain-of-Thought reasoning, and guardrails for domain adherence.

Embedding model: `intfloat/multilingual-e5-base` (278M, requires "query:"/"passage:" prefixes, normalize_embeddings=True). Reranker: `cross-encoder/mmarco-mMiniLMv2-L12-H384-v1` (multilingual mMARCO, good for Portuguese).

Data processors handle various data sources for quick queries and sizing tools, such as CBO, CID-10 (local and WHO API), CNAE (IBGE API), CA/EPI (Ministry of Labor FTP), and NR-specific tables for CIPA, SESMT, and fines. Document generators use `python-docx` and `docxtpl` for creating DOCX/PDF outputs.

Document processing (`document_processors/`) supports various formats (PDF, DOCX, Excel, images with Tesseract OCR, PPTX) with automatic type detection. Google Drive integration (`google_drive_integrator.py`, `drive_sync.py`) manages document upload, download, sharing, and scheduled bidirectional synchronization.

Security features include rate limiting, security logging, input validation, and reCAPTCHA.

### Observability and RAG Evaluation

The system incorporates a "Golden Set" of Q&A pairs for NRs, a RAG Logger for detailed query tracing, and an evaluation script (`scripts/evaluate_rag.py`) to measure faithfulness, answer relevance, context recall, and precision. An Admin Panel provides historical metrics and analysis.

### Data Storage

Key data is stored locally:
- `data/chroma_db/`: Persistent ChromaDB vector store.
- `data/ai_config.json`: RAG pipeline configuration.
- `data/feature_flags.json`: Application feature flags.
- `data/plans/plans.json`: Subscription plans.
- `data/eval/`: RAG evaluation golden set and results.
- `data/rag_logs/`: JSONL logs of RAG pipeline activities.

PostgreSQL (Replit built-in database via `DATABASE_URL`) is used for:
- `google_oauth_tokens`: Persists the Google Drive user OAuth token across container restarts and deployments. The `google_auth.py` module reads/writes tokens here first, falling back to the local `token_user.json` file only if the database is unavailable. An existing `token_user.json` is automatically migrated to the database on first load.
- `data/games/`: Game-specific data.
- `logs/app.log` and `logs/security.log`: Application and security logs.

### Authentication and Authorization

Google OAuth 2.0 handles user login and service account access for Google Drive. CSRF tokens ensure security during the OAuth flow. Admin access is controlled via `ADMIN_EMAILS` environment variables.

### Production Deployment

The application is deployed on Google Cloud Platform, using Artifact Registry for Docker images, Cloud Run for serving the application, Secret Manager for handling sensitive keys, and Firebase Hosting for domain redirection. The Docker image includes Python 3.12, Tesseract OCR, and Poppler.

## External Dependencies

### APIs

- **OpenRouter:** LLM provider for the RAG chat.
- **Google Drive API:** Document library integration.
- **WHO ICD-11 API:** International CID consultations.
- **Adzuna Jobs API:** OSH job board.
- **IBGE API:** CNAE and municipality data (public).
- **reCAPTCHA:** Anti-bot protection.
- **FTP mtps.gov.br:** CA/EPI data from the Ministry of Labor (public).

### Python Libraries

- **AI/ML:** `langchain`, `langchain-community`, `langchain-chroma`, `langchain-openai`, `sentence-transformers`, `chromadb`.
- **Document Processing:** `pypdf`, `PyPDF2`, `python-docx`, `docxtpl`, `pymupdf`, `pytesseract`, `pdf2image`, `openpyxl`.
- **Web Framework:** `streamlit`, `streamlit-autorefresh`, `streamlit-drawable-canvas`.
- **Google Services:** `google-auth`, `google-auth-oauthlib`, `google-api-python-client`.
- **Data & Utilities:** `pandas`, `requests`, `httpx`, `feedparser`, `beautifulsoup4`.