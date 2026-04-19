import streamlit as st
import logging

logger = logging.getLogger(__name__)


def _render_nav_item(icon_key_string: str, label: str, page_key: str, current_page: str) -> None:
    from safety_ai_app.theme_config import render_nav_item
    nav_html = render_nav_item(icon_key_string, label, page_key, current_page)
    st.markdown(nav_html, unsafe_allow_html=True)


def _render_nav_item_with_badge(icon_key_string: str, label: str, page_key: str, current_page: str, badge: str = "") -> None:
    from safety_ai_app.theme_config import get_icon
    active = " active" if current_page == page_key else ""
    href = f"?page={page_key}&sync_done=true"
    badge_html = (
        f'<span style="'
        f'display:inline-flex;align-items:center;justify-content:center;'
        f'background:#F87171;color:#fff;border-radius:50%;'
        f'min-width:1.1em;height:1.1em;font-size:0.65em;font-weight:700;'
        f'margin-left:0.35em;padding:0 0.2em;line-height:1;'
        f'">{badge}</span>'
    ) if badge else ""
    nav_html = (
        f'<a href="{href}" class="nav-item{active}" target="_self">'
        f"{get_icon(icon_key_string)}<span>{label}{badge_html}</span></a>"
    )
    st.markdown(nav_html, unsafe_allow_html=True)


def _get_sync_failure_badge() -> str:
    """Return a badge string if the last auto-sync failed, otherwise empty string."""
    try:
        from safety_ai_app.auto_sync_scheduler import get_scheduler
        status = get_scheduler().get_status()
        if status.get("last_run_success") is False:
            return "!"
    except Exception as exc:
        logger.debug("Could not read auto-sync status for sidebar badge: %s", exc)
    return ""


def render_sidebar_menu(theme: dict, get_image_base64) -> None:
    import os
    from safety_ai_app.theme_config import get_icon

    st.sidebar.markdown(f"""
        <div class="sidebar-logo">
            <img src="{get_image_base64(theme['images']['app_logo'])}" alt="SafetyAI Logo">
        </div>
    """, unsafe_allow_html=True)

    st.sidebar.markdown(
        f'<div class="sidebar-title">{get_icon("shield")} {theme["phrases"]["app_title"]} {get_icon("shield")}</div>',
        unsafe_allow_html=True
    )

    current_page = st.session_state.get("current_page", "home")

    user_email = st.session_state.get("user_email", "").strip().lower()
    admin_emails_raw = os.environ.get("ADMIN_EMAILS", "")
    admin_emails = {e.strip().lower() for e in admin_emails_raw.split(",") if e.strip()}
    is_admin = st.session_state.get("is_admin", False) or (user_email and user_email in admin_emails)

    _render_nav_item('home_icon', theme['phrases']['home_page'], "home", current_page)
    _render_nav_item('chat_bubble', theme['phrases']['chat'], "chat", current_page)
    _render_nav_item('library_books', theme['phrases']['document_library'], "library", current_page)
    _render_nav_item('brain_gear', theme['phrases']['knowledge_base_ai'], "knowledge_base", current_page)
    _render_nav_item('jobs_board', theme['phrases']['jobs_board'], "jobs_board", current_page)
    _render_nav_item('news_feed', theme['phrases']['news_feed'], "news_feed", current_page)

    st.sidebar.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)

    with st.sidebar.expander(f"🔍 {theme['phrases']['quick_consults']}", expanded=False):
        _render_nav_item('cbo_consult', theme['phrases']['cbo_consult'], "cbo_consult", current_page)
        _render_nav_item('cid_consult', theme['phrases']['cid_consult'], "cid_consult", current_page)
        _render_nav_item('cnae_consult', theme['phrases']['cnae_consult'], "cnae_consult", current_page)
        _render_nav_item('ca_consult', theme['phrases']['ca_consult'], "ca_consult", current_page)
        _render_nav_item('fines_consult', theme['phrases']['fines_consult'], "fines_consult", current_page)

    with st.sidebar.expander(f"📊 {theme['phrases'].get('sizing', 'Dimensionamentos')}", expanded=False):
        _render_nav_item('emergency_brigade', theme['phrases'].get('emergency_brigade_sizing', 'Brigada de Emergência'), "emergency_brigade_sizing", current_page)
        _render_nav_item('cipa_sizing', theme['phrases'].get('cipa_sizing', 'Dimensionamento CIPA'), "cipa_sizing", current_page)
        _render_nav_item('sesmt_sizing', theme['phrases'].get('sesmt_sizing', 'Dimensionamento SESMT'), "sesmt_sizing", current_page)

    with st.sidebar.expander(f"📄 {theme['phrases'].get('document_emission', 'Emissão de Laudos')}", expanded=False):
        _render_nav_item('apr_generator_icon', theme['phrases'].get('apr_generator', "APR (Análise Preliminar de Risco)"), "apr_generator", current_page)
        _render_nav_item('ata_generator_icon', theme['phrases'].get('ata_generator', "Emissão de Ata"), "ata_generator", current_page)

    with st.sidebar.expander(f"🎮 {theme['phrases'].get('games_page', 'Jogos e Desafios')}", expanded=False):
        _render_nav_item('quiz_game', theme['phrases'].get('quiz_game', 'Quiz SST (Show do Milhão)'), "quiz_game", current_page)
        _render_nav_item('puzzle', theme['phrases'].get('crossword_game', 'Palavras Cruzadas SST'), "crossword_game", current_page)

    st.sidebar.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)

    _render_nav_item('settings', theme['phrases']['settings'], "settings", current_page)

    if is_admin:
        sync_badge = _get_sync_failure_badge()
        with st.sidebar.expander(f"🔧 {theme['phrases'].get('administration', 'Administração')}", expanded=False):
            _render_nav_item_with_badge('admin_panel', theme['phrases'].get('admin_panel', 'Painel Admin'), "admin_panel", current_page, badge=sync_badge)
            _render_nav_item('ai_evaluation', theme['phrases'].get('ai_evaluation', 'Avaliação IA'), "ai_evaluation", current_page)

    try:
        from safety_ai_app.web_interface.pwa_support import get_pwa_install_button_html
        st.sidebar.markdown(get_pwa_install_button_html(), unsafe_allow_html=True)
    except Exception:
        pass

    if st.session_state.logged_in:
        user_name = st.session_state.get("user_name", "Usuário")
        user_email = st.session_state.get("user_email", "")

        st.sidebar.markdown(f"""
        <div class="sidebar-user-info">
            <div class="user-name">{user_name}</div>
            {f'<div class="user-email">{user_email}</div>' if user_email else ""}
        </div>
        """, unsafe_allow_html=True)

        _render_nav_item('logout', theme['phrases']['logout'], "logout_action", current_page)
