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

### Status por NR — Cobertura planejada (2026-04-20)

**Todos os 38 PDFs oficiais MTE disponíveis em `data/nrs/`**:
NR-01 a NR-38 — fonte única e autoritativa para indexação.

**Arquivos excluídos da indexação** (sínteses AI-geradas / fragmentos legados):
- `NR-XX-referencia.txt` (todos) — excluídos via `SKIP_TXT_SUFFIXES`
- `NR-29-parte1.txt` a `NR-29-parte4.txt` — excluídos via `SKIP_TXT_PREFIXES_PARTS`
- Substituídos por `NR-29.pdf` (PDF oficial)

**Guias técnicos indexados** (legítimos, mantidos):
- `GUIA-PGR-elaboracao.txt` — Guia de elaboração de PGR (fonte: MTE/FUNDACENTRO)
- `GUIA-LTCAT-AET.txt` — Guia técnico LTCAT/AET (fonte: MTE)

**Cobertura via Google Drive / Biblioteca** (6 NRs com PDF atualizado):
NR-33, NR-34, NR-35, NR-36, NR-37, NR-38

**Mecanismo**: O indexador automático iniciado pelo `server.py` processa os 38 PDFs
locais de forma incremental, limpando chunks sintéticos antes de indexar.
O `purge_synthetic_txt_chunks()` é executado em cada run incremental.
Chunk counts precisos disponíveis via Admin Panel → Pipeline de IA após a indexação.

### nr_number — Contrato de metadados (normalizado)

O campo `nr_number` usa o formato `"NR-X"` (ex: `"NR-5"`, `"NR-15"`) em **ambos** os scripts
de indexação (`vectorize_nrs.py` e `index_local_nrs.py`), alinhados desde 2026-04-20.

Derivação: `NR[-_\s]?(\d{1,2})` extraído do nome do arquivo → prefixado com `"NR-"`.
Exemplos: `"NR-05.pdf"` → `nr_number = "NR-5"`, `"NR-15.pdf"` → `nr_number = "NR-15"`.

- `get_indexed_nr_numbers_from_mte()` e `get_already_indexed()` normalizam automaticamente
  formatos legados (dígito puro, int) para o formato `"NR-X"` atual.
- Chunks indexados antes de 2026-04-20 podem ter `nr_number` em formato legado —
  um `--force-reindex` os recria com o contrato atual.

### Mecanismo de Indexação Automática

O `server.py` inicia um thread que:
1. Aguarda 120s após o startup para o modelo Streamlit aquecer
2. Executa `_nr_indexer_runner.py` como subprocesso isolado
3. O subprocesso indexa apenas as NRs ainda pendentes (idempotente — verifica quais estão já indexadas)
4. Estado de runtime salvo em `data/nr_indexing_status.json` (excluído do git — ver `.gitignore`)

O Admin Panel (Pipeline de IA → 🗂️ Indexar NRs) também permite disparar manualmente.

---

## Inventário Completo das NRs — Versões e Datas (2026-04-20)

> Dados extraídos dos metadados internos dos PDFs em `data/nrs/`.
> "Data PDF" = data de publicação/atualização do PDF pelo MTE (campo CreationDate).
> "Última Portaria" = última portaria/ato normativo citado na 1ª página do PDF.

