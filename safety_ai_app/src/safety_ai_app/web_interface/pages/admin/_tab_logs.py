"""
TAB 2 — Logs do Sistema
Painel de Administração SafetyAI

Sub-tabs: Logs da Aplicação (com paginação), Eventos de Segurança, Pipeline RAG.
"""

import json
import logging
import time
from datetime import datetime
from typing import Any, Dict, List

import streamlit as st

from safety_ai_app.web_interface.pages.admin._helpers import (
    _LOG_PATH,
    _SECURITY_LOG_PATH,
    _RAG_LOGS_DIR,
)

logger = logging.getLogger(__name__)

_LOG_PAGE_SIZE = 50


def _read_log_lines(path: Any, n: int) -> List[Dict[str, Any]]:
    """Read last n lines from a JSON-lines log file using a seek-from-end strategy
    so only the needed tail bytes are loaded — O(tail size) not O(file size)."""
    if not path.exists():
        return []
    try:
        _CHUNK = 65536  # 64 KB per read
        with path.open("rb") as fh:
            fh.seek(0, 2)
            remaining = fh.tell()
            chunks: List[bytes] = []
            newline_count = 0
            while remaining > 0 and newline_count < n + 1:
                to_read = min(_CHUNK, remaining)
                remaining -= to_read
                fh.seek(remaining)
                chunk = fh.read(to_read)
                newline_count += chunk.count(b"\n")
                chunks.append(chunk)
        raw = b"".join(reversed(chunks)).decode("utf-8", errors="replace")
        all_lines = raw.splitlines()
        tail = all_lines[-n:] if len(all_lines) > n else all_lines
        records: List[Dict[str, Any]] = []
        for line in tail:
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                records.append({"message": line, "level": "RAW", "timestamp": "", "logger": "", "correlation_id": ""})
        return records
    except Exception as exc:
        logger.warning("Erro ao ler log %s: %s", path, exc)
        return []


