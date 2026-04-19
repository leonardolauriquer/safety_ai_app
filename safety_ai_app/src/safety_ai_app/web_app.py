import os
import sys
import time
import streamlit as st
import logging
from typing import Optional, Any

script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(script_dir, '..', '..'))
src_path = os.path.abspath(os.path.join(project_root, 'src'))
if src_path not in sys.path:
    sys.path.insert(0, src_path)

if "project_root" not in st.session_state:
    st.session_state.project_root = project_root

from safety_ai_app.logging_config import setup_logging, set_correlation_id
setup_logging()
logger = logging.getLogger(__name__)

try:
    from safety_ai_app.theme_config import GLOBAL_STYLES, THEME, _get_material_icon_html_for_button_css, _get_material_icon_html
except ImportError as e:
    logger.critical(f"[ERRO CRÍTICO] Falha ao importar theme_config: {e}.")
    st.error(f"Erro crítico: Não foi possível carregar as configurações de tema. Detalhes: {e}")
    st.stop()

st.set_page_config(
    page_title=THEME["phrases"]["app_title"],
    page_icon=os.path.join(project_root, THEME["images"]["page_icon"]),
    layout="wide",
    initial_sidebar_state="collapsed"
)

try:
    from safety_ai_app.google_drive_integrator import (
        get_google_drive_user_creds_and_auth_info,
        get_google_drive_service_user,
        get_service_account_drive_service,
        GoogleDriveIntegrator,
        get_file_bytes_by_id,
    )
except Exception as e:
    logger.critical(f"[ERRO CRÍTICO] Falha ao importar google_drive_integrator: {e}.")
    st.error(f"Erro crítico: Não foi possível carregar o integrador do Google Drive. Detalhes: {e}")
    st.stop()

try:
    from safety_ai_app.nr_rag_qa import NRQuestionAnswering, start_model_warmup, is_warmup_complete
except Exception as e:
    logger.critical(f"[ERRO CRÍTICO] Falha ao importar nr_rag_qa: {e}.")
    st.error(f"Erro crítico: Não foi possível carregar o módulo RAG QA. Detalhes: {e}")
    st.stop()

from safety_ai_app.web_interface.utils import get_image_base64 as _get_image_base64, process_markdown_for_external_links
from safety_ai_app.web_interface import session_state as _ss
from safety_ai_app.security.security_logger import log_security_event, SecurityEvent


def get_image_base64(image_path: str) -> str:
    return _get_image_base64(project_root, image_path)


@st.cache_resource
def get_qa_instance_cached() -> Optional[NRQuestionAnswering]:
    try:
        return NRQuestionAnswering()
    except Exception as e:
        logger.critical(f"[ERRO CRÍTICO] ERRO ao inicializar NRQuestionAnswering: {e}", exc_info=True)
        st.error(f"Erro crítico ao inicializar o serviço de IA. Detalhes: {e}")
        return None


@st.cache_resource
def get_app_drive_service_cached() -> Optional[Any]:
    try:
        return get_service_account_drive_service()
    except Exception as e:
        logger.error(f"[ERRO] ERRO ao inicializar o serviço da conta de aplicativo: {e}", exc_info=True)
        return None


@st.cache_resource
def _trigger_model_warmup_once() -> bool:
    """Start background model pre-loading exactly once per app lifecycle."""
    start_model_warmup()
    return True


@st.cache_resource
def _start_auto_sync_scheduler() -> bool:
    """Start the background auto-sync scheduler exactly once per app lifecycle."""
    try:
        from safety_ai_app.auto_sync_scheduler import get_scheduler, DEFAULT_INTERVAL_MINUTES
        from safety_ai_app.web_interface.pages.settings_page import load_user_settings

        saved_settings = load_user_settings()
        try:
            raw_interval = saved_settings.get("admin", {}).get(
                "auto_sync_interval_minutes", DEFAULT_INTERVAL_MINUTES
            )
            saved_interval = max(1, min(int(raw_interval), 1440))
        except (TypeError, ValueError):
            logger.warning(
                "Invalid auto_sync_interval_minutes in settings; falling back to %d min.",
                DEFAULT_INTERVAL_MINUTES,
            )
            saved_interval = DEFAULT_INTERVAL_MINUTES

        scheduler = get_scheduler(interval_minutes=saved_interval)
        scheduler.configure(
            get_qa=get_qa_instance_cached,
            get_drive_service=get_app_drive_service_cached,
        )
        scheduler.start()
        logger.info(
            "Auto-sync scheduler initialised and started (interval: %d min).",
            saved_interval,
        )
    except Exception as exc:
        logger.error("Failed to start auto-sync scheduler: %s", exc, exc_info=True)
    return True


