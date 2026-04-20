import os
import sys

script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(script_dir, '..'))
src_path = os.path.join(project_root, 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)

import logging
import argparse
import re

from safety_ai_app.google_drive_integrator import (
    get_service_account_drive_integrator_instance,
    AI_CHAT_SYNC_SUBFOLDER_NAME,
    SAFETY_AI_ROOT_FOLDER_NAME,
)
from safety_ai_app.nr_rag_qa import NRQuestionAnswering

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

CHROMADB_PERSIST_DIRECTORY = os.path.join(project_root, "data", "chroma_db")
COLLECTION_NAME = "nrs_collection"
LOCAL_NRS_DIR = os.path.join(project_root, "data", "nrs")

EMBEDDING_MODEL_NAME = 'intfloat/multilingual-e5-large-instruct'

_EMBEDDING_SENTINEL_FILE = os.path.join(CHROMADB_PERSIST_DIRECTORY, ".embedding_model")

SUPPORTED_LOCAL_TYPES = {
    ".pdf": "application/pdf",
    ".txt": "text/plain",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}

SKIP_LOCAL_FILES = {"nr_35_chunks.json"}

# Patterns (lowercase) that identify synthetic/split .txt files which should NOT be
# indexed because they contain AI-generated summaries or split text that conflicts
# with official PDF citations.
# - "*-referencia.txt"  : AI-generated reference/summary files for each NR
# - "nr-29-parte*.txt"  : split legacy text fragments for NR-29 (replaced by PDF)
_SKIP_TXT_SUFFIXES = ("-referencia.txt",)
_SKIP_TXT_PREFIXES_PARTS = ("nr-29-parte",)


def _read_indexed_model() -> str:
    try:
        with open(_EMBEDDING_SENTINEL_FILE, "r", encoding="utf-8") as f:
            return f.read().strip()
    except FileNotFoundError:
        return ""


def _write_indexed_model(model_name: str) -> None:
    os.makedirs(CHROMADB_PERSIST_DIRECTORY, exist_ok=True)
    with open(_EMBEDDING_SENTINEL_FILE, "w", encoding="utf-8") as f:
        f.write(model_name)


def _needs_reindex() -> bool:
    indexed = _read_indexed_model()
    if not indexed:
        logger.warning(
            "MIGRATION GUARD: Arquivo sentinela de modelo não encontrado. "
            "Estado do modelo de embeddings é desconhecido — forçando re-indexação completa."
        )
        return True
    if indexed != EMBEDDING_MODEL_NAME:
        logger.warning(
            f"MIGRATION GUARD: A coleção ChromaDB foi indexada com '{indexed}', "
            f"mas o modelo atual é '{EMBEDDING_MODEL_NAME}'. "
            "Forçando re-indexação completa para evitar incompatibilidade de dimensão."
        )
        return True
    return False


def _infer_nr_metadata(filename: str) -> dict:
    """
    Infer NR number and document type from filename.

    Metadata fields produced:
      - nr_number  : formatted as "NR-X" (e.g. "NR-35") or "" for guides/portarias
      - doc_type   : "norma_regulamentadora" | "guia_tecnico" | "portaria"
      - source     : "local_nrs_dir"
      - source_file: original filename
      - section    : inferred section label (e.g. "NR-35" or guide name)
      - page       : "1" (text files have no real page; PDFs set per-page later)
    """
    base = os.path.splitext(filename)[0].upper()
    nr_match = re.search(r'NR[-_\s]?(\d{1,2})', base, re.IGNORECASE)
    if nr_match:
        nr_num = nr_match.group(1)
        nr_number = f"NR-{nr_num}"
        doc_type = "norma_regulamentadora"
        section = nr_number
    else:
        nr_number = ""
        doc_type = "guia_tecnico"
        section = base.split("-")[0].strip()
        if "PORTARIA" in base:
            doc_type = "portaria"

    if any(kw in base for kw in ["PGR", "PCMSO", "LTCAT", "AET", "GUIA"]):
        doc_type = "guia_tecnico"

    return {
        "nr_number": nr_number,
        "doc_type": doc_type,
        "source": "local_nrs_dir",
        "source_file": filename,
        "section": section,
        "page": "1",
    }


