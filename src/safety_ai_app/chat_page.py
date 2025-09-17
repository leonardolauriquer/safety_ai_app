import streamlit as st
import os
import markdown
import logging
from datetime import date # Necessário para o controle de doações, se for re-utilizado algo
import io

# Importações para extração de texto
try:
    from pypdf import PdfReader
except ImportError:
    PdfReader = None
    logging.warning("pypdf não está instalado. Não será possível extrair texto de PDFs.")

try:
    from docx import Document
except ImportError:
    Document = None
    logging.warning("python-docx não está instalado. Não será possível extrair texto de DOCX.")


# Importações do seu RAG e tema
from safety_ai_app.nr_rag_qa import NRQuestionAnswering
from safety_ai_app.theme_config import THEME # Importado para acessar emojis e frases

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

def extract_text_from_bytes(file_bytes: bytes, mime_type: str) -> str:
    """
    Função para extrair texto de bytes de arquivos.
    """
    if not file_bytes:
        return ""
    
    if mime_type == 'text/plain':
        try:
            return file_bytes.decode('utf-8')
        except UnicodeDecodeError:
            return file_bytes.decode('latin-1', errors='ignore')

    elif mime_type == 'application/pdf' and PdfReader:
        try:
            reader = PdfReader(io.BytesIO(file_bytes))
            text = ""
            for page in reader.pages:
                text += page.extract_text() or "" # Garante que adicione string vazia se extract_text for None
            return text
        except Exception as e:
            logging.error(f"Erro ao extrair texto de PDF: {e}")
            return f"[ERRO: Falha ao extrair texto do PDF. Detalhes: {e}]"
            
    elif mime_type == 'application/vnd.openxmlformats-officedocument.wordprocessingml.document' and Document:
        try:
            document = Document(io.BytesIO(file_bytes))
            text = ""
            for para in document.paragraphs:
                text += para.text + "\n"
            return text
        except Exception as e:
            logging.error(f"Erro ao extrair texto de DOCX: {e}")
            return f"[ERRO: Falha ao extrair texto do DOCX. Detalhes: {e}]"

    logging.warning(f"Tipo de arquivo '{mime_type}' não tem um extrator de texto implementado ou biblioteca ausente. Conteúdo não será usado.")
    return f"[Conteúdo do tipo {mime_type} não pode ser extraído para o RAG. Biblioteca ausente ou tipo não suportado.]"


