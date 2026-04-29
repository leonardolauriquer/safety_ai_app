"""
NR Indexer — SafetyAI RAG Pipeline

Responsabilidade única: indexação de NR PDFs em background thread.
Extraído de nr_rag_qa.py para isolar o gerenciamento de threads
do motor RAG principal.
"""

import json
import logging
import os
import threading
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

_script_dir = os.path.dirname(os.path.abspath(__file__))
_project_root = os.path.abspath(os.path.join(_script_dir, "..", ".."))
CHROMADB_PERSIST_DIRECTORY = os.path.join(_project_root, "data", "chroma_db")

NR_INDEXING_STATUS_FILE = os.path.join(
    os.path.dirname(CHROMADB_PERSIST_DIRECTORY), "nr_indexing_status.json"
)

# ---------------------------------------------------------------------------
# Thread state
# ---------------------------------------------------------------------------

_nr_indexing_thread: Optional[threading.Thread] = None
_nr_indexing_lock = threading.Lock()


# ---------------------------------------------------------------------------
# Core helpers
# ---------------------------------------------------------------------------

def get_indexed_nr_numbers_from_mte(collection: Any) -> List[int]:
    """Return sorted list of NR numbers (int) already indexed from MTE-oficial source."""
    try:
        result = collection.get(include=["metadatas"])
        indexed = set()
        for meta in result.get("metadatas", []):
            if meta.get("source") == "MTE-oficial":
                nr = meta.get("nr_number")
                if isinstance(nr, int):
                    indexed.add(nr)
                elif isinstance(nr, str):
                    try:
                        clean = nr.replace("NR-", "").lstrip("0") or "0"
                        indexed.add(int(clean))
                    except ValueError:
                        pass
        return sorted(indexed)
    except Exception as exc:
        logger.warning("[NR-INDEX] Erro ao checar NRs indexadas: %s", exc)
        return []


def _nr_indexing_worker(qa_instance: Any, nr_list: List[int]) -> None:
    """Background thread: indexes NR PDFs using the app's existing QA instance."""
    nrs_dir = os.path.join(os.path.dirname(CHROMADB_PERSIST_DIRECTORY), "nrs")
    status: Dict[str, Any] = {
        "running": True,
        "started_at": datetime.now().isoformat(),
        "total": len(nr_list),
        "done": 0,
        "errors": 0,
        "current": None,
        "results": {},
    }

    def _save_status() -> None:
        try:
            with open(NR_INDEXING_STATUS_FILE, "w") as f:
                json.dump(status, f)
        except Exception:
            pass

    _save_status()

    for nr in nr_list:
        pdf_path = os.path.join(nrs_dir, f"NR-{nr:02d}.pdf")
        status["current"] = f"NR-{nr:02d}"
        _save_status()

        if not os.path.exists(pdf_path):
            logger.warning("[NR-INDEX] NR-%02d: PDF não encontrado", nr)
            status["results"][str(nr)] = {"status": "not_found"}
            status["done"] += 1
            _save_status()
            continue

        try:
            meta = {
                "nr_number": nr,
                "doc_type": "norma_regulamentadora",
                "source": "MTE-oficial",
                "source_file": f"NR-{nr:02d}.pdf",
                "document_name": f"NR-{nr:02d}",
                "source_type": "local_pdf",
                "extraction_method": "pypdf",
                "file_type": "application/pdf",
            }
            before = qa_instance.vector_db._collection.count()
            qa_instance.process_document_to_chroma(
                file_path=pdf_path,
                document_name=f"NR-{nr:02d}.pdf",
                source="MTE-oficial",
                file_type="application/pdf",
                additional_metadata=meta,
            )
            after = qa_instance.vector_db._collection.count()
            added = after - before
            logger.info("[NR-INDEX] NR-%02d: OK, +%d chunks (total: %d)", nr, added, after)
            status["results"][str(nr)] = {"status": "ok", "chunks_added": added}
        except Exception as exc:
            logger.error("[NR-INDEX] NR-%02d: ERRO — %s", nr, exc, exc_info=True)
            status["results"][str(nr)] = {"status": "error", "error": str(exc)}
            status["errors"] += 1

        status["done"] += 1
        _save_status()

    status["running"] = False
    status["current"] = None
    status["finished_at"] = datetime.now().isoformat()
    _save_status()
    logger.info(
        "[NR-INDEX] Indexamento concluido. %d/%d NRs processadas.",
        status["done"], status["total"],
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def start_nr_indexing_background(qa_instance: Any, nr_list: List[int]) -> bool:
    """Start background NR indexing thread.

    Returns:
        True if the thread was started successfully.
        False if indexing is already running.
    """
    global _nr_indexing_thread
    with _nr_indexing_lock:
        if _nr_indexing_thread is not None and _nr_indexing_thread.is_alive():
            return False
        _nr_indexing_thread = threading.Thread(
            target=_nr_indexing_worker,
            args=(qa_instance, nr_list),
            daemon=True,
            name="nr-indexing",
        )
        _nr_indexing_thread.start()
        logger.info("[NR-INDEX] Background indexing started for %d NRs.", len(nr_list))
        return True


def get_nr_indexing_status() -> Dict[str, Any]:
    """Return current indexing status from the status file."""
    try:
        if os.path.exists(NR_INDEXING_STATUS_FILE):
            with open(NR_INDEXING_STATUS_FILE) as f:
                return json.load(f)
    except Exception:
        pass
    return {}


def is_nr_indexing_running() -> bool:
    """Return True if the background indexing thread is still alive."""
    global _nr_indexing_thread
    return _nr_indexing_thread is not None and _nr_indexing_thread.is_alive()
