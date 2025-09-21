import streamlit as st
import os
from pathlib import Path
import io
import logging
from datetime import date
import pypdf # Adicionado para processamento de PDF local

# Configuração de logging, para melhor rastreamento de eventos e erros.
logger = logging.getLogger(__name__)

# Importações de módulos internos do projeto
from safety_ai_app.google_drive_integrator import (
    get_google_drive_service_user,
    get_service_account_drive_service,
    get_file_bytes_for_download,
    get_download_metadata,
    upload_file_to_drive,
    list_drive_folders,
    _fetch_drive_files_cached,
    OUR_DRIVE_FOLDER_ID,
    OUR_DRIVE_DONATION_FOLDER_ID,
    DOWNLOAD_FOLDER
)
from safety_ai_app.theme_config import THEME # Importado para acessar emojis e frases
from safety_ai_app.nr_rag_qa import NRQuestionAnswering # Importado para processamento de PDF local para o chatbot

# Constantes para limites de doação
MAX_DAILY_DONATIONS = 5
MAX_DONATION_SIZE_MB = 20
MAX_DONATION_SIZE_BYTES = MAX_DONATION_SIZE_MB * 1024 * 1024

# Diretório temporário para uploads locais
TEMP_DOCS_DIR = "./temp_docs_local"
os.makedirs(TEMP_DOCS_DIR, exist_ok=True)


# MIME types de arquivos suportados pela aplicação.
SUPPORTED_MIME_TYPES = list(set([
    'application/pdf',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document', # DOCX
    'application/msword',                                                    # DOC
    'text/plain',                                                            # TXT
    'application/vnd.google-apps.document',                                  # Google Docs
    'application/vnd.google-apps.presentation',                              # Google Slides
    'application/vnd.google-apps.spreadsheet',                               # Google Sheets
    'application/vnd.google-apps.drawing',                                   # Google Drawing
    'application/vnd.google-apps.script',                                    # Google Script
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',     # XLSX
    'application/vnd.openxmlformats-officedocument.presentationml.presentation', # PPTX
    'image/jpeg', 'image/png', 'image/gif', 'image/bmp', 'image/webp', 'image/tiff', 'image/svg+xml',
    'video/mp4', 'video/x-msvideo', 'video/quicktime', 'video/x-flv', 'video/webm', 'video/mpeg', 'video/3gpp'
]))

# Mapeamento de MIME types para exibição amigável.
MIME_TYPE_DISPLAY = {
    'application/pdf': 'PDF Documento',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document': 'DOCX Documento',
    'application/msword': 'DOC Documento',
    'text/plain': 'TXT Documento',
    'application/vnd.google-apps.document': 'Google Docs (exportará para DOCX)',
    'application/vnd.google-apps.spreadsheet': 'Google Sheets (exportará para XLSX)',
    'application/vnd.google-apps.presentation': 'Google Slides (exportará para PPTX)',
    'application/vnd.google-apps.drawing': 'Google Drawing (exportará para PNG)',
    'application/vnd.google-apps.script': 'Google Script (exportará para JSON)',
    'application/vnd.google-apps.folder': 'Pasta do Google Drive',
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': 'XLSX Planilha',
    'application/vnd.openxmlformats-officedocument.presentationml.presentation': 'PPTX Apresentação',
    'image/jpeg': 'JPEG Imagem', 'image/png': 'PNG Imagem', 'image/gif': 'GIF Imagem',
    'image/bmp': 'BMP Imagem', 'image/webp': 'WebP Imagem', 'image/tiff': 'TIFF Imagem', 'image/svg+xml': 'SVG Imagem',
    'video/mp4': 'MP4 Vídeo', 'video/x-msvideo': 'AVI Vídeo', 'video/quicktime': 'MOV Vídeo',
    'video/x-flv': 'FLV Vídeo', 'video/webm': 'WebM Vídeo', 'video/mpeg': 'MPEG Vídeo', 'video/3gpp': '3GPP Vídeo',
    'default': 'Tipo de Arquivo Desconhecido'
}