def index_local_nrs(qa: NRQuestionAnswering, force: bool = False) -> int:
    """
    Index all supported files in LOCAL_NRS_DIR into ChromaDB.

    Returns the number of files newly indexed.
    """
    if not os.path.isdir(LOCAL_NRS_DIR):
        logger.warning(f"Diretório de NRs locais não encontrado: {LOCAL_NRS_DIR}")
        return 0

    files = sorted(os.listdir(LOCAL_NRS_DIR))
    indexed = 0
    skipped = 0
    errors = 0

    for fname in files:
        if fname in SKIP_LOCAL_FILES:
            continue
        ext = os.path.splitext(fname)[1].lower()
        if ext not in SUPPORTED_LOCAL_TYPES:
            continue

        # Skip synthetic reference summaries and legacy split txt fragments
        fname_lower = fname.lower()
        if ext == ".txt":
            if any(fname_lower.endswith(s) for s in _SKIP_TXT_SUFFIXES):
                logger.info(f"SKIP '{fname}' — arquivo de referência sintética (não indexar).")
                skipped += 1
                continue
            if any(fname_lower.startswith(p) for p in _SKIP_TXT_PREFIXES_PARTS):
                logger.info(f"SKIP '{fname}' — fragmento txt legado (não indexar).")
                skipped += 1
                continue

        filepath = os.path.join(LOCAL_NRS_DIR, fname)
        mime_type = SUPPORTED_LOCAL_TYPES[ext]
        meta = _infer_nr_metadata(fname)

        if not force:
            try:
                existing = qa.vector_db._collection.get(
                    where={"source_file": fname},
                    include=["metadatas"],
                )
                if existing and existing.get("ids"):
                    logger.info(
                        f"SKIP '{fname}' — já indexado ({len(existing['ids'])} chunks). "
                        "Use --force-reindex para re-indexar."
                    )
                    skipped += 1
                    continue
            except Exception:
                pass

        try:
            logger.info(f"Indexando arquivo local: {fname}")
            qa.process_document_to_chroma(
                file_path=filepath,
                document_name=fname,
                source="NRs Locais",
                file_type=mime_type,
                additional_metadata=meta,
            )
            indexed += 1
        except Exception as e:
            logger.error(f"ERRO ao indexar '{fname}': {e}", exc_info=True)
            errors += 1

    logger.info(
        f"Arquivos locais — Indexados: {indexed}, Pulados: {skipped}, Erros: {errors}"
    )
    return indexed


def purge_synthetic_txt_chunks(qa: NRQuestionAnswering) -> int:
    """
    Remove from ChromaDB any chunks whose `source_file` matches synthetic/split
    .txt files that should never have been indexed:
      - *-referencia.txt  (AI-generated NR summaries)
      - NR-29-parte*.txt  (legacy split text fragments)

    Returns the number of chunk IDs deleted.
    """
    try:
        all_docs = qa.vector_db._collection.get(include=["metadatas"])
    except Exception as e:
        logger.warning(f"purge_synthetic_txt_chunks: não foi possível listar coleção: {e}")
        return 0

    ids_to_delete = []
    for doc_id, meta in zip(all_docs.get("ids", []), all_docs.get("metadatas", [])):
        src = (meta or {}).get("source_file", "").lower()
        if any(src.endswith(s) for s in _SKIP_TXT_SUFFIXES):
            ids_to_delete.append(doc_id)
            continue
        if any(src.startswith(p) for p in _SKIP_TXT_PREFIXES_PARTS):
            ids_to_delete.append(doc_id)

    if not ids_to_delete:
        logger.info("purge_synthetic_txt_chunks: nenhum chunk sintético encontrado.")
        return 0

    try:
        qa.vector_db._collection.delete(ids=ids_to_delete)
        logger.info(
            f"purge_synthetic_txt_chunks: {len(ids_to_delete)} chunks removidos "
            f"(*-referencia.txt / NR-29-parte*.txt)."
        )
    except Exception as e:
        logger.error(f"purge_synthetic_txt_chunks: erro ao deletar chunks: {e}", exc_info=True)
        return 0

    return len(ids_to_delete)


