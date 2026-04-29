import streamlit as st
import logging
import os
import tempfile
import shutil
from typing import List, Dict, Any, Optional
import time

# Importa as configurações de tema e a nova função para injetar CSS de ícones nos botões
from safety_ai_app.theme_config import THEME, _get_material_icon_html_for_button_css, _get_material_icon_html
from safety_ai_app.web_interface.shared_styles import inject_glass_styles, glass_marker
from safety_ai_app.security.security_logger import log_security_event, SecurityEvent
from safety_ai_app.security.rate_limiter import check_rate_limit, RateLimitExceeded
from safety_ai_app.google_drive_integrator import (
    list_drive_folders,
    synchronize_user_drive_folder_to_chroma,
    synchronize_app_central_library_to_chroma,
    get_app_central_library_info
)
from safety_ai_app.nr_rag_qa import NRQuestionAnswering
from safety_ai_app.text_extractors import PROCESSABLE_MIME_TYPES

logger = logging.getLogger(__name__)


def _alert(msg: str, kind: str = "info") -> None:
    _CFG = {
        "error":   {"bg": "rgba(239,68,68,0.12)",  "border": "#EF4444", "color": "#FCA5A5", "icon": "error"},
        "warning": {"bg": "rgba(245,158,11,0.12)", "border": "#F59E0B", "color": "#FCD34D", "icon": "warning"},
        "info":    {"bg": "rgba(34,211,238,0.12)",  "border": "#22D3EE", "color": "#67E8F9", "icon": "info"},
        "success": {"bg": "rgba(74,222,128,0.12)", "border": "#4ADE80", "color": "#86EFAC", "icon": "check_circle"},
    }
    c = _CFG.get(kind, _CFG["info"])
    st.markdown(
        f'<div style="background:{c["bg"]};border-left:3px solid {c["border"]};'
        f'padding:0.5rem 0.75rem;border-radius:6px;margin:0.25rem 0;'
        f'color:{c["color"]};font-size:0.85rem;">'
        f'{_get_material_icon_html(c["icon"])} {msg}</div>',
        unsafe_allow_html=True,
    )


# --- Helper functions para renderização consistente de ícones e mensagens ---
def _render_info_like_message(message_type, message, icon_name=None):
    """
    Renderiza uma mensagem com estilo Streamlit (info, warning, success, error)
    permitindo a inclusão de um ícone SVG inline.
    """
    icon_html = _get_material_icon_html(icon_name) if icon_name else ""
    st.markdown(f"<div class='st-{message_type}-like'>{icon_html} {message}</div>", unsafe_allow_html=True)

# REMOVIDA A FUNÇÃO _get_st_button_label, pois os ícones serão injetados via CSS

# --- Helper function ---
def _refresh_rag_qa_instance():
    """
    Recarrega a instância de NRQuestionAnswering para refletir as últimas
    alterações na ChromaDB. Isso é crucial após adicionar/remover documentos.
    """
    if 'nr_qa' in st.session_state and isinstance(st.session_state.nr_qa, NRQuestionAnswering):
        st.cache_resource.clear()
        st.session_state.nr_qa = NRQuestionAnswering()
        logger.info("Instância NRQuestionAnswering recarregada no session_state após sincronização/limpeza.")
    else:
        logger.warning("Não foi possível recarregar a instância de NRQuestionAnswering, ela não está no session_state ou não é do tipo esperado.")

