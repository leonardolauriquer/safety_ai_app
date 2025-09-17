import streamlit as st
from safety_ai_app.home_page import home_page
from safety_ai_app.chat_page import chat_page
from safety_ai_app.theme_config import THEME # Importado o tema
from safety_ai_app.library_page import library_page

# Configuração da página principal (aplicada a todas as sub-páginas)
st.set_page_config(
    page_title="Safety AI - SST",
    page_icon="🤖", # Ícone geral do aplicativo
    layout="centered",
    initial_sidebar_state="auto"
)

# Inicializa o estado da página se ainda não estiver definido
if "page" not in st.session_state:
    st.session_state.page = "home" # Página inicial padrão

# Inicializa o histórico de chat para a página de chat
if "messages" not in st.session_state:
    st.session_state.messages = []

# Router para as páginas
if st.session_state.page == "home":
    home_page()
elif st.session_state.page == "chat":
    # Se voltar para o chat, podemos querer limpar a query antiga
    if "user_query_input" in st.session_state:
        del st.session_state.user_query_input
    chat_page()
elif st.session_state.page == "library":
    library_page()
elif st.session_state.page == "procedures":
    st.markdown(f"<h1 style='color:{THEME['colors']['accent_green']}; text-align:center;'>�� Procedimentos", unsafe_allow_html=True)
    st.markdown(f"<p style='color:{THEME['colors']['text_primary']}; text-align:center;'>Esta seção está em desenvolvimento.", unsafe_allow_html=True)
    if st.button("Voltar para a Página Inicial", key="back_home_procedures"):
        st.session_state.page = "home"
        st.rerun()