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

---

## Correção: Exclusão de arquivos sintéticos da indexação (2026-04-20)

**Problema identificado**: versões anteriores do `vectorize_nrs.py` indexavam tanto
os PDFs oficiais quanto os arquivos `*-referencia.txt` (resumos AI-gerados por NR) e
os fragmentos `NR-29-parte*.txt` (texto legado dividido), criando chunks duplicados e
conflitantes que enfraqueciam a qualidade das citações RAG.

**Correção aplicada**:
- `SKIP_TXT_SUFFIXES = ("-referencia.txt",)` → exclui todos os `NR-XX-referencia.txt`
- `SKIP_TXT_PREFIXES_PARTS = ("nr-29-parte",)` → exclui fragmentos legados da NR-29
- Função `purge_synthetic_txt_chunks()` adicionada: remove automaticamente chunks
  contaminados já existentes no ChromaDB em cada execução incremental do indexador
- Guias técnicos legítimos (`GUIA-PGR-elaboracao.txt`, `GUIA-LTCAT-AET.txt`) são mantidos
- Todos os 38 PDFs oficiais estão disponíveis em `data/nrs/` (NR-01 a NR-38)

**Status**: O indexador automático (iniciado pelo `server.py`) executa a limpeza
de chunks sintéticos e indexa as NRs pendentes via PDF oficial a cada inicialização.

---

## Migração para PDFs Oficiais MTE (Task #80 — 2026-04-20)

**Objetivo**: Substituir os `.txt` de referência pelos PDFs oficiais do MTE, com metadados
de página real (pypdf), source `"MTE-oficial"`, e metadados completos:
`source`, `nr_number`, `page`, `page_number`, `section`, `doc_type`.

### Metadata Contract (por chunk)

Todos os chunks indexados via `process_document_to_chroma` agora incluem:

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `source` | str | `"MTE-oficial"` para PDFs oficiais |
| `nr_number` | int/str | Número da NR (ex: `15` ou `"15"`) |
| `page` | str | Número da página no PDF (alias de `page_number`) |
| `page_number` | str | Número da página no PDF |
| `section` | str | Seção derivada de nr_number + item (ex: `"NR-15 15.1"`) |
| `doc_type` | str | `"norma_regulamentadora"` |
| `source_file` | str | Nome do arquivo PDF (ex: `"NR-15.pdf"`) |
| `item` | str | Item específico detectado (ex: `"15.1"`) |
| `article` | str | Artigo detectado, se houver |

### Status por NR — Cobertura atual (2026-04-20)

**Indexados via PDF MTE-oficial (15 NRs)**:
NR-01, NR-02, NR-03, NR-04, NR-05, NR-06, NR-07, NR-08, NR-09, NR-10, NR-11, NR-14, NR-21, NR-25, NR-27

**Indexados via Google Drive / Biblioteca (6 NRs)**:
NR-33, NR-34, NR-35, NR-36, NR-37, NR-38

**Total coberto: 21 NRs — 3.601 chunks** (em atualização contínua pelo indexador automático)

**Indexamento automático em andamento (17 NRs pendentes)**:
NR-12, NR-13, NR-15, NR-16, NR-17, NR-18, NR-19, NR-20,
NR-22, NR-23, NR-24, NR-26, NR-28, NR-29, NR-30, NR-31, NR-32

### nr_number — Formato dos metadados

O campo `nr_number` segue o formato de string com o número bruto extraído do nome do arquivo PDF
via regex `NR[\s\-_]?(\d{1,2})` (ex: `"NR-05.pdf"` → `nr_number = "05"`).

Notas de compatibilidade:
- Chunks indexados antes de 2026-04-20 podem ter formato `"NR-5"` (com prefixo) — foi corrigido
- `get_indexed_nr_numbers_from_mte()` e `get_already_indexed()` normalizam automaticamente ambos os formatos
- Novos chunks sempre usam formato de dígito puro (ex: `"05"`, `"11"`)

### Mecanismo de Indexação Automática

O `server.py` inicia um thread que:
1. Aguarda 120s após o startup para o modelo Streamlit aquecer
2. Executa `_nr_indexer_runner.py` como subprocesso isolado
3. O subprocesso indexa apenas as NRs ainda pendentes (idempotente — verifica quais estão já indexadas)
4. Estado de runtime salvo em `data/nr_indexing_status.json` (excluído do git — ver `.gitignore`)

O Admin Panel (Pipeline de IA → 🗂️ Indexar NRs) também permite disparar manualmente.

---

## Estado Pré-Migração (2026-04-19 — índice de referência com .txt)

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
- `chunk_size`: 1000, `chunk_overlap`: 150 (structural NR chunker)

## Notes

- `safety_ai_app/data/chroma_db/` is excluded from git (see `.gitignore`) — this file serves
  as the git-trackable record of indexing operations.
- Both `nr_rag_qa.py` and `vectorize_nrs.py` use the same `EMBEDDING_MODEL_NAME` constant,
  ensuring runtime retrieval and indexing are always in sync.
- The script auto-detects model changes via a sentinel file and forces reindex automatically
  on startup if the last model has changed.
- The `_split_nr_document_structurally` chunker detects NR item/chapter boundaries and enriches
  each chunk with `nr_number`, `article`, `item`, and `section` metadata.
- Both `page` and `page_number` fields are set on every chunk for compatibility.
