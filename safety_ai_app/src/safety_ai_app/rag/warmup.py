import logging
import threading
from typing import Optional
from .retriever import _get_reranker, RERANKER_MODEL_NAME

logger = logging.getLogger(__name__)

_warmup_done = threading.Event()
_warmup_thread: Optional[threading.Thread] = None

def _warmup_worker() -> None:
    """Pre-load the cross-encoder reranker in the background."""
    _reranker_ok = False
    try:
        logger.info("[WARMUP] Pre-loading cross-encoder reranker '%s'…", RERANKER_MODEL_NAME)
        result = _get_reranker()
        if result is not None:
            _reranker_ok = True
            logger.info("[WARMUP] Reranker loaded successfully.")
        else:
            logger.warning("[WARMUP] Reranker unavailable after pre-load attempt.")
    except Exception as exc:
        logger.warning("[WARMUP] Could not pre-load reranker: %s", exc)

    _warmup_done.set()
    status = "complete" if _reranker_ok else "finished (reranker unavailable)"
    logger.info("[WARMUP] Model warmup %s.", status)


def start_model_warmup() -> None:
    """Start background model pre-loading. Safe to call multiple times."""
    global _warmup_thread
    if _warmup_done.is_set():
        return
    if _warmup_thread is not None and _warmup_thread.is_alive():
        return
    _warmup_thread = threading.Thread(
        target=_warmup_worker, daemon=True, name="model-warmup"
    )
    _warmup_thread.start()
    logger.info("[WARMUP] Background model warmup thread started.")


def is_warmup_complete() -> bool:
    """Return True if the reranker background warmup has finished."""
    return _warmup_done.is_set()
