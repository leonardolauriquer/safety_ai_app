# src/safety_ai_app/web_interface/pages/games_page.py

import streamlit as st
import logging
from typing import Any, Dict

# Importa o tema para ícones e frases
try:
    from safety_ai_app.theme_config import _get_material_icon_html, _get_material_icon_html_for_button_css, THEME
except ImportError:
    st.error("Erro ao carregar configurações de tema. Verifique 'theme_config.py'.")
    _get_material_icon_html = lambda icon: f"<span>{icon}</span>" # Fallback
    _get_material_icon_html_for_button_css = lambda btn_key, icon_key: "" # Fallback
    THEME = {"phrases": {}, "icons": {}} # Fallback

# Importa estilos compartilhados
try:
    from safety_ai_app.web_interface.shared_styles import inject_glass_styles, glass_marker
except ImportError:
    st.error("Erro ao carregar estilos compartilhados. Verifique 'shared_styles.py'.")
    inject_glass_styles = lambda: None
    glass_marker = lambda: ""

# Importa os jogos
try:
    from safety_ai_app.web_interface.components.games.quiz_game import render_quiz_game
except ImportError as e:
    st.error(f"Erro ao carregar o Quiz: {e}. Verifique 'quiz_game.py'.")
    render_quiz_game = None

try:
    from safety_ai_app.web_interface.components.games.crossword_game import render_crossword_game
except ImportError as e:
    st.error(f"Erro ao carregar Palavras Cruzadas: {e}. Verifique 'crossword_game.py'.")
    render_crossword_game = None

logger = logging.getLogger(__name__)

def games_page() -> None:
    """
    Renderiza a página principal de jogos, permitindo ao usuário escolher entre os jogos disponíveis.
    """
    inject_glass_styles()
    
    games_icon = THEME['icons'].get('games_icon', 'sports_esports')
    games_title = THEME['phrases'].get('games_page', 'Jogos e Desafios')

    with st.container():
        st.markdown(glass_marker(), unsafe_allow_html=True)
        
        # Header compacto
        st.markdown(f"""
            <div class='page-header'>
                {_get_material_icon_html(games_icon)}
                <h1>{games_title}</h1>
            </div>
            <div class='page-subtitle'>
                Teste seus conhecimentos em Saúde e Segurança do Trabalho de forma interativa.
            </div>
        """, unsafe_allow_html=True)

        # Inicializa o estado para a seleção do jogo
        if "current_game_selection" not in st.session_state:
            st.session_state.current_game_selection = None

        if st.session_state.current_game_selection is None:
            # Exibe as opções de jogos
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown(f"""
                    <div class='result-card'>
                        <div class='result-title'>{THEME['phrases'].get('quiz_game', 'Quiz SST')}</div>
                        <div class='result-meta'>Show do Milhão com perguntas sobre NRs e SST.</div>
                    </div>
                """, unsafe_allow_html=True)
                st.markdown(_get_material_icon_html_for_button_css('select_quiz_game', THEME['icons'].get('quiz_icon', 'quiz')), unsafe_allow_html=True)
                if st.button(f"Jogar Quiz", key="select_quiz_game", use_container_width=True):
                    st.session_state.current_game_selection = "quiz"
                    st.rerun()
                    
            with col2:
                st.markdown(f"""
                    <div class='result-card'>
                        <div class='result-title'>{THEME['phrases'].get('crossword_game', 'Palavras Cruzadas')}</div>
                        <div class='result-meta'>Desafio de termos técnicos e conceitos de segurança.</div>
                    </div>
                """, unsafe_allow_html=True)
                st.markdown(_get_material_icon_html_for_button_css('select_crossword_game', THEME['icons'].get('crossword_icon', 'puzzle')), unsafe_allow_html=True)
                if st.button(f"Jogar Palavras Cruzadas", key="select_crossword_game", use_container_width=True):
                    st.session_state.current_game_selection = "crossword"
                    st.rerun()
            
            st.markdown(f"""
                <div class='info-hint'>
                    {_get_material_icon_html('info')}
                    <span>Selecione um dos desafios acima para começar. <b>O aprendizado lúdico ajuda na retenção de normas!</b></span>
                </div>
            """, unsafe_allow_html=True)

        else:
            # Botão para voltar à seleção de jogos
            st.markdown(_get_material_icon_html_for_button_css('back_to_game_selection', THEME['icons'].get('back_arrow', 'arrow_back')), unsafe_allow_html=True)
            if st.button(f"Voltar para Seleção de Jogos", key="back_to_game_selection"):
                st.session_state.current_game_selection = None
                # Resetar estados dos jogos ao voltar para evitar que o jogo continue de onde parou
                if "quiz_started" in st.session_state:
                    del st.session_state.quiz_started
                if "crossword_started" in st.session_state:
                    del st.session_state.crossword_started
                st.rerun()
            
            # Renderiza o jogo selecionado
            if st.session_state.current_game_selection == "quiz":
                if render_quiz_game:
                    render_quiz_game()
                else:
                    st.error("O jogo Quiz SST não pôde ser carregado.")
            elif st.session_state.current_game_selection == "crossword":
                if render_crossword_game:
                    render_crossword_game()
                else:
                    st.error("O jogo Palavras Cruzadas SST não pôde ser carregado.")
