"""
Página de Avaliação de IA — Painel administrativo exclusivo para administradores.

Exibe:
  - Métricas agregadas da avaliação RAG mais recente
  - Gráficos de tendência histórica por métrica
  - Tabela por pergunta com destaque de falhas (baixa faithfulness / answer relevance)
  - Link para executar nova avaliação via CLI
"""

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import streamlit as st

from safety_ai_app.theme_config import get_icon, _get_material_icon_html
from safety_ai_app.web_interface.shared_styles import inject_glass_styles

logger = logging.getLogger(__name__)

_PROJECT_ROOT = Path(__file__).parents[4]
_RESULTS_DIR = _PROJECT_ROOT / "data" / "eval" / "results"
_GOLDEN_SET_PATH = _PROJECT_ROOT / "data" / "eval" / "golden_set.json"

THRESHOLDS: Dict[str, float] = {
    "faithfulness": 0.70,
    "answer_relevance": 0.60,
    "context_recall": 0.60,
    "context_precision": 0.50,
}

METRIC_LABELS: Dict[str, str] = {
    "faithfulness": "Fidelidade ao Contexto",
    "answer_relevance": "Relevância da Resposta",
    "context_recall": "Cobertura do Contexto",
    "context_precision": "Precisão do Contexto",
}

METRIC_DESCRIPTIONS: Dict[str, str] = {
    "faithfulness": "Fração das frases da resposta ancoradas no contexto recuperado.",
    "answer_relevance": "Fração dos termos da pergunta presentes na resposta.",
    "context_recall": "Fração dos termos da resposta esperada encontrados no contexto.",
    "context_precision": "Fração dos chunks recuperados que contêm informação relevante.",
}

ADMIN_EMAILS_ENV = "ADMIN_EMAILS"


# ---------------------------------------------------------------------------
# Admin check
# ---------------------------------------------------------------------------

def _is_admin() -> bool:
    """Return True if the current user is an administrator."""
    if st.session_state.get("is_admin"):
        return True
    user_email = st.session_state.get("user_email", "").strip().lower()
    if not user_email:
        return False
    admin_emails_raw = os.environ.get(ADMIN_EMAILS_ENV, "")
    admin_emails = {e.strip().lower() for e in admin_emails_raw.split(",") if e.strip()}
    return user_email in admin_emails


# ---------------------------------------------------------------------------
# Data loading helpers
# ---------------------------------------------------------------------------

def _load_result_files() -> List[Tuple[str, Dict[str, Any]]]:
    """Load all evaluation result JSON files, sorted newest first."""
    _RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    files = sorted(_RESULTS_DIR.glob("eval_*.json"), reverse=True)
    results = []
    for f in files:
        try:
            with f.open(encoding="utf-8") as fh:
                data = json.load(fh)
            results.append((f.name, data))
        except Exception as exc:
            logger.warning("Failed to load eval result %s: %s", f.name, exc)
    return results


def _format_timestamp(ts: str) -> str:
    try:
        dt = datetime.strptime(ts, "%Y%m%dT%H%M%SZ")
        return dt.strftime("%d/%m/%Y %H:%M UTC")
    except Exception:
        return ts


def _metric_color(value: float, threshold: float) -> str:
    if value >= threshold:
        return "#4ADE80"
    if value >= threshold * 0.85:
        return "#F59E0B"
    return "#EF4444"


# ---------------------------------------------------------------------------
# Render helpers
# ---------------------------------------------------------------------------

