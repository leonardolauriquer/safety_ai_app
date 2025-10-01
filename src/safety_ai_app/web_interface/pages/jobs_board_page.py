import streamlit as st
from safety_ai_app.theme_config import THEME

def render_page(): # RENOMEADA PARA render_page
    page_title = THEME["phrases"]["jobs_board"]
    page_emoji = THEME["icons"]["jobs_board"]
    st.markdown(f'<h1 class="neon-title">{page_emoji} {page_title}</h1>', unsafe_allow_html=True)
    st.markdown(f"<p style='color:{THEME['colors']['text_primary']}; text-align:center;'>Esta seção de vagas está em desenvolvimento. Em breve, você encontrará aqui oportunidades de SST relevantes!</p>", unsafe_allow_html=True)