@st.cache_resource
def get_nr_rag_qa_system():
    try:
        qa_system = NRQuestionAnswering()
        return qa_system
    except Exception as e:
        st.error(f"{THEME['emojis']['error_x']} Erro ao inicializar o Sistema de QA de SST: {e}")
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
    # Botão de voltar, usando a chave específica para o estilo global.
    if st.button(f"{THEME['emojis']['back_arrow']} {THEME['phrases']['back_to_home']}", key="btn_back_home_from_chat"):
        st.session_state.page = "home"
        st.rerun()

    # Título neon usando a classe global e emojis centralizados
    st.markdown(f'<h1 class="neon-title">{THEME["emojis"]["ai_robot"]} Safety AI Chat</h1>', unsafe_allow_html=True)
    st.markdown("Seu assistente inteligente para dúvidas sobre **Saúde e Segurança do Trabalho**.")

    if "messages" not in st.session_state:
        st.session_state.messages = []
    
    if "show_document_context_selector" not in st.session_state:
        st.session_state.show_document_context_selector = False
    if "user_drive_service" not in st.session_state:
        st.session_state["user_drive_service"] = None
    if "chat_context_files_metadata" not in st.session_state:
        st.session_state["chat_context_files_metadata"] = []
    if "chat_local_files_bytes" not in st.session_state:
        st.session_state["chat_local_files_bytes"] = []

    welcome_message = f"""
    {THEME["emojis"]["welcome_wave"]} Olá! Eu sou o <b>Leo</b>, seu <b>chatbot amigável</b> e especializado em <b>Saúde e Segurança do Trabalho</b>.
    Estou aqui para <b>facilitar sua jornada</b>! Que tal <b>fazer uma pergunta</b> para começar?
    Ou, se preferir, pode <b>enviar um documento</b> para que eu o analise!
    """
    
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
            st.button(THEME["emojis"]["magic_pencil"], key="btn_icon_pencil", help=THEME["phrases"]["refine_edit"], on_click=_on_pencil_click, use_container_width=True)
        with icon_cols[1]: # Microfone
            st.button(THEME["emojis"]["microphone"], key="btn_icon_mic", help=THEME["phrases"]["audio_to_text"], on_click=_on_mic_click, use_container_width=True)
        with icon_cols[2]: # Documentos (Agora ativa o seletor de contexto)
            st.button(THEME["emojis"]["folder_docs"], key="btn_icon_docs", help=THEME["phrases"]["use_docs_context"], on_click=_on_docs_click, use_container_width=True)
        with icon_cols[3]: # Imagem
            st.button(THEME["emojis"]["image_frame"], key="btn_icon_image", help=THEME["phrases"]["analyze_image"], on_click=_on_image_click, use_container_width=True)
        with icon_cols[4]: # Gerar Conteúdo
            st.button(THEME["emojis"]["settings_gear"], key="btn_icon_generate", help=THEME["phrases"]["generate_content"], on_click=_on_generate_click, use_container_width=True)
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
                # ATUALIZADO: Lógica para limpar arquivos locais se o uploader estiver vazio
                if uploaded_local_files:
                    current_local_files_data = []
                    for up_file in uploaded_local_files:
                        file_bytes = up_file.getvalue()
                        if file_bytes:
                            current_local_files_data.append({
                                "name": up_file.name,
                                "mime_type": up_file.type,
                                "bytes": file_bytes
                            })
                    st.session_state["chat_local_files_bytes"] = current_local_files_data
                    st.info(f"{THEME['emojis']['info_sparkle']} **{len(uploaded_local_files)} documento(s) do seu computador selecionado(s) para contexto.**")
                else:
                    st.session_state["chat_local_files_bytes"] = [] # Garante que a lista é limpa se nada for selecionado
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
                    user_service_status_message_chat_context = f"{THEME['emojis']['error_x']} Erro: {e}. Tente novamente."

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
                        st.error(f"{THEME['emojis']['error_x']} Erro ao listar suas pastas: {e}. Verifique sua conexão ou permissões.")

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
                            format_func=lambda x: f"{THEME['emojis']['file_doc']} {x['name']} ({MIME_TYPE_DISPLAY_FOR_CHAT_CONTEXT.get(x['mimeType'], MIME_TYPE_DISPLAY_FOR_CHAT_CONTEXT['default'])})",
                            key="chat_drive_files_multiselect",
                            help="Selecione os documentos que deseja que o SafetyAI use como base para responder."
                        )
                        st.session_state["chat_context_files_metadata"] = selected_drive_files_metadata
                        if selected_drive_files_metadata:
                            st.info(f"{THEME['emojis']['info_sparkle']} **{len(selected_drive_files_metadata)} documento(s) do Google Drive selecionado(s) para contexto.**")
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
                    placeholder=THEME["phrases"]["default_placeholder"],
                    key="user_chat_query_input",
                    label_visibility="collapsed"
                )
            with form_cols[1]:
                nr_query_button = st.form_submit_button(THEME["emojis"]["send_arrow"]) 
            
            if nr_query_button:
                submitted_query = st.session_state.user_chat_query_input 
                
                if submitted_query.strip():
                    # Adiciona a mensagem do usuário ao histórico antes de processar
                    st.session_state.messages.append({"role": "user", "content": submitted_query})
                    
                    with st.spinner("⏳ Analisando e gerando resposta..."):
                        dynamic_context_texts = []

                        # Processar arquivos locais selecionados
                        if st.session_state["chat_local_files_bytes"]:
                            st.markdown(f"{THEME['emojis']['chat_bubble']} **Processando seus arquivos locais para contexto...**")
                            for file_data in st.session_state["chat_local_files_bytes"]:
                                try:
                                    text = extract_text_from_bytes(file_data["bytes"], file_data["mime_type"])
                                    if text and not text.startswith("[ERRO:"): # Verificar se houve erro na extração
                                        dynamic_context_texts.append(f"Conteúdo de '{file_data['name']}':\n{text}")
                                    elif text.startswith("[ERRO:"):
                                        st.warning(f"{THEME['emojis']['error_x']} Não foi possível extrair texto de '{file_data['name']}'. {text}")
                                    else:
                                        st.warning(f"{THEME['emojis']['error_x']} Não foi possível extrair texto de '{file_data['name']}'. Conteúdo vazio.")
                                except Exception as e:
                                    logging.error(f"Erro ao processar arquivo local '{file_data['name']}': {e}")
                                    st.error(f"{THEME['emojis']['error_x']} Erro ao processar arquivo local '{file_data['name']}'. Detalhes: {e}")
                            
                        # Processar arquivos do Google Drive selecionados
                        if st.session_state["chat_context_files_metadata"] and st.session_state["user_drive_service"]:
                            st.markdown(f"{THEME['emojis']['chat_bubble']} **Baixando e processando documentos do seu Google Drive para contexto...**")
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
                                            if text and not text.startswith("[ERRO:"): # Verificar se houve erro na extração
                                                dynamic_context_texts.append(f"Conteúdo de '{file_name}':\n{text}")
                                            elif text.startswith("[ERRO:"):
                                                st.warning(f"{THEME['emojis']['error_x']} Não foi possível extrair texto de '{file_name}'. {text}")
                                            else:
                                                st.warning(f"{THEME['emojis']['error_x']} Conteúdo vazio ou não disponível para '{file_name}'.")
                                        else:
                                            st.warning(f"{THEME['emojis']['error_x']} Conteúdo vazio ou não disponível para '{file_name}'.")
                                    else:
                                        st.warning(f"{THEME['emojis']['error_x']} Arquivo '{file_name}' não pode ser baixado/exportado para contexto.")
                                except Exception as e:
                                    logging.error(f"Erro ao baixar/processar arquivo do Drive '{file_name}' (ID: {file_id}) para contexto: {e}")
                                    st.error(f"{THEME['emojis']['error_x']} Erro ao usar '{file_name}' como contexto. Detalhes: {e}")

                        try:
                            # Chama o sistema de QA passando o contexto dinâmico
                            nr_answer = qa_system.answer_question(submitted_query, st.session_state.messages, dynamic_context_texts=dynamic_context_texts)
                            st.session_state.messages.append({"role": "ai", "content": nr_answer})
                            st.rerun() # Atualiza a página para mostrar a nova mensagem
                        except Exception as e:
                            st.error(f"{THEME['emojis']['error_x']} Ocorreu um erro ao obter a resposta: {e}")
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
        {THEME["phrases"]["footer_text"]}
    </div>
    """, unsafe_allow_html=True)