# src/safety_ai_app/chat_page.py

import streamlit as st
import os
import markdown # <-- Importado para converter Markdown em HTML
from safety_ai_app.nr_rag_qa import NRQuestionAnswering
from safety_ai_app.theme_config import THEME

COLORS = THEME["colors"]
FONTS = THEME["fonts"]

@st.cache_resource
def get_nr_rag_qa_system():
    try:
        qa_system = NRQuestionAnswering()
        return qa_system
    except Exception as e:
        st.error(f"❌ Erro ao inicializar o Sistema de QA de SST: {e}")
        st.error("Verifique se o ChromaDB foi populado e se a API Key está acessível (definida como variável de ambiente).")
        return None

# --- Funções de callback para os botões de ícone (fora do st.form) ---
def _on_pencil_click():
    st.info("Funcionalidade de Refinamento e Edição (Lápis Mágico) em desenvolvimento!") 
    
def _on_mic_click():
    st.info("Funcionalidade de Áudio para Texto (Microfone) é um recurso da plataforma. Ative o microfone para usar!")

def _on_docs_click():
    st.session_state.show_file_uploader = not st.session_state.show_file_uploader

def _on_image_click():
    st.info("Funcionalidade de Análise de Imagem: Em breve! Explorará capacidades multimodais.")

def _on_generate_click():
    st.info("Funcionalidade de Geração: Permite criar novos conteúdos e resumos. Em breve!")
# --- Fim das funções de callback ---