def _render_metric_card(label: str, value: float, threshold: float, description: str) -> None:
    color = _metric_color(value, threshold)
    pct = int(value * 100)
    status = "✓" if value >= threshold else "✗"
    st.markdown(f"""
        <div style="
            background: rgba(15,23,42,0.9);
            border: 1px solid {color}44;
            border-left: 4px solid {color};
            border-radius: 12px;
            padding: 1rem 1.2rem;
            margin-bottom: 0.5rem;
        ">
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <span style="color:#94A3B8; font-size:0.85rem;">{label}</span>
                <span style="color:{color}; font-size:1.4rem; font-weight:800;">{status} {pct}%</span>
            </div>
            <div style="
                background:#1E293B;
                border-radius:6px;
                height:8px;
                margin-top:0.5rem;
                overflow:hidden;
            ">
                <div style="
                    width:{pct}%;
                    height:8px;
                    background:{color};
                    border-radius:6px;
                    transition:width 0.5s ease;
                "></div>
            </div>
            <div style="color:#64748B; font-size:0.75rem; margin-top:0.4rem;">{description}</div>
            <div style="color:#475569; font-size:0.72rem; margin-top:0.2rem;">
                Limiar: {int(threshold * 100)}%
            </div>
        </div>
    """, unsafe_allow_html=True)


def _render_aggregate_metrics(report: Dict[str, Any]) -> None:
    agg = report.get("aggregate_metrics", {})
    violations = report.get("threshold_violations", [])

    if violations:
        st.warning(
            f"⚠ **{len(violations)} métrica(s) abaixo do limiar** nesta avaliação. "
            "Veja os detalhes abaixo."
        )

    cols = st.columns(4)
    for col, (key, label) in zip(cols, METRIC_LABELS.items()):
        with col:
            _render_metric_card(
                label=label,
                value=agg.get(key, 0.0),
                threshold=THRESHOLDS[key],
                description=METRIC_DESCRIPTIONS[key],
            )


def _render_trend_chart(all_results: List[Tuple[str, Dict[str, Any]]]) -> None:
    if len(all_results) < 2:
        st.info("São necessárias ao menos 2 avaliações para exibir o gráfico de tendência.")
        return

    import pandas as pd

    rows = []
    for _filename, report in reversed(all_results[-10:]):
        ts = report.get("timestamp", "")
        agg = report.get("aggregate_metrics", {})
        rows.append({
            "Data": _format_timestamp(ts),
            "Fidelidade": agg.get("faithfulness", 0),
            "Relevância Resposta": agg.get("answer_relevance", 0),
            "Cobertura Contexto": agg.get("context_recall", 0),
            "Precisão Contexto": agg.get("context_precision", 0),
        })

    df = pd.DataFrame(rows).set_index("Data")
    st.markdown(f'<div class="section-title">{_get_material_icon_html("trending_up")} Tendência Histórica (últimas 10 avaliações)</div>', unsafe_allow_html=True)
    st.line_chart(df, height=300)