def get_user_drive_service_wrapper() -> Optional[str]:
    session_user_id = st.session_state.get("session_id")
    creds, auth_url, auth_error_message = get_google_drive_user_creds_and_auth_info(
        user_id=session_user_id
    )
    st.session_state.user_drive_auth_needed = False
    st.session_state.user_drive_auth_url = None
    st.session_state.user_drive_auth_error = None

    if auth_url:
        st.session_state.user_drive_auth_needed = True
        st.session_state.user_drive_auth_url = auth_url
        return None
    elif auth_error_message == "REDIRECTING_SUCCESS":
        return "REDIRECTING_SUCCESS"
    elif auth_error_message:
        st.session_state.user_drive_auth_error = auth_error_message
        return None
    elif creds:
        service = get_google_drive_service_user(creds)
        if service:
            st.session_state.logged_in = True
            st.session_state.user_drive_service = service
            return service
    else:
        st.session_state.user_drive_auth_needed = True
    return None


def _cleanup_temp_files(max_age_seconds: int = 3600) -> None:
    """Remove arquivos temporários com mais de max_age_seconds da pasta downloads_temp."""
    temp_dir = os.path.join(project_root, "downloads_temp")
    if not os.path.isdir(temp_dir):
        return
    now = time.time()
    removed = 0
    try:
        for fname in os.listdir(temp_dir):
            fpath = os.path.join(temp_dir, fname)
            if os.path.isfile(fpath):
                age = now - os.path.getmtime(fpath)
                if age > max_age_seconds:
                    os.remove(fpath)
                    removed += 1
        if removed:
            log_security_event(SecurityEvent.TEMP_CLEANUP, detail=f"{removed} arquivo(s) temporários removidos de downloads_temp")
            logger.info(f"[TEMP_CLEANUP] {removed} arquivo(s) antigos removidos de '{temp_dir}'.")
    except Exception as e:
        logger.warning(f"[TEMP_CLEANUP] Erro ao limpar downloads_temp: {e}")


def do_logout(reason: str = "user_action") -> None:
    try:
        user_email = st.session_state.get("user_email")
        from safety_ai_app.auth.google_auth import _delete_creds as _gdrive_delete_creds
        _gdrive_delete_creds(user_id=st.session_state.get("session_id"))
        st.session_state.logged_in = False
        st.session_state.user_drive_service = None
        st.session_state.user_drive_auth_needed = False
        st.session_state.user_drive_auth_url = None
        st.session_state.user_drive_auth_error = None
        if "messages" in st.session_state:
            st.session_state.messages = []
        st.session_state.current_page = "home"
        if "last_activity" in st.session_state:
            del st.session_state["last_activity"]
        log_security_event(SecurityEvent.LOGOUT, user_email=user_email, detail=reason)
        st.query_params.clear()
        st.query_params["page"] = "home"
        st.query_params["sync_done"] = "true"
    except Exception as e:
        logger.error(f"Erro durante o logout: {e}", exc_info=True)
        st.error(f"Ocorreu um erro ao tentar fazer logout. Detalhes: {e}")
    st.rerun()


