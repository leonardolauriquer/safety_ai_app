import streamlit as st
import os # Necessário para acessar variáveis de ambiente, como as carregadas pelo dotenv
from dotenv import load_dotenv # Importa a função para carregar .env

# Carrega as variáveis do arquivo .env no início da aplicação
load_dotenv()

from safety_ai_app.home_page import home_page
from safety_ai_app.chat_page import chat_page
from safety_ai_app.library_page import library_page
from safety_ai_app.theme_config import GLOBAL_STYLES, THEME # Importado GLOBAL_STYLES e THEME para a página de Procedimentos

# Configuração da página principal (aplicada a todas as sub-páginas)
st.set_page_config(
    page_title="Safety AI - SST",
    page_icon=THEME["emojis"]["ai_robot"], # Ícone geral do aplicativo puxado do tema
    layout="wide", # Alterado para wide para aproveitar melhor a tela
    initial_sidebar_state="auto"
)

# Inicializa o estado da página se ainda não estiver definido
if "page" not in st.session_state:
    st.session_state.page = "home" # Página inicial padrão

# Inicializa o histórico de chat para a página de chat
if "messages" not in st.session_state:
    st.session_state.messages = []

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