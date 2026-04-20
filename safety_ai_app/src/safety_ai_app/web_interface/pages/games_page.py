# src/safety_ai_app/web_interface/pages/games_page.py

import streamlit as st
import logging
from typing import Any, Dict

try:
    from safety_ai_app.theme_config import _get_material_icon_html, _get_material_icon_html_for_button_css, THEME
except ImportError:
    st.error("Erro ao carregar configurações de tema. Verifique 'theme_config.py'.")
    _get_material_icon_html = lambda icon: f"<span>{icon}</span>"
    _get_material_icon_html_for_button_css = lambda btn_key, icon_key: ""
    THEME = {"phrases": {}, "icons": {}, "colors": {}}

try:
    from safety_ai_app.web_interface.shared_styles import inject_glass_styles, glass_marker
except ImportError:
    st.error("Erro ao carregar estilos compartilhados. Verifique 'shared_styles.py'.")
    inject_glass_styles = lambda: None
    glass_marker = lambda: ""

try:
    from safety_ai_app.web_interface.components.games.quiz_game import render_quiz_game
except ImportError as e:
    st.error(f"Erro ao carregar o Quiz: {e}.")
    render_quiz_game = None

try:
    from safety_ai_app.web_interface.components.games.crossword_game import render_crossword_game
except ImportError as e:
    st.error(f"Erro ao carregar Palavras Cruzadas: {e}.")
    render_crossword_game = None

try:
    from safety_ai_app.web_interface.components.games.hangman_game import render_hangman_game
except ImportError as e:
    st.error(f"Erro ao carregar Jogo da Forca: {e}.")
    render_hangman_game = None

try:
    from safety_ai_app.web_interface.components.games.word_search_game import render_word_search_game
except ImportError as e:
    st.error(f"Erro ao carregar Caça-Palavras: {e}.")
    render_word_search_game = None

try:
    from safety_ai_app.web_interface.components.games.accident_investigation_game import render_accident_investigation_game
except ImportError as e:
    st.error(f"Erro ao carregar Investigação de Acidente: {e}.")
    render_accident_investigation_game = None

try:
    from safety_ai_app.web_interface.components.games.memory_game import render_memory_game
except ImportError as e:
    st.error(f"Erro ao carregar Jogo da Memória: {e}.")
    render_memory_game = None

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


GAMES = [
    {
        "key": "quiz",
        "title": "Quiz SST",
        "icon": "quiz",
        "description": "Show do Milhão com NRs, EPIs e conceitos de SST. Com ligas e placar da sessão.",
        "btn_label": "Jogar Quiz",
        "renderer": lambda: render_quiz_game() if render_quiz_game else _alert("Quiz indisponível.", "error"),
    },
    {
        "key": "crossword",
        "title": "Palavras Cruzadas",
        "icon": "extension",
        "description": "Desvende termos técnicos de segurança em grades de palavras cruzadas com dicas.",
        "btn_label": "Jogar Palavras Cruzadas",
        "renderer": lambda: render_crossword_game() if render_crossword_game else _alert("Palavras Cruzadas indisponíveis.", "error"),
    },
    {
        "key": "hangman",
        "title": "Jogo da Forca SST",
        "icon": "sports_esports",
        "description": "Descubra NRs, EPIs e siglas de SST letra por letra antes do boneco ser completado.",
        "btn_label": "Jogar Forca",
        "renderer": lambda: render_hangman_game() if render_hangman_game else _alert("Jogo da Forca indisponível.", "error"),
    },
    {
        "key": "wordsearch",
        "title": "Caça-Palavras SST",
        "icon": "search",
        "description": "Encontre termos de SST escondidos em uma grade de letras contra o relógio.",
        "btn_label": "Jogar Caça-Palavras",
        "renderer": lambda: render_word_search_game() if render_word_search_game else _alert("Caça-Palavras indisponível.", "error"),
    },
    {
        "key": "accident",
        "title": "Investigação de Acidente",
        "icon": "policy",
        "description": "Analise cenários reais de acidentes e identifique NRs violadas e EPIs faltantes.",
        "btn_label": "Investigar Acidente",
        "renderer": lambda: render_accident_investigation_game() if render_accident_investigation_game else _alert("Investigação indisponível.", "error"),
    },
    {
        "key": "memory",
        "title": "Jogo da Memória SST",
        "icon": "grid_view",
        "description": "Associe siglas a definições, EPIs a funções e NRs a temas em um jogo de memória.",
        "btn_label": "Jogar Memória",
        "renderer": lambda: render_memory_game() if render_memory_game else _alert("Jogo da Memória indisponível.", "error"),
    },
]


