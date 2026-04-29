"""
Pacote de Chat — SafetyAI
Responsabilidade: Orquestração da página de chat, gestão de estado e integração com API/Drive.
"""

import streamlit as st
import logging
import io
from datetime import datetime

# Imports Internos do Pacote Chat
from ._styles import inject_chat_styles, render_welcome_header
from ._security import get_safe_markdown
from ._logic import (
    SHORTCUT_CHIPS, 
    generate_follow_ups, 
    extract_drive_search_keyword, 
    export_chat_docx
)
from ._renderer import (
    render_message, 
    render_typing_indicator, 
    render_follow_ups
)

# Imports Compartilhados da App
from safety_ai_app.theme_config import _get_material_icon_html
from safety_ai_app.web_interface.shared_styles import inject_glass_styles
from safety_ai_app.input_validators import sanitize_text_input
from safety_ai_app.security.rate_limiter import check_rate_limit, RateLimitExceeded
from safety_ai_app.security.security_logger import log_security_event, SecurityEvent
from safety_ai_app.api_client import SafetyAIAPIClient
from safety_ai_app.google_drive_integrator import list_drive_files_by_keyword

# Imports de Controle de Acesso (Feature Flags/Quota)
try:
    from safety_ai_app.feature_access import (
        check_chat_quota,
        increment_chat_messages_today,
        render_chat_quota_exceeded,
        render_upgrade_prompt,
        get_daily_chat_limit,
        get_chat_messages_sent_today,
        is_feature_globally_enabled,
    )
except ImportError:
    def check_chat_quota(): return True
    def increment_chat_messages_today(): pass
    def render_chat_quota_exceeded(): st.error("Quota excedida.")
    def render_upgrade_prompt(f): st.error(f"Upgrade necessário para {f}")
    def get_daily_chat_limit(): return 0
    def get_chat_messages_sent_today(): return 0
    def is_feature_globally_enabled(f): return True

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

def _init_session_state():
    if "messages" not in st.session_state: st.session_state.messages = []
    if "active_context_files" not in st.session_state: st.session_state.active_context_files = []
    if "pending_query" not in st.session_state: st.session_state.pending_query = None
    if "chat_mode" not in st.session_state: st.session_state.chat_mode = "deep"
    if "last_follow_ups" not in st.session_state: st.session_state.last_follow_ups = []

