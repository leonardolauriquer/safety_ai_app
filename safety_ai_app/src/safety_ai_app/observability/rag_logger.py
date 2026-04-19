"""
Structured logger for the RAG pipeline.

Logs each call to answer_question() with:
  - original query
  - expanded query (if applicable)
  - retrieved chunks (source + score)
  - model used
  - latency per pipeline stage
  - response size
  - alert when any metric drops below configured threshold
"""

import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("safety_ai.rag")

_LOG_DIR = Path(__file__).parents[3] / "data" / "rag_logs"

ALERT_THRESHOLDS: Dict[str, float] = {
    "faithfulness": 0.70,
    "answer_relevance": 0.60,
    "context_recall": 0.60,
    "context_precision": 0.50,
}


class RAGLogger:
    """
    Lightweight structured logger for the SafetyAI RAG pipeline.

    Usage::

        rag_log = RAGLogger()
        call_id = rag_log.start_call(query="...")
        ...
        rag_log.log_retrieval(call_id, chunks=[...])
        rag_log.log_generation(call_id, answer="...", latency_ms=...)
        rag_log.finish_call(call_id)
    """

    def __init__(self, log_dir: Optional[Path] = None):
        self._log_dir = Path(log_dir) if log_dir else _LOG_DIR
        self._log_dir.mkdir(parents=True, exist_ok=True)
        self._active: Dict[str, Dict[str, Any]] = {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def start_call(self, query: str, session_id: str = "unknown") -> str:
        """Begin tracking a RAG pipeline call. Returns a unique call_id."""
        call_id = f"{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')}_{session_id[:8]}"
        self._active[call_id] = {
            "call_id": call_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "session_id": session_id,
            "query": query,
            "query_expanded": None,
            "retrieved_chunks": [],
            "model_used": None,
            "latency_retrieval_ms": None,
            "latency_generation_ms": None,
            "latency_total_ms": None,
            "answer_length_chars": None,
            "error": None,
            "_t_start": time.perf_counter(),
            "_t_retrieval_start": None,
            "_t_generation_start": None,
        }
        return call_id

    def set_expanded_query(self, call_id: str, expanded_query: str) -> None:
        if call_id not in self._active:
            return
        self._active[call_id]["query_expanded"] = expanded_query

    def start_retrieval(self, call_id: str) -> None:
        if call_id not in self._active:
            return
        self._active[call_id]["_t_retrieval_start"] = time.perf_counter()

    def log_retrieval(
        self,
        call_id: str,
        chunks: List[Dict[str, Any]],
    ) -> None:
        """
        Log retrieved chunks.

        Each chunk dict should have at minimum:
          - source: str  (document name or path)
          - score: float (similarity score, 0–1 or distance)
          - content_preview: str (first 200 chars of the chunk text)
        """
        if call_id not in self._active:
            return
        entry = self._active[call_id]
        t_now = time.perf_counter()
        if entry.get("_t_retrieval_start"):
            entry["latency_retrieval_ms"] = round(
                (t_now - entry["_t_retrieval_start"]) * 1000, 1
            )
        sanitized_chunks = []
        for c in chunks:
            sanitized_chunks.append({
                "source": str(c.get("source", "unknown"))[:200],
                "score": round(float(c.get("score", 0.0)), 4),
                "content_preview": str(c.get("content_preview", ""))[:200],
            })
        entry["retrieved_chunks"] = sanitized_chunks

    def start_generation(self, call_id: str, model_used: str = "unknown") -> None:
        if call_id not in self._active:
            return
        entry = self._active[call_id]
        entry["_t_generation_start"] = time.perf_counter()
        entry["model_used"] = model_used

    def log_generation(
        self,
        call_id: str,
        answer: str,
    ) -> None:
        if call_id not in self._active:
            return
        entry = self._active[call_id]
        t_now = time.perf_counter()
        if entry.get("_t_generation_start"):
            entry["latency_generation_ms"] = round(
                (t_now - entry["_t_generation_start"]) * 1000, 1
            )
        entry["answer_length_chars"] = len(answer)

    def finish_call(self, call_id: str, error: Optional[str] = None) -> None:
        """Finalize the call record and flush to disk."""
        if call_id not in self._active:
            return
        entry = self._active.pop(call_id)
        t_now = time.perf_counter()
        entry["latency_total_ms"] = round(
            (t_now - entry["_t_start"]) * 1000, 1
        )
        if error:
            entry["error"] = str(error)[:500]

        record = {k: v for k, v in entry.items() if not k.startswith("_")}
        self._write_record(record)
        self._log_to_logger(record)

    def log_metrics_alert(self, metrics: Dict[str, float]) -> None:
        """Emit WARNING logs when any metric drops below its threshold."""
        for metric_name, value in metrics.items():
            threshold = ALERT_THRESHOLDS.get(metric_name)
            if threshold is not None and value < threshold:
                logger.warning(
                    "[RAG ALERT] Metric '%s' = %.3f is below threshold %.3f",
                    metric_name,
                    value,
                    threshold,
                )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _write_record(self, record: Dict[str, Any]) -> None:
        log_file = self._log_dir / f"rag_{datetime.now(timezone.utc).strftime('%Y%m%d')}.jsonl"
        try:
            with log_file.open("a", encoding="utf-8") as f:
                f.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")
        except Exception as exc:
            logger.error("RAGLogger: failed to write record: %s", exc)

    def _log_to_logger(self, record: Dict[str, Any]) -> None:
        logger.info(
            "RAG call finished | query='%s...' | chunks=%d | total_ms=%s | answer_len=%s | error=%s",
            (record.get("query") or "")[:60],
            len(record.get("retrieved_chunks") or []),
            record.get("latency_total_ms"),
            record.get("answer_length_chars"),
            record.get("error"),
        )


_default_instance: Optional[RAGLogger] = None


def get_rag_logger() -> RAGLogger:
    global _default_instance
    if _default_instance is None:
        _default_instance = RAGLogger()
    return _default_instance