def main(force_reindex: bool = False, local_only: bool = False):
    """
    Pipeline completo de vetorização e indexação de NRs.

    Etapas:
      1. Indexa todos os arquivos locais em data/nrs/ (NRs 1-38 + guias).
      2. Sincroniza documentos do Google Drive (se --local-only não estiver ativo).

    Args:
        force_reindex: Se True, deleta e recria a coleção ChromaDB antes de indexar.
        local_only:    Se True, pula a sincronização com Google Drive.
    """
    logger.info("Iniciando pipeline de vetorização e indexação das NRs...")
    logger.info(f"Modelo de embeddings: {EMBEDDING_MODEL_NAME}")

    if not force_reindex and _needs_reindex():
        force_reindex = True
        logger.warning("Re-indexação forçada automaticamente por mudança de modelo de embeddings.")

    qa_system = NRQuestionAnswering(chroma_persist_directory=CHROMADB_PERSIST_DIRECTORY)
    if not qa_system:
        logger.critical("Falha ao inicializar NRQuestionAnswering. Encerrando.")
        return

    if force_reindex:
        logger.info(
            f"--force-reindex ativo: deletando e recriando a coleção '{COLLECTION_NAME}'..."
        )
        try:
            qa_system.clear_chroma_collection()
            logger.info(f"Coleção '{COLLECTION_NAME}' recriada com sucesso.")
        except Exception as e:
            logger.error(f"ERRO ao recriar a coleção ChromaDB: {e}", exc_info=True)
    else:
        # Incremental run: purge any synthetic *-referencia.txt / NR-29-parte*.txt
        # chunks that may have been indexed by a previous version of this script.
        logger.info("[Purge] Removendo chunks de arquivos sintéticos/legados do ChromaDB...")
        purged = purge_synthetic_txt_chunks(qa_system)
        if purged:
            logger.info(f"[Purge] {purged} chunks sintéticos removidos com sucesso.")

    # ── Etapa 1: arquivos locais ──────────────────────────────────────────────
    initial_count = qa_system.vector_db._collection.count()
    logger.info(
        f"[Etapa 1] Indexando arquivos locais em '{LOCAL_NRS_DIR}' "
        f"(chunks antes: {initial_count})..."
    )
    local_indexed = index_local_nrs(qa_system, force=force_reindex)
    after_local = qa_system.vector_db._collection.count()
    logger.info(
        f"[Etapa 1] Concluída. Novos chunks: {after_local - initial_count} "
        f"(total: {after_local})"
    )

    # ── Etapa 2: Google Drive ─────────────────────────────────────────────────
    drive_count = 0
    if not local_only:
        logger.info("[Etapa 2] Sincronizando documentos do Google Drive...")
        drive_integrator = get_service_account_drive_integrator_instance()
        if not drive_integrator:
            logger.warning(
                "GoogleDriveIntegrator indisponível — pulando sincronização com Drive."
            )
        else:
            ai_chat_sync_folder_id = drive_integrator._get_ai_chat_sync_folder_id()
            if not ai_chat_sync_folder_id:
                logger.warning(
                    f"Pasta '{SAFETY_AI_ROOT_FOLDER_NAME}/{AI_CHAT_SYNC_SUBFOLDER_NAME}' "
                    "não encontrada no Drive — pulando sincronização."
                )
            else:
                drive_count = drive_integrator.synchronize_app_central_library_to_chroma(
                    qa_system=qa_system,
                    progress_callback=None,
                )
                logger.info(
                    f"[Etapa 2] Concluída. Drive: {drive_count} documentos processados."
                )
    else:
        logger.info("[Etapa 2] Pulada (--local-only ativo).")

    final_count = qa_system.vector_db._collection.count()
    logger.info(
        f"\n{'='*60}\n"
        f"RESUMO FINAL:\n"
        f"  Arquivos locais indexados: {local_indexed}\n"
        f"  Documentos do Drive processados: {drive_count}\n"
        f"  Chunks totais no ChromaDB: {final_count}\n"
        f"{'='*60}"
    )

    _write_indexed_model(EMBEDDING_MODEL_NAME)
    logger.info(f"Sentinela de modelo atualizado: '{EMBEDDING_MODEL_NAME}'")

    # Demonstração de busca
    logger.info("\n--- Demonstração de Busca ---")
    query_text = "Quais são os requisitos de segurança para trabalho em altura?"
    logger.info(f"Query: '{query_text}'")
    try:
        docs = qa_system.vector_db.similarity_search(query_text, k=3)
        for i, doc in enumerate(docs):
            meta = doc.metadata
            logger.info(
                f"Resultado {i+1}: NR={meta.get('nr_number','?')} | "
                f"section={meta.get('section','?')} | "
                f"doc={meta.get('document_name','?')[:40]} | "
                f"texto: {doc.page_content[:120]}..."
            )
    except Exception as e:
        logger.error(f"ERRO na demonstração de busca: {e}", exc_info=True)

    logger.info("Pipeline de vetorização concluído!")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description=(
            "Pipeline completo de vetorização das NRs Brasileiras no ChromaDB.\n"
            f"Modelo: {EMBEDDING_MODEL_NAME} (multilíngue, 1024 dims).\n\n"
            "Etapa 1: indexa todos os arquivos em data/nrs/ (NRs 1-38 + guias).\n"
            "Etapa 2: sincroniza documentos do Google Drive.\n\n"
            "IMPORTANTE: Use --force-reindex ao trocar o modelo de embeddings."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--force-reindex",
        action="store_true",
        help=(
            "Deleta e recria a coleção nrs_collection no ChromaDB e re-indexa "
            "todos os documentos (locais + Drive). "
            "Obrigatório após troca de modelo de embeddings."
        ),
    )
    parser.add_argument(
        "--local-only",
        action="store_true",
        help="Indexa apenas os arquivos locais em data/nrs/, sem sincronizar com o Drive.",
    )
    args = parser.parse_args()
    main(force_reindex=args.force_reindex, local_only=args.local_only)