def games_page() -> None:
    """
    Renderiza a página principal de jogos com 6 cards em grid 2x3.
    """
    inject_glass_styles()

    games_icon = THEME['icons'].get('games_icon', 'sports_esports')
    games_title = THEME['phrases'].get('games_page', 'Jogos e Desafios')

    st.markdown("""
    <style>
    .game-card {
        background: rgba(15,23,42,0.55);
        border: 1px solid rgba(74,222,128,0.12);
        border-radius: 14px;
        padding: 18px 16px 14px 16px;
        margin-bottom: 6px;
        transition: all 0.15s;
        min-height: 130px;
    }
    .game-card:hover {
        background: rgba(74,222,128,0.06);
        border-color: rgba(74,222,128,0.22);
        transform: translateY(-1px);
    }
    .game-card-icon { font-size: 1.6em; margin-bottom: 6px; }
    .game-card-title {
        color: #E2E8F0;
        font-size: 0.97em;
        font-weight: 600;
        margin-bottom: 4px;
    }
    .game-card-desc {
        color: #64748B;
        font-size: 0.78em;
        line-height: 1.4;
    }
    </style>
    """, unsafe_allow_html=True)

    with st.container():
        st.markdown(glass_marker(), unsafe_allow_html=True)

        st.markdown(f"""
            <div class='page-header'>
                {_get_material_icon_html(games_icon)}
                <h1>{games_title}</h1>
            </div>
            <div class='page-subtitle'>
                Teste seus conhecimentos em Saúde e Segurança do Trabalho de forma interativa.
            </div>
        """, unsafe_allow_html=True)

        if "current_game_selection" not in st.session_state:
            st.session_state.current_game_selection = None

        if st.session_state.current_game_selection is None:
            for row_start in range(0, len(GAMES), 3):
                row_games = GAMES[row_start:row_start + 3]
                cols = st.columns(3)
                for i, game in enumerate(row_games):
                    with cols[i]:
                        st.markdown(f"""
                            <div class='game-card'>
                                <div class='game-card-icon'>{_get_material_icon_html(game['icon'])}</div>
                                <div class='game-card-title'>{game['title']}</div>
                                <div class='game-card-desc'>{game['description']}</div>
                            </div>
                        """, unsafe_allow_html=True)
                        if st.button(game["btn_label"], key=f"select_{game['key']}", use_container_width=True):
                            st.session_state.current_game_selection = game["key"]
                            st.rerun()

            st.markdown(f"""
                <div class='info-hint'>
                    {_get_material_icon_html('info')}
                    <span>Selecione um dos 6 desafios acima para começar. <b>O aprendizado lúdico ajuda na retenção de normas!</b></span>
                </div>
            """, unsafe_allow_html=True)

        else:
            if st.button("← Voltar para Seleção de Jogos", key="back_to_game_selection"):
                st.session_state.current_game_selection = None
                for state_key in ["quiz_started", "crossword_started", "hangman_started",
                                   "ws_started", "acc_started", "mem_started"]:
                    if state_key in st.session_state:
                        del st.session_state[state_key]
                st.rerun()

            selected = st.session_state.current_game_selection
            game_entry = next((g for g in GAMES if g["key"] == selected), None)
            if game_entry:
                game_entry["renderer"]()
            else:
                _alert("Jogo não encontrado.", "error")
                st.session_state.current_game_selection = None