def _render_auto_sync_status_panel() -> None:
    """Render the auto-sync scheduler status card in the knowledge-base admin panel."""
    try:
        from safety_ai_app.auto_sync_scheduler import get_scheduler
        scheduler = get_scheduler()
        status = scheduler.get_status()
    except Exception as exc:
        logger.warning("Auto-sync scheduler not available: %s", exc)
        return

    if status["last_run_success"] is False:
        failed_message = status.get("last_run_message", "Erro desconhecido.")
        last_run_time = status.get("last_run_time")
        last_run_str = last_run_time.strftime("%d/%m/%Y %H:%M:%S") if last_run_time else "hora desconhecida"
        _alert(
            f"Sincronização automática falhou — última tentativa em {last_run_str}: {failed_message}. "
            "Verifique as credenciais do Google Drive e tente uma nova sincronização abaixo.",
            "error",
        )

    accent_green = THEME["colors"].get("accent_green", "#4ADE80")
    accent_cyan = THEME["colors"].get("accent_cyan", "#22D3EE")
    text_secondary = THEME["colors"].get("text_secondary", "#94A3B8")

    st.markdown(
        f'<div class="section-title">{_get_material_icon_html("schedule")} Sincronização Automática</div>',
        unsafe_allow_html=True,
    )

    is_syncing: bool = status["is_syncing"]
    last_success: Optional[bool] = status["last_run_success"]
    last_time = status["last_run_time"]
    next_time = status["next_run_time"]
    interval: int = status["interval_minutes"]
    message: str = status["last_run_message"]
    processed: int = status["last_processed_count"]

    last_time_str = last_time.strftime("%d/%m/%Y %H:%M:%S") if last_time else "Nunca"
    next_time_str = next_time.strftime("%d/%m/%Y %H:%M:%S") if next_time else "Aguardando inicialização..."

    if is_syncing:
        sync_status_icon = _get_material_icon_html("sync")
        sync_status_label = "Sincronizando agora..."
        status_color = accent_cyan
    elif last_success is True:
        sync_status_icon = _get_material_icon_html("check_circle")
        sync_status_label = "Última sincronização concluída com sucesso"
        status_color = accent_green
    elif last_success is False:
        sync_status_icon = _get_material_icon_html("error")
        sync_status_label = "Última sincronização falhou"
        status_color = "#F87171"
    else:
        sync_status_icon = _get_material_icon_html("hourglass_empty")
        sync_status_label = "Aguardando primeira execução automática"
        status_color = text_secondary

    st.markdown(
        f"""
        <div style="
            background: rgba(255,255,255,0.04);
            border: 1px solid rgba(74,222,128,0.25);
            border-radius: 12px;
            padding: 1rem 1.25rem;
            margin-bottom: 1rem;
        ">
            <div style="display:flex; align-items:center; gap:0.5rem; margin-bottom:0.75rem;">
                <span style="color:{status_color}; font-size:1.3em;">{sync_status_icon}</span>
                <span style="color:{status_color}; font-weight:600;">{sync_status_label}</span>
            </div>
            <div style="display:grid; grid-template-columns:1fr 1fr; gap:0.5rem 1.5rem; font-size:0.9em; color:{text_secondary};">
                <div><b>Intervalo automático:</b> a cada {interval} minutos</div>
                <div><b>Documentos na última execução:</b> {processed}</div>
                <div><b>Última execução:</b> {last_time_str}</div>
                <div><b>Próxima execução:</b> {next_time_str}</div>
                <div style="grid-column:1/-1;"><b>Resultado:</b> {message}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    sync_now_key = "auto_sync_trigger_now_kb"
    st.markdown(
        _get_material_icon_html_for_button_css(sync_now_key, "sync"),
        unsafe_allow_html=True,
    )
    if st.button(
        label="Sincronizar Agora (Auto-sync)",
        key=sync_now_key,
        help="Dispara uma sincronização incremental imediata em segundo plano.",
        disabled=is_syncing,
    ):
        triggered = scheduler.trigger_now()
        if triggered:
            _render_info_like_message(
                "success",
                "Sincronização automática disparada em segundo plano. "
                "Recarregue esta página em alguns momentos para ver o resultado.",
                THEME["icons"]["success_check"],
            )
        else:
            _render_info_like_message(
                "Uma sincronização já está em andamento. Aguarde a conclusão.",
                THEME["icons"]["warning_sign"],
            )


def render_page():
    inject_glass_styles()

    with st.container():
        st.markdown(glass_marker(), unsafe_allow_html=True)
        st.markdown(f'''
        <div class="page-header">
            {_get_material_icon_html(THEME["icons"]["brain_gear"])}
            <h1>{THEME.get("phrases", {}).get("knowledge_base_page_title", "Base de Conhecimento Curada")}</h1>
        </div>
        <div class="page-subtitle">Repositório central de normas e procedimentos validados pela engenharia de segurança.</div>
        ''', unsafe_allow_html=True)

    client = st.session_state.get("api_client")
    if not client:
        _render_info_like_message("error", "Erro ao conectar com o servidor central.", THEME["icons"]["error_x"])
        return

    # Se for admin, mostrar botão para ir ao painel administrativo
    if st.session_state.get("is_admin", False):
        st.markdown(
            f"""
            <div style="background: rgba(74, 222, 128, 0.1); border: 1px solid #4ade80; border-radius: 12px; padding: 15px; margin-bottom: 20px;">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <div>
                        <b style="color: #4ade80;">Você é Administrador</b><br>
                        <span style="font-size: 0.85rem; color: #94a3b8;">Use o painel de gestão para adicionar, remover ou desativar documentos.</span>
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )
        if st.button("🚀 Ir para Painel de Gestão Admin", use_container_width=True):
            st.session_state.page = "admin_knowledge_base"
            st.rerun()

    st.markdown(f'<div class="section-title">{_get_material_icon_html(THEME["icons"]["document_stack"])} Documentos Disponíveis</div>', unsafe_allow_html=True)
    _render_info_like_message("info", "Estes documentos alimentam a inteligência do Chat SST e dos geradores de documentos técnicos.", THEME["icons"]["info_circular_outline"])

    # Buscar documentos da API (Base Curada)
    with st.spinner("Carregando base de conhecimento..."):
        documents = client.list_knowledge()

    if documents:
        search_term = st.text_input("Filtrar documentos:", key="kb_search_docs_public").lower()
        if search_term:
            documents = [doc for doc in documents if search_term in doc.get('title', '').lower() or search_term in doc.get('category', '').lower()]

        for doc in documents:
            with st.container():
                st.markdown(f"""
                <div style="
                    border: 1px solid rgba(255, 255, 255, 0.1);
                    border-radius: 12px;
                    padding: 15px;
                    margin-bottom: 12px;
                    background-color: rgba(30, 41, 59, 0.3);
                ">
                    <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                        <div>
                            <span style="font-size: 1rem; font-weight: 600; color: #f8fafc;">
                                {_get_material_icon_html("description")} {doc.get('title', 'Sem Título')}
                            </span>
                            <div style="font-size: 0.8rem; color: #94a3b8; margin-top: 4px;">
                                Categoria: <b>{doc.get('category', 'Geral')}</b> • Arquivo: {doc.get('filename', 'N/A')}
                            </div>
                            {f'<div style="font-size: 0.8rem; color: #64748b; margin-top: 6px; font-style: italic;">{doc["description"]}</div>' if doc.get("description") else ""}
                        </div>
                        <div style="font-size: 0.75rem; background: rgba(34, 211, 238, 0.1); color: #22d3ee; padding: 3px 10px; border-radius: 20px; border: 1px solid rgba(34, 211, 238, 0.3);">
                            Curadoria Oficial
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
    else:
        _render_info_like_message("warning", "Nenhum documento disponível na base curada no momento.", THEME["icons"]["warning_sign"])

    st.markdown("<br><br>", unsafe_allow_html=True)
()

    else:
        _render_info_like_message("info", "Nenhum documento na base de conhecimento ainda. Sincronize ou faça upload para começar!", THEME["icons"]["generic_info"])