def render_page() -> None:
    """Função principal de renderização da página de chat."""
    if not is_feature_globally_enabled("chat"):
        render_upgrade_prompt("Chat SST")
        return

    inject_glass_styles()
    inject_chat_styles()
    _init_session_state()

    # --- Header ---
    st.markdown(f"""
    <div class="chat-header">
        <div class="chat-header-icon">{_get_material_icon_html("smart_toy")}</div>
        <div class="chat-header-text">
            <h1>Chat SST</h1>
            <p>Assistente de Segurança do Trabalho</p>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # --- Toolbar ---
    hcols = st.columns([1, 1, 1, 1])
    with hcols[0]:
        if st.button("⚡ Consulta Rápida", use_container_width=True, 
                     type="primary" if st.session_state.chat_mode == "quick" else "secondary"):
            st.session_state.chat_mode = "quick"
            st.rerun()
    with hcols[1]:
        if st.button("🔬 Análise Técnica", use_container_width=True,
                     type="primary" if st.session_state.chat_mode == "deep" else "secondary"):
            st.session_state.chat_mode = "deep"
            st.rerun()
    with hcols[2]:
        if st.session_state.messages:
            docx_bytes = export_chat_docx(st.session_state.messages)
            if docx_bytes:
                st.download_button("⬇ Exportar", data=docx_bytes, 
                                 file_name=f"SafetyAI_Chat_{datetime.now().strftime('%Y%m%d_%H%M')}.docx",
                                 mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                                 use_container_width=True)
    with hcols[3]:
        if st.session_state.messages:
            if st.button("🗑️ Limpar", use_container_width=True):
                st.session_state.messages = []; st.session_state.last_follow_ups = []; st.rerun()

    # --- Quota Progress Bar ---
    _daily_limit = get_daily_chat_limit()
    if _daily_limit > 0:
        _sent = get_chat_messages_sent_today()
        _pct = int((_sent / _daily_limit) * 100)
        _color = "#ef4444" if _sent >= _daily_limit else "#4ade80"
        st.markdown(f"""
            <div style="display:flex; align-items:center; gap:10px; background: rgba(15,23,42,0.7); border-radius:10px; padding:8px 14px; margin-bottom:8px; font-size:0.83rem; color:#94a3b8;">
                <span>💬 Mensagens hoje:</span>
                <div style="flex:1; background:#1e293b; border-radius:4px; height:6px; overflow:hidden;">
                    <div style="width:{_pct}%; background:{_color}; height:100%; border-radius:4px; transition:width .3s;"></div>
                </div>
                <span style="color:#f8fafc; font-weight:600;">{_sent}/{_daily_limit}</span>
            </div>
            """, unsafe_allow_html=True)

    # --- Knowledge Base Selector ---
    with st.expander("📚 Base de Conhecimento Focada", expanded=False):
        api_client = st.session_state.get("api_client") or SafetyAIAPIClient()
        curated_docs = api_client.list_knowledge()
        if curated_docs:
            options = {f"{d['title']} ({d['category']})": d for d in curated_docs}
            selected = st.multiselect("Documentos para foco:", options=list(options.keys()))
            st.session_state.active_context_files = [
                {'id': options[t]['id'], 'name': options[t]['title'], 'source': 'curated'} for t in selected
            ]
        else:
            _alert("Nenhum documento disponível.", "info")

    # --- Chat History Container ---
    chat_container = st.container(height=450, border=False)

    # --- Input Form ---
    with st.form(key='chat_form', clear_on_submit=True):
        cols = st.columns([0.88, 0.12])
        user_input = cols[0].text_input("Pergunta", placeholder="Faça qualquer pergunta sobre SST...", label_visibility="collapsed")
        submitted = cols[1].form_submit_button("", icon=":material/send:", use_container_width=True)

    # --- Logic Orchestration ---
    query_to_process = None
    if submitted and user_input.strip():
        query_to_process = sanitize_text_input(user_input, max_length=5000)
    elif st.session_state.pending_query:
        query_to_process = st.session_state.pending_query
        st.session_state.pending_query = None

    if query_to_process:
        if not check_chat_quota():
            render_chat_quota_exceeded()
        else:
            try:
                check_rate_limit("chat_llm")
                
                # Inicia processamento
                st.session_state.messages.append({"role": "user", "content": query_to_process})
                st.session_state.last_follow_ups = []
                
                with chat_container:
                    for idx, m in enumerate(st.session_state.messages):
                        render_message(m, idx, get_safe_markdown)
                    
                    stream_slot = st.empty()
                    render_typing_indicator()
                    
                    api_client = st.session_state.get("api_client") or SafetyAIAPIClient()
                    chat_history = [{"role": m["role"], "content": m["content"]} for m in st.session_state.messages[:-1]]
                    
                    # Contexto de Modo (Quick vs Deep)
                    mode_prompt = "MODO CONSULTA RÁPIDA: Seja objetivo." if st.session_state.chat_mode == "quick" else "MODO ANÁLISE TÉCNICA: Detalhe NRs."
                    context = [mode_prompt]
                    
                    # Streaming
                    full_text = ""
                    for chunk in api_client.stream_ask(query_to_process, chat_history, context):
                        full_text += chunk
                        content_html = get_safe_markdown(full_text + " ▌")
                        stream_slot.markdown(f'<div class="msg-ai"><div class="msg-ai-avatar">{_get_material_icon_html("smart_toy")}</div><div class="msg-ai-content">{content_html}</div></div>', unsafe_allow_html=True)
                    
                    # Pós-processamento: Downloads e Follow-ups
                    downloads = api_client.get_last_suggested_downloads()
                    kw = extract_drive_search_keyword(query_to_process)
                    if kw:
                        files = list_drive_files_by_keyword(st.session_state.get("user_drive_service", "app_service"), kw)
                        for f in files[:3]:
                            downloads.append({"document_name": f['name'], "file_type": f['mimeType'], "drive_file_id": f['id']})
                    
                    st.session_state.messages.append({
                        "role": "assistant", "content": full_text, "suggested_downloads": downloads
                    })
                    st.session_state.last_follow_ups = generate_follow_ups(query_to_process, full_text)
                    increment_chat_messages_today()
                    st.rerun()

            except RateLimitExceeded as rle:
                _alert(f"Aguarde {rle.retry_after:.0f}s.", "warning")
            except Exception as e:
                logger.error(f"Chat error: {e}")
                _alert("Erro ao processar sua pergunta.", "error")

    # Renderização Inicial / Padrão
    with chat_container:
        if not st.session_state.messages:
            render_welcome_header()
            # Render Chips
            cols = st.columns(4)
            for i, (icon, label) in enumerate(SHORTCUT_CHIPS[:4]):
                if cols[i].button(f"{icon} {label}", key=f"s1_{i}", use_container_width=True):
                    st.session_state.pending_query = label; st.rerun()
            cols2 = st.columns(4)
            for i, (icon, label) in enumerate(SHORTCUT_CHIPS[4:]):
                if cols2[i].button(f"{icon} {label}", key=f"s2_{i}", use_container_width=True):
                    st.session_state.pending_query = label; st.rerun()
            st.markdown("</div></div>", unsafe_allow_html=True)
        else:
            for idx, m in enumerate(st.session_state.messages):
                render_message(m, idx, get_safe_markdown)
            if st.session_state.last_follow_ups:
                render_follow_ups(st.session_state.last_follow_ups)
