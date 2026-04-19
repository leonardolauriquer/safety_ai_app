"""
Painel de Administração Completo — SafetyAI

Acessível apenas para administradores (ADMIN_EMAILS env var).
Oferece 5 abas: Visão Geral, Logs, Planos & Preços, Configurações Avançadas, Pipeline de IA.
"""

import json
import logging
import os
import io
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import streamlit as st

from safety_ai_app.theme_config import get_icon
from safety_ai_app.web_interface.shared_styles import inject_glass_styles

logger = logging.getLogger(__name__)

_PROJECT_ROOT = Path(__file__).parents[4]
_DATA_DIR = _PROJECT_ROOT / "data"
_PLANS_PATH = _DATA_DIR / "plans" / "plans.json"
_AI_CONFIG_PATH = _DATA_DIR / "ai_config.json"
_FEATURE_FLAGS_PATH = _DATA_DIR / "feature_flags.json"
_LOG_PATH = _PROJECT_ROOT / "logs" / "app.log"
_SECURITY_LOG_PATH = _PROJECT_ROOT / "logs" / "security.log"
_RAG_LOGS_DIR = _DATA_DIR / "rag_logs"
_CHROMA_DB_DIR = _DATA_DIR / "chroma_db"


# ---------------------------------------------------------------------------
# Admin guard
# ---------------------------------------------------------------------------

def _is_admin() -> bool:
    if st.session_state.get("is_admin"):
        return True
    user_email = st.session_state.get("user_email", "").strip().lower()
    if not user_email:
        return False
    raw = os.environ.get("ADMIN_EMAILS", "")
    admin_set = {e.strip().lower() for e in raw.split(",") if e.strip()}
    return user_email in admin_set


# ---------------------------------------------------------------------------
# Helpers: load / save JSON files
# ---------------------------------------------------------------------------

def _load_json(path: Path, default: Any) -> Any:
    try:
        if path.exists():
            with path.open(encoding="utf-8") as f:
                return json.load(f)
    except Exception as exc:
        logger.warning("Falha ao carregar %s: %s", path, exc)
    return default


def _save_json(path: Path, data: Any) -> bool:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as exc:
        logger.error("Falha ao salvar %s: %s", path, exc)
        return False