# Mapeamento de categorias de filtro para seus respectivos MIME types.
FILE_CATEGORY_MAP = {
    "Todos": "all",
    "Pastas": "folders",
    "PDF": ['application/pdf'],
    "Documentos": [
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'application/msword',
        'text/plain',
        'application/vnd.google-apps.document',
    ],
    "Planilhas": [
        'application/vnd.google-apps.spreadsheet',
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    ],
    "Apresentações": [
        'application/vnd.google-apps.presentation',
        'application/vnd.openxmlformats-officedocument.presentationml.presentation',
    ],
    "Imagens": [
        'image/jpeg', 'image/png', 'image/gif', 'image/bmp', 'image/webp', 'image/tiff', 'image/svg+xml',
        'application/vnd.google-apps.drawing'
    ],
    "Vídeos": [
        'video/mp4', 'video/x-msvideo', 'video/quicktime', 'video/x-flv', 'video/webm', 'video/mpeg', 'video/3gpp'
    ],
    "Scripts": ['application/vnd.google-apps.script']
}


def format_file_size(size_bytes):
    if size_bytes is None:
        return "N/A"
    try:
        size_bytes = int(size_bytes)
        if size_bytes < 0:
            return "N/A"
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024**2:
            return f"{size_bytes / 1024:.2f} KB"
        elif size_bytes < 1024**3:
            return f"{size_bytes / (1024**2):.2f} MB"
        else:
            return f"{size_bytes / (1024**3):.2f} GB"
    except (ValueError, TypeError) as e:
        logger.warning(f"Invalid file size received for formatting: {size_bytes}. Error: {e}")
        return "N/A"


