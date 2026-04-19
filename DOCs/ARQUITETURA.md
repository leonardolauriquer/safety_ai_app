# Arquitetura Tecnica do SafetyAI

## Estrutura de Diretorios

```
safety_ai_app/
├── src/
│   └── safety_ai_app/
│       ├── web_app.py                    # Ponto de entrada principal (Streamlit)
│       ├── nr_rag_qa.py                  # Sistema RAG com LLM
│       ├── theme_config.py               # Configuracao do tema Cyber-Neon
│       ├── google_drive_integrator.py    # Integracao com Google Drive
│       ├── text_extractors.py            # Extracao de texto de documentos
│       │
│       ├── # Data Processors
│       ├── cbo_data_processor.py         # Processador CBO (Ocupacoes)
│       ├── cid_data_processor.py         # Processador CID-10/11 (Doencas)
│       ├── cnae_data_processor.py        # Processador CNAE (Atividades)
│       ├── cnae_risk_data_processor.py   # Grau de Risco por CNAE
│       ├── ca_data_processor.py          # Processador CA/EPI
│       ├── cipa_data_processor.py        # Dimensionamento CIPA + Cronograma
│       ├── sesmt_data_processor.py       # Dimensionamento SESMT
│       ├── quiz_data_processor.py        # Dados para jogos educativos
│       ├── job_api_integrator.py         # Integracao API Adzuna
│       │
│       ├── document_generators/
│       │   ├── apr_document_generator.py # Gerador APR
│       │   ├── ata_document_generator.py # Gerador ATA
│       │   └── templates/
│       │       ├── apr_template.docx     # Template APR
│       │       └── ata_template.docx     # Template ATA
│       │
│       └── web_interface/
│           ├── pages/                    # Todas as paginas da aplicacao
│           │   ├── home_page.py
│           │   ├── chat_page.py
│           │   ├── sync_page.py
│           │   ├── cbo_consult_page.py
│           │   ├── cid_consult_page.py
│           │   ├── cnae_consult_page.py
│           │   ├── ca_consult_page.py
│           │   ├── cipa_sizing_page.py
│           │   ├── sesmt_sizing_page.py
│           │   ├── emergency_brigade_sizing_page.py
│           │   ├── apr_generator_page.py
│           │   ├── ata_generator_page.py
│           │   ├── knowledge_base_page.py
│           │   ├── library_page.py
│           │   ├── games_page.py
│           │   ├── news_feed_page.py
│           │   ├── jobs_board_page.py
│           │   ├── fines_consult_page.py
│           │   ├── quick_queries_page.py
│           │   ├── sizing_page.py
│           │   └── settings_page.py
│           │
│           └── components/
│               └── games/
│                   ├── quiz_game.py      # Jogo de Quiz
│                   └── crossword_game.py # Palavras Cruzadas
│
└── data/
    ├── chroma_db/                        # Vector store ChromaDB
    ├── nrs/                              # Documentos NRs processados
    ├── brazilian_cities.json             # Cidades brasileiras
    └── ca_data.parquet                   # Cache de dados CA
```

## Diagrama de Componentes

```
┌─────────────────────────────────────────────────────────────────────┐
│                         FRONTEND (Streamlit)                         │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐ │
│  │  Login Page │  │  Sync Page  │  │  Main App   │  │  Sidebar    │ │
│  │  (OAuth)    │  │  (Drive)    │  │  (Router)   │  │  Navigation │ │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘ │
└─────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         BACKEND SERVICES                             │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐  │
│  │  NRQuestionAns   │  │  Data Processors │  │  Doc Generators  │  │
│  │  (RAG + LLM)     │  │  (CBO,CID,CNAE)  │  │  (APR, ATA)      │  │
│  └──────────────────┘  └──────────────────┘  └──────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         DATA LAYER                                   │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐  │
│  │  ChromaDB        │  │  Google Drive    │  │  External APIs   │  │
│  │  (Vectors)       │  │  (Documents)     │  │  (IBGE, ICD)     │  │
│  └──────────────────┘  └──────────────────┘  └──────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

## Fluxo de Dados

### 1. Fluxo de Autenticacao

```
Usuario → Login Page → Google OAuth → Token Validation → Session State
                                                              │
                                                              ▼
                                                     Sync Page (Drive)
                                                              │
                                                              ▼
                                                      Main Application
```

### 2. Fluxo de Chat RAG

```
Pergunta do Usuario
        │
        ▼
┌───────────────────┐
│  Retriever        │
│  (Vector + BM25)  │
└───────────────────┘
        │
        ▼
┌───────────────────┐
│  Documentos       │
│  Relevantes       │
└───────────────────┘
        │
        ▼
┌───────────────────┐
│  LLM (OpenRouter) │
│  + System Prompt  │
└───────────────────┘
        │
        ▼
   Resposta com Citacoes
```

### 3. Fluxo de Consultas

```
Termo de Busca
        │
        ▼
┌───────────────────┐
│  Data Processor   │
│  (CBO/CID/CNAE)   │
└───────────────────┘
        │
        ├──> API Externa (IBGE, ICD)
        │
        └──> Cache Local / Google Drive
                    │
                    ▼
            Resultados Formatados
```

## Padroes de Design Utilizados

### Singleton Pattern
Usado nos Data Processors para garantir uma unica instancia:
- `CBODatabase`
- `CIDDatabase`
- `CNAEDataProcessor`
- `CNAERiskDataProcessor`

### Factory Pattern
Usado na inicializacao do LLM com fallback:
- Tenta Replit AI Integrations primeiro
- Fallback para OPENROUTER_API_KEY direto

### Observer Pattern
Streamlit `st.session_state` para gerenciamento de estado reativo.

### Template Method Pattern
Geradores de documentos usam templates DOCX com `docxtpl`.

## Configuracao de Cache

| Tipo | Funcao | TTL |
|------|--------|-----|
| `@st.cache_resource` | Singleton de processadores | Permanente |
| `@st.cache_data` | Dados de consulta | Varia |
| `@lru_cache` | Funcoes puras | Permanente |
| Parquet files | Cache de CA | 24 horas |

## Portas e Endpoints

| Servico | Porta | Descricao |
|---------|-------|-----------|
| Streamlit | 5000 | Aplicacao principal |

## Dependencias Principais

### IA/ML
- `langchain`, `langchain-community`, `langchain-chroma`, `langchain-openai`
- `sentence-transformers`
- `chromadb`

### Processamento de Documentos
- `pypdf`, `PyPDF2`
- `python-docx`, `docxtpl`
- `pymupdf`, `pytesseract`
- `openpyxl`, `pandas`

### Web e APIs
- `streamlit`
- `requests`, `httpx`
- `google-auth`, `google-api-python-client`
