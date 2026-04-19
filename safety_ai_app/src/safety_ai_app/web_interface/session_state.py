import uuid
import time
import os
from queue import Queue
import streamlit as st
import logging

logger = logging.getLogger(__name__)

SESSION_IDLE_TIMEOUT_SECONDS = 1800


def touch_last_activity() -> None:
    """Atualiza o timestamp da última interação do usuário."""
    st.session_state.last_activity = time.time()


def is_session_idle_expired() -> bool:
    """Retorna True se a sessão ficou inativa por mais de SESSION_IDLE_TIMEOUT_SECONDS."""
    last = st.session_state.get("last_activity")
    if last is None:
        return False
    return (time.time() - last) > SESSION_IDLE_TIMEOUT_SECONDS


def initialize_common(get_qa_instance_cached, get_app_drive_service_cached, set_correlation_id) -> None:
    if "session_id" not in st.session_state:
        st.session_state.session_id = str(uuid.uuid4())
    if "correlation_id" not in st.session_state:
        st.session_state.correlation_id = str(uuid.uuid4())[:8]
        set_correlation_id(st.session_state.correlation_id)
    if "current_page" not in st.session_state:
        st.session_state.current_page = "home"
    if "user_name" not in st.session_state:
        st.session_state.user_name = "Leo"
    if "user_email" not in st.session_state:
        st.session_state.user_email = ""
    if "is_admin" not in st.session_state:
        st.session_state.is_admin = False
    if "user_plan" not in st.session_state:
        st.session_state.user_plan = "free"
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False
    if "nr_qa" not in st.session_state:
        st.session_state.nr_qa = get_qa_instance_cached()
    if "app_drive_service" not in st.session_state:
        st.session_state.app_drive_service = get_app_drive_service_cached()
    if "user_drive_service" not in st.session_state:
        st.session_state.user_drive_service = None
    if "user_drive_auth_needed" not in st.session_state:
        st.session_state.user_drive_auth_needed = False
    if "user_drive_auth_error" not in st.session_state:
        st.session_state.user_drive_auth_error = None
    if "trigger_login_flow_rerun_from_iframe" not in st.session_state:
        st.session_state.trigger_login_flow_rerun_from_iframe = False
    if "nav_request" not in st.session_state:
        st.session_state.nav_request = ""
    if "sync_result_queue" not in st.session_state:
        st.session_state.sync_result_queue = Queue()
    if "sync_status_data" not in st.session_state:
        st.session_state.sync_status_data = {
            "check_performed": False, "check_in_progress": False,
            "pending_files_count": 0, "in_progress": False, "finished": False,
            "success": False, "message": "Sincronização não iniciada.",
            "processed_count": 0, "total_count": 0, "current_doc_name": "",
            "last_check_time": None, "sync_thread": None, "sync_thread_id": None,
        }
    for key in ["sync_check_performed", "sync_pending_files_count", "sync_check_in_progress",
                "sync_process_expected_to_be_active", "sync_finished", "sync_success",
                "sync_message", "sync_start_time", "sync_thread", "sync_thread_id",
                "sync_processed_count", "sync_total_count", "sync_current_doc_name",
                "sync_progress_updates"]:
        if key in st.session_state:
            del st.session_state[key]


def _refresh_is_admin() -> None:
    """Re-evaluate is_admin based on current user_email and ADMIN_EMAILS env var."""
    user_email = st.session_state.get("user_email", "").strip().lower()
    if user_email:
        raw = os.environ.get("ADMIN_EMAILS", "")
        admin_set = {e.strip().lower() for e in raw.split(",") if e.strip()}
        st.session_state.is_admin = user_email in admin_set


def initialize_post_login() -> None:
    _refresh_is_admin()
    if "messages" not in st.session_state:
        st.session_state.messages = []
        welcome_message = (
            f"Olá, **{st.session_state.user_name}**! Seja muito bem-vindo(a) ao **SafetyAI**!\n\n"
            f"Sou seu **assistente de IA especializado** em *Saúde e Segurança do Trabalho (SST)* no Brasil. \n"
            f"Estou aqui para te auxiliar com as **Normas Regulamentadoras** e diversos outros tópicos cruciais da área. "
            f"Pode me perguntar sobre legislação, boas práticas, dimensionamento e muito mais!\n\n"
            f"**Como posso te ajudar hoje?** Conte-me!"
        )
        st.session_state.messages.append({"role": "ai", "content": {"answer": welcome_message, "suggested_downloads": []}})
    if "user_query_input" not in st.session_state:
        st.session_state.user_query_input = ""
    if "processed_documents" not in st.session_state:
        st.session_state.processed_documents = []
    if "dynamic_context_texts" not in st.session_state:
        st.session_state.dynamic_context_texts = []
    if "show_document_context_selector" not in st.session_state:
        st.session_state.show_document_context_selector = False
    if "active_context_files" not in st.session_state:
        st.session_state.active_context_files = []
