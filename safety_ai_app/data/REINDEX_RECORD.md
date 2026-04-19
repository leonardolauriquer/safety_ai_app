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

## NR Reference Files Indexed (2026-04-19)

Total ChromaDB chunks: **2.288**

| Arquivo | Chunks | Fonte |
|---------|--------|-------|
| NR-01-referencia.txt | 21 | Local — NR-1 + psicossociais 2025 |
| NR-06-referencia.txt | 13 | Local — EPI |
| NR-07-referencia.txt | 16 | Local — PCMSO |
| NR-15-referencia.txt | 9 | Local — Insalubridade |
| NR-17-referencia.txt | 21 | Local — Ergonomia |
| NR-33-referencia.txt | 18 | Local — Espaços Confinados |
| GUIA-PGR-elaboracao.txt | 11 | Local — Guia PGR |
| GUIA-LTCAT-AET.txt | 10 | Local — Guia LTCAT/AET |
| nr-33-atualizada-2022-_retificada.pdf | 134 | Google Drive |
| nr-34-atualizada-2023-2.pdf | 485 | Google Drive |
| nr-35-atualizada-2025.pdf | 198 | Google Drive |
| nr-36-atualizada-2024-1.pdf | 390 | Google Drive |
| nr-37-atualizada-2023.pdf | 833 | Google Drive |
| nr-38-atualizada-2025-3.pdf | 129 | Google Drive |

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
  on startup if the model has changed since the last run.
