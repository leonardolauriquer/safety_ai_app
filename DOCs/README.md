# SafetyAI - Documentacao Tecnica

## Visao Geral

O SafetyAI e uma aplicacao de inteligencia artificial especializada em Saude e Seguranca do Trabalho (SST) no Brasil. A aplicacao fornece um assistente inteligente que ajuda engenheiros e profissionais de seguranca a navegar pelas Normas Regulamentadoras (NRs), utilizando uma arquitetura RAG (Retrieval-Augmented Generation) alimentada por LLM OpenRouter e ChromaDB.

## Principais Recursos

| Recurso | Descricao |
|---------|-----------|
| Chat com IA | Assistente de SST com conhecimento das 38 NRs brasileiras |
| Consultas Rapidas | Pesquisa de CBO, CID-10/11, CNAE, CA/EPI |
| Dimensionamento CIPA | Calculo de membros efetivos e suplentes (NR-05) |
| Dimensionamento SESMT | Calculo de profissionais necessarios (NR-04) |
| Geracao de Documentos | APR (Analise Preliminar de Risco) e ATA |
| Jogos Educativos | Quiz e Palavras Cruzadas sobre SST |
| Integracao Drive | Sincronizacao com Google Drive para documentos |

## Stack Tecnologico

- **Frontend**: Streamlit com design Cyber-Neon
- **Backend**: Python 3.12
- **IA/LLM**: OpenRouter (openai/gpt-oss-120b)
- **Vector Store**: ChromaDB
- **Embeddings**: Sentence Transformers (all-MiniLM-L6-v2)
- **Banco de Dados**: PostgreSQL (Replit)
- **Autenticacao**: Google OAuth 2.0

## Estrutura da Documentacao

| Arquivo | Conteudo |
|---------|----------|
| [ARQUITETURA.md](ARQUITETURA.md) | Arquitetura tecnica completa |
| [FUNCIONALIDADES.md](FUNCIONALIDADES.md) | Todas as funcionalidades detalhadas |
| [CALCULOS.md](CALCULOS.md) | Algoritmos e formulas (CIPA, SESMT) |
| [PROCESSADORES_DADOS.md](PROCESSADORES_DADOS.md) | Processadores CBO, CID, CNAE, CA |
| [RAG_IA.md](RAG_IA.md) | Sistema de IA com RAG |
| [INTEGRACOES.md](INTEGRACOES.md) | APIs externas e integracoes |
| [INTERFACE.md](INTERFACE.md) | Design cyber-neon e UI |
| [AUTENTICACAO.md](AUTENTICACAO.md) | Fluxo de autenticacao |
| [2026-04-20-Correcao-OAuth-Performance.md](2026-04-20-Correcao-OAuth-Performance.md) | Manutencao de Performance e OAuth |
| [2026-04-20-Correcao-Build-Deploy.md](2026-04-20-Correcao-Build-Deploy.md) | Correcao de Build e Deploy (Cloud Run) |
| [2026-04-20-Padronizacao-Project-ID.md](2026-04-20-Padronizacao-Project-ID.md) | Padronizacao do Project ID (safetyai-472110) |
| [2026-04-20-Otimizacao-Inicializacao-Rapida.md](2026-04-20-Otimizacao-Inicializacao-Rapida.md) | Otimizacao de Inicializacao Rapida e Deferimento |
| [2026-04-21-Otimizacao-Login-Extrema.md](2026-04-21-Otimizacao-Login-Extrema.md) | Otimizacao Extrema de Performance no Login |
| [2026-04-29-Security-Hardening.md](2026-04-29-Security-Hardening.md) | **Security Hardening** — CORS restrito, CSP/HSTS, MIME validation, RAG fix, Firestore retry, OG tags |

## Como Executar

```bash
# O projeto utiliza Streamlit na porta 5000
python -m streamlit run safety_ai_app/src/safety_ai_app/web_app.py --server.port 5000 --server.address 0.0.0.0 --server.headless true
```

## Variaveis de Ambiente Necessarias

| Variavel | Descricao |
|----------|-----------|
| `AI_INTEGRATIONS_OPENROUTER_API_KEY` | Chave da API OpenRouter (Replit Integration) |
| `AI_INTEGRATIONS_OPENROUTER_BASE_URL` | URL base OpenRouter (Replit Integration) |
| `OPENROUTER_API_KEY` | Chave OpenRouter (fallback) |
| `GOOGLE_API_KEY` | Chave da API Google |
| `ICD_API_CLIENT_ID` | Client ID da API ICD (OMS) |
| `ICD_API_CLIENT_SECRET` | Client Secret da API ICD (OMS) |
| `ADZUNA_APP_ID` | ID do App Adzuna |
| `ADZUNA_API_KEY` | Chave da API Adzuna |

## Versao

**v2.0** - Janeiro 2026

## Contato

Para suporte tecnico, consulte a documentacao completa nos arquivos acima.
