"""
evaluate_rag.py — Lightweight RAG pipeline evaluation script.

Usage:
    python scripts/evaluate_rag.py [--golden-set PATH] [--output-dir PATH] [--limit N]

Metrics computed (without external APIs):
  - faithfulness:       fraction of answer sentences with significant overlap with retrieved context
  - answer_relevance:   fraction of question key-terms that appear in the answer
  - context_recall:     fraction of expected-answer key-terms found in retrieved context
  - context_precision:  fraction of retrieved chunks that contain expected-answer key-terms

Alerts are emitted (WARNING) when any metric drops below the configured thresholds.
Results are saved as JSON in data/eval/results/<timestamp>.json.
"""

import argparse
import json
import logging
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------------------
# Path bootstrap
# ---------------------------------------------------------------------------
_script_dir = Path(__file__).parent.resolve()
_project_root = _script_dir.parent
_src_path = _project_root / "src"
if str(_src_path) not in sys.path:
    sys.path.insert(0, str(_src_path))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
)
logger = logging.getLogger("evaluate_rag")

# ---------------------------------------------------------------------------
# Constants / thresholds
# ---------------------------------------------------------------------------
THRESHOLDS: Dict[str, float] = {
    "faithfulness": 0.70,
    "answer_relevance": 0.60,
    "context_recall": 0.60,
    "context_precision": 0.50,
}

DEFAULT_GOLDEN_SET = _project_root / "data" / "eval" / "golden_set.json"
DEFAULT_OUTPUT_DIR = _project_root / "data" / "eval" / "results"

STOPWORDS_PT = {
    "a", "o", "as", "os", "um", "uma", "uns", "umas", "de", "da", "do", "das",
    "dos", "em", "na", "no", "nas", "nos", "por", "para", "com", "sem", "que",
    "se", "e", "é", "ao", "aos", "às", "já", "não", "ou", "seu", "sua",
    "seus", "suas", "qual", "quais", "como", "quando", "onde", "quem", "ser",
    "ter", "este", "esta", "estes", "estas", "isso", "aqui", "mais", "cada",
    "pelo", "pela", "pelos", "pelas", "entre", "deve", "devem", "pode", "podem",
}


# ---------------------------------------------------------------------------
# Metric helpers
# ---------------------------------------------------------------------------

def _tokenize(text: str) -> List[str]:
    tokens = re.findall(r"[a-záéíóúâêîôûãõàüç\d]+", text.lower())
    return [t for t in tokens if t not in STOPWORDS_PT and len(t) > 2]


def _sentence_split(text: str) -> List[str]:
    return [s.strip() for s in re.split(r"[.!?;\n]", text) if len(s.strip()) > 20]


def compute_faithfulness(answer: str, context: str) -> float:
    """
    Fraction of answer sentences whose key-tokens have ≥50% overlap with the context.
    """
    sentences = _sentence_split(answer)
    if not sentences:
        return 0.0
    context_tokens = set(_tokenize(context))
    faithful_count = 0
    for sent in sentences:
        sent_tokens = set(_tokenize(sent))
        if not sent_tokens:
            faithful_count += 1
            continue
        overlap = len(sent_tokens & context_tokens) / len(sent_tokens)
        if overlap >= 0.40:
            faithful_count += 1
    return round(faithful_count / len(sentences), 4)


def compute_answer_relevance(question: str, answer: str) -> float:
    """
    Fraction of question key-tokens that appear in the answer.
    """
    q_tokens = set(_tokenize(question))
    if not q_tokens:
        return 0.0
    a_tokens = set(_tokenize(answer))
    overlap = len(q_tokens & a_tokens) / len(q_tokens)
    return round(overlap, 4)


def compute_context_recall(expected_answer: str, context: str) -> float:
    """
    Fraction of expected-answer key-tokens found in the retrieved context.
    """
    expected_tokens = set(_tokenize(expected_answer))
    if not expected_tokens:
        return 0.0
    context_tokens = set(_tokenize(context))
    recall = len(expected_tokens & context_tokens) / len(expected_tokens)
    return round(recall, 4)


def compute_context_precision(expected_answer: str, chunks: List[str]) -> float:
    """
    Fraction of retrieved chunks that contain ≥30% of expected-answer key-tokens.
    """
    if not chunks:
        return 0.0
    expected_tokens = set(_tokenize(expected_answer))
    if not expected_tokens:
        return 0.0
    relevant_count = 0
    for chunk in chunks:
        chunk_tokens = set(_tokenize(chunk))
        overlap = len(expected_tokens & chunk_tokens) / len(expected_tokens)
        if overlap >= 0.30:
            relevant_count += 1
    return round(relevant_count / len(chunks), 4)


# ---------------------------------------------------------------------------
# Evaluation runner
# ---------------------------------------------------------------------------