def _render_per_question_table(report: Dict[str, Any]) -> None:
    per_q = report.get("per_question_results", [])
    if not per_q:
        st.info("Nenhum resultado por pergunta disponível.")
        return

    st.markdown(f'<div class="section-title">{_get_material_icon_html("quiz")} Resultados por Pergunta</div>', unsafe_allow_html=True)

    failures = [
        r for r in per_q
        if r.get("faithfulness", 1.0) < THRESHOLDS["faithfulness"]
        or r.get("answer_relevance", 1.0) < THRESHOLDS["answer_relevance"]
    ]
    if failures:
        with st.expander(f"⚠ {len(failures)} perguntas com baixo desempenho (expandir para ver)", expanded=False):
            for r in failures:
                faith_color = _metric_color(r.get("faithfulness", 0), THRESHOLDS["faithfulness"])
                rel_color = _metric_color(r.get("answer_relevance", 0), THRESHOLDS["answer_relevance"])
                st.markdown(f"""
                    <div style="
                        border-left: 4px solid #EF4444;
                        padding: 0.8rem 1rem;
                        margin-bottom: 0.8rem;
                        background: rgba(239,68,68,0.05);
                        border-radius: 0 8px 8px 0;
                    ">
                        <div style="color:#CBD5E1; font-weight:600; margin-bottom:0.3rem;">
                            [{r.get('relevant_nr','')} · {r.get('query_type','')}] {r.get('question','')[:120]}
                        </div>
                        <div style="display:flex; gap:1rem; margin:0.3rem 0; font-size:0.85rem;">
                            <span style="color:{faith_color};">Fidelidade: {int(r.get('faithfulness',0)*100)}%</span>
                            <span style="color:{rel_color};">Relevância: {int(r.get('answer_relevance',0)*100)}%</span>
                            <span style="color:#94A3B8;">Latência: {r.get('latency_ms',0):.0f}ms</span>
                        </div>
                        <details style="margin-top:0.3rem;">
                            <summary style="color:#64748B; cursor:pointer; font-size:0.8rem;">Ver resposta gerada</summary>
                            <div style="color:#94A3B8; font-size:0.82rem; margin-top:0.4rem; padding:0.5rem; background:rgba(0,0,0,0.3); border-radius:6px;">
                                {(r.get('generated_answer','') or 'Sem resposta')[:600]}
                            </div>
                        </details>
                    </div>
                """, unsafe_allow_html=True)

    import pandas as pd

    rows = []
    for r in per_q:
        faith = r.get("faithfulness", 0)
        rel = r.get("answer_relevance", 0)
        recall = r.get("context_recall", 0)
        prec = r.get("context_precision", 0)
        rows.append({
            "ID": r.get("id", ""),
            "NR": r.get("relevant_nr", ""),
            "Tipo": r.get("query_type", ""),
            "Fidelidade": f"{int(faith*100)}%",
            "Relevância": f"{int(rel*100)}%",
            "Cobertura": f"{int(recall*100)}%",
            "Precisão": f"{int(prec*100)}%",
            "Latência (ms)": int(r.get("latency_ms", 0)),
            "Erro": "Sim" if r.get("error") else "",
        })
    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True, height=400)


def _render_golden_set_info() -> None:
    if not _GOLDEN_SET_PATH.exists():
        st.warning("Golden set não encontrado em: " + str(_GOLDEN_SET_PATH))
        return
    try:
        with _GOLDEN_SET_PATH.open(encoding="utf-8") as f:
            gs = json.load(f)
        questions = gs.get("questions", [])
        by_nr: Dict[str, int] = {}
        by_type: Dict[str, int] = {}
        for q in questions:
            nr = q.get("relevant_nr", "Outro")
            qt = q.get("query_type", "unknown")
            by_nr[nr] = by_nr.get(nr, 0) + 1
            by_type[qt] = by_type.get(qt, 0) + 1

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total de perguntas", len(questions))
        with col2:
            st.metric("NRs cobertas", len(by_nr))
        with col3:
            st.metric("Versão do golden set", gs.get("version", "?"))

        col_a, col_b = st.columns(2)
        with col_a:
            st.caption("Por NR")
            for nr, count in sorted(by_nr.items(), key=lambda x: x[1], reverse=True):
                st.progress(count / len(questions), text=f"{nr}: {count}")
        with col_b:
            st.caption("Por tipo de consulta")
            for qt, count in sorted(by_type.items(), key=lambda x: x[1], reverse=True):
                st.progress(count / len(questions), text=f"{qt}: {count}")
    except Exception as exc:
        st.error(f"Erro ao carregar golden set: {exc}")


# ---------------------------------------------------------------------------
# Main page renderer
# ---------------------------------------------------------------------------

