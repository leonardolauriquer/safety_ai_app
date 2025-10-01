import streamlit as st
import logging
import markdown 
import os
import tempfile
import shutil
import uuid 
import time

from safety_ai_app.theme_config import THEME, _get_material_icon_html
from safety_ai_app.google_drive_integrator import (
    list_drive_folders,
    get_file_bytes_for_download,
    get_processable_drive_files_in_folder,
    get_download_metadata,
)
from safety_ai_app.nr_rag_qa import NRQuestionAnswering 
from safety_ai_app.text_extractors import get_text_from_file_path, get_mime_type_for_drive_export as get_extractor_export_mime

logger = logging.getLogger(__name__)

PROCESSABLE_MIME_TYPES_FOR_RAG = [
    'application/pdf',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document', 
    'text/plain',
    'application/vnd.google-apps.document', 
]

MIME_TYPE_DISPLAY_FOR_CHAT_CONTEXT = {
    'application/pdf': 'PDF Documento',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document': 'DOCX Documento',
    'text/plain': 'TXT Documento',
    'application/vnd.google-apps.document': 'Google Docs',
    'default': 'Arquivo'
}

def _render_info_like_message(message_type: str, message: str, icon_name: str = None) -> None:
    """
    Renderiza uma mensagem com estilo Streamlit (info, warning, success, error)
    permitindo a inclusão de um ícone Material Symbols.
    
    Args:
        message_type: Tipo da mensagem (info, warning, success, error)
        message: Texto da mensagem
        icon_name: Nome do ícone Material Symbol (opcional)
        
    Raises:
        None: Função não levanta exceções
    """
    icon_html = _get_material_icon_html(icon_name) if icon_name else ""
    st.markdown(f"<div class='st-{message_type}-like'>{icon_html} {message}</div>", unsafe_allow_html=True)

def _on_docs_click_wrapper() -> None:
    """
    Wrapper para a função _on_docs_click para ser chamada pelo botão de documentos.
    
    Raises:
        None: Função não levanta exceções
    """
    st.session_state.show_document_context_selector = not st.session_state.show_document_context_selector

