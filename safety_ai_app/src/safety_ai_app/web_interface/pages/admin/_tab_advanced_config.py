"""
TAB 4 — Configurações Avançadas
Painel de Administração SafetyAI

Sub-tabs: Administradores, Sincronização, Configurações de IA, Feature Flags.
"""

import logging
import os

import streamlit as st

from safety_ai_app.web_interface.pages.admin._helpers import (
    _load_json,
    _save_json,
    _load_persisted_admin_emails,
    _save_persisted_admin_emails,
    _AI_CONFIG_PATH,
    _FEATURE_FLAGS_PATH,
)

logger = logging.getLogger(__name__)

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


def _tab_advanced_config() -> None:
    conf_tab1, conf_tab2, conf_tab3, conf_tab4 = st.tabs([
        "👤 Administradores",
        "🔄 Sincronização",
        "🤖 Configurações de IA",
        "🚩 Feature Flags",
    ])

    # ------------------------------------------------------------------
    with conf_tab1:
        st.markdown('<div class="section-title">Gestão de Administradores</div>', unsafe_allow_html=True)
        st.markdown("""
            <div class="result-card" style="padding:12px 16px; margin-bottom:12px;">
                <div style="color:#4ADE80; font-size:0.85em;">
                    ✅ Administradores adicionados aqui são <strong>persistidos em disco</strong> (admin_config.json)
                    e permanecem ativos após reinicialização do servidor.<br>
                    A variável de ambiente <code>ADMIN_EMAILS</code> também continua sendo verificada.
                </div>
            </div>
        """, unsafe_allow_html=True)

        raw_env = os.environ.get("ADMIN_EMAILS", "")
        env_admins = [e.strip().lower() for e in raw_env.split(",") if e.strip()]
        persisted_admins = _load_persisted_admin_emails()
        current_admins = sorted(set(env_admins + persisted_admins))

        st.markdown("**Administradores actuais:**")
        if current_admins:
            for email in current_admins:
                source = "env" if email in env_admins else "arquivo"
                st.markdown(f"- `{email}` _{source}_")
        else:
            st.info("Nenhum administrador configurado.")

        st.markdown("**Adicionar administrador:**")
        new_admin_email = st.text_input("Email do novo administrador", key="admin_new_email",
                                         placeholder="email@exemplo.com")
        if st.button("➕ Adicionar e Salvar", key="admin_add_btn"):
            if new_admin_email and "@" in new_admin_email:
                email_clean = new_admin_email.strip().lower()
                if email_clean not in current_admins:
                    updated = list(set(persisted_admins + [email_clean]))
                    os.environ["ADMIN_EMAILS"] = ",".join(set(env_admins + [email_clean]))
                    if _save_persisted_admin_emails(updated):
                        st.success(f"✅ `{email_clean}` adicionado e salvo permanentemente.")
                    else:
                        st.warning(f"⚠️ `{email_clean}` adicionado na sessão, mas falhou ao salvar em disco.")
                    st.rerun()
                else:
                    st.warning("Este email já é administrador.")
            else:
                st.error("Insira um email válido.")

        if persisted_admins:
            st.markdown("**Remover administrador (arquivo):**")
            email_to_remove = st.selectbox("Selecione o email para remover", persisted_admins, key="admin_remove_select")
            if st.button("🗑️ Remover do arquivo", key="admin_remove_btn"):
                updated = [e for e in persisted_admins if e != email_to_remove]
                if _save_persisted_admin_emails(updated):
                    st.success(f"✅ `{email_to_remove}` removido do arquivo.")
                    st.rerun()
                else:
                    st.error("Falha ao salvar alterações.")

    # ------------------------------------------------------------------
    with conf_tab2:
        st.markdown('<div class="section-title">Sincronização Automática</div>', unsafe_allow_html=True)
        try:
            from safety_ai_app.auto_sync_scheduler import get_scheduler, DEFAULT_INTERVAL_MINUTES
            scheduler = get_scheduler()
            status = scheduler.get_status()

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

    # ------------------------------------------------------------------
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

    # ------------------------------------------------------------------
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