def display_file_list(drive_service_key_for_display, files, drive_type_prefix):
    filter_col1, filter_col2 = st.columns([0.6, 0.4])

    with filter_col1:
        search_query = st.text_input(
            f"Buscar por nome em {drive_type_prefix.replace('_', ' ').title()} Drive:",
            key=f"search_{drive_type_prefix}",
            placeholder="Digite para buscar..."
        )

    with filter_col2:
        selected_file_category = st.selectbox(
            "Filtrar por tipo de arquivo:",
            list(FILE_CATEGORY_MAP.keys()),
            key=f"file_category_filter_{drive_type_prefix}",
            help="Selecione um tipo de arquivo para filtrar a lista de documentos exibidos."
        )
    
    filtered_files_by_search_and_category = []
    
    for file_item in files:
        file_mime_type = file_item['mimeType']
        is_folder = file_mime_type == 'application/vnd.google-apps.folder'

        name_matches = search_query.lower() in file_item['name'].lower()

        category_match = False
        if selected_file_category == "Todos":
            category_match = True
        elif selected_file_category == "Pastas":
            category_match = is_folder
        else:
            if file_mime_type in FILE_CATEGORY_MAP[selected_file_category]:
                category_match = True

        if name_matches and category_match:
            # Inclui arquivos que são pastas, ou que estão na lista de suportados
            # ou que são de apps do Google (para serem exportados)
            if is_folder or file_mime_type in SUPPORTED_MIME_TYPES or file_mime_type.startswith('application/vnd.google-apps'):
                filtered_files_by_search_and_category.append(file_item)

    filtered_files = filtered_files_by_search_and_category

    if not filtered_files:
        st.info('Nenhum arquivo encontrado com os filtros aplicados.')
        return

    st.markdown(f"**Arquivos encontrados ({len(filtered_files)}):**")

    current_drive_service = st.session_state.get(drive_service_key_for_display)

    if current_drive_service is None:
        st.warning(f"Não foi possível acessar o serviço de Drive para baixar arquivos. Verifique a autenticação ou configuração.")
    
    for file_item in filtered_files:
        file_display_name = file_item['name']
        file_id = file_item['id']
        file_mime_type = file_item['mimeType']
        file_size = file_item.get('size')

        is_folder = file_mime_type == 'application/vnd.google-apps.folder'

        col1, col2 = st.columns([0.8, 0.2])

        with col1:
            if is_folder:
                st.markdown(f"**{THEME['emojis']['folder_docs']} Pasta: {file_display_name}**")
            else:
                st.markdown(f"**{THEME['emojis']['file_doc']} {file_display_name}**")
                st.caption(f"{MIME_TYPE_DISPLAY.get(file_mime_type, MIME_TYPE_DISPLAY['default'])} | Tamanho: {format_file_size(file_size)}")

        with col2:
            if not is_folder:
                download_filename, download_mime = get_download_metadata(file_display_name, file_mime_type)
                
                download_state_key = f"dl_state_{drive_type_prefix}_{file_id}" 
                download_bytes_key = f"dl_bytes_{drive_type_prefix}_{file_id}" 

                current_dl_state = st.session_state.get(download_state_key, 'initial')

                if current_drive_service is None:
                    st.caption("Serviço indisponível")
                elif download_filename is None:
                    st.caption("Não baixável")
                else:
                    if current_dl_state == 'initial':
                        if st.button(f"{THEME['emojis']['download_arrow']} Baixar", key=f"dl_trigger_{drive_type_prefix}_{file_id}", help="Clique para iniciar o download do arquivo."):
                            st.session_state[download_state_key] = 'fetching'
                            st.session_state[download_bytes_key] = None
                            st.rerun()

                    elif current_dl_state == 'fetching':
                        st.button(f"{THEME['emojis']['loading_hourglass']} Baixando...", disabled=True, key=f"dl_trigger_{drive_type_prefix}_{file_id}") 
                        with st.spinner(f"Baixando '{file_display_name}' do Google Drive..."):
                            try:
                                file_bytes = get_file_bytes_for_download(current_drive_service, file_id, download_mime)
                                if file_bytes:
                                    st.session_state[download_bytes_key] = io.BytesIO(file_bytes)
                                    st.session_state[download_state_key] = 'ready'
                                else:
                                    st.session_state[download_state_key] = 'error'
                                    st.toast(f"{THEME['emojis']['error_x']} Conteúdo do arquivo '{file_display_name}' vazio ou não disponível.", icon=THEME["emojis"]["error_x"])
                                    logger.warning(f"Empty or unavailable file content: {file_display_name} (ID: {file_id})")
                            except Exception as e:
                                st.session_state[download_state_key] = 'error'
                                st.toast(f"{THEME['emojis']['error_x']} Erro ao buscar '{file_display_name}': {e}. Tente novamente.", icon=THEME["emojis"]["error_x"])
                                logger.error(f"Error fetching bytes for {file_display_name} (ID: {file_id}): {type(e).__name__}: {e}")
                            st.rerun()

                    elif current_dl_state == 'ready':
                        if st.session_state.get(download_bytes_key):
                            st.download_button(
                                label=f"{THEME['emojis']['save_disk']} Salvar no Dispositivo",
                                data=st.session_state[download_bytes_key],
                                file_name=download_filename,
                                mime=download_mime,
                                key=f"dl_final_{drive_type_prefix}_{file_id}",
                                help="Clique para salvar o arquivo no seu computador.",
                                on_click=lambda: st.session_state.update({
                                    download_state_key: 'completed',
                                    download_bytes_key: None
                                })
                            )
                        else:
                            st.session_state[download_state_key] = 'error'
                            st.toast(f"{THEME['emojis']['error_x']} Erro interno: Dados do arquivo não encontrados para download. Tente novamente.", icon=THEME["emojis"]["error_x"])
                            logger.error(f"Bytes data for {file_display_name} (ID: {file_id}) not found in 'ready' state.")
                            st.rerun()

                    elif current_dl_state == 'completed':
                        st.button(f"{THEME['emojis']['success_check']} Concluído", disabled=True, key=f"dl_status_{drive_type_prefix}_{file_id}")
                        if st.button("Baixar Novamente", key=f"dl_retry_completed_{drive_type_prefix}_{file_id}"):
                            st.session_state[download_state_key] = 'initial'
                            st.rerun()

                    elif current_dl_state == 'error':
                        st.button(f"{THEME['emojis']['error_x']} Falha", disabled=True, key=f"dl_status_{drive_type_prefix}_{file_id}")
                        if st.button("Tentar Novamente", key=f"dl_retry_{drive_type_prefix}_{file_id}"):
                            st.session_state[download_state_key] = 'initial'
                            st.rerun()
        st.markdown("---")


