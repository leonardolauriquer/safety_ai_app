# src/safety_ai_app/home_page.py

import streamlit as st
from safety_ai_app.theme_config import THEME # Importa as configurações de tema para emojis e frases

def home_page():
    # Título neon usando a classe global e emojis centralizados
    st.markdown(f'<h1 class="neon-title">{THEME["emojis"]["ai_robot"]} Safety AI {THEME["emojis"]["ai_robot"]}</h1>', unsafe_allow_html=True)
    st.markdown("<h2>Sua plataforma inteligente para Saúde e Segurança do Trabalho</h2>", unsafe_allow_html=True)

    # Contêiner para os botões principais, estilizado globalmente para alinhamento
    st.markdown('<div class="home-button-container">', unsafe_allow_html=True)

    if st.button(f"{THEME['emojis']['chat_bubble']} {THEME['phrases']['chat_with_ai']}", key="btn_chat", use_container_width=True):
        st.session_state.page = "chat"
        st.rerun()

    if st.button(f"{THEME['emojis']['library_books']} {THEME['phrases']['document_library']}", key="btn_library", use_container_width=True):
        st.session_state.page = "library"
        st.rerun()

    if st.button(f"{THEME['emojis']['procedures_clipboard']} {THEME['phrases']['procedures']}", key="btn_procedures", use_container_width=True):
        st.session_state.page = "procedures"
        st.rerun()

    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown(f"""
    <br>
    <div class="footer">
        {THEME["phrases"]["footer_text"]}
    </div>
    """, unsafe_allow_html=True)
