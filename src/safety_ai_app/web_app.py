<<<<<<< HEAD
# src/safety_ai_app/web_app.py
import streamlit as st
# import os # Removido, não é mais usado aqui
from safety_ai_app.home_page import home_page
from safety_ai_app.chat_page import chat_page
from safety_ai_app.library_page import library_page
from safety_ai_app.theme_config import GLOBAL_STYLES, THEME # Importado GLOBAL_STYLES e THEME para a página de Procedimentos
=======
# src/safety_ai_app/web_app.py (Novo ponto de entrada principal)

import streamlit as st
from safety_ai_app.home_page import home_page
from safety_ai_app.chat_page import chat_page
from safety_ai_app.theme_config import THEME
>>>>>>> 4905d811e996186d329c45a9547be5d2370b9e18

# Configuração da página principal (aplicada a todas as sub-páginas)
st.set_page_config(
    page_title="Safety AI - SST",
<<<<<<< HEAD
    page_icon=THEME["emojis"]["ai_robot"], # Ícone geral do aplicativo puxado do tema
    layout="wide", # Alterado para wide para aproveitar melhor a tela
=======
    page_icon="🤖", # Ícone geral do aplicativo
    layout="centered",
>>>>>>> 4905d811e996186d329c45a9547be5d2370b9e18
    initial_sidebar_state="auto"
)

# Inicializa o estado da página se ainda não estiver definido
if "page" not in st.session_state:
    st.session_state.page = "home" # Página inicial padrão

# Inicializa o histórico de chat para a página de chat
if "messages" not in st.session_state:
    st.session_state.messages = []

<<<<<<< HEAD
def main():
    # Injeta os estilos CSS globais no início da aplicação
    st.markdown(GLOBAL_STYLES, unsafe_allow_html=True)

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
        st.markdown(f'<h1 class="neon-title">{THEME["emojis"]["procedures_clipboard"]} {THEME["phrases"]["procedures"]}</h1>', unsafe_allow_html=True)
        st.markdown(f"<p style='color:{THEME['colors']['text_primary']}; text-align:center;'>Esta seção está em desenvolvimento.</p>", unsafe_allow_html=True)
        # Botão de voltar padronizado
        if st.button(f"{THEME['emojis']['back_arrow']} {THEME['phrases']['back_to_home']}", key="back_home_procedures"):
            st.session_state.page = "home"
            st.rerun()

if __name__ == "__main__":
    main()
=======
# Router para as páginas
if st.session_state.page == "home":
    home_page()
elif st.session_state.page == "chat":
    # Se voltar para o chat, podemos querer limpar a query antiga
    if "user_query_input" in st.session_state:
        del st.session_state.user_query_input
    chat_page()
elif st.session_state.page == "library":
    st.markdown(f"<h1 style='color:{THEME['colors']['accent_green']}; text-align:center;'>📚 Biblioteca de Documentos</h1>", unsafe_allow_html=True)
    st.markdown(f"<p style='color:{THEME['colors']['text_primary']}; text-align:center;'>Esta seção está em desenvolvimento.</p>", unsafe_allow_html=True)
    if st.button("Voltar para a Página Inicial", key="back_home_library"):
        st.session_state.page = "home"
        st.rerun()
elif st.session_state.page == "procedures":
    st.markdown(f"<h1 style='color:{THEME['colors']['accent_green']}; text-align:center;'>📋 Procedimentos</h1>", unsafe_allow_html=True)
    st.markdown(f"<p style='color:{THEME['colors']['text_primary']}; text-align:center;'>Esta seção está em desenvolvimento.</p>", unsafe_allow_html=True)
    if st.button("Voltar para a Página Inicial", key="back_home_procedures"):
        st.session_state.page = "home"
        st.rerun()
>>>>>>> 4905d811e996186d329c45a9547be5d2370b9e18