def library_page():
    # Botão de voltar para a Página Inicial, posicionado no topo
    if st.button(f"{THEME['emojis']['back_arrow']} {THEME['phrases']['back_to_home']}", key="back_to_home_library"): 
        st.session_state.page = "home"
        st.rerun()

    # Título neon usando a classe global e emojis centralizados
    st.markdown(f'<h1 class="neon-title">{THEME["emojis"]["library_books"]} {THEME["phrases"]["document_library"]}</h1>', unsafe_allow_html=True)
    st.write("Aqui você pode gerenciar os documentos que servem como base de conhecimento para o SafetyAI.")
    st.markdown("---") # Separador após a descrição inicial

    # Inicializa NR_RAG_QA uma vez e armazena em session_state
    if 'rag_qa' not in st.session_state:
        try:
            st.session_state.rag_qa = NRQuestionAnswering()
            logger.info("NR_RAG_QA inicializado com sucesso na biblioteca.")
        except Exception as e:
            st.error(f"Erro ao inicializar o sistema de QA: {e}. Verifique sua GOOGLE_API_KEY e a existência do ChromaDB.")
            logger.error(f"Erro ao inicializar NR_RAG_QA: {e}")
            # Não retorna aqui para permitir que outras abas renderizem, mesmo que o QA não esteja pronto.

    if "user_drive_service" not in st.session_state:
        st.session_state["user_drive_service"] = None
    if "app_drive_service" not in st.session_state:
        st.session_state["app_drive_service"] = None
    
    if 'daily_donations_count' not in st.session_state:
        st.session_state['daily_donations_count'] = 0
    if 'last_donation_date' not in st.session_state:
        st.session_state['last_donation_date'] = date.min 

    today = date.today()
    if st.session_state['last_donation_date'] != today:
        st.session_state['daily_donations_count'] = 0
        st.session_state['last_donation_date'] = today

    user_service_status_message = ""
    try:
        if st.session_state["user_drive_service"] is None:
            temp_user_service = get_google_drive_service_user()
            if temp_user_service:
                st.session_state["user_drive_service"] = temp_user_service
        if st.session_state["user_drive_service"] is None:
            user_service_status_message = "⚠️ Serviço do Google Drive do usuário não está disponível. Por favor, autentique-se novamente na página inicial para acessar seu Drive pessoal."
    except Exception as e:
        logger.error(f"Unexpected error initializing user_drive_service: {type(e).__name__}: {e}")
        user_service_status_message = f"❌ Erro inesperado ao inicializar o serviço do Google Drive do usuário: {e}. Verifique as credenciais e permissões concedidas na página inicial."

    app_service_status_message = ""
    try:
        if st.session_state["app_drive_service"] is None:
            temp_app_service = get_service_account_drive_service()
            if temp_app_service:
                st.session_state["app_drive_service"] = temp_app_service
        if st.session_state["app_drive_service"] is None:
            app_service_status_message = "⚠️ Serviço da conta de aplicativo não está disponível para listar a Biblioteca. Verifique se o arquivo 'service_account_key.json' está configurado corretamente e se a conta de serviço tem as permissões necessárias."
    except Exception as e:
        logger.error(f"Unexpected error initializing app_drive_service: {type(e).__name__}: {e}")
        app_service_status_message = f"❌ Erro inesperado ao inicializar o serviço do Google Drive da conta de serviço: {e}. Verifique se o arquivo 'service_account_key.json' está presente, formatado corretamente e se a conta de serviço foi adicionada como editora na pasta do Drive da biblioteca."

    if user_service_status_message:
        st.warning(user_service_status_message)
    if app_service_status_message:
        st.warning(app_service_status_message)

    tab1, tab2, tab3 = st.tabs(["Biblioteca Central", "Doação de Conteúdo", "Processar Local para Chatbot"])

    with tab1:
        st.header("Biblioteca Central")
        st.info(
            "Esta é a biblioteca de documentos principal do SafetyAI. "
            "Utilize-a para baixar arquivos e aprimorar seu conhecimento. Tenha um ótimo estudo!"
        )

        app_files = []
        if st.session_state["app_drive_service"]:
            app_files = _fetch_drive_files_cached(st.session_state["app_drive_service"], OUR_DRIVE_FOLDER_ID)
            if not app_files and not app_service_status_message:
                st.error(
                    f"{THEME['emojis']['error_x']} Não foi possível listar os arquivos da Biblioteca. "
                    f"Verifique se a pasta com ID '{OUR_DRIVE_FOLDER_ID}' existe, "
                    f"se a conta de serviço tem permissão de leitura nela e "
                    f"se as credenciais da conta de serviço estão corretas."
                )
            elif app_files:
                display_file_list("app_drive_service", app_files, "app")
        else:
            st.info("O serviço da conta de aplicativo não está configurado ou autenticado. Não é possível exibir a biblioteca central.")

    with tab2:
        st.header("Doação de Conteúdo")
        st.info(
            "Aqui você pode doar conteúdo valioso para enriquecer a biblioteca do SafetyAI. "
            "Seu apoio ajuda a construir uma base de conhecimento mais robusta para todos! "
            f"Você pode enviar até {MAX_DAILY_DONATIONS} conteúdos por dia, com limite de {MAX_DONATION_SIZE_MB}MB por arquivo. "
            "O conteúdo enviado será analisado pela nossa equipe antes de ser incluído na biblioteca principal."
        )

        if st.session_state["user_drive_service"]:
            can_upload_more = st.session_state['daily_donations_count'] < MAX_DAILY_DONATIONS
            uploads_left = MAX_DAILY_DONATIONS - st.session_state['daily_donations_count']

            if not can_upload_more:
                st.warning(f"Você atingiu o limite de {MAX_DAILY_DONATIONS} doações por dia. Volte amanhã para doar mais!")
            
            uploaded_files = st.file_uploader(
                f"Selecione arquivos para doação (PDF, DOCX, TXT): (Restantes hoje: {uploads_left})",
                type=['pdf', 'docx', 'txt'],
                accept_multiple_files=can_upload_more,
                key="donation_file_uploader",
                help=f"Selecione até {MAX_DAILY_DONATIONS} arquivos por dia, com no máximo {MAX_DONATION_SIZE_MB}MB cada."
            )
            
            if uploaded_files:
                st.subheader("Conteúdos para doação:")
                for i, up_file in enumerate(uploaded_files):
                    col1, col2 = st.columns([0.7, 0.3])
                    
                    file_too_large = up_file.size > MAX_DONATION_SIZE_BYTES
                    
                    with col1:
                        st.write(f"- **{up_file.name}** (Tamanho: {format_file_size(up_file.size)})")
                        if file_too_large:
                            st.error(f"{THEME['emojis']['error_x']} Arquivo '{up_file.name}' excede o limite de {MAX_DONATION_SIZE_MB}MB.")

                    with col2:
                        if can_upload_more and not file_too_large:
                            if st.button(f"{THEME['emojis']['upload_arrow']} Doar Conteúdo", key=f"donate_file_{up_file.name}_{i}"):
                                try:
                                    upload_file_to_drive(st.session_state["user_drive_service"], up_file, parent_folder_id=OUR_DRIVE_DONATION_FOLDER_ID)
                                    st.session_state['daily_donations_count'] += 1
                                    st.toast(f"{THEME['emojis']['success_check']} Conteúdo '{up_file.name}' doado com sucesso! Obrigado pela sua contribuição.", icon=THEME["emojis"]["donation_hands"])
                                    st.rerun() 
                                except Exception as e:
                                    st.error(f"{THEME['emojis']['error_x']} Erro ao doar o arquivo '{up_file.name}': {e}. Verifique suas permissões na pasta de destino.")
                                    logger.error(f"Erro ao doar o arquivo '{up_file.name}': {e}")
                        elif file_too_large:
                             st.button(f"{THEME['emojis']['upload_arrow']} Doar Conteúdo", key=f"donate_file_{up_file.name}_{i}", disabled=True)
                        else:
                            st.button(f"{THEME['emojis']['upload_arrow']} Doar Conteúdo", key=f"donate_file_{up_file.name}_{i}", disabled=True, help="Limite diário de doações atingido.")
        else:
            st.info("Faça login com seu Google Drive para começar a doar conteúdos!")

    with tab3:
        st.header(f"{THEME['emojis']['upload_folder']} Processar Documentos Locais para o Chatbot")
        st.info(
            "Aqui você pode fazer upload de arquivos PDF do seu computador para que o chatbot os utilize como "
            "base de conhecimento. Estes documentos serão processados e armazenados localmente no ChromaDB para melhorar as respostas do SafetyAI. "
            "**Importante:** Estes arquivos não são enviados para o Google Drive de doação."
        )

        if 'rag_qa' not in st.session_state:
            st.error("O sistema de QA não está inicializado. Por favor, verifique sua configuração de GOOGLE_API_KEY para habilitar esta funcionalidade.")
        else:
            local_uploaded_file = st.file_uploader(
                "Selecione um arquivo PDF para processar para o chatbot:",
                type=["pdf"],
                key="local_pdf_uploader",
                help="Faça upload de um PDF para que o chatbot possa consultá-lo em suas respostas."
            )

            if local_uploaded_file is not None:
                file_path = os.path.join(TEMP_DOCS_DIR, local_uploaded_file.name)
                
                # Salva o arquivo uploaded temporariamente
                with open(file_path, "wb") as f:
                    f.write(local_uploaded_file.getbuffer())
                
                document_id = local_uploaded_file.name # Usando o nome do arquivo como ID do documento
                source_url = None 

                # Lógica para atribuir source_url com base no nome do arquivo ou outros critérios
                if "NR-35" in local_uploaded_file.name:
                    source_url = "https://www.gov.br/trabalho-e-emprego/pt-br/acesso-a-informacao/participacao-social/conselhos-e-orgaos-colegiados/comissao-tripartite-partitaria-permanente/nrs-atualizadas/NR-35%20(1).pdf"
                elif "NR-1" in local_uploaded_file.name:
                    source_url = "https://www.gov.br/trabalho-e-emprego/pt-br/acesso-a-informacao/participacao-social/conselhos-e-orgaos-colegiados/comissao-tripartite-partitaria-permanente/nrs-atualizadas/NR-1%20(1).pdf"
                else:
                    source_url = f"local_file://{local_uploaded_file.name}"
                    st.warning(f"Nenhuma URL de origem específica encontrada para '{local_uploaded_file.name}'. Usando um placeholder para o chatbot.")

                st.info(f"Processando documento: {local_uploaded_file.name} para o chatbot...")
                with st.spinner(f"Extraindo texto e adicionando '{local_uploaded_file.name}' à base de conhecimento..."):
                    try:
                        # Extrair texto do PDF
                        reader = pypdf.PdfReader(file_path)
                        full_text = ""
                        for page in reader.pages:
                            full_text += page.extract_text() or ""

                        # Chunk e adicionar ao ChromaDB com metadados
                        # ATENÇÃO: Verifique se 'st.session_state.rag_qa.text_splitter' está definido
                        # Se não estiver, você precisará adicionar um inicializador para ele em NRQuestionAnswering
                        text_splitter = st.session_state.rag_qa.text_splitter
                        texts = text_splitter.split_text(full_text)
                        
                        metadatas = []
                        ids = []
                        for i, text in enumerate(texts):
                            chunk_metadata = {"document_id": document_id, "chunk_id": f"{document_id}-{i}"}
                            if source_url:
                                chunk_metadata["source_url"] = source_url
                            if "NR-" in local_uploaded_file.name:
                                try:
                                    # Extrai o número da NR do nome do arquivo (ex: "NR-35 (1).pdf" -> "35")
                                    nr_number_str = local_uploaded_file.name.split("NR-")[1].split(".")[0].split(" ")[0].split("(")[0]
                                    chunk_metadata["nr_number"] = nr_number_str
                                except Exception:
                                    pass # Ignora se não conseguir extrair o número da NR
                            metadatas.append(chunk_metadata)
                            ids.append(f"{document_id}-{i}")

                        st.session_state.rag_qa.collection.add(
                            documents=texts,
                            metadatas=metadatas,
                            ids=ids
                        )
                        st.success(f"Documento '{local_uploaded_file.name}' processado e chunks adicionados à base de conhecimento do chatbot! Total de chunks: {len(texts)}")
                        logger.info(f"Documento '{local_uploaded_file.name}' chunks added to ChromaDB. Source URL: {source_url if source_url else 'N/A'}")
                    except Exception as e:
                        st.error(f"Erro ao processar o PDF para o chatbot: {e}")
                        logger.error(f"Error processing local PDF '{local_uploaded_file.name}' for chatbot: {e}")
                    finally:
                        if os.path.exists(file_path):
                            os.remove(file_path)
                            logger.info(f"Temporary file '{file_path}' removed.")

            st.markdown("---")
            st.subheader(f"{THEME['emojis']['document_icon']} Documentos Processados na Base de Conhecimento (Chatbot)")
            
            # Listar documentos processados no ChromaDB
            try:
                all_metadatas = st.session_state.rag_qa.collection.get(
                    include=['metadatas']
                )['metadatas']
                
                unique_documents = {}
                for md in all_metadatas:
                    doc_id = md.get('document_id', 'Desconhecido')
                    if doc_id not in unique_documents:
                        unique_documents[doc_id] = {
                            'source_url': md.get('source_url', 'N/A'),
                            'nr_number': md.get('nr_number', 'N/A'),
                            'chunk_count': 0
                        }
                    unique_documents[doc_id]['chunk_count'] += 1

                if unique_documents:
                    st.write("Os seguintes documentos foram processados para o chatbot:")
                    for doc_id, info in unique_documents.items():
                        display_name = doc_id
                        if info['nr_number'] != 'N/A':
                            display_name = f"NR-{info['nr_number']} ({doc_id})"
                        
                        st.markdown(f"- **{display_name}** (Chunks: {info['chunk_count']})")
                        if info['source_url'] and info['source_url'] != 'N/A' and not info['source_url'].startswith('local_file://'):
                            st.markdown(f"  - Fonte: [{info['source_url']}]({info['source_url']})")
                        elif info['source_url'].startswith('local_file://'):
                             st.markdown(f"  - Fonte: Arquivo local ({info['source_url'].replace('local_file://', '')})")
                else:
                    st.info("Nenhum documento processado para o chatbot ainda. Faça o upload de um PDF para começar!")
            except Exception as e:
                st.error(f"Erro ao carregar documentos processados para o chatbot: {e}")
                logger.error(f"Error loading processed documents for chatbot: {e}")


    st.markdown("---") # Separador antes do rodapé padrão
    st.markdown(f"""
    <br>
    <div class="footer">
        {THEME["phrases"]["footer_text"]}
    </div>
    """, unsafe_allow_html=True)