def render_page() -> None:
    inject_glass_styles()

    st.markdown(
        f'<h1 class="neon-title">{_get_material_icon_html("ai_evaluation")} Avaliação do Pipeline de IA</h1>',
        unsafe_allow_html=True,
    )

    if not _is_admin():
        st.error(
            "Acesso restrito. Esta página é exclusiva para administradores. "
            "Se você é administrador, verifique se sua conta está configurada corretamente."
        )
        st.stop()
        return

    st.markdown(
        "<p style='color:#94A3B8; text-align:center; margin-bottom:1.5rem;'>"
        "Métricas de qualidade do pipeline RAG geradas pelo conjunto de avaliação (golden set).</p>",
        unsafe_allow_html=True,
    )

    tab1, tab2, tab3 = st.tabs([
        "📊 Última Avaliação",
        "📈 Tendência Histórica",
        "📋 Golden Set",
    ])

    all_results = _load_result_files()

    with tab1:
        if not all_results:
            st.info(
                "Nenhuma avaliação encontrada ainda. Execute o script de avaliação para gerar resultados:\n\n"
                "```bash\n"
                "python safety_ai_app/scripts/evaluate_rag.py\n"
                "```\n\n"
                f"Os resultados serão salvos em: `{_RESULTS_DIR}`"
            )
        else:
            _filename, latest = all_results[0]
            ts = latest.get("timestamp", "")
            n_eval = latest.get("questions_evaluated", 0)
            n_err = latest.get("questions_with_errors", 0)

            col_info1, col_info2, col_info3 = st.columns(3)
            col_info1.metric("Data da avaliação", _format_timestamp(ts))
            col_info2.metric("Perguntas avaliadas", n_eval)
            col_info3.metric("Com erro", n_err, delta_color="inverse")

            _render_aggregate_metrics(latest)
            _render_per_question_table(latest)

    with tab2:
        if not all_results:
            st.info("Nenhuma avaliação encontrada ainda.")
        else:
            _render_trend_chart(all_results)

            st.markdown(f'<div class="section-title">{_get_material_icon_html("history")} Histórico de Avaliações</div>', unsafe_allow_html=True)
            rows = []
            for fname, report in all_results:
                agg = report.get("aggregate_metrics", {})
                rows.append({
                    "Arquivo": fname,
                    "Data": _format_timestamp(report.get("timestamp", "")),
                    "Perguntas": report.get("questions_evaluated", 0),
                    "Fidelidade": f"{int(agg.get('faithfulness',0)*100)}%",
                    "Relevância": f"{int(agg.get('answer_relevance',0)*100)}%",
                    "Cobertura": f"{int(agg.get('context_recall',0)*100)}%",
                    "Precisão": f"{int(agg.get('context_precision',0)*100)}%",
                    "Violações": len(report.get("threshold_violations", [])),
                })
            import pandas as pd
            st.dataframe(pd.DataFrame(rows), use_container_width=True)

    with tab3:
        st.markdown(f'<div class="section-title">{_get_material_icon_html("dataset")} Conjunto de Avaliação (Golden Set)</div>', unsafe_allow_html=True)
        st.markdown(
            f"<p style='color:#94A3B8;'>Localização: <code>{_GOLDEN_SET_PATH}</code></p>",
            unsafe_allow_html=True,
        )
        _render_golden_set_info()
        st.markdown(f'<div class="section-title">{_get_material_icon_html("terminal")} Como executar uma nova avaliação</div>', unsafe_allow_html=True)
        st.code(
            "# Avaliação completa (35 perguntas)\n"
            "python safety_ai_app/scripts/evaluate_rag.py\n\n"
            "# Avaliação rápida (5 perguntas)\n"
            "python safety_ai_app/scripts/evaluate_rag.py --limit 5\n\n"
            "# Usando diretório customizado\n"
            "python safety_ai_app/scripts/evaluate_rag.py \\\n"
            "    --golden-set data/eval/golden_set.json \\\n"
            "    --output-dir data/eval/results/",
            language="bash",
        )
        st.markdown(
            "<p style='color:#64748B; font-size:0.85rem;'>"
            "⚠ A avaliação completa requer que o pipeline RAG esteja inicializado e conectado ao LLM. "
            "Execute em ambiente com ChromaDB populado.</p>",
            unsafe_allow_html=True,
        )
