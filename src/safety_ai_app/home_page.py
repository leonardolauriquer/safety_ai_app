# src/safety_ai_app/home_page.py

import streamlit as st
<<<<<<< HEAD
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
=======
from safety_ai_app.theme_config import THEME # Importa as configurações de tema

# Cores e fontes do tema
COLORS = THEME["colors"]
FONTS = THEME["fonts"]

def home_page():
    st.markdown(
        f"""
        <style>
        @import url('{FONTS["primary_url"]}');

        .stApp {{
            background-color: {COLORS["background_primary"]};
            color: {COLORS["text_primary"]};
            font-family: {FONTS["primary_family"]};
        }}
        h1 {{
            color: {COLORS["accent_green"]};
            text-align: center;
            font-size: 3.5em; /* Impacto! */
            margin-top: 80px; /* Espaço do topo */
            text-shadow: 0 0 15px {COLORS["accent_green_shadow"]};
        }}
        h2 {{
            color: {COLORS["text_secondary"]};
            text-align: center;
            font-size: 1.5em;
            margin-bottom: 60px; /* Espaço antes dos botões */
        }}
        .home-button-container {{
            display: flex;
            flex-direction: column; /* Botões um abaixo do outro */
            gap: 20px; /* Espaçamento entre os botões */
            align-items: center; /* Centraliza os botões */
            width: 100%;
        }}
        .home-button-container .stButton>button {{
            background-color: {COLORS["accent_green"]};
            color: white;
            border-radius: 12px; /* Mais arredondado para impacto */
            border: 1px solid {COLORS["accent_green"]};
            padding: 18px 40px; /* Botões maiores */
            font-size: 1.5em; /* Texto maior */
            font-weight: bold;
            transition: all 0.3s ease;
            box-shadow: 0 0 20px {COLORS["accent_green_shadow"]};
            width: 70%; /* Ocupa uma boa parte da largura */
            max-width: 400px; /* Limite máximo de largura */
        }}
        .home-button-container .stButton>button:hover {{
            background-color: {COLORS["accent_green_hover"]};
            border-color: {COLORS["accent_green_hover"]};
            box-shadow: 0 0 25px {COLORS["accent_green_shadow"]};
            transform: translateY(-5px); /* Efeito de elevação */
        }}
        .footer {{
            text-align: center;
            color: {COLORS["text_secondary"]};
            font-size: 0.85em;
            margin-top: 100px; /* Mais espaço para o rodapé */
            padding-top: 20px;
            border-top: 1px dashed {COLORS["border_color"]};
        }}
        </style>
        """,
        unsafe_allow_html=True
    )

    st.markdown("<h1>Safety AI</h1>", unsafe_allow_html=True)
    st.markdown("<h2>Sua plataforma inteligente para Saúde e Segurança do Trabalho</h2>", unsafe_allow_html=True)

    st.markdown('<div class="home-button-container">', unsafe_allow_html=True)

    if st.button("💬 Chat com Safety AI", key="btn_chat"):
        st.session_state.page = "chat"
        st.rerun()

    if st.button("📚 Biblioteca de Documentos", key="btn_library"):
        st.session_state.page = "library"
        st.rerun()

    if st.button("📋 Procedimentos", key="btn_procedures"):
>>>>>>> 4905d811e996186d329c45a9547be5d2370b9e18
        st.session_state.page = "procedures"
        st.rerun()

    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown(f"""
    <br>
    <div class="footer">
<<<<<<< HEAD
        {THEME["phrases"]["footer_text"]}
=======
        Desenvolvido com IA 🤖 por Eng. Leonardo Lauriquer Ribeiro - Focado em um futuro mais seguro.
>>>>>>> 4905d811e996186d329c45a9547be5d2370b9e18
    </div>
    """, unsafe_allow_html=True)