def _human_size(n_bytes: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n_bytes < 1024:
            return f"{n_bytes:.1f} {unit}"
        n_bytes /= 1024
    return f"{n_bytes:.1f} TB"


# ---------------------------------------------------------------------------
# TAB 1 — Visão Geral
# ---------------------------------------------------------------------------

def _render_metric_card(col, icon: str, value: str, label: str, color: str = "#4ADE80") -> None:
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
        total = 0
        for col in client.list_collections():
            total += col.count()
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
        results_dir = _DATA_DIR / "eval" / "results"
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


# ---------------------------------------------------------------------------
# TAB 2 — Logs do Sistema
# ---------------------------------------------------------------------------

def _read_log_lines(path: Path, n: int) -> List[Dict[str, Any]]:
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
    log_tab1, log_tab2, log_tab3 = st.tabs([
        "📋 Logs da Aplicação",
        "🔒 Eventos de Segurança",
        "🔍 Pipeline RAG",
    ])

    with log_tab1:
        st.markdown('<div class="section-title">Logs da Aplicação</div>', unsafe_allow_html=True)

        _LOG_PAGE_SIZE = 50

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
            import pandas as pd

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
                    '<div style="margin-top:8px; font-size:0.82em; color:#94A3B8;">'
                    f'{len(long_messages)} mensagen(s) truncada(s) nesta página — clique para ver completa:'
                    '</div>',
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
            import pandas as pd
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
                    import pandas as pd
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


# ---------------------------------------------------------------------------
# TAB 3 — Planos & Preços
# ---------------------------------------------------------------------------

_FEATURE_LABELS = {
    "chat_messages_per_day": "Msgs de chat por dia (-1 = ilimitado)",
    "knowledge_base_sync": "Sincronização da Base de Conhecimento",
    "document_generation": "Geração de Documentos (APR, ATA)",
    "job_board": "Quadro de Empregos",
    "games": "Jogos e Desafios",
    "quick_queries": "Consultas Rápidas (CBO, CID, CNAE, CA)",
    "dimensioning": "Dimensionamentos (CIPA, SESMT, Brigada)",
    "news_feed": "Feed de Notícias",
    "custom_branding": "Personalização Visual",
    "priority_support": "Suporte Prioritário",
}


_DEFAULT_PLANS = {
    "plans": [
        {"id": "free", "name": "Gratuito", "price_monthly": 0.0, "price_yearly": 0.0, "currency": "BRL",
         "description": "Acesso básico às NRs e consultas rápidas.",
         "features": {"chat_messages_per_day": 10, "knowledge_base_sync": False, "document_generation": False,
                      "job_board": True, "games": True, "quick_queries": True, "dimensioning": True,
                      "news_feed": True, "custom_branding": False, "priority_support": False}},
        {"id": "pro", "name": "Profissional", "price_monthly": 29.90, "price_yearly": 299.00, "currency": "BRL",
         "description": "Acesso completo com geração de documentos e sincronização automática.",
         "features": {"chat_messages_per_day": -1, "knowledge_base_sync": True, "document_generation": True,
                      "job_board": True, "games": True, "quick_queries": True, "dimensioning": True,
                      "news_feed": True, "custom_branding": False, "priority_support": False}},
        {"id": "enterprise", "name": "Enterprise", "price_monthly": 99.90, "price_yearly": 999.00, "currency": "BRL",
         "description": "Multi-utilizador, suporte prioritário e personalização completa.",
         "features": {"chat_messages_per_day": -1, "knowledge_base_sync": True, "document_generation": True,
                      "job_board": True, "games": True, "quick_queries": True, "dimensioning": True,
                      "news_feed": True, "custom_branding": True, "priority_support": True}},
    ]
}


def _tab_plans() -> None:
    plans_data = _load_json(_PLANS_PATH, None)
    if not plans_data or not plans_data.get("plans"):
        plans_data = _DEFAULT_PLANS
        _save_json(_PLANS_PATH, plans_data)
    plans: List[Dict] = plans_data.get("plans", [])

    if not plans:
        st.warning("Nenhum plano definido. Clique em 'Adicionar Novo Plano' para começar.")
        plans = list(_DEFAULT_PLANS["plans"])

    st.markdown('<div class="section-title">💳 Planos Actuais</div>', unsafe_allow_html=True)

    plan_names = [f"{p.get('name', p.get('id', '?'))} ({p.get('id', '?')})" for p in plans]
    sel_idx = st.selectbox("Seleccionar plano para editar", range(len(plan_names)),
                           format_func=lambda i: plan_names[i], key="admin_plan_select")

    if plans:
        plan = plans[sel_idx]
    else:
        plan = {}

    col_edit, col_preview = st.columns([3, 2])

    with col_edit:
        st.markdown('<div class="section-title">✏️ Editar Plano</div>', unsafe_allow_html=True)

        new_id = st.text_input("ID (chave única)", value=plan.get("id", ""), key="plan_id")
        new_name = st.text_input("Nome", value=plan.get("name", ""), key="plan_name")
        new_desc = st.text_area("Descrição", value=plan.get("description", ""), key="plan_desc", height=80)
        new_currency = st.text_input("Moeda", value=plan.get("currency", "BRL"), key="plan_currency")

        pcol1, pcol2 = st.columns(2)
        with pcol1:
            new_price_m = st.number_input("Preço Mensal", min_value=0.0, step=0.01,
                                          value=float(plan.get("price_monthly", 0.0)), key="plan_price_m", format="%.2f")
        with pcol2:
            new_price_y = st.number_input("Preço Anual", min_value=0.0, step=0.01,
                                          value=float(plan.get("price_yearly", 0.0)), key="plan_price_y", format="%.2f")

        st.markdown('<div class="section-title" style="margin-top:12px;">🔧 Funcionalidades</div>', unsafe_allow_html=True)
        features = dict(plan.get("features", {}))
        new_features = {}
        for feat_key, feat_label in _FEATURE_LABELS.items():
            current_val = features.get(feat_key, False)
            if feat_key == "chat_messages_per_day":
                new_features[feat_key] = st.number_input(
                    feat_label, value=int(current_val) if isinstance(current_val, (int, float)) else 10,
                    min_value=-1, step=1, key=f"feat_{feat_key}_{sel_idx}",
                )
            else:
                new_features[feat_key] = st.checkbox(
                    feat_label, value=bool(current_val), key=f"feat_{feat_key}_{sel_idx}"
                )

        bcol1, bcol2, bcol3 = st.columns(3)
        with bcol1:
            if st.button("💾 Salvar Plano", key="plan_save", type="primary", use_container_width=True):
                updated_plan = {
                    "id": new_id,
                    "name": new_name,
                    "price_monthly": new_price_m,
                    "price_yearly": new_price_y,
                    "currency": new_currency,
                    "description": new_desc,
                    "features": new_features,
                }
                plans[sel_idx] = updated_plan
                plans_data["plans"] = plans
                if _save_json(_PLANS_PATH, plans_data):
                    st.success("✅ Plano salvo com sucesso!")
                else:
                    st.error("❌ Erro ao salvar. Verifique as permissões de ficheiro.")

        with bcol2:
            if st.button("➕ Novo Plano", key="plan_add", use_container_width=True):
                new_plan = {
                    "id": f"novo_{len(plans)+1}",
                    "name": "Novo Plano",
                    "price_monthly": 0.0,
                    "price_yearly": 0.0,
                    "currency": "BRL",
                    "description": "Descrição do novo plano.",
                    "features": {k: False for k in _FEATURE_LABELS},
                }
                plans.append(new_plan)
                plans_data["plans"] = plans
                _save_json(_PLANS_PATH, plans_data)
                st.rerun()

        with bcol3:
            if st.button("🗑️ Remover Plano", key="plan_remove", use_container_width=True):
                if len(plans) > 1:
                    plans.pop(sel_idx)
                    plans_data["plans"] = plans
                    if _save_json(_PLANS_PATH, plans_data):
                        st.success("Plano removido.")
                        st.rerun()
                else:
                    st.warning("Não é possível remover o último plano.")

    with col_preview:
        st.markdown('<div class="section-title">👁️ Pré-visualização</div>', unsafe_allow_html=True)
        price_m = plan.get("price_monthly", 0)
        price_y = plan.get("price_yearly", 0)
        currency = plan.get("currency", "BRL")
        feats_preview = plan.get("features", {})
        feat_list = "".join([
            f'<li style="color:#{"4ADE80" if v else "475569"}; font-size:0.82em; padding:2px 0;">'
            f'{"✓" if v else "✗"} {lbl}</li>'
            for feat_key, lbl in _FEATURE_LABELS.items()
            if (v := feats_preview.get(feat_key, False)) is not None
        ])
        st.markdown(f"""
            <div class="result-card" style="padding:20px 18px;">
                <div style="color:#4ADE80; font-size:1.1em; font-weight:700; margin-bottom:4px;">{plan.get('name','–')}</div>
                <div style="color:#94A3B8; font-size:0.82em; margin-bottom:12px;">{plan.get('description','')}</div>
                <div style="color:#F8FAFC; font-size:1.4em; font-weight:800; margin-bottom:4px;">
                    {currency} {price_m:.2f}<span style="font-size:0.55em;color:#64748B;">/mês</span>
                </div>
                <div style="color:#64748B; font-size:0.78em; margin-bottom:14px;">
                    ou {currency} {price_y:.2f}/ano
                </div>
                <ul style="list-style:none; padding:0; margin:0;">
                    {feat_list}
                </ul>
            </div>
        """, unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# TAB 4 — Configurações Avançadas
# ---------------------------------------------------------------------------

def _tab_advanced_config() -> None:
    conf_tab1, conf_tab2, conf_tab3, conf_tab4 = st.tabs([
        "👤 Administradores",
        "🔄 Sincronização",
        "🤖 Configurações de IA",
        "🚩 Feature Flags",
    ])

    with conf_tab1:
        st.markdown('<div class="section-title">Gestão de Administradores</div>', unsafe_allow_html=True)
        st.markdown("""
            <div class="result-card" style="padding:12px 16px; margin-bottom:12px;">
                <div style="color:#F59E0B; font-size:0.85em;">
                    ⚠️ Alterações aqui actualizam apenas a sessão actual.<br>
                    Para persistir, actualize o secret <code>ADMIN_EMAILS</code> no painel do Replit com os emails separados por vírgula.
                </div>
            </div>
        """, unsafe_allow_html=True)

        current_raw = os.environ.get("ADMIN_EMAILS", "")
        current_admins = [e.strip() for e in current_raw.split(",") if e.strip()]

        st.markdown("**Administradores actuais:**")
        if current_admins:
            for email in current_admins:
                st.markdown(f"- `{email}`")
        else:
            st.info("Nenhum administrador configurado via ADMIN_EMAILS.")

        st.markdown("**Adicionar administrador (sessão actual):**")
        new_admin_email = st.text_input("Email do novo administrador", key="admin_new_email",
                                         placeholder="email@exemplo.com")
        if st.button("➕ Adicionar (sessão)", key="admin_add_btn"):
            if new_admin_email and "@" in new_admin_email:
                if new_admin_email not in current_admins:
                    current_admins.append(new_admin_email.strip().lower())
                    os.environ["ADMIN_EMAILS"] = ",".join(current_admins)
                    st.success(f"✅ `{new_admin_email}` adicionado para esta sessão.")
                    st.info("Lembre-se de actualizar o secret ADMIN_EMAILS no Replit para persistir.")
                else:
                    st.warning("Este email já é administrador.")
            else:
                st.error("Insira um email válido.")

    with conf_tab2:
        st.markdown('<div class="section-title">Sincronização Automática</div>', unsafe_allow_html=True)
        try:
            from safety_ai_app.auto_sync_scheduler import get_scheduler, DEFAULT_INTERVAL_MINUTES
            scheduler = get_scheduler()
            status = get_scheduler().get_status()

            is_running = status.get("running", False)
            interval = status.get("interval_minutes", DEFAULT_INTERVAL_MINUTES)

            st.markdown(f"""
                <div class="result-card" style="padding:14px 16px; margin-bottom:12px;">
                    <div style="color:#CBD5E1; font-size:0.88em;">
                        Estado: <strong style="color:{'#4ADE80' if is_running else '#EF4444'}">
                            {'▶ A correr' if is_running else '⏹ Parado'}
                        </strong> &nbsp;|&nbsp;
                        Intervalo: <strong style="color:#4ADE80;">{interval} min</strong><br>
                        Última execução: {status.get('last_run_time', '–')}<br>
                        Próxima execução: {status.get('next_run_time', '–')}
                    </div>
                </div>
            """, unsafe_allow_html=True)

            sync_enabled_toggle = st.toggle(
                "Sincronização Automática Activa",
                value=is_running,
                key="admin_sync_enabled_toggle",
            )
            if sync_enabled_toggle != is_running:
                try:
                    if sync_enabled_toggle:
                        scheduler.start()
                        st.success("▶ Sincronização automática activada.")
                    else:
                        scheduler.stop()
                        st.success("⏹ Sincronização automática desactivada.")
                    st.rerun()
                except Exception as exc:
                    st.error(f"Erro ao alterar estado: {exc}")

            new_interval = st.slider("Intervalo de sincronização (minutos)", 5, 1440, value=int(interval), step=5,
                                      key="admin_sync_interval")

            scol1, scol2 = st.columns(2)
            with scol1:
                if st.button("🔄 Sincronizar Agora", key="admin_sync_now", type="primary", use_container_width=True):
                    try:
                        scheduler.trigger_sync()
                        st.success("Sincronização iniciada!")
                    except Exception as exc:
                        st.error(f"Erro: {exc}")

            with scol2:
                if st.button("💾 Aplicar Intervalo", key="admin_sync_apply", use_container_width=True):
                    try:
                        scheduler.set_interval(new_interval)
                        st.success(f"Intervalo actualizado para {new_interval} min.")
                    except Exception as exc:
                        st.error(f"Erro: {exc}")

        except Exception as exc:
            st.error(f"Não foi possível aceder ao scheduler: {exc}")

    with conf_tab3:
        st.markdown('<div class="section-title">Configurações de IA</div>', unsafe_allow_html=True)
        ai_cfg = _load_json(_AI_CONFIG_PATH, {
            "model": "openai/gpt-4o-mini",
            "temperature_factual": 0.1,
            "temperature_document": 0.5,
            "max_history_tokens": 16000,
            "max_history_turns": 10,
            "guardrail_threshold": 0.3,
            "retriever_top_k": 6,
            "bm25_weight": 0.3,
            "semantic_weight": 0.7,
        })

        new_model = st.text_input("Modelo activo (OpenRouter)", value=ai_cfg.get("model", ""), key="ai_model")
        ai_col1, ai_col2 = st.columns(2)
        with ai_col1:
            new_temp_f = st.slider("Temperatura (consultas factuais)", 0.0, 1.0,
                                    value=float(ai_cfg.get("temperature_factual", 0.1)), step=0.05, key="ai_temp_f")
            new_max_tokens = st.number_input("Máx. tokens de histórico", min_value=1000, max_value=64000,
                                              value=int(ai_cfg.get("max_history_tokens", 16000)), step=1000, key="ai_max_tok")
            new_top_k = st.number_input("Top-K chunks recuperados", min_value=1, max_value=20,
                                         value=int(ai_cfg.get("retriever_top_k", 6)), step=1, key="ai_top_k")
        with ai_col2:
            new_temp_d = st.slider("Temperatura (geração de documentos)", 0.0, 1.0,
                                    value=float(ai_cfg.get("temperature_document", 0.5)), step=0.05, key="ai_temp_d")
            new_max_turns = st.number_input("Máx. turnos de histórico", min_value=1, max_value=50,
                                             value=int(ai_cfg.get("max_history_turns", 10)), step=1, key="ai_max_turns")
            new_guardrail = st.slider("Threshold de guardrail (fora do domínio SST)", 0.0, 1.0,
                                       value=float(ai_cfg.get("guardrail_threshold", 0.3)), step=0.05, key="ai_guardrail")

        bm25_w = st.slider("Peso BM25 (retriever híbrido)", 0.0, 1.0,
                            value=float(ai_cfg.get("bm25_weight", 0.3)), step=0.05, key="ai_bm25")
        sem_w = round(1.0 - bm25_w, 2)
        st.caption(f"Peso semântico automático: {sem_w:.2f}")

        ai_btn_col1, ai_btn_col2 = st.columns(2)
        with ai_btn_col1:
            if st.button("💾 Aplicar Configurações de IA", key="ai_cfg_save", type="primary", use_container_width=True):
                new_cfg = {
                    "model": new_model,
                    "temperature_factual": new_temp_f,
                    "temperature_document": new_temp_d,
                    "max_history_tokens": new_max_tokens,
                    "max_history_turns": new_max_turns,
                    "guardrail_threshold": new_guardrail,
                    "retriever_top_k": new_top_k,
                    "bm25_weight": bm25_w,
                    "semantic_weight": sem_w,
                }
                if _save_json(_AI_CONFIG_PATH, new_cfg):
                    st.success("✅ Configurações salvas. Use '🔄 Recarregar Pipeline' para aplicar sem reiniciar.")
                else:
                    st.error("❌ Erro ao salvar configurações.")

        with ai_btn_col2:
            if st.button("🔄 Recarregar Pipeline", key="ai_cfg_reload", use_container_width=True):
                try:
                    from safety_ai_app.nr_rag_qa import NRQuestionAnswering
                    nr_qa = st.session_state.get("nr_qa")
                    if nr_qa is None:
                        st.error("❌ Instância do pipeline não encontrada na sessão.")
                    elif not isinstance(nr_qa, NRQuestionAnswering):
                        st.error("❌ Objecto de pipeline inválido na sessão.")
                    else:
                        with st.spinner("A recarregar pipeline…"):
                            ok = nr_qa.reload_from_config()
                        if ok:
                            st.success(f"✅ Pipeline recarregado com modelo '{nr_qa._llm_model_name}'.")
                        else:
                            st.error("❌ Erro ao recarregar o pipeline. Consulte os logs para detalhes.")
                except Exception as exc:
                    st.error(f"❌ Erro inesperado ao recarregar: {exc}")

    with conf_tab4:
        st.markdown('<div class="section-title">Feature Flags</div>', unsafe_allow_html=True)
        st.markdown("""
            <div class="result-card" style="padding:12px 16px; margin-bottom:12px;">
                <div style="color:#94A3B8; font-size:0.83em;">
                    Activa ou desactiva funcionalidades globalmente. As páginas verificam estas flags ao carregar.
                </div>
            </div>
        """, unsafe_allow_html=True)

        flags = _load_json(_FEATURE_FLAGS_PATH, {})
        _FLAG_LABELS = {
            "chat": "Chat com IA",
            "library": "Biblioteca de Documentos",
            "knowledge_base": "Base de Conhecimento",
            "job_board": "Quadro de Empregos",
            "news_feed": "Feed de Notícias",
            "games": "Jogos e Desafios",
            "quick_queries": "Consultas Rápidas",
            "dimensioning": "Dimensionamentos",
            "apr_generator": "Gerador de APR",
            "ata_generator": "Gerador de ATA",
        }

        new_flags = {}
        flag_cols = st.columns(2)
        for i, (key, label) in enumerate(_FLAG_LABELS.items()):
            with flag_cols[i % 2]:
                new_flags[key] = st.toggle(label, value=flags.get(key, True), key=f"flag_{key}")

        if st.button("💾 Salvar Flags", key="flags_save", type="primary"):
            if _save_json(_FEATURE_FLAGS_PATH, new_flags):
                st.success("✅ Flags salvas com sucesso!")
            else:
                st.error("❌ Erro ao salvar flags.")


# ---------------------------------------------------------------------------
# TAB 5 — Pipeline de IA
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

    ai_tab1, ai_tab2, ai_tab3, ai_tab4 = st.tabs([
        "📊 Última Avaliação",
        "📈 Tendência Histórica",
        "📋 Golden Set",
        "▶ Executar Avaliação",
    ])

    all_results = _load_result_files()

    with ai_tab1:
        if not all_results:
            st.info(
                "Nenhuma avaliação encontrada. Use a aba '▶ Executar Avaliação' para gerar resultados."
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

    with ai_tab2:
        if not all_results:
            st.info("Nenhuma avaliação encontrada.")
        else:
            _render_trend_chart(all_results)
            if len(all_results) > 1:
                import pandas as pd
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
                        capture_output=True, text=True, timeout=300
                    )
                if result.returncode == 0:
                    st.success("✅ Avaliação concluída! Recarregue para ver os resultados.")
                else:
                    st.error(f"❌ Erro na avaliação:\n{result.stderr[:1000]}")
            else:
                st.error("Script `evaluate_rag.py` não encontrado.")


# ---------------------------------------------------------------------------
# Main render
# ---------------------------------------------------------------------------

def render_page() -> None:
    inject_glass_styles()

    if not _is_admin():
        st.markdown("""
            <div style="
                text-align:center; padding:60px 20px;
                background:rgba(239,68,68,0.06);
                border:1px solid rgba(239,68,68,0.2);
                border-radius:16px; margin-top:40px;
            ">
                <div style="font-size:2.5em; margin-bottom:12px;">🔒</div>
                <div style="color:#EF4444; font-size:1.1em; font-weight:600; margin-bottom:8px;">
                    Acesso Restrito
                </div>
                <div style="color:#94A3B8; font-size:0.88em;">
                    Esta página é exclusiva para administradores do SafetyAI.<br>
                    Se acredita ser administrador, verifique se o seu email está configurado em <code>ADMIN_EMAILS</code>.
                </div>
            </div>
        """, unsafe_allow_html=True)
        st.stop()
        return

    st.markdown("""
        <div class="page-header">
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor">
                <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"/>
            </svg>
            <h1>Painel de Administração</h1>
        </div>
        <p class="page-subtitle">Controlo total do SafetyAI — logs, planos, configurações e métricas de IA.</p>
    """, unsafe_allow_html=True)

    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📊 Visão Geral",
        "📋 Logs do Sistema",
        "💳 Planos & Preços",
        "⚙️ Configurações Avançadas",
        "🤖 Pipeline de IA",
    ])

    with tab1:
        _tab_overview()

    with tab2:
        _tab_logs()

    with tab3:
        _tab_plans()

    with tab4:
        _tab_advanced_config()

    with tab5:
        _tab_ai_pipeline()
