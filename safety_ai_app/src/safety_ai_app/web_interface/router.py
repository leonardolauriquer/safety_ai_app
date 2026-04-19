import streamlit as st
import logging
from typing import Callable, Dict

logger = logging.getLogger(__name__)

VALID_PAGES = [
    # Main navigation
    "home", "chat", "library", "knowledge_base", "jobs_board", "news_feed",
    # Quick consultations
    "cbo_consult", "cid_consult", "cnae_consult", "ca_consult", "fines_consult",
    # Dimensioning
    "emergency_brigade_sizing", "cipa_sizing", "sesmt_sizing",
    # Document generators
    "apr_generator", "ata_generator",
    # Games
    "games_page", "quiz_game", "crossword_game",
    # System
    "admin", "settings", "quick_queries_page", "sizing_page",
    # Admin
    "ai_evaluation", "admin_panel",
    # Handled before registry dispatch in main_app_entrypoint (listed for URL validation only)
    "sync_page",
]


def _make_placeholder(title_key: str, icon_key: str, theme: dict, get_material_icon_html: Callable) -> Callable:
    def _render():
        page_title = theme["phrases"].get(title_key, title_key.replace('_', ' ').title())
        page_icon_html = get_material_icon_html(icon_key)
        st.markdown(f'<h1 class="neon-title">{page_icon_html} {page_title}</h1>', unsafe_allow_html=True)
        st.markdown(
            f"<p style='color:{theme['colors']['text_primary']}; text-align:center;'>Esta seção está em desenvolvimento.</p>",
            unsafe_allow_html=True
        )
    return _render


def build_page_registry(
    theme: dict,
    get_material_icon_html: Callable,
    process_markdown_func: Callable,
    do_logout: Callable,
) -> Dict[str, Callable]:
    from safety_ai_app.web_interface.pages.home_page import home_page as render_home_page
    from safety_ai_app.web_interface.pages.chat_page import render_page as render_chat_page
    from safety_ai_app.web_interface.pages.library_page import render_page as render_library_page
    from safety_ai_app.web_interface.pages.knowledge_base_page import render_page as render_knowledge_base_page
    from safety_ai_app.web_interface.pages.jobs_board_page import render_page as render_jobs_board_page
    from safety_ai_app.web_interface.pages.cbo_consult_page import cbo_consult_page as render_cbo_consult_page
    from safety_ai_app.web_interface.pages.cid_consult_page import cid_consult_page as render_cid_consult_page
    from safety_ai_app.web_interface.pages.cnae_consult_page import cnae_consult_page as render_cnae_consult_page
    from safety_ai_app.web_interface.pages.ca_consult_page import ca_consult_page as render_ca_consult_page
    from safety_ai_app.web_interface.pages.fines_consult_page import fines_consult_page as render_fines_consult_page
    from safety_ai_app.web_interface.pages.cipa_sizing_page import cipa_sizing_page as render_cipa_sizing_page
    from safety_ai_app.web_interface.pages.sesmt_sizing_page import sesmt_sizing_page as render_sesmt_sizing_page
    from safety_ai_app.web_interface.pages.emergency_brigade_sizing_page import emergency_brigade_sizing_page as render_emergency_brigade_sizing_page
    from safety_ai_app.web_interface.pages.apr_generator_page import apr_generator_page as render_apr_generator_page
    from safety_ai_app.web_interface.pages.ata_generator_page import ata_generator_page as render_ata_generator_page
    from safety_ai_app.web_interface.pages.games_page import games_page as render_games_page
    from safety_ai_app.web_interface.pages.quick_queries_page import quick_queries_page as render_quick_queries_page
    from safety_ai_app.web_interface.pages.sizing_page import sizing_page as render_sizing_page
    from safety_ai_app.web_interface.pages.settings_page import render_page as render_settings_page
    from safety_ai_app.web_interface.pages.ai_evaluation_page import render_page as render_ai_evaluation_page
    from safety_ai_app.web_interface.pages.admin_panel_page import render_page as render_admin_panel_page

    try:
        from safety_ai_app.web_interface.pages.news_feed_page import render_page as render_news_feed_page
    except ImportError:
        logger.warning("news_feed_page.py não encontrado. Usando placeholder.")
        def render_news_feed_page():
            st.title("Feed de Notícias")
            st.write("Conteúdo do Feed de Notícias em breve!")
    except Exception as e:
        err_msg = str(e)
        logger.critical(f"[ROUTER] Falha ao importar news_feed_page: {err_msg}", exc_info=True)
        def render_news_feed_page():
            st.error(f"Erro crítico: Não foi possível carregar a página 'news_feed'. Detalhes: {err_msg}")

    def _chat():
        render_chat_page(process_markdown_for_external_links_func=process_markdown_func)

    def _quiz():
        page_title = theme["phrases"].get("quiz_game", "Quiz SST")
        page_icon_html = get_material_icon_html("quiz_game")
        st.markdown(f'<h1 class="neon-title">{page_icon_html} {page_title}</h1>', unsafe_allow_html=True)
        st.markdown(f"<p style='color:{theme['colors']['text_primary']}; text-align:center;'>Conteúdo do Quiz SST em breve!</p>", unsafe_allow_html=True)

    def _crossword():
        page_title = theme["phrases"].get("crossword_game", "Palavras Cruzadas SST")
        page_icon_html = get_material_icon_html("crossword_icon")
        st.markdown(f'<h1 class="neon-title">{page_icon_html} {page_title}</h1>', unsafe_allow_html=True)
        st.markdown(f"<p style='color:{theme['colors']['text_primary']}; text-align:center;'>Conteúdo de Palavras Cruzadas SST em breve!</p>", unsafe_allow_html=True)

    return {
        "home": render_home_page,
        "chat": _chat,
        "library": render_library_page,
        "knowledge_base": render_knowledge_base_page,
        "jobs_board": render_jobs_board_page,
        "news_feed": render_news_feed_page,
        "cbo_consult": render_cbo_consult_page,
        "cid_consult": render_cid_consult_page,
        "cnae_consult": render_cnae_consult_page,
        "ca_consult": render_ca_consult_page,
        "fines_consult": render_fines_consult_page,
        "cipa_sizing": render_cipa_sizing_page,
        "sesmt_sizing": render_sesmt_sizing_page,
        "apr_generator": render_apr_generator_page,
        "ata_generator": render_ata_generator_page,
        "games_page": render_games_page,
        "quiz_game": _quiz,
        "crossword_game": _crossword,
        "quick_queries_page": render_quick_queries_page,
        "sizing_page": render_sizing_page,
        "settings": render_settings_page,
        "ai_evaluation": render_ai_evaluation_page,
        "logout_action": do_logout,
        "emergency_brigade_sizing": render_emergency_brigade_sizing_page,
        "admin": render_admin_panel_page,
        "admin_panel": render_admin_panel_page,
    }


def route_page(current_page: str, page_registry: Dict[str, Callable]) -> None:
    render_fn = page_registry.get(current_page)
    if render_fn is None:
        logger.warning(f"[ROUTER] Página desconhecida '{current_page}'. Redirecionando para home.")
        st.session_state.current_page = "home"
        st.rerun()
        return
    try:
        render_fn()
    except Exception as e:
        logger.critical(
            f"[ERRO CRÍTICO] Erro ao renderizar '{current_page}': {e}. Tipo: {type(e).__name__}",
            exc_info=True
        )
        st.error(f"Erro crítico ao renderizar '{current_page}'. Detalhes: {e}")
