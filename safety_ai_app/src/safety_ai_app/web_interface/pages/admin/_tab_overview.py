"""
TAB 1 — Visão Geral do Sistema
Painel de Administração SafetyAI
"""

import logging
import os
from datetime import datetime, timezone
from typing import Any

import streamlit as st

from safety_ai_app.web_interface.pages.admin._helpers import (
    _load_json,
    _CHROMA_DB_DIR,
    _LOG_PATH,
    _RAG_LOGS_DIR,
    _FEATURE_FLAGS_PATH,
    _AI_CONFIG_PATH,
    _human_size,
)

logger = logging.getLogger(__name__)


def _render_metric_card(col: Any, icon: str, value: str, label: str, color: str = "#4ADE80") -> None:
    with col:
        st.markdown(f"""
            <div class="result-card" style="text-align:center; padding:18px 12px;">
                <div style="font-size:1.6em; margin-bottom:4px;">{icon}</div>
                <div style="color:{color}; font-size:1.25em; font-weight:700; margin-bottom:4px;">{value}</div>
                <div style="color:#64748B; font-size:0.78em; line-height:1.3;">{label}</div>
            </div>
        """, unsafe_allow_html=True)


def _tab_overview() -> None:
    st.markdown('<div class="section-title">📊 Métricas do Sistema</div>', unsafe_allow_html=True)

    # ChromaDB doc count
    chroma_count = "–"
    try:
        import chromadb
        client = chromadb.PersistentClient(path=str(_CHROMA_DB_DIR))
        total = sum(col.count() for col in client.list_collections())
        chroma_count = f"{total:,}"
    except Exception:
        chroma_count = "–"

    # Embedding model
    embedding_model = "–"
    sentinel = _CHROMA_DB_DIR / ".embedding_model"
    if sentinel.exists():
        try:
            embedding_model = sentinel.read_text(encoding="utf-8").strip() or "–"
        except Exception:
            pass

    # Warmup status
    warmup_status = "–"
    try:
        from safety_ai_app.nr_rag_qa import is_warmup_complete
        warmup_status = "✅ Pronto" if is_warmup_complete() else "⏳ Aquecendo"
    except Exception:
        warmup_status = "–"

    # Log sizes
    app_log_size = "–"
    rag_log_size = "–"
    try:
        if _LOG_PATH.exists():
            app_log_size = _human_size(_LOG_PATH.stat().st_size)
    except Exception:
        pass
    try:
        if _RAG_LOGS_DIR.exists():
            total_rag = sum(f.stat().st_size for f in _RAG_LOGS_DIR.rglob("*.jsonl"))
            rag_log_size = _human_size(total_rag)
    except Exception:
        pass

    # Last sync
    last_sync = "–"
    sync_ok = "–"
    next_sync = "–"
    try:
        from safety_ai_app.auto_sync_scheduler import get_scheduler
        status = get_scheduler().get_status()
        if status.get("last_run_time"):
            dt = datetime.fromtimestamp(status["last_run_time"], tz=timezone.utc)
            last_sync = dt.strftime("%d/%m/%Y %H:%M")
        sync_ok = "✅ OK" if status.get("last_run_success") else "❌ Falhou"
        if status.get("next_run_time"):
            dt2 = datetime.fromtimestamp(status["next_run_time"], tz=timezone.utc)
            next_sync = dt2.strftime("%d/%m/%Y %H:%M")
    except Exception:
        pass

    # Last AI evaluation
    last_eval = "–"
    try:
        import json
        from pathlib import Path
        results_dir = _AI_CONFIG_PATH.parent / "eval" / "results"
        if results_dir.exists():
            files = sorted(results_dir.glob("eval_*.json"), reverse=True)
            if files:
                with files[0].open(encoding="utf-8") as f:
                    rpt = json.load(f)
                agg = rpt.get("aggregate_metrics", {})
                score = sum(agg.values()) / len(agg) if agg else 0
                last_eval = f"{int(score*100)}%"
    except Exception:
        pass

    # Active AI model
    ai_model = os.environ.get("OPENROUTER_MODEL", "–")
    if ai_model == "–":
        cfg = _load_json(_AI_CONFIG_PATH, {})
        ai_model = cfg.get("model", "–")

    row1 = st.columns(3)
    _render_metric_card(row1[0], "📚", chroma_count, "Documentos na Base de Conhecimento")
    _render_metric_card(row1[1], "🔄", f"{last_sync}", f"Última Sincronização · {sync_ok}")
    _render_metric_card(row1[2], "⏰", next_sync, "Próxima Sincronização")

    st.markdown("")
    row2 = st.columns(3)
    _render_metric_card(row2[0], "🤖", last_eval, "Score da Última Avaliação de IA")
    _render_metric_card(row2[1], "⚡", warmup_status, "Estado do Warmup")
    _render_metric_card(row2[2], "🧠", embedding_model[:28] if len(embedding_model) > 28 else embedding_model, "Modelo de Embeddings Activo")

    st.markdown("")
    row3 = st.columns(3)
    _render_metric_card(row3[0], "📝", app_log_size, "Tamanho do Log da Aplicação")
    _render_metric_card(row3[1], "📊", rag_log_size, "Tamanho dos Logs RAG")
    _render_metric_card(row3[2], "🌐", ai_model[:28] if len(ai_model) > 28 else ai_model, "Modelo de IA Activo")

    st.markdown('<div class="section-title" style="margin-top:24px;">⚙️ Estado das Flags de Funcionalidade</div>', unsafe_allow_html=True)
    flags = _load_json(_FEATURE_FLAGS_PATH, {})
    if flags:
        fcols = st.columns(5)
        for i, (key, val) in enumerate(flags.items()):
            with fcols[i % 5]:
                badge = "🟢" if val else "🔴"
                st.markdown(f"""
                    <div class="result-card" style="text-align:center; padding:10px 8px; margin-bottom:8px;">
                        <div style="font-size:1.1em;">{badge}</div>
                        <div style="color:#CBD5E1; font-size:0.75em; margin-top:2px;">{key.replace('_', ' ').title()}</div>
                    </div>
                """, unsafe_allow_html=True)
