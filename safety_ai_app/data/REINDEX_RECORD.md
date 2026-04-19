# ChromaDB Reindex Record

## Last Full Reindex

- **Date**: 2026-04-19
- **Embedding model**: `intfloat/multilingual-e5-large-instruct` (1024 dims)
- **Previous model**: `sentence-transformers/paraphrase-multilingual-mpnet-base-v2` (768 dims)
- **Reason**: Embedding model upgrade — dimension mismatch requires full collection rebuild; switched to E5-large-instruct for superior multilingual retrieval quality
- **Command**: `python safety_ai_app/scripts/vectorize_nrs.py --force-reindex`

## Verification Results

- **E5 conventions**: Query prefix `"query:"` applied at retrieval time; `"passage:"` prefix applied at indexing time; `normalize_embeddings=True`
- **Reranker**: `cross-encoder/mmarco-mMiniLMv2-L12-H384-v1` (multilingual mMARCO)
- **Sentinel file**: `safety_ai_app/data/chroma_db/.embedding_model` written with `intfloat/multilingual-e5-large-instruct`
- **ChromaDB**: Cleared and rebuilt from scratch (previous 768-dim collection deleted)

## Expansion Update (2026-04-19 — Task #80: Todas as 38 NRs)

Total ChromaDB chunks: **2.931** (cobertura completa: NR-01 a NR-38)

### Documentos Locais (data/nrs/)

| Arquivo | Chunks | Conteúdo |
|---------|--------|----------|
| NR-01-referencia.txt | 21 | NR-1 completa + riscos psicossociais 2025 |
| NR-02-referencia.txt | 1 | NR-2 — Inspeção Prévia |
| NR-03-referencia.txt | 2 | NR-3 — Embargo e Interdição |
| NR-04-referencia.txt | 4 | NR-4 — SESMT |
| NR-05-referencia.txt | 10 | NR-5 — CIPA |
| NR-06-referencia.txt | 13 | NR-6 — EPI |
| NR-07-referencia.txt | 16 | NR-7 — PCMSO |
| NR-08-referencia.txt | 2 | NR-8 — Edificações |
| NR-09-referencia.txt | 4 | NR-9 — PPRA/GRO |
| NR-10-referencia.txt | 4 | NR-10 — Instalações Elétricas |
| NR-11-referencia.txt | 3 | NR-11 — Transporte e Armazenagem |
| NR-12-referencia.txt | 4 | NR-12 — Máquinas e Equipamentos |
| NR-13-referencia.txt | 4 | NR-13 — Caldeiras e Vasos de Pressão |
| NR-14-referencia.txt | 2 | NR-14 — Fornos |
| NR-15-referencia.txt | 9 | NR-15 — Insalubridade |
| NR-16-referencia.txt | 3 | NR-16 — Periculosidade |
| NR-17-referencia.txt | 21 | NR-17 — Ergonomia |
| NR-18-referencia.txt | 42 | NR-18 — Construção Civil |
| NR-19-referencia.txt | 2 | NR-19 — Explosivos |
| NR-20-referencia.txt | 3 | NR-20 — Inflamáveis e Combustíveis |
| NR-21-referencia.txt | 2 | NR-21 — Trabalho a Céu Aberto |
| NR-22-referencia.txt | 2 | NR-22 — Mineração |
| NR-23-referencia.txt | 2 | NR-23 — Proteção contra Incêndio |
| NR-24-referencia.txt | 3 | NR-24 — Condições Sanitárias |
| NR-25-referencia.txt | 2 | NR-25 — Resíduos Industriais |
| NR-26-referencia.txt | 3 | NR-26 — Sinalização de Segurança |
| NR-27-referencia.txt | 2 | NR-27 — Registro Profissional |
| NR-28-referencia.txt | 2 | NR-28 — Fiscalização e Penalidades |
| NR-29-parte1.txt | 95 | NR-29 Trabalho Portuário (parte 1/4) |
| NR-29-parte2.txt | 151 | NR-29 Trabalho Portuário (parte 2/4) |
| NR-29-parte3.txt | ~64 | NR-29 Trabalho Portuário (parte 3/4) |
| NR-29-parte4.txt | 49 | NR-29 Trabalho Portuário (parte 4/4) |
| NR-30-referencia.txt | 107 | NR-30 — Trabalho Aquaviário |
| NR-31-referencia.txt | 66 | NR-31 — Trabalho Rural |
| NR-32-referencia.txt | 3 | NR-32 — Saúde em Serviços de Saúde |
| NR-33-referencia.txt | 18 | NR-33 — Espaços Confinados |
| GUIA-PGR-elaboracao.txt | 11 | Guia técnico PGR |
| GUIA-LTCAT-AET.txt | 10 | Guia técnico LTCAT/AET |

### Documentos via Google Drive (PDFs oficiais)

| Arquivo | Chunks | Fonte |
|---------|--------|-------|
| nr-33-atualizada-2022-_retificada.pdf | 134 | Google Drive — PDF oficial atualizado |
| nr-34-atualizada-2023-2.pdf | 485 | Google Drive — PDF oficial atualizado |
| nr-35-atualizada-2025.pdf | 198 | Google Drive — PDF oficial atualizado |
| nr-36-atualizada-2024-1.pdf | 390 | Google Drive — PDF oficial atualizado |
| nr-37-atualizada-2023.pdf | 833 | Google Drive — PDF oficial atualizado |
| nr-38-atualizada-2025-3.pdf | 129 | Google Drive — PDF oficial atualizado |

## RAG Configuration

- `retriever_top_k`: 8
- `bm25_weight`: 0.3 / `semantic_weight`: 0.7
- `chunk_size`: 1000, `chunk_overlap`: 150

## Notes

- `safety_ai_app/data/chroma_db/` is excluded from git (see `.gitignore`) — this file serves
  as the git-trackable record of indexing operations.
- Both `nr_rag_qa.py` and `vectorize_nrs.py` use the same `EMBEDDING_MODEL_NAME` constant,
  ensuring runtime retrieval and indexing are always in sync.
- The script auto-detects model changes via a sentinel file and forces reindex automatically
  on startup if the last model has changed.
- NR-29 (Trabalho Portuário) was split into 4 parts due to its size (101KB) to work within
  the embedding pipeline's memory constraints. All parts share `nr_number: "NR-29"` metadata.
- NR-29, NR-30, NR-31 reference files were created from scraped portal content (substantial
  PDF text extracted). NRs 2–28 and 32 were written as structured reference documents.