def render_page(process_markdown_for_external_links_func) -> None:
    """
    Renderiza a página de chat completa.
    
    Args:
        process_markdown_for_external_links_func: Função para processar links externos
        
    Raises:
        None: Função não levanta exceções
    """
    # Título da página de chat com neon
    st.markdown(f'<h1 class="neon-title">{_get_material_icon_html(THEME["icons"]["chat_bubble"])} {THEME["phrases"]["chat_page_title"]}</h1>', unsafe_allow_html=True)

    qa_system: NRQuestionAnswering = st.session_state.nr_qa
    if qa_system is None:
        _render_info_like_message("error", "O sistema de QA (RAG) não foi inicializado. Por favor, verifique as configurações da API Key e ChromaDB.", THEME["icons"]["error_x"])
        return 

    # Área de exibição do chat
    chat_display_area = st.container(height=480, border=True)
    with chat_display_area:
        for message in st.session_state.messages:
            processed_content_html = process_markdown_for_external_links_func(message["content"])
            
            if message["role"] == "user":
                st.markdown(f'<div class="chat-message-container"><div class="chat-message user">{processed_content_html}</div></div>', unsafe_allow_html=True)
            else:
                st.markdown(f"""
                <div class="chat-message-container">
                    <div class="chat-message ai">
                        {processed_content_html}
                    </div>
                </div>
                """, unsafe_allow_html=True)
        
        # Auto-scroll para o final do chat
        st.markdown("""
            <script>
                var chatContainer = document.querySelector('[data-testid="stVerticalBlock"] > div[data-testid="stVerticalBlock"] > div[data-testid="stVerticalBlock"]:nth-child(2)');
                if (chatContainer) {
                    chatContainer.scrollTop = chatContainer.scrollHeight;
                }
            </script>
        """, unsafe_allow_html=True)

    st.markdown('<div class="chat-input-area">', unsafe_allow_html=True) 

    # Botões de ação com ícones - CORRIGIDOS
    icon_cols = st.columns([0.08, 0.08, 0.08, 0.08, 0.08, 1]) 

    with icon_cols[0]:
        if st.button("", key="btn_icon_pencil", help=THEME["phrases"]["refine_edit"], icon=":material/edit:"):
             _render_info_like_message("info", "Funcionalidade de Refinamento e Edição (Lápis Mágico) em desenvolvimento!", THEME["icons"]["info_circular_outline"])
    
    with icon_cols[1]:
        if st.button("", key="btn_icon_mic", help=THEME["phrases"]["audio_to_text"], icon=":material/mic:"):
            _render_info_like_message("info", "Funcionalidade de Áudio para Texto (Microfone) é um recurso da plataforma. Ative o microfone para usar!", THEME["icons"]["info_circular_outline"])
    
    with icon_cols[2]:
        if st.button("", key="btn_icon_docs", help=THEME["phrases"]["use_docs_context"], icon=":material/folder_open:"):
            _on_docs_click_wrapper() 
    
    with icon_cols[3]:
        if st.button("", key="btn_icon_image", help="Analisar Imagem", icon=":material/image:"):
            _render_info_like_message("info", "Funcionalidade de Análise de Imagem: Em breve! Explorará capacidades multimodais.", THEME["icons"]["info_circular_outline"])
    
    with icon_cols[4]:
        if st.button("", key="btn_icon_generate", help="Gerar Conteúdo", icon=":material/tune:"):
            _render_info_like_message("info", "Funcionalidade de Geração: Permite criar novos conteúdos e resumos. Em breve!", THEME["icons"]["info_circular_outline"])

    # Seletor de documentos para contexto
    if st.session_state.show_document_context_selector:
        st.markdown('<div class="drive-selector-area">', unsafe_allow_html=True)
        st.subheader("Documentos para Contexto da Conversa")
        _render_info_like_message("info", f"Aqui você pode selecionar documentos do seu computador ou do Google Drive para que o SafetyAI use como contexto nas suas respostas. **Os documentos selecionados permanecerão ativos para todas as perguntas.**", THEME["icons"]["info_circular_outline"])

        tab_local, tab_drive = st.tabs(["Meu Computador", "Google Drive Pessoal"])

        with tab_local:
            st.markdown("Envie documentos do seu computador para usar como contexto.")
            uploaded_local_files = st.file_uploader(
                "Selecione um ou mais documentos (.pdf, .docx, .txt)",
                type=["pdf", "docx", "txt"],
                accept_multiple_files=True,
                key="file_uploader_chat_local"
            )
            
            new_local_files = []
            if uploaded_local_files:
                for up_file in uploaded_local_files:
                    file_id = f"local_{uuid.uuid4()}"
                    new_local_files.append({
                        'id': file_id,
                        'name': up_file.name,
                        'source': 'local',
                        'mime_type': up_file.type,
                        'bytes': up_file.getvalue() 
                    })
            
            st.session_state.active_context_files = [
                f for f in st.session_state.active_context_files if f['source'] != 'local'
            ] + new_local_files
            
            if new_local_files:
                _render_info_like_message("info", f"**{len(new_local_files)} documento(s) do seu computador selecionado(s) para contexto.**", THEME["icons"]["info_circular_outline"])
            elif not any(f['source'] == 'local' for f in st.session_state.active_context_files):
                _render_info_like_message("info", "Nenhum arquivo local selecionado.", THEME["icons"]["generic_info"])

        with tab_drive:
            if st.session_state.get("user_drive_service") is None:
                _render_info_like_message("warning", f"Por favor, autentique seu Google Drive para usar seus arquivos como contexto.", THEME["icons"]["warning_sign"])
                if st.button("Tentar Autenticar Google Drive Agora", key="re_auth_drive_chat_context", icon=":material/vpn_key:"):
                    st.session_state["user_drive_service"] = None
                    st.rerun()
            elif st.session_state["user_drive_service"]:
                user_folders = [{'id': 'root', 'name': 'Meu Drive (Raiz)'}]
                try:
                    folders_from_drive = list_drive_folders(st.session_state["user_drive_service"])
                    user_folders.extend([f for f in folders_from_drive if f['id'] != 'root'])
                except Exception as e:
                    logger.error(f"Erro ao listar pastas do Drive do usuário para contexto: {e}", exc_info=True)
                    _render_info_like_message("error", f"Erro ao listar suas pastas: {e}. Verifique sua conexão ou permissões.", THEME["icons"]["error_x"])

                folder_options = {f['name']: f['id'] for f in user_folders}
                sorted_folder_names = sorted(folder_options.keys(), key=lambda x: (x != 'Meu Drive (Raiz)', x))

                selected_folder_name = st.selectbox(
                    "Selecione uma pasta do seu Drive:",
                    options=sorted_folder_names,
                    key="user_chat_folder_selector",
                    help="Escolha uma pasta para listar arquivos que podem ser usados como contexto."
                )
                selected_folder_id = folder_options.get(selected_folder_name, 'root')

                all_drive_files_in_folder = get_processable_drive_files_in_folder(st.session_state["user_drive_service"], selected_folder_id)
                
                processable_drive_files_options = all_drive_files_in_folder
                
                current_drive_context_ids = {f['id'] for f in st.session_state.active_context_files if f['source'] == 'drive'}
                default_selected_drive_files = [
                    f for f in processable_drive_files_options if f['id'] in current_drive_context_ids
                ]

                selected_drive_files_metadata = st.multiselect(
                    f"Selecione arquivos da pasta '{selected_folder_name}' para contexto:",
                    options=processable_drive_files_options,
                    default=default_selected_drive_files,
                    format_func=lambda x: f" {x['name']} ({MIME_TYPE_DISPLAY_FOR_CHAT_CONTEXT.get(x['mimeType'], MIME_TYPE_DISPLAY_FOR_CHAT_CONTEXT['default'])})",
                    key="chat_drive_files_multiselect",
                    help="Selecione os documentos que deseja que o SafetyAI use como base para responder."
                )
                
                st.session_state.active_context_files = [
                    f for f in st.session_state.active_context_files if f['source'] != 'drive'
                ] + [
                    {'id': f['id'], 'name': f['name'], 'source': 'drive', 'mime_type': f['mimeType']} for f in selected_drive_files_metadata
                ]

                if selected_drive_files_metadata:
                    _render_info_like_message("info", f"**{len(selected_drive_files_metadata)} documento(s) do Google Drive selecionado(s) para contexto.**", THEME["icons"]["info_circular_outline"])
                elif not any(f['source'] == 'drive' for f in st.session_state.active_context_files):
                    _render_info_like_message("info", "Nenhum arquivo do Drive selecionado.", THEME["icons"]["generic_info"])
            else:
                _render_info_like_message("info", "Nenhum serviço do Google Drive do usuário disponível para selecionar arquivos.", THEME["icons"]["generic_info"])
        
        st.markdown('</div>', unsafe_allow_html=True) 

    # Exibição dos documentos ativos no contexto
    if st.session_state.active_context_files:
        st.markdown(f"---")
        st.markdown(f"**{_get_material_icon_html(THEME['icons']['info_circular_outline'])} Documentos ativos no contexto do chat ({len(st.session_state.active_context_files)}):**", unsafe_allow_html=True)
        
        num_active_files = len(st.session_state.active_context_files)
        cols_per_row = 5
        
        for i in range(0, num_active_files, cols_per_row):
            row_files = st.session_state.active_context_files[i : i + cols_per_row]
            current_active_cols = st.columns(len(row_files))
            for j, item in enumerate(row_files):
                with current_active_cols[j]:
                    st.markdown(f"<span style='font-size:0.8em;'>{_get_material_icon_html(THEME['icons']['file_doc'])} {item['name']} ({'Local' if item['source']=='local' else 'Drive'})</span>", unsafe_allow_html=True)
        
        # Botão para limpar contexto - CORRIGIDO
        if st.button("Limpar Todos os Anexos de Contexto", key="clear_all_dynamic_context_files", icon=":material/delete:", type="secondary"):
            st.session_state.active_context_files = []
            st.session_state.dynamic_context_texts = [] 
            st.toast("Todos os anexos de contexto dinâmico limpos!", icon=":material/check_circle:")
            st.rerun() 
        st.markdown(f"---")

    # Formulário de entrada do chat
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
            nr_query_button = st.form_submit_button(
                label="",
                icon=":material/send:",
                use_container_width=False
            )
        
        if nr_query_button:
            submitted_query = st.session_state.user_chat_query_input 
            
            if submitted_query.strip():
                st.session_state.messages.append({"role": "user", "content": submitted_query})
                
                with st.spinner(""):
                    st.markdown(f"<p style='text-align: center; color: var(--text-color);'>{_get_material_icon_html(THEME['icons']['loading_hourglass'])} Analisando e gerando resposta...</p>", unsafe_allow_html=True)
                    dynamic_context_texts = []

                    if st.session_state.active_context_files:
                        st.markdown(f"{_get_material_icon_html(THEME['icons']['chat_bubble'])} **Processando {len(st.session_state.active_context_files)} documento(s) para contexto...**", unsafe_allow_html=True)
                        
                        temp_dir = tempfile.mkdtemp(prefix="chat_context_")
                        try:
                            for file_data in st.session_state.active_context_files:
                                file_name = file_data['name']
                                file_id = file_data['id']
                                file_source = file_data['source']
                                original_mime_type = file_data['mime_type']
                                
                                try:
                                    final_file_name_for_temp, export_mime = get_download_metadata(file_name, original_mime_type)

                                    temp_file_path = os.path.join(temp_dir, final_file_name_for_temp)
                                    
                                    if file_source == 'local':
                                        file_bytes_to_process = file_data['bytes']
                                        with open(temp_file_path, 'wb') as f:
                                            f.write(file_bytes_to_process)
                                    elif file_source == 'drive':
                                        file_bytes_to_process = get_file_bytes_for_download(
                                            st.session_state.user_drive_service,
                                            file_id,
                                            original_mime_type, 
                                            export_mime
                                        )
                                        with open(temp_file_path, "wb") as f:
                                            f.write(file_bytes_to_process)
                                    else:
                                        file_bytes_to_process = None 

                                    processed_mime_type = export_mime 
                                    
                                    if file_bytes_to_process:
                                        text = get_text_from_file_path(temp_file_path, file_name, processed_mime_type)
                                        
                                        if text and not text.strip().startswith("[ERRO:"):
                                            dynamic_context_texts.append(f"Conteúdo de '{file_name}' ({file_source}):\n{text}")
                                        elif text.strip().startswith("[ERRO:"):
                                            _render_info_like_message("warning", f"Não foi possível extrair texto de '{file_name}'. {text}", THEME["icons"]["error_x"])
                                        else:
                                            _render_info_like_message("warning", f"Conteúdo vazio ou não disponível para '{file_name}'.", THEME["icons"]["error_x"])
                                    else:
                                        _render_info_like_message("warning", f"Não foi possível obter o conteúdo de '{file_name}' ({file_source}).", THEME["icons"]["error_x"])
                                except Exception as e:
                                    logging.error(f"Erro ao processar arquivo '{file_name}' ({file_source}) para contexto: {e}", exc_info=True)
                                    _render_info_like_message("error", f"Erro ao usar '{file_name}' como contexto. Detalhes: {e}", THEME["icons"]["error_x"])
                            
                        finally:
                            if os.path.exists(temp_dir):
                                shutil.rmtree(temp_dir)
                                logger.info(f"Diretório temporário '{temp_dir}' removido.")
                    
                    try:
                        ai_response = qa_system.answer_question(
                            query=submitted_query, 
                            chat_history=st.session_state.messages,
                            dynamic_context_texts=dynamic_context_texts
                        )
                        st.session_state.messages.append({"role": "ai", "content": ai_response})
                    except Exception as e:
                        logger.error(f"Erro ao gerar resposta da IA: {e}", exc_info=True)
                        st.session_state.messages.append({"role": "ai", "content": f"Desculpe, ocorreu um erro ao gerar a resposta: {e}"})
                
                st.rerun() 
            else:
                _render_info_like_message("warning", "Por favor, digite uma pergunta antes de enviar.", THEME["icons"]["warning_sign"])
        
    st.markdown('</div>', unsafe_allow_html=True)
