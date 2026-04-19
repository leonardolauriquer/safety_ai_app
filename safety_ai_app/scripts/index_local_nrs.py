"""
Script de indexação local das NRs e documentos técnicos complementares.

Processa todos os arquivos em safety_ai_app/data/nrs/ e adiciona ao ChromaDB.
Suporta PDF, TXT e DOCX. Uso independente do pipeline Google Drive.

Uso:
    python safety_ai_app/scripts/index_local_nrs.py
    python safety_ai_app/scripts/index_local_nrs.py --force-reindex
    python safety_ai_app/scripts/index_local_nrs.py --file NR-01.txt
"""

import os
import sys
import argparse
import logging

script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(script_dir, '..'))
src_path = os.path.join(project_root, 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from safety_ai_app.nr_rag_qa import (
    NRQuestionAnswering,
    CHROMADB_PERSIST_DIRECTORY,
    COLLECTION_NAME,
)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

NRS_DIR = os.path.join(project_root, "data", "nrs")

SUPPORTED_TYPES = {
    ".pdf": "application/pdf",
    ".txt": "text/plain",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
}

SKIP_FILES = {
    "nr_35_chunks.json",
}


def _infer_metadata(filename: str) -> dict:
    """Infer NR number and document type from filename."""
    import re
    base = os.path.splitext(filename)[0].upper()
    nr_match = re.search(r'NR[-_\s]?(\d{1,2})', base, re.IGNORECASE)
    nr_number = nr_match.group(1) if nr_match else ""

    doc_type = "norma_regulamentadora" if nr_number else "guia_tecnico"
    if any(kw in base for kw in ["PGR", "PCMSO", "LTCAT", "AET", "GUIA", "PORTARIA"]):
        doc_type = "guia_tecnico"
    if "PORTARIA" in base:
        doc_type = "portaria"

    return {
        "nr_number": nr_number,
        "doc_type": doc_type,
        "source_file": filename,
        "source": "local_nrs_dir",
    }


def index_file(qa: NRQuestionAnswering, filepath: str, force: bool = False) -> bool:
    filename = os.path.basename(filepath)
    ext = os.path.splitext(filename)[1].lower()

    if ext not in SUPPORTED_TYPES:
        logger.warning(f"Tipo não suportado: {filename}")
        return False

    mime_type = SUPPORTED_TYPES[ext]
    meta = _infer_metadata(filename)

    # Check if already indexed (by source file, skip if not force)
    if not force:
        try:
            existing = qa.vector_db._collection.get(
                where={"source_file": filename},
                include=["metadatas"],
            )
            if existing and existing.get("ids"):
                logger.info(f"SKIP '{filename}' — já indexado ({len(existing['ids'])} chunks). Use --force-reindex para re-indexar.")
                return False
        except Exception:
            pass

    logger.info(f"Indexando: {filename} (tipo: {mime_type})")
    qa.process_document_to_chroma(
        file_path=filepath,
        document_name=filename,
        source="NRs Locais",
        file_type=mime_type,
        additional_metadata=meta,
    )
    return True


def main():
    parser = argparse.ArgumentParser(description="Indexa NRs locais no ChromaDB.")
    parser.add_argument("--force-reindex", action="store_true",
                        help="Re-indexa todos os arquivos, mesmo os já presentes.")
    parser.add_argument("--file", type=str, default=None,
                        help="Indexa apenas um arquivo específico (nome ou caminho).")
    args = parser.parse_args()

    logger.info("Inicializando NRQuestionAnswering...")
    qa = NRQuestionAnswering(chroma_persist_directory=CHROMADB_PERSIST_DIRECTORY)
    if not qa:
        logger.critical("Falha ao inicializar QA. Encerrando.")
        return

    initial_count = qa.vector_db._collection.count()
    logger.info(f"ChromaDB: {initial_count} chunks antes da indexação.")

    if args.file:
        filepath = args.file if os.path.isabs(args.file) else os.path.join(NRS_DIR, args.file)
        if not os.path.exists(filepath):
            logger.error(f"Arquivo não encontrado: {filepath}")
            return
        index_file(qa, filepath, force=args.force_reindex)
    else:
        if not os.path.isdir(NRS_DIR):
            logger.error(f"Diretório não encontrado: {NRS_DIR}")
            return

        files = sorted(os.listdir(NRS_DIR))
        indexed = 0
        skipped = 0
        failed = 0

        for fname in files:
            if fname in SKIP_FILES:
                continue
            ext = os.path.splitext(fname)[1].lower()
            if ext not in SUPPORTED_TYPES:
                continue

            filepath = os.path.join(NRS_DIR, fname)
            try:
                result = index_file(qa, filepath, force=args.force_reindex)
                if result:
                    indexed += 1
                else:
                    skipped += 1
            except Exception as e:
                logger.error(f"ERRO ao indexar {fname}: {e}", exc_info=True)
                failed += 1

        final_count = qa.vector_db._collection.count()
        logger.info(f"\n{'='*60}")
        logger.info(f"RESUMO DA INDEXAÇÃO:")
        logger.info(f"  Indexados: {indexed}")
        logger.info(f"  Pulados (já existentes): {skipped}")
        logger.info(f"  Erros: {failed}")
        logger.info(f"  Chunks totais no ChromaDB: {final_count} (antes: {initial_count})")
        logger.info(f"{'='*60}")

    logger.info("Indexação local concluída.")


if __name__ == "__main__":
    main()
