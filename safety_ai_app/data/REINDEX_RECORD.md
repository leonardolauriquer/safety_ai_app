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

## Notes

- `safety_ai_app/data/chroma_db/` is excluded from git (see `.gitignore`) — this file serves
  as the git-trackable record of indexing operations.
- Both `nr_rag_qa.py` and `vectorize_nrs.py` use the same `EMBEDDING_MODEL_NAME` constant,
  ensuring runtime retrieval and indexing are always in sync.
- The script auto-detects model changes via a sentinel file and forces reindex automatically
  on startup if the model has changed since the last run.