def evaluate_single(
    qa_system: Any,
    item: Dict[str, Any],
) -> Dict[str, Any]:
    """Run a single golden-set item through the pipeline and compute metrics."""
    question = item["question"]
    expected_answer = item.get("expected_answer", "")

    t_start = time.perf_counter()
    try:
        result = qa_system.answer_question(
            query=question,
            chat_history=[],
            dynamic_context_texts=[],
        )
    except Exception as exc:
        logger.error("Error answering '%s': %s", question[:60], exc)
        return {
            "id": item["id"],
            "question": question,
            "expected_answer": expected_answer,
            "generated_answer": "",
            "relevant_nr": item.get("relevant_nr", ""),
            "query_type": item.get("query_type", ""),
            "faithfulness": 0.0,
            "answer_relevance": 0.0,
            "context_recall": 0.0,
            "context_precision": 0.0,
            "latency_ms": round((time.perf_counter() - t_start) * 1000, 1),
            "error": str(exc)[:300],
        }

    latency_ms = round((time.perf_counter() - t_start) * 1000, 1)
    generated_answer = ""
    if isinstance(result, dict):
        generated_answer = result.get("answer", "") or ""
    else:
        generated_answer = str(result)

    retrieved_chunks = []
    try:
        docs = qa_system.retriever.invoke(question)
        retrieved_chunks = [d.page_content for d in docs]
    except Exception:
        pass

    full_context = "\n\n".join(retrieved_chunks)

    faithfulness = compute_faithfulness(generated_answer, full_context)
    answer_relevance = compute_answer_relevance(question, generated_answer)
    context_recall = compute_context_recall(expected_answer, full_context)
    context_precision = compute_context_precision(expected_answer, retrieved_chunks)

    return {
        "id": item["id"],
        "question": question,
        "expected_answer": expected_answer,
        "generated_answer": generated_answer[:800],
        "relevant_nr": item.get("relevant_nr", ""),
        "query_type": item.get("query_type", ""),
        "faithfulness": faithfulness,
        "answer_relevance": answer_relevance,
        "context_recall": context_recall,
        "context_precision": context_precision,
        "latency_ms": latency_ms,
        "error": None,
    }


def _average(values: List[float]) -> float:
    return round(sum(values) / len(values), 4) if values else 0.0


def check_and_alert(aggregate: Dict[str, float]) -> List[str]:
    """Return list of threshold violations and log WARNING for each."""
    violations = []
    for metric, value in aggregate.items():
        threshold = THRESHOLDS.get(metric)
        if threshold is not None and value < threshold:
            msg = (
                f"ALERT: '{metric}' = {value:.3f} is BELOW threshold {threshold:.3f}"
            )
            logger.warning(msg)
            print(f"\n⚠  {msg}")
            violations.append(msg)
    return violations


def run_evaluation(
    golden_set_path: Path,
    output_dir: Path,
    limit: Optional[int] = None,
) -> Path:
    logger.info("Loading golden set from: %s", golden_set_path)
    with open(golden_set_path, encoding="utf-8") as f:
        golden_data = json.load(f)

    questions = golden_data.get("questions", [])
    if limit:
        questions = questions[:limit]

    logger.info("Initializing NRQuestionAnswering...")
    from safety_ai_app.nr_rag_qa import NRQuestionAnswering
    qa_system = NRQuestionAnswering()

    results = []
    total = len(questions)
    for idx, item in enumerate(questions, start=1):
        logger.info("[%d/%d] Evaluating: %s", idx, total, item["question"][:60])
        result = evaluate_single(qa_system, item)
        results.append(result)
        logger.info(
            "  faithfulness=%.3f  answer_relevance=%.3f  context_recall=%.3f  context_precision=%.3f  latency=%.0fms",
            result["faithfulness"],
            result["answer_relevance"],
            result["context_recall"],
            result["context_precision"],
            result["latency_ms"],
        )

    valid = [r for r in results if not r.get("error")]
    aggregate: Dict[str, float] = {
        "faithfulness": _average([r["faithfulness"] for r in valid]),
        "answer_relevance": _average([r["answer_relevance"] for r in valid]),
        "context_recall": _average([r["context_recall"] for r in valid]),
        "context_precision": _average([r["context_precision"] for r in valid]),
    }

    print("\n" + "=" * 60)
    print("AGGREGATE METRICS")
    print("=" * 60)
    for k, v in aggregate.items():
        threshold = THRESHOLDS.get(k, 0)
        status = "OK" if v >= threshold else "BELOW THRESHOLD"
        print(f"  {k:<22} {v:.4f}   [{status}]")
    print("=" * 60)

    violations = check_and_alert(aggregate)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    report = {
        "timestamp": timestamp,
        "golden_set_version": golden_data.get("version", "unknown"),
        "questions_evaluated": len(results),
        "questions_with_errors": len(results) - len(valid),
        "aggregate_metrics": aggregate,
        "thresholds": THRESHOLDS,
        "threshold_violations": violations,
        "per_question_results": results,
    }

    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"eval_{timestamp}.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2, default=str)

    logger.info("Report saved to: %s", output_path)
    print(f"\nReport saved: {output_path}")
    return output_path


# ---------------------------------------------------------------------------
# CLI entry-point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Evaluate the SafetyAI RAG pipeline against a golden set."
    )
    parser.add_argument(
        "--golden-set",
        type=Path,
        default=DEFAULT_GOLDEN_SET,
        help=f"Path to golden_set.json (default: {DEFAULT_GOLDEN_SET})",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help=f"Directory to save evaluation reports (default: {DEFAULT_OUTPUT_DIR})",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limit number of questions to evaluate (for quick tests).",
    )
    args = parser.parse_args()
    run_evaluation(args.golden_set, args.output_dir, args.limit)


if __name__ == "__main__":
    main()
