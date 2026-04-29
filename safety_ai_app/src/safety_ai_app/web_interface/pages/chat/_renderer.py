"""
Módulo de Renderização — SafetyAI Chat
Responsabilidade: Exibir mensagens, downloads, indicadores de digitação e follow-ups.
"""

import streamlit as st
import logging
from typing import Callable
from safety_ai_app.theme_config import _get_material_icon_html
from safety_ai_app.google_drive_integrator import get_file_bytes_for_download

logger = logging.getLogger(__name__)

def render_message(msg: dict, idx: int, markdown_func: Callable):
    """Renderiza uma única mensagem (usuário ou IA) com seu estilo correspondente."""
    content = msg.get("content", "")
    if isinstance(content, dict):
        content = content.get("answer", content.get("content", str(content)))
    if not isinstance(content, str):
        content = str(content) if content else ""
    
    if msg.get("role") == "user":
        # Escapa tags HTML básicas para o usuário (prevenção simples de XSS no lado do cliente)
        safe_content = content.replace('<', '&lt;').replace('>', '&gt;')
        st.markdown(f"""
        <div class="msg-user">
            <div class="msg-user-bubble">{safe_content}</div>
        </div>
        """, unsafe_allow_html=True)
    else:
        # Usa o processador de Markdown seguro extraído
        content_html = markdown_func(content)
        st.markdown(f"""
        <div class="msg-ai">
            <div class="msg-ai-avatar">
                {_get_material_icon_html("smart_toy")}
            </div>
            <div class="msg-ai-content">{content_html}</div>
        </div>
        """, unsafe_allow_html=True)
        
        if "suggested_downloads" in msg and msg["suggested_downloads"]:
            render_downloads(msg["suggested_downloads"], idx)

def render_downloads(downloads: list, msg_idx: int):
    """Renderiza botões de download para arquivos sugeridos do Drive."""
    mime_icons = {
        'application/pdf': '📕',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document': '📘',
        'text/plain': '📄',
        'application/vnd.google-apps.document': '📝',
    }
    mime_labels = {
        'application/pdf': 'PDF',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document': 'DOCX',
        'text/plain': 'TXT',
        'application/vnd.google-apps.document': 'Google Doc',
    }

    st.markdown("""
    <div style="background: rgba(139,92,246,0.08); border: 1px solid rgba(139,92,246,0.25); border-radius: 12px; padding: 12px 16px; margin: 10px 0 4px 0;">
        <div style="font-size:0.82rem; color:#a78bfa; font-weight:600; margin-bottom:8px; letter-spacing:0.03em;">
            📁 Documentos Relacionados na Biblioteca
        </div>
    </div>
    """, unsafe_allow_html=True)

    cols = st.columns(min(len(downloads), 3))
    for i, doc in enumerate(downloads):
        with cols[i % 3]:
            icon = mime_icons.get(doc.get('file_type', ''), '📄')
            label_type = mime_labels.get(doc.get('file_type', ''), 'Arquivo')
            short_name = doc['document_name'][:22] + "…" if len(doc['document_name']) > 22 else doc['document_name']
            try:
                # Recupera bytes do Drive (orquestrado via service no session_state)
                file_bytes = get_file_bytes_for_download(
                    st.session_state.user_drive_service,
                    doc['drive_file_id'],
                    doc['file_type'],
                    doc['file_type']
                )
                ext = {
                    'application/pdf': '.pdf',
                    'application/vnd.openxmlformats-officedocument.wordprocessingml.document': '.docx',
                    'text/plain': '.txt',
                    'application/vnd.google-apps.document': '.docx'
                }.get(doc['file_type'], '')
                filename = doc['document_name'] + ext if not doc['document_name'].endswith(ext) else doc['document_name']
                
                st.download_button(
                    label=f"{icon} {short_name} [{label_type}]",
                    data=file_bytes,
                    file_name=filename,
                    mime=doc['file_type'],
                    key=f"dl_{msg_idx}_{i}_{doc['drive_file_id']}",
                    use_container_width=True,
                    help=doc['document_name'],
                )
            except Exception as e:
                logger.error(f"Erro ao processar download do documento {doc['document_name']}: {e}")
                st.markdown(f"<span style='font-size:0.78rem;color:#64748b;'>{icon} {short_name} (Indisponível)</span>", unsafe_allow_html=True)

def render_follow_ups(follow_ups: list):
    """Renderiza chips de perguntas sugeridas."""
    if not follow_ups:
        return
    st.markdown('<div style="margin: 6px 0 2px 0; font-size:0.78rem; color:#64748b; font-style:italic;">Perguntas de acompanhamento:</div>', unsafe_allow_html=True)
    cols = st.columns(len(follow_ups))
    for i, q in enumerate(follow_ups):
        with cols[i]:
            if st.button(q, key=f"followup_{i}", use_container_width=True):
                st.session_state.pending_query = q
                st.session_state.last_follow_ups = []
                st.rerun()

def render_typing_indicator():
    """Exibe a animação de 'digitando...' da IA."""
    st.markdown(f"""
    <div class="typing-indicator">
        <div class="msg-ai-avatar">
            {_get_material_icon_html("smart_toy")}
        </div>
        <div class="typing-dots">
            <span></span><span></span><span></span>
        </div>
    </div>
    """, unsafe_allow_html=True)