def _tab_logs() -> None:
    import pandas as pd

    log_tab1, log_tab2, log_tab3 = st.tabs([
        "📋 Logs da Aplicação",
        "🔒 Eventos de Segurança",
        "🔍 Pipeline RAG",
    ])

    with log_tab1:
        st.markdown('<div class="section-title">Logs da Aplicação</div>', unsafe_allow_html=True)

        ctrl_col1, ctrl_col2, ctrl_col3_ar = st.columns([3, 2, 2])
        with ctrl_col1:
            level_filter = st.multiselect(
                "Filtrar por nível",
                ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
                default=["WARNING", "ERROR", "CRITICAL"],
                key="admin_log_level_filter",
            )
        with ctrl_col2:
            n_lines = st.select_slider("Linhas", options=[50, 200, 500, 1000], value=200, key="admin_log_lines")
        with ctrl_col3_ar:
            auto_refresh = st.toggle(
                "Auto-refresh a cada 10s",
                value=False,
                key="admin_log_auto_refresh",
            )

        ctrl_col3, ctrl_col4 = st.columns(2)
        with ctrl_col3:
            text_filter = st.text_input("🔍 Filtrar por texto", key="admin_log_text_filter", placeholder="Ex: sync, error, import...")
        with ctrl_col4:
            corr_filter = st.text_input("🔗 Filtrar por Correlation ID", key="admin_log_corr_filter", placeholder="Ex: 24cdd08e")

        records = _read_log_lines(_LOG_PATH, n_lines)

        if level_filter:
            records = [r for r in records if r.get("level", "").upper() in level_filter]
        if text_filter:
            records = [r for r in records if text_filter.lower() in json.dumps(r, ensure_ascii=False).lower()]
        if corr_filter:
            records = [r for r in records if corr_filter.lower() in str(r.get("correlation_id", "")).lower()]

        records_ordered = list(reversed(records))
        total_records = len(records_ordered)
        total_pages = max(1, -(-total_records // _LOG_PAGE_SIZE))

        _filter_sig = (tuple(sorted(level_filter)), text_filter, corr_filter, n_lines)
        if st.session_state.get("admin_log_filter_sig") != _filter_sig:
            st.session_state.admin_log_filter_sig = _filter_sig
            st.session_state.admin_log_page = 0

        if "admin_log_page" not in st.session_state:
            st.session_state.admin_log_page = 0
        if st.session_state.admin_log_page >= total_pages:
            st.session_state.admin_log_page = 0

        page_idx = st.session_state.admin_log_page
        page_start = page_idx * _LOG_PAGE_SIZE
        page_end = page_start + _LOG_PAGE_SIZE
        page_records = records_ordered[page_start:page_end]

        if not records_ordered:
            st.info("Nenhum registo encontrado com os filtros actuais.")
        else:
            pg_col_left, pg_col_mid, pg_col_right = st.columns([1, 3, 1])
            with pg_col_left:
                if st.button("◀ Anterior", disabled=(page_idx == 0), key="admin_log_prev"):
                    st.session_state.admin_log_page = max(0, page_idx - 1)
                    st.rerun()
            with pg_col_mid:
                st.markdown(
                    f'<div style="text-align:center; padding:6px 0; color:#94A3B8; font-size:0.85em;">'
                    f'Página {page_idx + 1} de {total_pages} · {total_records} registos'
                    f'</div>',
                    unsafe_allow_html=True,
                )
            with pg_col_right:
                if st.button("Próxima ▶", disabled=(page_idx >= total_pages - 1), key="admin_log_next"):
                    st.session_state.admin_log_page = min(total_pages - 1, page_idx + 1)
                    st.rerun()

            _MAX_MSG_DISPLAY = 500
            long_messages: List[Dict[str, Any]] = []
            rows = []
            for r in page_records:
                full_msg = str(r.get("message", ""))
                if len(full_msg) > _MAX_MSG_DISPLAY:
                    display_msg = full_msg[:_MAX_MSG_DISPLAY] + "…"
                    long_messages.append({"ts": r.get("timestamp", ""), "level": r.get("level", ""), "full": full_msg})
                else:
                    display_msg = full_msg
                rows.append({
                    "Timestamp": r.get("timestamp", ""),
                    "Nível": r.get("level", ""),
                    "Logger": r.get("logger", "")[:40],
                    "Mensagem": display_msg,
                    "Correlation ID": r.get("correlation_id", ""),
                })
            df = pd.DataFrame(rows)

            def _style_log_row(row: "pd.Series") -> List[str]:
                level = str(row.get("Nível", "")).upper()
                if level in ("ERROR", "CRITICAL"):
                    bg = "background-color: rgba(239,68,68,0.15)"
                elif level == "WARNING":
                    bg = "background-color: rgba(245,158,11,0.12)"
                else:
                    bg = ""
                return [bg] * len(row)

            styled_df = df.style.apply(_style_log_row, axis=1)
            st.dataframe(styled_df, use_container_width=True, height=400)

            if long_messages:
                st.markdown(
                    f'<div style="margin-top:8px; font-size:0.82em; color:#94A3B8;">'
                    f'{len(long_messages)} mensagen(s) truncada(s) nesta página — clique para ver completa:'
                    f'</div>',
                    unsafe_allow_html=True,
                )
                for i, lm in enumerate(long_messages):
                    label = f"[{lm['level']}] {lm['ts']} — Ver mensagem completa"
                    with st.expander(label, expanded=False):
                        st.text(lm["full"])

            csv_bytes = pd.DataFrame([{
                "Timestamp": r.get("timestamp", ""),
                "Nível": r.get("level", ""),
                "Logger": r.get("logger", "")[:40],
                "Mensagem": str(r.get("message", "")),
                "Correlation ID": r.get("correlation_id", ""),
            } for r in records_ordered]).to_csv(index=False).encode("utf-8")
            st.download_button(
                label="📥 Exportar CSV (todos os registos)",
                data=csv_bytes,
                file_name=f"app_logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv",
                key="admin_log_export",
            )

        if auto_refresh:
            refresh_placeholder = st.empty()
            for remaining in range(10, 0, -1):
                refresh_placeholder.markdown(
                    f'<div style="color:#64748B; font-size:0.8em; margin-top:4px;">🔄 Actualizando em {remaining}s…</div>',
                    unsafe_allow_html=True,
                )
                time.sleep(1)
            refresh_placeholder.empty()
            st.rerun()

    with log_tab2:
        st.markdown('<div class="section-title">Eventos de Segurança</div>', unsafe_allow_html=True)

        event_filter = st.multiselect(
            "Filtrar por tipo de evento",
            ["login_success", "login_failure", "logout", "rate_limit_exceeded",
             "file_rejected", "suspicious_input", "prompt_injection_attempt",
             "csrf_error", "auth_error", "session_timeout", "temp_cleanup"],
            key="admin_sec_event_filter",
        )

        sec_records = _read_log_lines(_SECURITY_LOG_PATH, 500)
        if not sec_records:
            all_app_records = _read_log_lines(_LOG_PATH, 2000)
            sec_records = [
                r for r in all_app_records
                if r.get("logger", "").startswith("safety_ai.security")
                or "security_event" in json.dumps(r, ensure_ascii=False).lower()
            ]

        if event_filter:
            sec_records = [r for r in sec_records if r.get("event", r.get("message", "")) in event_filter
                           or any(evt in json.dumps(r, ensure_ascii=False) for evt in event_filter)]

        if not sec_records:
            st.info("Nenhum evento de segurança registado ainda, ou nenhum correspondente ao filtro.")
        else:
            rows = []
            for r in reversed(sec_records):
                rows.append({
                    "Timestamp": r.get("timestamp", ""),
                    "Evento": r.get("event", r.get("level", "")),
                    "User Hash": r.get("user_hash", ""),
                    "Detalhe": str(r.get("detail", r.get("message", "")))[:200],
                })
            df = pd.DataFrame(rows)
            st.dataframe(df, use_container_width=True, height=400)

    with log_tab3:
        st.markdown('<div class="section-title">Logs do Pipeline RAG</div>', unsafe_allow_html=True)

        if not _RAG_LOGS_DIR.exists():
            st.info("Nenhum ficheiro de log RAG encontrado em `data/rag_logs/`.")
        else:
            rag_files = sorted(_RAG_LOGS_DIR.glob("*.jsonl"), reverse=True)
            if not rag_files:
                st.info("Nenhum log RAG disponível.")
            else:
                selected_file = st.selectbox(
                    "Seleccionar ficheiro de log",
                    [f.name for f in rag_files],
                    key="admin_rag_log_select",
                )
                selected_path = _RAG_LOGS_DIR / selected_file
                rag_records = _read_log_lines(selected_path, 500)

                if rag_records:
                    from datetime import datetime as _dt
                    rows = []
                    for r in rag_records:
                        lat = r.get("total_latency_ms", r.get("latency_ms", 0)) or 0
                        ts_raw = r.get("timestamp", "")
                        try:
                            ts_parsed = _dt.strptime(ts_raw[:19], "%Y-%m-%dT%H:%M:%S").strftime("%Y-%m-%d %H:%M")
                            day = ts_raw[:10]
                        except Exception:
                            ts_parsed = ts_raw
                            day = ts_raw[:10] if ts_raw else ""
                        rows.append({
                            "Timestamp": ts_parsed,
                            "Dia": day,
                            "Query": str(r.get("query", ""))[:70],
                            "Query Expandida": str(r.get("expanded_query", r.get("query", "")))[:70],
                            "Modelo": r.get("model", ""),
                            "Latência (ms)": int(lat),
                            "Chunks": r.get("chunks_retrieved", r.get("num_chunks", "–")),
                            "Tam. Resposta": r.get("answer_length", "–"),
                        })
                    df = pd.DataFrame(rows)
                    display_cols = [c for c in df.columns if c != "Dia"]
                    st.dataframe(df[display_cols], use_container_width=True, height=350)

                    if rows:
                        st.markdown('<div class="section-title">📈 Latência Média por Dia</div>', unsafe_allow_html=True)
                        day_df = df.groupby("Dia")["Latência (ms)"].mean().reset_index()
                        day_df = day_df.sort_values("Dia")
                        day_chart = day_df.set_index("Dia")[["Latência (ms)"]]
                        st.line_chart(day_chart, height=200)
