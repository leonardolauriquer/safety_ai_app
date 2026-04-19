# ChromaDB Reindex Record

## Last Full Reindex

- **Date**: 2026-04-18
- **Embedding model**: `sentence-transformers/paraphrase-multilingual-mpnet-base-v2` (768 dims)
- **Previous model**: `all-MiniLM-L6-v2` (384 dims)
- **Reason**: Embedding model upgrade — dimension mismatch requires full collection rebuild
- **Command**: `python safety_ai_app/scripts/vectorize_nrs.py --force-reindex`

## Verification Results

- **Total chunks indexed**: 12,724
- **Unique documents**: 39 (NR-01 to NR-38 + annexes)
- **Metadata fields**: `nr_number`, `article`, `item` present on all chunks
- **Sentinel file**: `safety_ai_app/data/chroma_db/.embedding_model` updated
- **Sample query**: "Quais são as responsabilidades da empresa em relação ao trabalho em altura?"
  - Returned 2 relevant results with correct `nr_number`, `item` metadata

## Notes

- `safety_ai_app/data/chroma_db/` is excluded from git (see `.gitignore`) — this file serves
  as the git-trackable record of indexing operations.
- Both `nr_rag_qa.py` and `vectorize_nrs.py` use the same `EMBEDDING_MODEL_NAME` constant,
  ensuring runtime retrieval and indexing are always in sync.
- The script auto-detects model changes via a sentinel file and forces reindex automatically
  on startup if the model has changed since the last run.