def main_app_entrypoint() -> None:
    from safety_ai_app.web_interface.login_page import render_login_page
    from safety_ai_app.web_interface.sidebar import render_sidebar_menu
    from safety_ai_app.web_interface.router import build_page_registry, route_page, VALID_PAGES
    from safety_ai_app.web_interface.pages.sync_page import render_page as render_sync_page
    from safety_ai_app.web_interface.session_state import is_session_idle_expired, touch_last_activity
    from safety_ai_app.web_interface.pwa_support import get_pwa_injection_html

    _trigger_model_warmup_once()
    _start_auto_sync_scheduler()
    _cleanup_temp_files()

    st.markdown("""
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
        <link href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:opsz,wght,FILL,GRAD@20..48,100..700,0..1,-50..200" rel="stylesheet">
    """, unsafe_allow_html=True)
    st.markdown(GLOBAL_STYLES, unsafe_allow_html=True)
    st.markdown(get_pwa_injection_html(project_root), unsafe_allow_html=True)
    st.markdown(_get_material_icon_html_for_button_css("start_chat_button", "chat"), unsafe_allow_html=True)
    st.markdown(_get_material_icon_html_for_button_css("explore_", "arrow_forward"), unsafe_allow_html=True)

    _ss.initialize_common(get_qa_instance_cached, get_app_drive_service_cached, set_correlation_id)

    requested_page_from_url = st.query_params.get("page")
    sync_done_in_url = st.query_params.get("sync_done") == "true"

    logger.info(f"[APP_FLOW] Session: {st.session_state.get('session_id', 'N/A')}, "
                f"logged_in={st.session_state.logged_in}, sync_done={sync_done_in_url}, page={requested_page_from_url}")

    if requested_page_from_url == "logout_action":
        do_logout()
        return

    user_drive_service_result = get_user_drive_service_wrapper()
    if user_drive_service_result == "REDIRECTING_SUCCESS":
        st.query_params.update({"page": "sync_page"})
        if "sync_done" in st.query_params:
            del st.query_params["sync_done"]
        st.rerun()
        st.stop()
        return

    if not st.session_state.logged_in:
        logger.info("[APP_FLOW] Usuário não está logado. Renderizando tela de login.")
        render_login_page(project_root, THEME, get_user_drive_service_wrapper)
        return

    if is_session_idle_expired():
        logger.info("[APP_FLOW] Sessão expirada por inatividade.")
        log_security_event(
            SecurityEvent.SESSION_TIMEOUT,
            user_email=st.session_state.get("user_email"),
            detail="Sessão encerrada por inatividade de 30 minutos.",
        )
        st.warning("⏱️ Sua sessão expirou por inatividade. Faça login novamente.")
        do_logout(reason="session_timeout")
        return

    touch_last_activity()

    if st.session_state.logged_in and not sync_done_in_url:
        logger.info("[APP_FLOW] Usuário logado mas sync não realizado. Redirecionando para sync_page.")
        st.query_params["page"] = "sync_page"
        if requested_page_from_url != "sync_page":
            st.rerun()
            return

    if requested_page_from_url == "sync_page":
        logger.info("Renderizando a página: sync_page")
        st.sidebar.empty()
        render_sync_page()
        return

    st.markdown("""
        <script>
            const parentHtml = window.parent.document.documentElement;
            const parentBody = window.parent.document.body;
            parentHtml.classList.remove('streamlit-login-page');
            parentBody.classList.remove('streamlit-login-page');
            parentHtml.style.backgroundImage = '';
            parentBody.style.backgroundColor = '#0d1117';
            parentBody.style.backgroundImage = '';
        </script>
    """, unsafe_allow_html=True)

    if st.session_state.nav_request:
        if st.session_state.nav_request == "logout_action":
            do_logout()
        st.session_state.nav_request = ""

    _ss.initialize_post_login()

    current_url_params = {k: v for k, v in st.query_params.items()}
    target_page = "home"
    if current_url_params.get("page") in VALID_PAGES:
        target_page = current_url_params["page"]
    if target_page == "sync_page" and sync_done_in_url:
        target_page = "home"

    st.session_state.current_page = target_page
    desired_url_params = {"page": st.session_state.current_page, "sync_done": "true"}

    if "code" in current_url_params:
        del current_url_params["code"]

    if (current_url_params.get("page") != desired_url_params.get("page") or
            current_url_params.get("sync_done") != desired_url_params.get("sync_done")):
        st.query_params.clear()
        st.query_params.update(desired_url_params)
        st.rerun()
        st.stop()
        return

    with st.sidebar:
        render_sidebar_menu(THEME, get_image_base64)

    current_page = st.session_state.current_page
    logger.info(f"Renderizando a página: {current_page}")

    page_registry = build_page_registry(THEME, _get_material_icon_html, process_markdown_for_external_links, do_logout)
    route_page(current_page, page_registry)


if __name__ == "__main__":
    main_app_entrypoint()
