"""
Standalone NR PDF indexer — run as subprocess by server.py after Streamlit warms up.
Indexes all MTE official NR PDFs that are not yet in ChromaDB.
"""
import sys
import os
import time
import json
import logging

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
logging.getLogger().setLevel(logging.ERROR)

try:
    import torch
    torch.set_num_threads(2)
except Exception:
    pass

_PACKAGE_DIR = os.path.dirname(os.path.abspath(__file__))   # .../safety_ai_app/src/safety_ai_app
_SRC_DIR = os.path.dirname(_PACKAGE_DIR)                      # .../safety_ai_app/src
_APP_ROOT = os.path.dirname(_SRC_DIR)                         # .../safety_ai_app

STATUS_FILE = os.path.join(_APP_ROOT, "data", "nr_indexing_status.json")
NRS_DIR = os.path.join(_APP_ROOT, "data", "nrs")

PENDING_NRS = list(range(1, 33))
DRIVE_NRS = {33, 34, 35, 36, 37, 38}


def log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def save_status(st: dict) -> None:
    try:
        with open(STATUS_FILE, "w") as f:
            json.dump(st, f)
    except Exception:
        pass


def get_already_indexed(collection) -> set:
    try:
        res = collection.get(where={"source": "MTE-oficial"}, include=["metadatas"])
        indexed = set()
        for m in res.get("metadatas", []):
            nr = m.get("nr_number")
            if isinstance(nr, int):
                indexed.add(nr)
            elif isinstance(nr, str):
                try:
                    indexed.add(int(nr.replace("NR-", "").lstrip("0") or "0"))
                except ValueError:
                    pass
        return indexed
    except Exception:
        return set()


def main() -> None:
    log("NR Indexer Runner iniciado")
    log(f"ChromaDB dir: {NRS_DIR}")

    log("Carregando NRQuestionAnswering...")
    t0 = time.time()
    try:
        from safety_ai_app.nr_rag_qa import NRQuestionAnswering, CHROMADB_PERSIST_DIRECTORY
        qa = NRQuestionAnswering(chroma_persist_directory=CHROMADB_PERSIST_DIRECTORY)
    except Exception as exc:
        log(f"ERRO ao carregar NRQuestionAnswering: {exc}")
        sys.exit(1)

    log(f"Modelo carregado em {time.time() - t0:.1f}s. Chunks iniciais: {qa.vector_db._collection.count()}")

    already = get_already_indexed(qa.vector_db._collection)
    pending = [
        nr for nr in PENDING_NRS
        if nr not in already
        and nr not in DRIVE_NRS
        and os.path.exists(os.path.join(NRS_DIR, f"NR-{nr:02d}.pdf"))
    ]

    log(f"Já indexadas (MTE): {sorted(already)}")
    log(f"Pendentes: {pending}")

    if not pending:
        log("Nenhuma NR pendente. Encerrando.")
        return

    status = {
        "running": True,
        "started_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "total": len(pending),
        "done": 0,
        "errors": 0,
        "current": None,
        "results": {},
    }
    save_status(status)

    for nr in pending:
        fname = f"NR-{nr:02d}.pdf"
        fp = os.path.join(NRS_DIR, fname)
        status["current"] = fname
        save_status(status)

        log(f"{fname}: iniciando ({os.path.getsize(fp) // 1024}KB)...")
        t1 = time.time()
        before = qa.vector_db._collection.count()

        try:
            qa.process_document_to_chroma(
                file_path=fp,
                document_name=fname,
                source="MTE-oficial",
                file_type="application/pdf",
                additional_metadata={
                    "nr_number": nr,
                    "doc_type": "norma_regulamentadora",
                    "source": "MTE-oficial",
                    "source_file": fname,
                    "document_name": fname,
                    "source_type": "local_pdf",
                },
            )
            added = qa.vector_db._collection.count() - before
            elapsed = time.time() - t1
            log(f"{fname}: OK +{added} chunks em {elapsed:.1f}s (total: {qa.vector_db._collection.count()})")
            status["results"][str(nr)] = {"status": "ok", "chunks_added": added, "elapsed_s": round(elapsed, 1)}
        except Exception as exc:
            log(f"{fname}: ERRO - {exc}")
            status["results"][str(nr)] = {"status": "error", "error": str(exc)}
            status["errors"] += 1

        status["done"] += 1
        save_status(status)

    status["running"] = False
    status["current"] = None
    status["finished_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    save_status(status)

    final_count = qa.vector_db._collection.count()
    log(f"Indexamento concluído! {status['done']}/{status['total']} NRs. Erros: {status['errors']}. Total chunks: {final_count}")


if __name__ == "__main__":
    main()
