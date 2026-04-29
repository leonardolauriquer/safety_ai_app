"""
Módulo de Gestão de Sessão — SafetyAI
Responsabilidade: Centralizar a inicialização, validação e persistência do st.session_state.
Elimina a necessidade do antigo session_state.py.
"""

import uuid
import time
import os
import logging
import streamlit as st
from queue import Queue
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

# Configurações Padrão de Sessão (Consolidado)
SESSION_DEFAULTS = {
    # Identificadores e Logs
    "session_id": None,
    "correlation_id": None,
    "last_activity": None,
    
    # Autenticação e Usuário
    "logged_in": False,
    "auth_status": False,
    "user_email": "",
    "user_name": "Usuário",
    "user_role": "user",
    "is_admin": False,
    "id_token": None,
    "user_plan": "free",
    
    # Integrações
    "api_client": None,
    "nr_qa": None,
    "app_drive_service": None,
    "user_drive_service": None,
    "user_drive_auth_needed": False,
    "user_drive_auth_error": None,
    "user_drive_auth_url": None,
    
    # Chat e Conteúdo
    "messages": [],
    "active_context_files": [],
    "processed_documents": [],
    "dynamic_context_texts": [],
    "pending_query": None,
    "chat_mode": "deep",
    "last_follow_ups": [],
    "user_query_input": "",
    "show_document_context_selector": False,
    
    # Sincronização
    "sync_result_queue": None,
    "sync_status_data": {
        "check_performed": False, "check_in_progress": False,
        "pending_files_count": 0, "in_progress": False, "finished": False,
        "success": False, "message": "Sincronização não iniciada.",
        "processed_count": 0, "total_count": 0, "current_doc_name": "",
        "last_check_time": None, "sync_thread": None, "sync_thread_id": None,
    },
    
    # UI/Navegação
    "current_page": "home",
    "sidebar_state": "collapsed",
    "warmup_done": False,
    "nav_request": "",
    "trigger_login_flow_rerun_from_iframe": False,
}

def initialize_session():
    """Inicializa todas as variáveis de sessão com seus valores padrão se não existirem."""
    if "session_id" not in st.session_state or not st.session_state.session_id:
        st.session_state.session_id = str(uuid.uuid4())
    
    if "correlation_id" not in st.session_state or not st.session_state.correlation_id:
        st.session_state.correlation_id = str(uuid.uuid4())[:8]
    
    if "last_activity" not in st.session_state:
        st.session_state.last_activity = time.time()

    for key, default_value in SESSION_DEFAULTS.items():
        if key not in st.session_state:
            # Inicialização especial para Queues que não podem ser clonadas facilmente
            if key == "sync_result_queue":
                st.session_state[key] = Queue()
            else:
                st.session_state[key] = default_value
    
    # Inicializa Admin Status
    _refresh_admin_status()

def _refresh_admin_status():
    """Verifica se o email atual está na lista de admins do ambiente."""
    email = st.session_state.get("user_email", "").strip().lower()
    if email:
        raw_admins = os.environ.get("ADMIN_EMAILS", "")
        admin_set = {e.strip().lower() for e in raw_admins.split(",") if e.strip()}
        st.session_state.is_admin = email in admin_set
        if st.session_state.is_admin:
            st.session_state.user_role = "admin"

def initialize_post_login(user_email: str, user_name: str, id_token: str = None):
    """Configura o estado após login bem-sucedido e cria a mensagem de boas-vindas."""
    st.session_state.logged_in = True
    st.session_state.auth_status = True
    st.session_state.user_email = user_email
    st.session_state.user_name = user_name
    st.session_state.id_token = id_token
    
    _refresh_admin_status()
    
    if not st.session_state.messages:
        welcome_msg = (
            f"Olá, **{user_name}**! Seja muito bem-vindo(a) ao **SafetyAI**!\n\n"
            f"Sou seu **assistente de IA especializado** em *Saúde e Segurança do Trabalho (SST)* no Brasil. \n"
            f"Estou aqui para te auxiliar com as **Normas Regulamentadoras** e diversos outros tópicos cruciais da área. \n\n"
            f"**Como posso te ajudar hoje?**"
        )
        st.session_state.messages.append({
            "role": "ai", 
            "content": {"answer": welcome_msg, "suggested_downloads": []}
        })

def touch_activity():
    """Atualiza o timestamp de atividade."""
    st.session_state.last_activity = time.time()

def is_session_expired(timeout_seconds: int = 1800) -> bool:
    """Verifica se a sessão expirou por inatividade."""
    last = st.session_state.get("last_activity")
    if not last: return False
    return (time.time() - last) > timeout_seconds

def reset_session():
    """Limpa dados sensíveis da sessão (Logout)."""
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    initialize_session()
