# src/safety_ai_app/chat_page.py

import streamlit as st
import os
import markdown
import logging
from datetime import date # Necessário para o controle de doações, se for re-utilizado algo
from pathlib import Path
import io

# Importações do seu RAG e tema
from safety_ai_app.nr_rag_qa import NRQuestionAnswering
from safety_ai_app.theme_config import THEME

# Importações do Google Drive Integrator
from safety_ai_app.google_drive_integrator import (
    get_google_drive_service_user,
    list_drive_folders,
    _fetch_drive_files_cached,
    get_file_bytes_for_download,
    get_download_metadata,
)

# --- Configuração de logging ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

COLORS = THEME["colors"]
FONTS = THEME["fonts"]

# --- Constantes para a funcionalidade de Drive Pessoal ---
# MIME types que seu sistema RAG pode processar para contexto.
PROCESSABLE_MIME_TYPES_FOR_RAG = [
    'application/pdf',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document', # DOCX
    'text/plain',
    'application/vnd.google-apps.document', # Google Docs (será exportado como DOCX)
]

# Mapeamento de MIME types para exibição amigável na seleção do Drive.
MIME_TYPE_DISPLAY_FOR_CHAT_CONTEXT = {
    'application/pdf': 'PDF Documento',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document': 'DOCX Documento',
    'text/plain': 'TXT Documento',
    'application/vnd.google-apps.document': 'Google Docs',
    'application/vnd.google-apps.spreadsheet': 'Google Sheets', # Pode ser exibido, mas não processável.
    'application/vnd.google-apps.presentation': 'Google Slides', # Pode ser exibido, mas não processável.
    'application/vnd.google-apps.folder': 'Pasta do Google Drive',
    'default': 'Arquivo'
}

# --- Placeholder para o extrator de texto ---
def extract_text_from_bytes(file_bytes: bytes, mime_type: str) -> str:
    """
    Função placeholder para extrair texto de bytes de arquivos.
    Você precisará implementar a lógica real usando bibliotecas como pypdf, python-docx, etc.
    """
    if not file_bytes:
        return ""
    
    # Exemplo muito simplificado:
    if mime_type == 'text/plain':
        try:
            return file_bytes.decode('utf-8')
        except UnicodeDecodeError:
            return file_bytes.decode('latin-1', errors='ignore') # Tentativa de fallback

    # Para PDF, DOCX, etc., você precisaria de bibliotecas específicas:
    # if mime_type == 'application/pdf':
    #     import pypdf
    #     reader = pypdf.PdfReader(io.BytesIO(file_bytes))
    #     text = ""
    #     for page in reader.pages:
    #         text += page.extract_text()
    #     return text
    # elif mime_type == 'application/vnd.openxmlformats-officedocument.wordprocessingml.document':
    #     import docx
    #     document = docx.Document(io.BytesIO(file_bytes))
    #     text = ""
    #     for para in document.paragraphs:
    #         text += para.text + "\n"
    #     return text

    logging.warning(f"Tipo de arquivo '{mime_type}' não tem um extrator de texto implementado. Conteúdo não será usado.")
    return f"[Conteúdo do tipo {mime_type} não pode ser extraído para o RAG.]"


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