| NR | Título | Páginas | Data PDF | Última Portaria citada |
|----|--------|---------|----------|------------------------|
| NR-01 | Disposições Gerais e GRO | 21 | 30/07/2025 | Portaria MTE nº 765, de 15/05/2025 |
| NR-02 | Inspeção Prévia | 2 | 02/08/2019 | Portaria SEPRT nº 915, de 30/07/2019 |
| NR-03 | Embargo e Interdição | 6 | 22/04/2020 | Portaria SEPRT nº 1.068, de 23/09/2019 |
| NR-04 | SESMT | 31 | 27/05/2025 | Portaria MTP nº 4.219, de 20/12/2022 |
| NR-05 | CIPA e Assédio | 14 | 23/10/2024 | Portaria MTP nº 4.219, de 20/12/2022 |
| NR-06 | EPI | 12 | 29/08/2025 | Portaria MTP nº 2.175, de 28/07/2022 |
| NR-07 | PCMSO | 39 | 23/04/2025 | Portaria SEPRT nº 6.734, de 10/03/2020 |
| NR-08 | Edificações | 2 | 22/08/2022 | Portaria MTP nº 2.188, de 28/07/2022 |
| NR-09 | Exposições Ocupacionais (GRO) | 15 | 13/03/2026 | Portaria SEPRT nº 6.735, de 10/03/2020 |
| NR-10 | Instalações Elétricas | 18 | 22/04/2020 | Portaria MTE nº 598, de 07/12/2004 |
| NR-11 | Transporte e Armazenagem | 14 | 10/08/2023 | Portaria SIT nº 82, de 01/06/2004 |
| NR-12 | Máquinas e Equipamentos | 165 | 17/01/2025 | Portaria MTb nº 3.214, de 08/06/1978 |
| NR-13 | Caldeiras e Vasos de Pressão | 35 | 03/01/2025 | Portaria MTb nº 1.846, de 01/07/2022 |
| NR-14 | Fornos | 1 | 22/08/2022 | Portaria MTP nº 2.189, de 28/07/2022 |
| NR-15 | Atividades Insalubres | 112 | 05/12/2025 | Portaria MTE nº 2.021, de 03/12/2025 |
| NR-16 | Atividades Perigosas | 22 | 05/12/2025 | — |
| NR-17 | Ergonomia | 22 | 23/10/2024 | Portaria MTP nº 423, de 07/10/2021 |
| NR-18 | Construção Civil | 54 | 23/03/2026 | Portaria SEPRT nº 3.733, de 10/02/2020 |
| NR-19 | Explosivos | 28 | 23/10/2024 | Portaria MTP nº 424, de 07/10/2021 |
| NR-20 | Inflamáveis e Combustíveis | 30 | 24/01/2025 | Portaria SEPRT nº 1.360, de 09/12/2019 |
| NR-21 | Trabalho a Céu Aberto | 2 | 22/04/2020 | Portaria MTE nº 2.037, de 15/12/1999 |
| NR-22 | Mineração | 70 | 13/03/2026 | Portaria MTE nº 225, de 26/02/2024 |
| NR-23 | Proteção contra Incêndio | 1 | 12/09/2022 | Portaria MTP nº 2.769, de 05/09/2022 |
| NR-24 | Condições Sanitárias | 14 | 12/09/2022 | Portaria MTP nº 2.772, de 05/09/2022 |
| NR-25 | Resíduos Industriais | 2 | 20/12/2022 | Portaria MTP nº 3.994, de 05/12/2022 |
| NR-26 | Sinalização de Segurança | 3 | 12/09/2022 | Portaria MTP nº 2.770, de 05/09/2022 |
| NR-27 | Registro Profissional *(revogada 2022)* | 2 | 28/01/2019 | Portaria SSST nº 13, de 20/12/1995 |
| NR-28 | Fiscalização e Penalidades | 138 | 30/03/2026 | — |
| NR-29 | Trabalho Portuário | 43 | 23/10/2024 | Portaria MTP nº 671, de 30/03/2022 |
| NR-30 | Trabalho Aquaviário | 51 | 23/10/2024 | Portaria MTP nº 4.219, de 20/12/2022 |
| NR-31 | Trabalho Rural | 81 | 24/10/2025 | Portaria MTP nº 4.219, de 20/12/2022 |
| NR-32 | Saúde em Serviços de Saúde | 50 | 03/01/2025 | Portaria MTP nº 806, de 13/04/2022 |
| NR-33 | Espaços Confinados | 18 | 08/12/2022 | Portaria MTP nº 1.690, de 15/06/2022 |
| NR-34 | Construção e Reparação Naval | 48 | 11/06/2025 | — |
| NR-35 | Trabalho em Altura | 15 | 03/01/2024 | Portaria MTE nº 3.903, de 28/12/2023 |
| NR-36 | Frigoríficos | 45 | 04/07/2024 | Portaria MTP nº 4.219, de 20/12/2022 |
| NR-37 | Plataformas de Petróleo | 82 | 23/10/2024 | Portaria MTP nº 4.219, de 20/12/2022 |
| NR-38 | Limpeza Urbana | 13 | 27/05/2025 | Portaria MTP nº 4.101, de 16/12/2022 |

### NRs com PDFs mais antigos — candidatas a atualização

| NR | Data PDF | Observação |
|----|----------|------------|
| NR-27 | 28/01/2019 | **Revogada** pela Portaria MTP nº 671/2022 — manter apenas para referência histórica |
| NR-02 | 02/08/2019 | Verificar se houve atualização posterior a 2019 no portal MTE |
| NR-10 | 22/04/2020 | Verificar se houve atualização posterior a 2020 |
| NR-03 | 22/04/2020 | Verificar se houve atualização posterior a 2020 |
| NR-21 | 22/04/2020 | NR simples (2 páginas) — verificar status |

### NRs mais recentes (atualizadas em 2025-2026)

NR-01 (07/2025), NR-06 (08/2025), NR-09 (03/2026), NR-15 (12/2025),
NR-16 (12/2025), NR-18 (03/2026), NR-22 (03/2026), NR-28 (03/2026)

### NRs 33-38 — versões locais vs. Google Drive

Para as NRs 33-38 existem duas fontes: o PDF local em `data/nrs/` e o PDF no Google Drive.
O indexador automático prioriza o Google Drive para essas NRs (via `drive_sync.py`).
Ao atualizar, basta fazer upload do novo PDF no Google Drive — o sync acontece automaticamente.

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
