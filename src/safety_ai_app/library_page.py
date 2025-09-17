import streamlit as st
import os
from pathlib import Path
import io
import logging
from datetime import date

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

from safety_ai_app.google_drive_integrator import (
    get_google_drive_service_user,
    get_service_account_drive_service,
    get_file_bytes_for_download,
    get_download_metadata,
    upload_file_to_drive,
    list_drive_folders,
    _fetch_drive_files_cached,
    OUR_DRIVE_FOLDER_ID,
    OUR_DRIVE_DONATION_FOLDER_ID, # Nova constante para a pasta de doações
    DOWNLOAD_FOLDER
)
from safety_ai_app.theme_config import THEME

# Constantes para limites de doação
MAX_DAILY_DONATIONS = 5
MAX_DONATION_SIZE_MB = 20
MAX_DONATION_SIZE_BYTES = MAX_DONATION_SIZE_MB * 1024 * 1024

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
        logging.warning(f"Invalid file size received for formatting: {size_bytes}. Error: {e}")
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
                st.markdown(f"**�� Pasta: {file_display_name}**")
            else:
                st.markdown(f"**📄 {file_display_name}**")
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
                        if st.button("⬇️ Baixar", key=f"dl_trigger_{drive_type_prefix}_{file_id}", help="Clique para iniciar o download do arquivo."):
                            st.session_state[download_state_key] = 'fetching'
                            st.session_state[download_bytes_key] = None
                            st.rerun()

                    elif current_dl_state == 'fetching':
                        st.button("⏳ Baixando...", disabled=True, key=f"dl_trigger_{drive_type_prefix}_{file_id}") 
                        with st.spinner(f"Baixando '{file_display_name}' do Google Drive..."):
                            try:
                                file_bytes = get_file_bytes_for_download(current_drive_service, file_id, download_mime)
                                if file_bytes:
                                    st.session_state[download_bytes_key] = io.BytesIO(file_bytes)
                                    st.session_state[download_state_key] = 'ready'
                                else:
                                    st.session_state[download_state_key] = 'error'
                                    st.error(f"❌ Conteúdo do arquivo '{file_display_name}' vazio ou não disponível.")
                                    logging.warning(f"Empty or unavailable file content: {file_display_name} (ID: {file_id})")
                            except Exception as e:
                                st.session_state[download_state_key] = 'error'
                                st.error(f"❌ Erro ao buscar '{file_display_name}': {e}. Tente novamente.")
                                logging.error(f"Error fetching bytes for {file_display_name} (ID: {file_id}): {type(e).__name__}: {e}")
                            st.rerun()

                    elif current_dl_state == 'ready':
                        if st.session_state.get(download_bytes_key):
                            st.download_button(
                                label="💾 Salvar no Dispositivo",
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
                            st.error("Erro interno: Dados do arquivo não encontrados para download. Tente novamente.")
                            logging.error(f"Bytes data for {file_display_name} (ID: {file_id}) not found in 'ready' state.")
                            st.rerun()

                    elif current_dl_state == 'completed':
                        st.button("✅ Concluído", disabled=True, key=f"dl_status_{drive_type_prefix}_{file_id}")
                        if st.button("Baixar Novamente", key=f"dl_retry_completed_{drive_type_prefix}_{file_id}"):
                            st.session_state[download_state_key] = 'initial'
                            st.rerun()

                    elif current_dl_state == 'error':
                        st.button("❌ Falha", disabled=True, key=f"dl_status_{drive_type_prefix}_{file_id}")
                        if st.button("Tentar Novamente", key=f"dl_retry_{drive_type_prefix}_{file_id}"):
                            st.session_state[download_state_key] = 'initial'
                            st.rerun()
        st.markdown("---")


def library_page():
    st.title("📚 Biblioteca de Documentos")
    st.write("Aqui você pode gerenciar os documentos que servem como base de conhecimento para o SafetyAI.")
    st.markdown("---")

    if "user_drive_service" not in st.session_state:
        st.session_state["user_drive_service"] = None
    if "app_drive_service" not in st.session_state:
        st.session_state["app_drive_service"] = None
    
    # Inicializa o contador de doações e a data da última doação na session_state.
    if 'daily_donations_count' not in st.session_state:
        st.session_state['daily_donations_count'] = 0
    if 'last_donation_date' not in st.session_state:
        st.session_state['last_donation_date'] = None

    # Reseta o contador de doações se o dia mudou.
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
        logging.error(f"Unexpected error initializing user_drive_service: {type(e).__name__}: {e}")
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
        logging.error(f"Unexpected error initializing app_drive_service: {type(e).__name__}: {e}")
        app_service_status_message = f"❌ Erro inesperado ao inicializar o serviço do Google Drive da conta de serviço: {e}. Verifique se o arquivo 'service_account_key.json' está presente, formatado corretamente e se a conta de serviço foi adicionada como editora na pasta do Drive da biblioteca."

    if user_service_status_message:
        st.warning(user_service_status_message)
    if app_service_status_message:
        st.warning(app_service_status_message)

    # Abas atualizadas: "Biblioteca" e "Doação de Conteúdo".
    tab1, tab2 = st.tabs(["Biblioteca", "Doação de Conteúdo"])

    with tab1:
        st.header("Biblioteca Central")
        # Mensagem simplificada para a Biblioteca Central.
        st.info(
            "Esta é a biblioteca de documentos principal do SafetyAI. "
            "Utilize-a para baixar arquivos e aprimorar seu conhecimento. Tenha um ótimo estudo!"
        )

        app_files = []
        if st.session_state["app_drive_service"]:
            app_files = _fetch_drive_files_cached(st.session_state["app_drive_service"], OUR_DRIVE_FOLDER_ID)
            if not app_files and not app_service_status_message:
                st.error(
                    f"❌ Não foi possível listar os arquivos da Biblioteca. "
                    f"Verifique se a pasta com ID '{OUR_DRIVE_FOLDER_ID}' existe, "
                    f"se a conta de serviço tem permissão de leitura/escrita nela e "
                    f"se as credenciais da conta de serviço estão corretas."
                )
            elif app_files:
                display_file_list("app_drive_service", app_files, "app")
        else:
            st.info("O serviço da conta de aplicativo não está configurado ou autenticado. Não é possível exibir a biblioteca central.")

    # A antiga tab2 "Seu Drive Pessoal" foi removida daqui.

    with tab2: # Esta é a antiga tab3 "Upload Local".
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
                accept_multiple_files=can_upload_more, # Desabilita upload se o limite diário for atingido.
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
                            st.error(f"❌ Arquivo '{up_file.name}' excede o limite de {MAX_DONATION_SIZE_MB}MB.")

                    with col2:
                        if can_upload_more and not file_too_large:
                            if st.button("⬆️ Doar Conteúdo", key=f"donate_file_{up_file.name}_{i}"):
                                try:
                                    # O arquivo é enviado para a pasta de doações.
                                    upload_file_to_drive(st.session_state["user_drive_service"], up_file, parent_folder_id=OUR_DRIVE_DONATION_FOLDER_ID)
                                    st.session_state['daily_donations_count'] += 1
                                    st.toast(f"✅ Conteúdo '{up_file.name}' doado com sucesso! Obrigado pela sua contribuição.", icon='🙏')
                                    # Força um rerun para atualizar o contador de doações e o estado dos botões.
                                    st.rerun() 
                                except Exception as e:
                                    st.error(f"❌ Erro ao doar o arquivo '{up_file.name}': {e}. Verifique suas permissões na pasta de destino.")
                        elif file_too_large:
                             st.button("⬆️ Doar Conteúdo", key=f"donate_file_{up_file.name}_{i}", disabled=True)
                        else:
                            st.button("⬆️ Doar Conteúdo", key=f"donate_file_{up_file.name}_{i}", disabled=True, help="Limite diário de doações atingido.")
        else:
            st.info("Faça login com seu Google Drive para começar a doar conteúdos!")

    st.markdown("---")
    if st.button("Voltar para a Página Inicial", key="back_to_home_library"):
        st.session_state.page = "home"
        st.rerun()

st.markdown("""
---
Desenvolvido com IA 🤖 por Leo - Focado em um futuro mais seguro.
""")