def chat_page():
    st.markdown(
        f"""
        <style>
        @import url('{FONTS["primary_url"]}');

        @keyframes neon-flicker {{
            0%, 100% {{
                text-shadow: 
                    0 0 5px rgba(0, 255, 127, 0.4), 
                    0 0 10px rgba(0, 255, 127, 0.3),
                    0 0 20px rgba(0, 255, 127, 0.2);
                color: {COLORS["accent_green"]};
            }}
            50% {{
                text-shadow: 
                    0 0 10px rgba(0, 255, 127, 0.6), 
                    0 0 20px rgba(0, 255, 127, 0.4),
                    0 0 40px rgba(0, 255, 127, 0.3);
                color: {COLORS["accent_green_hover"]};
            }}
        }}

        .neon-title {{
            animation: neon-flicker 2s ease-in-out infinite alternate;
        }}

        .stApp {{
            background-color: {COLORS["background_primary"]};
            color: {COLORS["text_primary"]};
            font-family: {FONTS["primary_family"]};
            padding: 15px;
        }}

        h1 {{
            text-align: center;
            margin-bottom: 25px;
            font-size: 2.5em;
        }}
        h2, h3, h4, h5, h6 {{
            color: {COLORS["accent_green"]};
            text-align: left;
            border-bottom: 2px solid {COLORS["border_color"]};
            padding-bottom: 10px;
            margin-top: 30px;
            margin-bottom: 20px;
        }}

        .stButton>button {{
            background-color: {COLORS["accent_green"]};
            color: white;
            border-radius: 8px;
            border: 1px solid {COLORS["accent_green"]};
            padding: 12px 25px;
            font-weight: bold;
            transition: all 0.3s ease;
            box-shadow: 0 0 15px {COLORS["accent_green_shadow"]};
            cursor: pointer;
            width: fit-content;
        }}
        .stButton>button:hover {{
            background-color: {COLORS["accent_green_hover"]};
            border-color: {COLORS["accent_green_hover"]};
            box-shadow: 0 0 20px {COLORS["accent_green_shadow"]};
            transform: translateY(-2px);
        }}
        
        div[data-testid="stVerticalBlock"] > div[data-testid="stVerticalBlock"] > div[data-testid="stVerticalBlock"]:nth-child(2) {{ 
            border: 2px solid {COLORS["border_color"]};
            border-radius: 10px;
            background-color: {COLORS["background_secondary"]};
            margin-top: 25px;
            box-shadow: 0 0 20px rgba(0, 255, 127, 0.1);
            overflow-y: auto;
            max-height: 480px;
            padding: 20px;
        }}
        
        .chat-message {{
            padding: 12px 18px;
            border-radius: 18px;
            margin-bottom: 12px;
            max-width: 85%;
            color: {COLORS["text_primary"]};
            word-wrap: break-word;
            line-height: 1.5;
            box-shadow: 0 2px 5px rgba(0,0,0,0.2);
        }}
        .chat-message.user {{
            background-color: {COLORS["user_message_bg"]};
            margin-left: auto;
            text-align: left;
            border-bottom-right-radius: 4px;
        }}
        .chat-message.ai {{
            background-color: {COLORS["ai_message_bg"]};
            border: 1px solid {COLORS["border_color"]};
            margin-right: auto;
            text-align: left;
            border-bottom-left-radius: 4px;
        }}
        .chat-message-container {{
            display: flex;
            width: 100%;
            margin-top: 5px;
        }}
        .chat-message p {{
            margin-bottom: 0;
        }}
        .chat-message ul, .chat-message ol {{
            padding-left: 20px;
            margin-top: 5px;
            margin-bottom: 5px;
        }}
        .chat-message li {{
            margin-bottom: 5px;
        }}
        .chat-message b {{
            color: {COLORS["accent_green_hover"]}; 
        }}

        .stAlert > div {{
            border-left: 5px solid;
            border-radius: 5px;
            background-color: {COLORS["background_secondary"]};
            color: {COLORS["text_primary"]};
            margin-top: 15px;
            padding: 15px;
        }}
        .stAlert.info > div {{ border-color: {COLORS["info_border"]}; }}
        .stAlert.success > div {{ border-color: {COLORS["accent_green_hover"]}; }}
        .stAlert.error > div {{ border-color: {COLORS["error_border"]}; }}

        .stAlert p {{
            color: {COLORS["text_primary"]} !important;
        }}

        .footer {{
            text-align: center;
            color: {COLORS["text_secondary"]};
            font-size: 0.85em;
            margin-top: 40px;
            padding-top: 20px;
            border-top: 1px dashed {COLORS["border_color"]};
        }}

        .chat-input-area {{
            background-color: {COLORS["background_secondary"]};
            border-radius: 12px;
            padding: 15px 20px;
            margin-top: 25px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.3);
            display: flex;
            flex-direction: column;
            gap: 4px; /* Espaçamento mínimo entre a linha de ícones e o formulário */
        }}
        
        .icon-buttons-row {{ /* Agrupa os botões de ícone */
            display: flex;
            align-items: center;
            justify-content: flex-start; /* Alinha os ícones à esquerda */
            gap: 8px; /* Espaçamento entre os botões de ícone */
            margin-bottom: 0 !important; /* Remove qualquer margem inferior extra */
        }}
        /* Estilo para as colunas Streamlit dentro de .icon-buttons-row para garantir o espaçamento correto */
        .icon-buttons-row > div[data-testid^="stColumn"] {{
            padding: 0px !important;
        }}

        .stTextInput>div>div>input {{ /* Aplica a todos os inputs de texto */
            background-color: {COLORS["input_background"]};
            color: {COLORS["text_primary"]};
            border: none;
            border-radius: 8px;
            padding: 15px 20px;
            font-size: 1.1em;
            height: auto;
            box-shadow: none;
            transition: box-shadow 0.2s ease;
        }}

        .stTextInput>div>div>input:focus {{
            box-shadow: 0 0 0 2px {COLORS["accent_green"]};
            outline: none;
        }}

        /* --- Estilo para os botões st.button que atuam como ícones (fora do form) --- */
        .stButton[data-testid*="btn_icon_"] > button {{
            background-color: {COLORS["input_background"]} !important;
            border: none !important;
            border-radius: 50% !important;
            width: 45px !important;
            min-width: 45px !important;
            height: 45px !important;
            display: flex !important;
            align-items: center !important;
            justify-content: center !important;
            color: {COLORS["text_secondary"]} !important; /* Cor neutra para o ícone */
            font-size: 1.3em !important;
            cursor: pointer !important;
            transition: all 0.2s ease !important;
            box-shadow: none !important;
            flex-shrink: 0;
            padding: 0 !important;
            line-height: 1 !important;
        }}
        .stButton[data-testid*="btn_icon_"] > button:hover {{
            background-color: {COLORS["button_action_hover"]} !important;
            color: {COLORS["accent_green"]} !important; /* Brilho verde no hover */
            transform: translateY(-1px) !important;
        }}
        .stButton[data-testid*="btn_icon_"] > button span {{
            color: inherit !important; /* Garante que o emoji herde a cor do pai */
            font-size: 1em !important;
            line-height: 1 !important;
            display: flex;
            align-items: center;
            justify-content: center;
        }}

        /* --- Estilo para o st.form_submit_button (agora um ícone) --- */
        .stButton[data-testid="stFormSubmitButton"] > button {{
            background-color: {COLORS["input_background"]} !important; /* Fundo neutro */
            border: none !important; /* Sem borda padrão */
            border-radius: 50% !important; /* Circular */
            width: 45px !important;
            min-width: 45px !important;
            height: 45px !important;
            display: flex !important;
            align-items: center !important;
            justify-content: center !important;
            color: {COLORS["text_secondary"]} !important; /* Cor neutra para o ícone */
            font-size: 1.3em !important; /* Tamanho do ícone */
            cursor: pointer !important;
            transition: all 0.2s ease !important;
            box-shadow: none !important;
            flex-shrink: 0;
            padding: 0 !important;
            line-height: 1 !important;
        }}
        .stButton[data-testid="stFormSubmitButton"] > button:hover {{
            background-color: {COLORS["button_action_hover"]} !important;
            color: {COLORS["accent_green"]} !important;
            transform: translateY(-1px) !important;
        }}
        .stButton[data-testid="stFormSubmitButton"] > button span {{
            color: inherit !important;
            font-size: 1em !important;
            line-height: 1 !important;
            display: flex;
            align-items: center;
            justify-content: center;
        }}

        .stForm {{
            margin: 0 !important; /* Remove margens padrão do formulário */
            display: flex; /* Habilita flexbox para alinhar input e botão de submissão */
            align-items: center;
            gap: 8px; /* Espaçamento entre o input de texto e o botão de envio */
        }}
        .stForm > div > div > div[data-testid^="stTextInput"] {{ /* stTextInput dentro do form */
             flex-grow: 1; /* Permite que o input de texto ocupe o espaço restante */
             margin-bottom: 0 !important; /* Remove margem inferior padrão */
        }}

        div[data-testid="stFileUploader"] {{
            background-color: {COLORS["input_background"]};
            border: 1px dashed {COLORS["border_color"]};
            border-radius: 10px;
            padding: 15px;
            margin-top: 15px;
            margin-left: auto;
            margin-right: auto;
            width: fit-content;
        }}
        div[data-testid="stFileUploader"] label p {{
            color: {COLORS["text_secondary"]};
            font-size: 0.9em;
            margin-bottom: 0;
        }}
        div[data-testid="stFileUploader"] > div {{
            justify-content: center;
        }}
        </style>
        """,
        unsafe_allow_html=True
    )

    if st.button("⬅️ Voltar para a Página Inicial", key="btn_back_home_from_chat"):
        st.session_state.page = "home"
        st.rerun()

    st.markdown('<h1 class="neon-title">�� Safety AI Chat</h1>', unsafe_allow_html=True)
    st.markdown("Seu assistente inteligente para dúvidas sobre **Saúde e Segurança do Trabalho**.")

    if "messages" not in st.session_state:
        st.session_state.messages = []
    
    if "show_file_uploader" not in st.session_state:
        st.session_state.show_file_uploader = False

    welcome_message = """
    👋 Olá! Eu sou o <b>Leo</b>, seu <b>chatbot amigável</b> e especializado em <b>Saúde e Segurança do Trabalho</b>.
    Estou aqui para <b>facilitar sua jornada</b>! Que tal <b>fazer uma pergunta</b> para começar?
    Ou, se preferir, pode <b>enviar um documento</b> para que eu o analise!
    """
    
    # Nova lógica para adicionar a welcome_message com a flag is_raw_html
    welcome_message_exists_and_is_correctly_flagged = False
    if st.session_state.messages and st.session_state.messages[0]["role"] == "ai":
        first_message = st.session_state.messages[0]
        # Garante que a mensagem é exatamente a welcome_message E que a flag está lá
        if first_message.get("is_raw_html", False) and first_message["content"].strip() == welcome_message.strip():
            welcome_message_exists_and_is_correctly_flagged = True

    if not welcome_message_exists_and_is_correctly_flagged:
        # Filtra mensagens de boas-vindas antigas (sem a flag ou diferentes) antes de inserir a nova
        st.session_state.messages = [
            msg for msg in st.session_state.messages 
            if not (msg["role"] == "ai" and msg["content"].strip() == welcome_message.strip() and msg.get("is_raw_html", False))
        ]
        st.session_state.messages.insert(0, {
            "role": "ai",
            "content": welcome_message,
            "is_raw_html": True # Adiciona a flag para indicar que é HTML puro
        })

    qa_system = get_nr_rag_qa_system()

    if qa_system:
        chat_display_area = st.container(height=480, border=True)
        with chat_display_area:
            for message in st.session_state.messages:
                content_to_display = message["content"]
                
                # Determina como o conteúdo será formatado
                if message.get("is_raw_html", False): # Se a flag is_raw_html for True
                    final_html = content_to_display # Usa o conteúdo como HTML puro (já formatado)
                else:
                    # Converte o Markdown para HTML para mensagens do usuário e da IA (se não for HTML puro)
                    final_html = markdown.markdown(content_to_display)
                    
                if message["role"] == "user":
                    st.markdown(f'<div class="chat-message-container"><div class="chat-message user">{final_html}</div></div>', unsafe_allow_html=True)
                else:
                    st.markdown(f'<div class="chat-message-container"><div class="chat-message ai">{final_html}</div></div>', unsafe_allow_html=True)
        
        st.markdown('<div class="chat-input-area">', unsafe_allow_html=True) 
        
        # --- Linha dos Botões de Ícone (FORA DO FORM, dentro da chat-input-area) ---
        st.markdown('<div class="icon-buttons-row">', unsafe_allow_html=True)
        icon_cols = st.columns([0.08, 0.08, 0.08, 0.08, 0.08, 1]) 

        with icon_cols[0]: # Lápis (Refinar/Editar)
            st.button("🪄", key="btn_icon_pencil", help="Refinar e Editar", on_click=_on_pencil_click, use_container_width=True)
        with icon_cols[1]: # Microfone - ÍCONE CORRIGIDO PARA O MICROFONE
            st.button("🎤", key="btn_icon_mic", help="Áudio para Texto", on_click=_on_mic_click, use_container_width=True)
        with icon_cols[2]: # Documentos
            st.button("📁", key="btn_icon_docs", help="Processar Documentos", on_click=_on_docs_click, use_container_width=True)
        with icon_cols[3]: # Imagem
            st.button("📷", key="btn_icon_image", help="Analisar Imagem", on_click=_on_image_click, use_container_width=True)
        with icon_cols[4]: # Gerar Conteúdo
            st.button("⚙️", key="btn_icon_generate", help="Gerar Conteúdo", on_click=_on_generate_click, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True) # Fim da div icon-buttons-row

        # --- Formulário Principal do Chat (com input de texto e botão de envio) ---
        with st.form(key='chat_form_submission', clear_on_submit=True):
            form_cols = st.columns([1, 0.15]) # Input de texto maior, botão de submissão menor
            with form_cols[0]:
                user_query_input = st.text_input(
                    "Digite sua pergunta...",
                    placeholder="Ex: Quais são as responsabilidades do empregador segundo a NR-35?",
                    key="user_chat_query_input",
                    label_visibility="collapsed"
                )
            with form_cols[1]:
                # Botão de envio como ícone (seta para a direita)
                nr_query_button = st.form_submit_button("➡️") 
            
            if nr_query_button:
                submitted_query = st.session_state.user_chat_query_input 
                
                if submitted_query.strip():
                    st.session_state.messages.append({"role": "user", "content": submitted_query})
                    
                    with st.spinner("⏳ Analisando e gerando resposta..."):
                        try:
                            # A resposta da IA já deve vir com o Markdown correto
                            nr_answer = qa_system.answer_question(submitted_query, st.session_state.messages)
                            st.session_state.messages.append({"role": "ai", "content": nr_answer})
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ Ocorreu um erro ao obter a resposta: {e}")
                            st.error("Por favor, tente novamente ou verifique o log para mais detalhes.")
                else:
                    st.warning("⚠️ Por favor, digite uma pergunta antes de enviar.")
        
        # --- File Uploader Condicional (logo abaixo do formulário, mas ainda dentro da chat-input-area) ---
        if st.session_state.show_file_uploader:
            uploaded_files = st.file_uploader(
                "Selecione um ou mais documentos (.pdf, .docx, .txt)",
                type=["pdf", "docx", "txt"],
                accept_multiple_files=True,
                key="file_uploader_main" 
            )
            if uploaded_files:
                st.info(f"✨ **Documentos para análise:** {[f.name for f in uploaded_files]}. O processamento do conteúdo desses documentos será ativado quando você enviar uma pergunta relacionada a eles!")

        st.markdown('</div>', unsafe_allow_html=True) # Fecha a div chat-input-area

    else:
        st.warning("⚠️ O sistema de QA de SST não pôde ser inicializado. Verifique se o ChromaDB está populado e a API Key está configurada corretamente nas variáveis de ambiente.")

    st.markdown("---")

    st.markdown(f"""
    <br>
    <div class="footer">
        Desenvolvido com IA 🤖 por Eng. Leonardo Lauriquer Ribeiro - Focado em um futuro mais seguro.
    </div>
    """, unsafe_allow_html=True)