# ALTERADO: Agora toggle 'show_document_context_selector'
def _on_docs_click():
    st.session_state.show_document_context_selector = not st.session_state.show_document_context_selector

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

        /* Estilos para File Uploader e seletores de Drive */
        div[data-testid="stFileUploader"] {{
            background-color: {COLORS["input_background"]};
            border: 1px dashed {COLORS["border_color"]};
            border-radius: 10px;
            padding: 15px;
            margin-top: 15px;
            margin-left: auto;
            margin-right: auto;
            width: fit-content; /* Ajusta a largura ao conteúdo */
        }}
        div[data-testid="stFileUploader"] label p {{
            color: {COLORS["text_secondary"]};
            font-size: 0.9em;
            margin-bottom: 0;
        }}
        div[data-testid="stFileUploader"] > div {{
            justify-content: center;
        }}

        /* Estilo para a área de seleção de arquivos do Drive */
        .drive-selector-area {{
            background-color: {COLORS["background_secondary"]};
            border: 1px solid {COLORS["border_color"]};
            border-radius: 10px;
            padding: 15px;
            margin-top: 15px;
            box-shadow: 0 0 10px rgba(0,0,0,0.1);
        }}
        .drive-selector-area h3 {{
            border-bottom: none;
            margin-top: 0;
            padding-bottom: 0;
        }}
        </style>
        """,
        unsafe_allow_html=True
    )

    if st.button("⬅️ Voltar para a Página Inicial", key="btn_back_home_from_chat"):
        st.session_state.page = "home"
        st.rerun()

    st.markdown('<h1 class="neon-title">🤖 Safety AI Chat</h1>', unsafe_allow_html=True)
    st.markdown("Seu assistente inteligente para dúvidas sobre **Saúde e Segurança do Trabalho**.")

    if "messages" not in st.session_state:
        st.session_state.messages = []
    
    # ALTERADO: Renomeado show_file_uploader para show_document_context_selector
    if "show_document_context_selector" not in st.session_state:
        st.session_state.show_document_context_selector = False
    if "user_drive_service" not in st.session_state:
        st.session_state["user_drive_service"] = None
    if "chat_context_files_metadata" not in st.session_state:
        st.session_state["chat_context_files_metadata"] = []
    if "chat_local_files_bytes" not in st.session_state:
        st.session_state["chat_local_files_bytes"] = []

    welcome_message = """
    �� Olá! Eu sou o <b>Leo</b>, seu <b>chatbot amigável</b> e especializado em <b>Saúde e Segurança do Trabalho</b>.
    Estou aqui para <b>facilitar sua jornada</b>! Que tal <b>fazer uma pergunta</b> para começar?
    Ou, se preferir, pode <b>enviar um documento</b> para que eu o analise!
    """
    
    # Lógica para adicionar a welcome_message com a flag is_raw_html
    welcome_message_exists_and_is_correctly_flagged = False
    if st.session_state.messages and st.session_state.messages[0]["role"] == "ai":
        first_message = st.session_state.messages[0]
        if first_message.get("is_raw_html", False) and first_message["content"].strip() == welcome_message.strip():
            welcome_message_exists_and_is_correctly_flagged = True

    if not welcome_message_exists_and_is_correctly_flagged:
        st.session_state.messages = [
            msg for msg in st.session_state.messages 
            if not (msg["role"] == "ai" and msg["content"].strip() == welcome_message.strip() and msg.get("is_raw_html", False))
        ]
        st.session_state.messages.insert(0, {
            "role": "ai",
            "content": welcome_message,
            "is_raw_html": True
        })

    qa_system = get_nr_rag_qa_system()

    if qa_system:
        chat_display_area = st.container(height=480, border=True)
        with chat_display_area:
            for message in st.session_state.messages:
                content_to_display = message["content"]
                
                if message.get("is_raw_html", False):
                    final_html = content_to_display
                else:
                    final_html = markdown.markdown(content_to_display)
                    
                if message["role"] == "user":
                    st.markdown(f'<div class="chat-message-container"><div class="chat-message user">{final_html}</div></div>', unsafe_allow_html=True)
                else:
                    st.markdown(f'<div class="chat-message-container"><div class="chat-message ai">{final_html}</div></div>', unsafe_allow_html=True)
        
        st.markdown('<div class="chat-input-area">', unsafe_allow_html=True) 
        
        # --- Linha dos Botões de Ícone ---
        st.markdown('<div class="icon-buttons-row">', unsafe_allow_html=True)
        icon_cols = st.columns([0.08, 0.08, 0.08, 0.08, 0.08, 1]) 

        with icon_cols[0]: # Lápis (Refinar/Editar)
            st.button("🪄", key="btn_icon_pencil", help="Refinar e Editar", on_click=_on_pencil_click, use_container_width=True)
        with icon_cols[1]: # Microfone
            st.button("🎤", key="btn_icon_mic", help="Áudio para Texto", on_click=_on_mic_click, use_container_width=True)
        with icon_cols[2]: # Documentos (Agora ativa o seletor de contexto)
            st.button("��", key="btn_icon_docs", help="Usar documentos como contexto", on_click=_on_docs_click, use_container_width=True)
        with icon_cols[3]: # Imagem
            st.button("📷", key="btn_icon_image", help="Analisar Imagem", on_click=_on_image_click, use_container_width=True)
        with icon_cols[4]: # Gerar Conteúdo
            st.button("⚙️", key="btn_icon_generate", help="Gerar Conteúdo", on_click=_on_generate_click, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True) # Fim da div icon-buttons-row

        # --- Seletor de Contexto de Documentos (condicional) ---
        if st.session_state.show_document_context_selector:
            st.markdown('<div class="drive-selector-area">', unsafe_allow_html=True)
            st.subheader("Documentos para Contexto da Conversa")
            st.info("Aqui você pode selecionar documentos do seu computador ou do Google Drive para que o SafetyAI use como contexto nas suas respostas.")

            tab_local, tab_drive = st.tabs(["Meu Computador", "Google Drive Pessoal"])

            # --- Tab: Meu Computador (Local File Uploader) ---
            with tab_local:
                st.markdown("Envie documentos do seu computador para usar como contexto.")
                uploaded_local_files = st.file_uploader(
                    "Selecione um ou mais documentos (.pdf, .docx, .txt)",
                    type=["pdf", "docx", "txt"],
                    accept_multiple_files=True,
                    key="file_uploader_chat_local"
                )
                if uploaded_local_files:
                    st.session_state["chat_local_files_bytes"] = []
                    for up_file in uploaded_local_files:
                        file_bytes = up_file.getvalue()
                        if file_bytes:
                            st.session_state["chat_local_files_bytes"].append({
                                "name": up_file.name,
                                "mime_type": up_file.type,
                                "bytes": file_bytes
                            })
                    st.info(f"✨ **{len(uploaded_local_files)} documento(s) do seu computador selecionado(s) para contexto.**")
                else:
                    st.session_state["chat_local_files_bytes"] = []
                    st.info("Nenhum documento local selecionado.")

            # --- Tab: Google Drive Pessoal ---
            with tab_drive:
                # Lógica de autenticação do Google Drive (se não estiver autenticado)
                user_service_status_message_chat_context = ""
                try:
                    if st.session_state["user_drive_service"] is None:
                        temp_user_service = get_google_drive_service_user()
                        if temp_user_service:
                            st.session_state["user_drive_service"] = temp_user_service
                    if st.session_state["user_drive_service"] is None:
                        user_service_status_message_chat_context = "⚠️ Por favor, autentique seu Google Drive para usar seus arquivos como contexto."
                except Exception as e:
                    logging.error(f"Erro ao obter user_drive_service para contexto do chat: {e}")
                    user_service_status_message_chat_context = f"❌ Erro: {e}. Tente novamente."

                if user_service_status_message_chat_context:
                    st.warning(user_service_status_message_chat_context)
                    if st.button("Tentar Autenticar Google Drive Agora", key="re_auth_drive_chat_context"):
                        st.session_state["user_drive_service"] = None
                        st.rerun()
                elif st.session_state["user_drive_service"]:
                    # Seletor de pastas do Drive
                    user_folders = [{'id': 'root', 'name': 'Meu Drive (Raiz)'}]
                    try:
                        folders_from_drive = list_drive_folders(st.session_state["user_drive_service"])
                        user_folders.extend([f for f in folders_from_drive if f['id'] != 'root'])
                    except Exception as e:
                        logging.error(f"Erro ao listar pastas do Drive do usuário para contexto: {e}")
                        st.error(f"❌ Erro ao listar suas pastas: {e}. Verifique sua conexão ou permissões.")

                    folder_options = {f['name']: f['id'] for f in user_folders}
                    sorted_folder_names = sorted(folder_options.keys(), key=lambda x: (x != 'Meu Drive (Raiz)', x))

                    selected_folder_name = st.selectbox(
                        "Selecione uma pasta do seu Drive:",
                        options=sorted_folder_names,
                        key="user_chat_folder_selector",
                        help="Escolha uma pasta para listar arquivos que podem ser usados como contexto."
                    )
                    selected_folder_id = folder_options.get(selected_folder_name, 'root')

                    # Busca arquivos da pasta selecionada
                    user_folder_files = _fetch_drive_files_cached(st.session_state["user_drive_service"], selected_folder_id)
                    
                    # Filtra e prepara arquivos processáveis para seleção
                    processable_files_options = []
                    for f in user_folder_files:
                        # Arquivos Google Docs precisam de exportação para serem processáveis como texto
                        if f['mimeType'] in PROCESSABLE_MIME_TYPES_FOR_RAG or f['mimeType'] == 'application/vnd.google-apps.document':
                            processable_files_options.append(f)
                    
                    if processable_files_options:
                        selected_drive_files_metadata = st.multiselect(
                            f"Selecione arquivos da pasta '{selected_folder_name}' para contexto:",
                            options=processable_files_options,
                            format_func=lambda x: f"📄 {x['name']} ({MIME_TYPE_DISPLAY_FOR_CHAT_CONTEXT.get(x['mimeType'], MIME_TYPE_DISPLAY_FOR_CHAT_CONTEXT['default'])})",
                            key="chat_drive_files_multiselect",
                            help="Selecione os documentos que deseja que o SafetyAI use como base para responder."
                        )
                        st.session_state["chat_context_files_metadata"] = selected_drive_files_metadata
                        if selected_drive_files_metadata:
                            st.info(f"✨ **{len(selected_drive_files_metadata)} documento(s) do Google Drive selecionado(s) para contexto.**")
                    else:
                        st.session_state["chat_context_files_metadata"] = []
                        st.info(f"Nenhum arquivo processável encontrado na pasta '{selected_folder_name}'.")
                else:
                    st.info("Nenhum serviço do Google Drive do usuário disponível para selecionar arquivos.")
            
            st.markdown('</div>', unsafe_allow_html=True) # Fecha a div drive-selector-area
        
        # --- Formulário Principal do Chat ---
        with st.form(key='chat_form_submission', clear_on_submit=True):
            form_cols = st.columns([1, 0.15])
            with form_cols[0]:
                user_query_input = st.text_input(
                    "Digite sua pergunta...",
                    placeholder="Ex: Quais são as responsabilidades do empregador segundo a NR-35?",
                    key="user_chat_query_input",
                    label_visibility="collapsed"
                )
            with form_cols[1]:
                nr_query_button = st.form_submit_button("➡️") 
            
            if nr_query_button:
                submitted_query = st.session_state.user_chat_query_input 
                
                if submitted_query.strip():
                    st.session_state.messages.append({"role": "user", "content": submitted_query})
                    
                    with st.spinner("⏳ Analisando e gerando resposta..."):
                        dynamic_context_texts = []

                        # Processar arquivos locais selecionados
                        if st.session_state["chat_local_files_bytes"]:
                            st.markdown("💬 **Processando seus arquivos locais para contexto...**")
                            for file_data in st.session_state["chat_local_files_bytes"]:
                                try:
                                    text = extract_text_from_bytes(file_data["bytes"], file_data["mime_type"])
                                    if text:
                                        dynamic_context_texts.append(text)
                                    else:
                                        st.warning(f"Não foi possível extrair texto de '{file_data['name']}'.")
                                except Exception as e:
                                    logging.error(f"Erro ao processar arquivo local '{file_data['name']}': {e}")
                                    st.error(f"❌ Erro ao processar arquivo local '{file_data['name']}'.")
                            
                        # Processar arquivos do Google Drive selecionados
                        if st.session_state["chat_context_files_metadata"] and st.session_state["user_drive_service"]:
                            st.markdown("💬 **Baixando e processando documentos do seu Google Drive para contexto...**")
                            for file_meta in st.session_state["chat_context_files_metadata"]:
                                file_id = file_meta['id']
                                file_name = file_meta['name']
                                original_mime_type = file_meta['mimeType']
                                
                                try:
                                    download_filename, export_mime = get_download_metadata(file_name, original_mime_type)
                                    
                                    if download_filename: # Se houver um nome de arquivo para download/exportação
                                        file_bytes = get_file_bytes_for_download(st.session_state["user_drive_service"], file_id, export_mime)
                                        
                                        if file_bytes:
                                            text = extract_text_from_bytes(file_bytes, export_mime) # Usa export_mime para extração
                                            if text:
                                                dynamic_context_texts.append(text)
                                            else:
                                                st.warning(f"Não foi possível extrair texto de '{file_name}'.")
                                        else:
                                            st.warning(f"Conteúdo vazio ou não disponível para '{file_name}'.")
                                    else:
                                        st.warning(f"Arquivo '{file_name}' não pode ser baixado/exportado para contexto.")
                                except Exception as e:
                                    logging.error(f"Erro ao baixar/processar arquivo do Drive '{file_name}' (ID: {file_id}) para contexto: {e}")
                                    st.error(f"❌ Erro ao usar '{file_name}' como contexto.")

                        try:
                            # Chama o sistema de QA passando o contexto dinâmico
                            # NOTA: Você precisará adaptar a classe NRQuestionAnswering para aceitar este parâmetro e usá-lo.
                            nr_answer = qa_system.answer_question(submitted_query, st.session_state.messages, dynamic_context_texts=dynamic_context_texts)
                            st.session_state.messages.append({"role": "ai", "content": nr_answer})
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ Ocorreu um erro ao obter a resposta: {e}")
                            st.error("Por favor, tente novamente ou verifique o log para mais detalhes.")
                else:
                    st.warning("⚠️ Por favor, digite uma pergunta antes de enviar.")
        
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