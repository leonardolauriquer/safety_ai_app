"""
TAB 5 — Pipeline de IA
Painel de Administração SafetyAI

Sub-tabs: Última Avaliação, Tendência Histórica, Golden Set, Executar Avaliação, Indexar NRs.
Inclui: NR Update Checker (verificação de atualizações no portal MTE) e controle de indexamento.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import streamlit as st

from safety_ai_app.web_interface.pages.admin._helpers import _DATA_DIR

logger = logging.getLogger(__name__)

_PROJECT_ROOT = _DATA_DIR.parent


# ---------------------------------------------------------------------------
# NR Update Checker
# ---------------------------------------------------------------------------

def _do_download_and_reindex(nr_num: int, pdf_url: str, qa_instance: Any) -> None:
    """Helper: download a single NR PDF and reindex it, showing feedback."""
    from safety_ai_app.nr_update_checker import (
        download_nr_update,
        trigger_reindex_for_nr,
        append_update_history,
    )

    if not pdf_url:
        st.error(f"❌ NR-{nr_num:02d}: URL do PDF não disponível.")
        return

    with st.spinner(f"Baixando NR-{nr_num:02d}..."):
        ok, msg = download_nr_update(nr_num, pdf_url)

    if not ok:
        st.error(f"❌ {msg}")
        append_update_history({
            "timestamp_str": datetime.now(timezone.utc).strftime("%d/%m/%Y %H:%M UTC"),
            "nr_label": f"NR-{nr_num:02d}",
            "result": "❌ Falha no download",
            "detail": msg,
        })
        return

    st.success(f"✅ {msg}")
    logger.info(msg)

    with st.spinner(f"Reindexando NR-{nr_num:02d} no ChromaDB..."):
        ok2, msg2 = trigger_reindex_for_nr(nr_num, qa_instance)

    if ok2:
        st.success(f"✅ {msg2}")
        logger.info(msg2)
        append_update_history({
            "timestamp_str": datetime.now(timezone.utc).strftime("%d/%m/%Y %H:%M UTC"),
            "nr_label": f"NR-{nr_num:02d}",
            "result": "✅ Atualizada e reindexada",
            "detail": f"{msg} | {msg2}",
        })
    else:
        st.warning(f"⚠️ Download OK mas falha na reindexação: {msg2}")
        logger.warning(msg2)
        append_update_history({
            "timestamp_str": datetime.now(timezone.utc).strftime("%d/%m/%Y %H:%M UTC"),
            "nr_label": f"NR-{nr_num:02d}",
            "result": "⚠️ Baixada, reindexação falhou",
            "detail": f"{msg} | {msg2}",
        })

    st.session_state.pop("nr_check_results", None)


def _render_nr_update_checker_section(qa_instance: Any) -> None:
    """Render the 'Verificar Atualizações no Portal MTE' section inside the NR indexing tab."""
    import time as _time

    from safety_ai_app.nr_update_checker import (
        check_nr_updates,
        download_nr_update,
        trigger_reindex_for_nr,
        get_cached_check_results,
        load_update_history,
        invalidate_cache,
        CACHE_TTL_SECONDS,
    )

    st.markdown(
        '<div class="section-title">🔎 Verificar Atualizações no Portal MTE</div>',
        unsafe_allow_html=True,
    )

    cached = get_cached_check_results()
    cache_info = ""
    if cached:
        age_h = (_time.time() - cached.get("cached_at", 0)) / 3600
        remaining_h = (CACHE_TTL_SECONDS / 3600) - age_h
        cache_info = (
            f"Cache de {cached.get('cached_at_str', '?')} "
            f"(válido por mais {remaining_h:.1f}h)"
        )

    btn_col1, btn_col2, btn_col3 = st.columns([2, 2, 3])
    with btn_col1:
        run_check = st.button(
            "🔍 Verificar Atualizações",
            key="nr_check_updates_btn",
            type="primary",
            use_container_width=True,
        )
    with btn_col2:
        force_check = st.button(
            "🔄 Forçar Nova Verificação",
            key="nr_force_check_btn",
            use_container_width=True,
            disabled=(cached is None),
        )
    with btn_col3:
        if cache_info:
            st.markdown(
                f'<div style="color:#64748B; font-size:0.8em; padding:8px 0;">'
                f'📦 {cache_info}</div>',
                unsafe_allow_html=True,
            )

    if force_check:
        invalidate_cache()
        st.session_state.pop("nr_check_results", None)
        st.rerun()

    if run_check:
        use_cache = not force_check
        with st.spinner("Verificando atualizações no portal MTE… (pode levar 15-30s)"):
            try:
                results = check_nr_updates(force=not use_cache)
                st.session_state["nr_check_results"] = results
            except Exception as exc:
                st.error(f"❌ Erro durante a verificação: {exc}")
                return

    results: Optional[List[Dict[str, Any]]] = st.session_state.get("nr_check_results")
    if results is None and cached:
        results = cached.get("results")
        if results:
            st.session_state["nr_check_results"] = results

    if not results:
        st.markdown(
            '<div style="color:#64748B; font-size:0.85em; margin-top:8px;">'
            "Clique em <strong>Verificar Atualizações</strong> para checar o portal MTE."
            "</div>",
            unsafe_allow_html=True,
        )
        return

    import pandas as pd

    outdated = [r for r in results if r.get("status") == "outdated"]
    updated = [r for r in results if r.get("status") == "updated"]
    no_remote = [r for r in results if r.get("status") in ("no_remote", "error")]

    sum_col1, sum_col2, sum_col3, sum_col4 = st.columns(4)
    sum_col1.metric("Total verificadas", len(results))
    sum_col2.metric("✅ Atualizadas", len(updated))
    sum_col3.metric("🆕 Com nova versão", len(outdated))
    sum_col4.metric("⚠️ Sem URL remota", len(no_remote))

    if outdated:
        st.markdown(
            '<div class="section-title" style="margin-top:16px;">🆕 NRs com Nova Versão Disponível</div>',
            unsafe_allow_html=True,
        )

        for r in outdated:
            nr_num = r["nr"]
            nr_label = r["nr_label"]
            pdf_url = r.get("pdf_url", "")
            local_size = r.get("local_size")
            remote_size = r.get("remote_size")
            local_mtime = r.get("local_mtime_str", "—")
            remote_lm = r.get("remote_last_modified_str", "—")

            local_size_str = f"{local_size / 1024:.1f} KB" if local_size else "—"
            remote_size_str = f"{remote_size / 1024:.1f} KB" if remote_size else "—"

            with st.container():
                st.markdown(f"""
                    <div class="result-card" style="padding:12px 16px; margin-bottom:8px;">
                        <div style="display:flex; align-items:center; gap:12px; flex-wrap:wrap;">
                            <span style="color:#FBBF24; font-weight:700; font-size:1em;">{nr_label}</span>
                            <span style="color:#94A3B8; font-size:0.82em;">
                                Local: {local_size_str} · {local_mtime} &nbsp;→&nbsp;
                                MTE: {remote_size_str} · {remote_lm}
                            </span>
                        </div>
                    </div>
                """, unsafe_allow_html=True)

                dl_key = f"nr_dl_{nr_num}"
                if st.button(f"⬇ Baixar e Reindexar {nr_label}", key=dl_key, use_container_width=False):
                    _do_download_and_reindex(nr_num, pdf_url, qa_instance)

        if len(outdated) > 1:
            st.markdown("---")
            bulk_label = f"⬇ Baixar Todas ({len(outdated)} novas)"
            if st.button(bulk_label, key="nr_dl_all_btn", type="primary", use_container_width=True):
                from safety_ai_app.nr_update_checker import (
                    download_nr_update as _dnl,
                    trigger_reindex_for_nr as _tri,
                    append_update_history as _auh,
                )
                progress = st.progress(0, text="Iniciando downloads...")
                log_lines: List[str] = []
                for i, r in enumerate(outdated):
                    nr_num = r["nr"]
                    pdf_url = r.get("pdf_url", "")
                    progress.progress(i / len(outdated), text=f"Baixando NR-{nr_num:02d} ({i+1}/{len(outdated)})...")
                    ok, msg = _dnl(nr_num, pdf_url)
                    if ok:
                        ok2, msg2 = _tri(nr_num, qa_instance)
                        _result = "✅ Atualizada e reindexada" if ok2 else "⚠️ Baixada, reindexação falhou"
                        log_lines.append(f"{'✅' if ok2 else '⚠️'} NR-{nr_num:02d}: {msg} | {msg2}")
                        _auh({
                            "timestamp_str": datetime.now(timezone.utc).strftime("%d/%m/%Y %H:%M UTC"),
                            "nr_label": f"NR-{nr_num:02d}",
                            "result": _result,
                            "detail": f"{msg} | {msg2}",
                        })
                    else:
                        log_lines.append(f"❌ NR-{nr_num:02d}: {msg}")
                        _auh({
                            "timestamp_str": datetime.now(timezone.utc).strftime("%d/%m/%Y %H:%M UTC"),
                            "nr_label": f"NR-{nr_num:02d}",
                            "result": "❌ Falha no download",
                            "detail": msg,
                        })

                progress.progress(1.0, text="Concluído!")
                for line in log_lines:
                    if line.startswith("✅"):
                        st.success(line)
                    elif line.startswith("⚠️"):
                        st.warning(line)
                    else:
                        st.error(line)
                st.session_state.pop("nr_check_results", None)
                st.rerun()
    else:
        st.success("✅ Todas as NRs verificadas estão atualizadas!")

    with st.expander("📋 Tabela completa de status", expanded=False):
        table_rows = []
        for r in results:
            local_size = r.get("local_size")
            remote_size = r.get("remote_size")
            table_rows.append({
                "NR": r["nr_label"],
                "Status": r.get("status_label", "—"),
                "Tamanho local": f"{local_size / 1024:.1f} KB" if local_size else "—",
                "Data local": r.get("local_mtime_str", "—"),
                "Tamanho MTE": f"{remote_size / 1024:.1f} KB" if remote_size else "—",
                "Data MTE": r.get("remote_last_modified_str", "—"),
            })
        st.dataframe(pd.DataFrame(table_rows), use_container_width=True, hide_index=True)

    history = load_update_history()
    if history:
        with st.expander(f"📜 Histórico de atualizações ({len(history)} eventos)", expanded=False):
            hist_rows = []
            for h in history[:20]:
                hist_rows.append({
                    "Data/hora": h.get("timestamp_str", "—"),
                    "NR": h.get("nr_label", "—"),
                    "Resultado": h.get("result", "—"),
                    "Detalhes": str(h.get("detail", ""))[:120],
                })
            st.dataframe(pd.DataFrame(hist_rows), use_container_width=True, hide_index=True)


# ---------------------------------------------------------------------------
# NR Indexing tab
# ---------------------------------------------------------------------------

def _render_nr_indexing_tab() -> None:
    """Render the NR PDF indexing admin tab."""
    import pandas as pd

    from safety_ai_app.nr_rag_qa import (
        get_indexed_nr_numbers_from_mte,
        start_nr_indexing_background,
        get_nr_indexing_status,
        is_nr_indexing_running,
    )
    try:
        from safety_ai_app.web_app import get_qa_instance_cached
        qa = get_qa_instance_cached()
    except Exception as e:
        st.error(f"Não foi possível carregar o sistema RAG: {e}")
        return

    all_nrs = list(range(1, 39))
    nrs_dir = _DATA_DIR / "nrs"

    st.markdown('<div class="section-title">📄 Estado do Indexamento das NRs Oficiais (MTE)</div>', unsafe_allow_html=True)

    try:
        indexed_mte = get_indexed_nr_numbers_from_mte(qa.vector_db._collection)
    except Exception:
        indexed_mte = []

    available_pdfs = [nr for nr in all_nrs if (nrs_dir / f"NR-{nr:02d}.pdf").exists()]
    pending = [nr for nr in available_pdfs if nr not in indexed_mte and nr not in range(33, 39)]
    drive_covered = list(range(33, 39))

    col_a, col_b, col_c = st.columns(3)
    col_a.metric("Total de NRs", 38)
    col_b.metric("Indexadas (MTE-oficial)", len(indexed_mte))
    col_c.metric("Pendentes", len(pending))

    st.markdown('<div class="section-title">Status por NR</div>', unsafe_allow_html=True)
    rows = []
    for nr in all_nrs:
        if nr in drive_covered:
            rows.append({"NR": f"NR-{nr:02d}", "Status": "✅ Drive (Google Drive)", "PDF": "Via Drive"})
        elif nr in indexed_mte:
            rows.append({"NR": f"NR-{nr:02d}", "Status": "✅ Indexada (MTE)", "PDF": f"NR-{nr:02d}.pdf"})
        elif (nrs_dir / f"NR-{nr:02d}.pdf").exists():
            rows.append({"NR": f"NR-{nr:02d}", "Status": "⏳ Pendente", "PDF": f"NR-{nr:02d}.pdf"})
        else:
            rows.append({"NR": f"NR-{nr:02d}", "Status": "❌ PDF não encontrado", "PDF": "—"})

    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    if is_nr_indexing_running():
        status = get_nr_indexing_status()
        current = status.get("current", "...")
        done = status.get("done", 0)
        total = status.get("total", len(pending))
        st.info(f"⚙️ Indexamento em andamento — NR atual: **{current}** ({done}/{total} concluídas)")
        if st.button("🔄 Atualizar Status", key="nr_idx_refresh"):
            st.rerun()
    elif pending:
        st.markdown('<div class="section-title">Iniciar Indexamento</div>', unsafe_allow_html=True)
        st.markdown(
            f"<p style='color:#94A3B8; font-size:0.87em;'>Serão indexadas {len(pending)} NRs pendentes "
            f"({', '.join(f'NR-{n:02d}' for n in pending)}) usando o modelo de embedding já carregado. "
            f"O processo roda em background — o app continua funcionando normalmente.</p>",
            unsafe_allow_html=True,
        )
        if st.button("▶ Iniciar Indexamento de NRs Pendentes", key="nr_idx_start", type="primary", use_container_width=True):
            ok = start_nr_indexing_background(qa, pending)
            if ok:
                st.success(f"✅ Indexamento iniciado em background para {len(pending)} NRs.")
                st.rerun()
            else:
                st.warning("Indexamento já está em andamento.")
    else:
        st.success("✅ Todas as NRs com PDF disponível já estão indexadas!")

    status = get_nr_indexing_status()
    if status and not status.get("running") and status.get("results"):
        with st.expander("📊 Último resultado do indexamento", expanded=False):
            results = status.get("results", {})
            ok_count = sum(1 for r in results.values() if r.get("status") == "ok")
            err_count = sum(1 for r in results.values() if r.get("status") == "error")
            st.markdown(
                f"**Concluído em:** {status.get('finished_at', '?')} | "
                f"**OK:** {ok_count} | **Erros:** {err_count}",
                unsafe_allow_html=True,
            )
            for nr_str, res in sorted(results.items(), key=lambda x: int(x[0])):
                icon = "✅" if res.get("status") == "ok" else ("⚠️" if res.get("status") == "not_found" else "❌")
                detail = f"+{res.get('chunks_added', 0)} chunks" if res.get("status") == "ok" else res.get("error", "")[:80]
                st.markdown(f"{icon} **NR-{int(nr_str):02d}** — {detail}")

    st.markdown("---")
    try:
        from safety_ai_app.web_app import get_qa_instance_cached as _get_qa
        _render_nr_update_checker_section(_get_qa())
    except Exception as e:
        st.error(f"Erro ao carregar verificador de NRs: {e}")


# ---------------------------------------------------------------------------
# TAB 5 — Pipeline de IA (entry point)
# ---------------------------------------------------------------------------

def _tab_ai_pipeline() -> None:
    from safety_ai_app.web_interface.pages.ai_evaluation_page import (
        _load_result_files,
        _render_aggregate_metrics,
        _render_trend_chart,
        _render_per_question_table,
        _render_golden_set_info,
        _format_timestamp,
        _RESULTS_DIR,
        _GOLDEN_SET_PATH,
    )
    import pandas as pd

    ai_tab1, ai_tab2, ai_tab3, ai_tab4, ai_tab5 = st.tabs([
        "📊 Última Avaliação",
        "📈 Tendência Histórica",
        "📋 Golden Set",
        "▶ Executar Avaliação",
        "🗂️ Indexar NRs",
    ])

    all_results = _load_result_files()

    with ai_tab1:
        if not all_results:
            st.info("Nenhuma avaliação encontrada. Use a aba '▶ Executar Avaliação' para gerar resultados.")
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

    with ai_tab2:
        if not all_results:
            st.info("Nenhuma avaliação encontrada.")
        else:
            _render_trend_chart(all_results)
            if len(all_results) > 1:
                rows = []
                for fname, report in all_results:
                    agg = report.get("aggregate_metrics", {})
                    rows.append({
                        "Data": _format_timestamp(report.get("timestamp", "")),
                        "Perguntas": report.get("questions_evaluated", 0),
                        "Fidelidade": f"{int(agg.get('faithfulness', 0)*100)}%",
                        "Relevância": f"{int(agg.get('answer_relevance', 0)*100)}%",
                        "Cobertura": f"{int(agg.get('context_recall', 0)*100)}%",
                        "Precisão": f"{int(agg.get('context_precision', 0)*100)}%",
                        "Violações": len(report.get("threshold_violations", [])),
                    })
                st.dataframe(pd.DataFrame(rows), use_container_width=True)

    with ai_tab3:
        st.markdown(
            f"<p style='color:#94A3B8; font-size:0.85em;'>Localização: <code>{_GOLDEN_SET_PATH}</code></p>",
            unsafe_allow_html=True,
        )
        _render_golden_set_info()

    with ai_tab4:
        st.markdown('<div class="section-title">Executar Nova Avaliação</div>', unsafe_allow_html=True)
        st.code(
            "# Avaliação completa (35 perguntas)\n"
            "python safety_ai_app/scripts/evaluate_rag.py\n\n"
            "# Avaliação rápida (5 perguntas)\n"
            "python safety_ai_app/scripts/evaluate_rag.py --limit 5",
            language="bash",
        )
        st.markdown(
            "<p style='color:#64748B; font-size:0.83em;'>"
            "⚠ A avaliação requer ChromaDB populado e conexão ao LLM via OpenRouter.</p>",
            unsafe_allow_html=True,
        )

        if st.button("▶ Executar Avaliação Rápida (5 perguntas)", key="admin_run_eval", type="primary"):
            import subprocess
            script = _PROJECT_ROOT / "scripts" / "evaluate_rag.py"
            if not script.exists():
                script = _PROJECT_ROOT / "safety_ai_app" / "scripts" / "evaluate_rag.py"
            if script.exists():
                with st.spinner("A executar avaliação..."):
                    result = subprocess.run(
                        ["python", str(script), "--limit", "5"],
                        capture_output=True, text=True, timeout=300,
                    )
                if result.returncode == 0:
                    st.success("✅ Avaliação concluída! Recarregue para ver os resultados.")
                else:
                    st.error(f"❌ Erro na avaliação:\n{result.stderr[:1000]}")
            else:
                st.error("Script `evaluate_rag.py` não encontrado.")

    with ai_tab5:
        _render_nr_indexing_tab()
