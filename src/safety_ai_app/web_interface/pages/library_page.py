import streamlit as st
import logging
import io
import os
from datetime import date, datetime
import time
import hashlib
import streamlit.components.v1 as components

from safety_ai_app.theme_config import THEME, _get_material_icon_html_for_button_css, _get_material_icon_html
from safety_ai_app.google_drive_integrator import (
    list_drive_folders,
    get_processable_drive_files_in_folder,
    get_file_bytes_for_download,
    upload_file_to_drive,
    get_app_central_library_info,
    synchronize_app_central_library_to_chroma,
    synchronize_user_drive_folder_to_chroma,
    get_download_metadata
)
from safety_ai_app.nr_rag_qa import NRQuestionAnswering, PROCESSABLE_MIME_TYPES

logger = logging.getLogger(__name__)

MAX_DAILY_DONATIONS = 5
MAX_DONATION_SIZE_MB = 20
MAX_DONATION_SIZE_BYTES = MAX_DONATION_SIZE_MB * 1024 * 1024

# CONFIGURAÇÃO DO RECAPTCHA (adicione no .env)
RECAPTCHA_SITE_KEY = os.getenv("RECAPTCHA_SITE_KEY", "")
RECAPTCHA_SECRET_KEY = os.getenv("RECAPTCHA_SECRET_KEY", "")

MIME_TYPE_DISPLAY = {
    'application/pdf': 'PDF',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document': 'DOCX',
    'application/msword': 'DOC',
    'text/plain': 'TXT',
    'application/vnd.google-apps.document': 'Google Docs',
    'application/vnd.google-apps.spreadsheet': 'Google Sheets',
    'application/vnd.google-apps.presentation': 'Google Slides',
    'application/vnd.google-apps.drawing': 'Google Drawing',
    'application/vnd.google-apps.script': 'Google Script',
    'application/vnd.google-apps.folder': 'Pasta',
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': 'XLSX',
    'application/vnd.openxmlformats-officedocument.spreadsheetml.template': 'XLSX Modelo',
    'application/vnd.ms-excel': 'XLS',
    'application/vnd.openxmlformats-officedocument.presentationml.presentation': 'PPTX',
    'application/vnd.ms-powerpoint': 'PPT',
    'image/jpeg': 'JPEG', 'image/png': 'PNG', 'image/gif': 'GIF',
    'image/bmp': 'BMP', 'image/webp': 'WebP', 'image/tiff': 'TIFF', 'image/svg+xml': 'SVG',
    'video/mp4': 'MP4', 'video/x-msvideo': 'AVI', 'video/quicktime': 'MOV',
    'video/x-flv': 'FLV', 'video/webm': 'WebM', 'video/mpeg': 'MPEG', 'video/3gpp': '3GPP',
    'default': 'Desconhecido'
}

FILE_CATEGORY_MAP = {
    "Todos": "all",
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
        'application/vnd.ms-excel',
    ],
    "Apresentações": [
        'application/vnd.google-apps.presentation',
        'application/vnd.openxmlformats-officedocument.presentationml.presentation',
        'application/vnd.ms-powerpoint',
    ]
}

def _render_info_like_message(message_type: str, message: str, icon_name: str = None) -> None:
    """
    Renderiza uma mensagem com estilo Streamlit usando ícones Material Symbols.
    
    Args:
        message_type: Tipo da mensagem (info, warning, success, error)
        message: Texto da mensagem
        icon_name: Nome do ícone Material Symbol (opcional)
        
    Raises:
        None: Função não levanta exceções
    """
    icon_html = _get_material_icon_html(icon_name) if icon_name else ""
    st.markdown(f"<div class='st-{message_type}-like'>{icon_html} {message}</div>", unsafe_allow_html=True)

def format_file_size(size_bytes: int) -> str:
    """
    Formata o tamanho do arquivo em uma string legível.
    
    Args:
        size_bytes: Tamanho em bytes
        
    Returns:
        str: Tamanho formatado (ex: "1.5 MB")
        
    Raises:
        None: Retorna "N/A" em caso de erro
    """
    if size_bytes is None:
        return "N/A"
    try:
        size_bytes = int(size_bytes)
        if size_bytes < 0:
            return "N/A"
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024**2:
            return f"{size_bytes / 1024:.1f} KB"
        elif size_bytes < 1024**3:
            return f"{size_bytes / (1024**2):.1f} MB"
        else:
            return f"{size_bytes / (1024**3):.1f} GB"
    except (ValueError, TypeError) as e:
        logger.warning(f"Invalid file size received for formatting: {size_bytes}. Error: {e}")
        return "N/A"

def get_file_hash(file_content: bytes) -> str:
    """
    Calcula o hash MD5 do conteúdo do arquivo para verificar duplicatas.
    
    Args:
        file_content: Conteúdo do arquivo em bytes
        
    Returns:
        str: Hash MD5 do arquivo
        
    Raises:
        None: Retorna string vazia em caso de erro
    """
    try:
        return hashlib.md5(file_content).hexdigest()
    except Exception as e:
        logger.error(f"Erro ao calcular hash do arquivo: {e}")
        return ""

def check_file_exists_in_drive(drive_service, folder_id: str, filename: str, file_hash: str = None) -> bool:
    """
    Verifica se um arquivo já existe na pasta do Google Drive.
    
    Args:
        drive_service: Serviço do Google Drive
        folder_id: ID da pasta para verificar
        filename: Nome do arquivo
        file_hash: Hash do arquivo (opcional)
        
    Returns:
        bool: True se o arquivo já existe, False caso contrário
        
    Raises:
        None: Retorna False em caso de erro
    """
    try:
        # Buscar arquivos com o mesmo nome na pasta
        query = f"'{folder_id}' in parents and name='{filename}' and trashed=false"
        results = drive_service.files().list(q=query, fields="files(id,name,size)").execute()
        files = results.get('files', [])
        
        if files:
            logger.info(f"Arquivo '{filename}' já existe na pasta {folder_id}")
            return True
        
        return False
    except Exception as e:
        logger.error(f"Erro ao verificar duplicata no Drive: {e}")
        return False

def verify_recaptcha(recaptcha_response: str) -> bool:
    """
    Verifica o reCAPTCHA com o Google.
    
    Args:
        recaptcha_response: Resposta do reCAPTCHA
        
    Returns:
        bool: True se válido, False caso contrário
        
    Raises:
        None: Retorna False em caso de erro
    """
    if not RECAPTCHA_SECRET_KEY or not recaptcha_response:
        return False
    
    try:
        import requests
        
        data = {
            'secret': RECAPTCHA_SECRET_KEY,
            'response': recaptcha_response
        }
        
        response = requests.post('https://www.google.com/recaptcha/api/siteverify', data=data)
        result = response.json()
        
        return result.get('success', False)
    except Exception as e:
        logger.error(f"Erro na verificação do reCAPTCHA: {e}")
        return False

def render_recaptcha() -> str:
    """
    Renderiza o widget reCAPTCHA e retorna a resposta.
    
    Returns:
        str: Resposta do reCAPTCHA ou string vazia
        
    Raises:
        None: Retorna string vazia em caso de erro
    """
    if not RECAPTCHA_SITE_KEY:
        st.warning("reCAPTCHA não configurado. Configure RECAPTCHA_SITE_KEY no arquivo .env")
        return ""
    
    recaptcha_html = f"""
    <div id="recaptcha-container">
        <div id="recaptcha-widget"></div>
        <input type="hidden" id="recaptcha-response" name="recaptcha-response" />
    </div>
    
    <script src="https://www.google.com/recaptcha/api.js?onload=onRecaptchaLoad&render=explicit" async defer></script>
    <script>
        var recaptchaWidget;
        
        function onRecaptchaLoad() {{
            recaptchaWidget = grecaptcha.render('recaptcha-widget', {{
                'sitekey': '{RECAPTCHA_SITE_KEY}',
                'callback': function(response) {{
                    document.getElementById('recaptcha-response').value = response;
                    window.parent.postMessage({{
                        type: 'streamlit:setComponentValue',
                        value: {{
                            key: 'recaptcha_response',
                            value: response
                        }}
                    }}, '*');
                }},
                'expired-callback': function() {{
                    document.getElementById('recaptcha-response').value = '';
                    window.parent.postMessage({{
                        type: 'streamlit:setComponentValue',
                        value: {{
                            key: 'recaptcha_response',
                            value: ''
                        }}
                    }}, '*');
                }}
            }});
        }}
        
        function resetRecaptcha() {{
            if (recaptchaWidget !== undefined) {{
                grecaptcha.reset(recaptchaWidget);
                document.getElementById('recaptcha-response').value = '';
            }}
        }}
    </script>
    
    <style>
        #recaptcha-container {{
            display: flex;
            justify-content: center;
            margin: 20px 0;
        }}
    </style>
    """
    
    # Renderizar o reCAPTCHA
    components.html(recaptcha_html, height=200)
    
    # Retornar a resposta se disponível
    return st.session_state.get('recaptcha_response', '')

def initialize_donation_session_state() -> None:
    """
    Inicializa o estado de sessão para doações.
    
    Raises:
        None: Função não levanta exceções
    """
    today_date = str(date.today())
    
    # Inicializar histórico de doações se não existir
    if 'donation_history' not in st.session_state:
        st.session_state['donation_history'] = []
    
    # Inicializar contador se não existir
    if 'daily_donations_count' not in st.session_state:
        st.session_state['daily_donations_count'] = 0
        
    # Inicializar data se não existir
    if 'last_donation_date' not in st.session_state:
        st.session_state['last_donation_date'] = today_date
    
    # Resetar contador diário se mudou o dia
    if st.session_state['last_donation_date'] != today_date:
        st.session_state['daily_donations_count'] = 0
        st.session_state['last_donation_date'] = today_date
        # Limpar histórico do dia anterior
        st.session_state['donation_history'] = []
        logger.info(f"Novo dia detectado. Resetando contador de doações para {today_date}")

def safe_download_file_on_demand(drive_service, file_id: str, file_mime_type: str, export_mime_type: str) -> bytes:
    """
    Realiza download seguro SOB DEMANDA com múltiplas tentativas.
    
    Args:
        drive_service: Serviço do Google Drive
        file_id: ID do arquivo
        file_mime_type: Tipo MIME original
        export_mime_type: Tipo MIME para exportação
        
    Returns:
        bytes: Conteúdo do arquivo ou None em caso de erro
        
    Raises:
        Exception: Para erros irrecuperáveis
    """
    max_retries = 3
    
    for attempt in range(max_retries):
        try:
            logger.info(f"Tentativa {attempt + 1} de download para arquivo {file_id}")
            
            # Método 1: Usar a função original
            if attempt == 0:
                return get_file_bytes_for_download(drive_service, file_id, file_mime_type, export_mime_type)
            
            # Método 2: Download direto sem chunking
            elif attempt == 1:
                logger.info(f"Tentando método direto para arquivo {file_id}")
                if file_mime_type.startswith('application/vnd.google-apps'):
                    request = drive_service.files().export_media(fileId=file_id, mimeType=export_mime_type)
                else:
                    request = drive_service.files().get_media(fileId=file_id)
                
                file_content = request.execute()
                return file_content
            
            # Método 3: Download com timeout reduzido
            else:
                logger.info(f"Tentando método com timeout para arquivo {file_id}")
                import socket
                original_timeout = socket.getdefaulttimeout()
                socket.setdefaulttimeout(30)  # 30 segundos
                
                try:
                    if file_mime_type.startswith('application/vnd.google-apps'):
                        request = drive_service.files().export_media(fileId=file_id, mimeType=export_mime_type)
                    else:
                        request = drive_service.files().get_media(fileId=file_id)
                    
                    file_content = request.execute()
                    return file_content
                finally:
                    socket.setdefaulttimeout(original_timeout)
                    
        except Exception as e:
            error_msg = str(e).lower()
            logger.warning(f"Tentativa {attempt + 1} falhou para arquivo {file_id}: {e}")
            
            if attempt == max_retries - 1:  # Última tentativa
                if "nonetype" in error_msg or "close" in error_msg:
                    raise Exception("Erro de conexão com Google Drive. Tente novamente.")
                elif "ssl" in error_msg:
                    raise Exception("Erro SSL. Verifique sua conexão.")
                else:
                    raise Exception(f"Falha no download após {max_retries} tentativas: {e}")
            
            # Aguardar antes da próxima tentativa
            time.sleep(1)
    
    return None

def render_pagination_controls(current_page: int, total_pages: int, drive_type_prefix: str) -> None:
    """
    Renderiza controles de paginação numerados no final da página.
    
    Args:
        current_page: Página atual
        total_pages: Total de páginas
        drive_type_prefix: Prefixo para identificar o tipo de drive
        
    Raises:
        None: Função não levanta exceções
    """
    if total_pages <= 1:
        return
    
    page_key = f"current_page_{drive_type_prefix}"
    
    st.markdown("---")
    st.markdown("### Páginas")
    
    # Determinar páginas visíveis
    max_visible = 7
    start_page = max(1, current_page - max_visible // 2)
    end_page = min(total_pages, start_page + max_visible - 1)
    
    if end_page - start_page + 1 < max_visible:
        start_page = max(1, end_page - max_visible + 1)
    
    cols = st.columns(min(end_page - start_page + 3, 10))
    col_idx = 0
    
    # Botão anterior
    with cols[col_idx]:
        if st.button("Anterior", key=f"pg_prev_{drive_type_prefix}", disabled=current_page == 1, icon=":material/arrow_back:"):
            st.session_state[page_key] = current_page - 1
            st.rerun()
    col_idx += 1
    
    # Primeira página
    if start_page > 1:
        with cols[col_idx]:
            if st.button("1", key=f"pg_1_{drive_type_prefix}", type="secondary" if current_page != 1 else "primary"):
                st.session_state[page_key] = 1
                st.rerun()
        col_idx += 1
        
        if start_page > 2:
            with cols[col_idx]:
                st.markdown("...")
            col_idx += 1
    
    # Páginas visíveis
    for page_num in range(start_page, min(end_page + 1, len(cols) - 1)):
        if col_idx >= len(cols) - 1:
            break
            
        with cols[col_idx]:
            button_type = "primary" if page_num == current_page else "secondary"
            if st.button(str(page_num), key=f"pg_{page_num}_{drive_type_prefix}", type=button_type):
                st.session_state[page_key] = page_num
                st.rerun()
        col_idx += 1
    
    # Última página
    if end_page < total_pages and col_idx < len(cols) - 1:
        if end_page < total_pages - 1:
            with cols[col_idx]:
                st.markdown("...")
            col_idx += 1
        
        if col_idx < len(cols) - 1:
            with cols[col_idx]:
                if st.button(str(total_pages), key=f"pg_{total_pages}_{drive_type_prefix}", 
                           type="secondary" if current_page != total_pages else "primary"):
                    st.session_state[page_key] = total_pages
                    st.rerun()
            col_idx += 1
    
    # Botão próximo
    with cols[-1]:
        if st.button("Próximo", key=f"pg_next_{drive_type_prefix}", disabled=current_page == total_pages, icon=":material/arrow_forward:"):
            st.session_state[page_key] = current_page + 1
            st.rerun()

def display_file_list(drive_service_key_for_display: str, all_files: list, drive_type_prefix: str, items_per_page: int = 20) -> None:
    """
    Exibe uma lista paginada de arquivos com download SOB DEMANDA.
    
    Args:
        drive_service_key_for_display: Chave do serviço do Drive no session_state
        all_files: Lista de arquivos para exibir
        drive_type_prefix: Prefixo para identificar o tipo de drive
        items_per_page: Número de itens por página
        
    Raises:
        None: Função não levanta exceções
    """
    # Filtros compactos
    col1, col2 = st.columns(2)
    with col1:
        search_query = st.text_input(
            "Buscar arquivo:",
            key=f"search_{drive_type_prefix}",
            placeholder="Digite o nome do arquivo...",
            help="Busque por nome do arquivo"
        )
    with col2:
        selected_file_category = st.selectbox(
            "Filtrar por tipo:",
            list(FILE_CATEGORY_MAP.keys()),
            key=f"file_category_filter_{drive_type_prefix}",
            help="Filtre por tipo de arquivo"
        )

    # Filtrar arquivos
    filtered_files = []
    for file_item in all_files:
        file_mime_type = file_item['mimeType']
        is_folder = file_mime_type == 'application/vnd.google-apps.folder'
        
        name_matches = search_query.lower() in file_item['name'].lower()
        
        category_match = False
        if selected_file_category == "Todos":
            category_match = True
        elif file_mime_type in FILE_CATEGORY_MAP.get(selected_file_category, []):
            category_match = True
        elif FILE_CATEGORY_MAP.get(selected_file_category) == "all" and not is_folder:
            category_match = True

        if name_matches and category_match:
            filtered_files.append(file_item)

    total_files = len(filtered_files)
    total_pages = (total_files + items_per_page - 1) // items_per_page

    if total_files == 0:
        _render_info_like_message("info", 'Nenhum arquivo encontrado com os filtros aplicados.', THEME["icons"]["generic_info"])
        return

    # Controle de página
    page_key = f"current_page_{drive_type_prefix}"
    if page_key not in st.session_state:
        st.session_state[page_key] = 1

    current_page = st.session_state[page_key]
    if current_page > total_pages:
        st.session_state[page_key] = total_pages
        current_page = total_pages
    if current_page < 1:
        st.session_state[page_key] = 1
        current_page = 1

    # Navegação no topo
    nav_col1, nav_col2, nav_col3 = st.columns([1, 2, 1])
    with nav_col1:
        if st.button("Anterior", disabled=current_page == 1, key=f"nav_prev_{drive_type_prefix}", icon=":material/arrow_back:"):
            st.session_state[page_key] -= 1
            st.rerun()
    with nav_col2:
        st.markdown(f"<p style='text-align:center;'><strong>Página {current_page} de {total_pages}</strong> ({total_files} arquivos)</p>", unsafe_allow_html=True)
    with nav_col3:
        if st.button("Próximo", disabled=current_page == total_pages, key=f"nav_next_{drive_type_prefix}", icon=":material/arrow_forward:"):
            st.session_state[page_key] += 1
            st.rerun()

    # Arquivos da página atual
    start_idx = (current_page - 1) * items_per_page
    end_idx = start_idx + items_per_page
    paginated_files = filtered_files[start_idx:end_idx]

    current_drive_service = st.session_state.get(drive_service_key_for_display)

    # Lista de arquivos - SEM PRÉ-CARREGAMENTO
    for file_item in paginated_files:
        file_display_name = file_item['name']
        file_id = file_item['id']
        file_mime_type = file_item['mimeType']
        file_size = file_item.get('size')
        is_folder = file_mime_type == 'application/vnd.google-apps.folder'

        with st.container():
            col1, col2 = st.columns([0.75, 0.25])
            
            with col1:
                icon_key = THEME['icons']['folder_docs'] if is_folder else THEME['icons']['document']
                file_type = MIME_TYPE_DISPLAY.get(file_mime_type, MIME_TYPE_DISPLAY['default'])
                st.markdown(f"**{_get_material_icon_html(icon_key)} {file_display_name}**", unsafe_allow_html=True)
                st.caption(f"{file_type} • {format_file_size(file_size)}")
            
            with col2:
                if not is_folder:
                    download_filename, export_mime_type = get_download_metadata(file_display_name, file_mime_type)
                    if download_filename and current_drive_service:
                        # BOTÃO DE DOWNLOAD SOB DEMANDA
                        download_key = f"download_btn_{drive_type_prefix}_{file_id}"
                        
                        if st.button("Baixar", key=download_key, type="primary", icon=":material/download:", use_container_width=True):
                            try:
                                with st.spinner(f"Baixando {file_display_name}..."):
                                    # Download SOB DEMANDA - só quando clicado
                                    file_bytes = safe_download_file_on_demand(
                                        current_drive_service, 
                                        file_id, 
                                        file_mime_type, 
                                        export_mime_type
                                    )
                                    
                                    if file_bytes:
                                        # Armazenar temporariamente para download
                                        download_data_key = f"download_ready_{file_id}"
                                        st.session_state[download_data_key] = {
                                            'data': file_bytes,
                                            'filename': download_filename,
                                            'mime': export_mime_type,
                                            'timestamp': time.time()
                                        }
                                        st.success(f"Arquivo '{file_display_name}' pronto para download!")
                                        st.rerun()
                                    else:
                                        st.error("Arquivo indisponível")
                            except Exception as e:
                                st.error(f"Erro: {str(e)}")
                                logger.error(f"Erro no download de {file_display_name}: {e}")
                        
                        # Verificar se há download pronto
                        download_data_key = f"download_ready_{file_id}"
                        if download_data_key in st.session_state:
                            download_data = st.session_state[download_data_key]
                            
                            # Limpar downloads antigos (mais de 5 minutos)
                            if time.time() - download_data['timestamp'] > 300:
                                st.session_state.pop(download_data_key, None)
                            else:
                                st.download_button(
                                    label="Salvar Arquivo",
                                    data=download_data['data'],
                                    file_name=download_data['filename'],
                                    mime=download_data['mime'],
                                    key=f"save_{file_id}",
                                    help="Clique para salvar no seu dispositivo",
                                    icon=":material/save:",
                                    type="secondary",
                                    use_container_width=True,
                                    on_click=lambda: st.session_state.pop(download_data_key, None)
                                )
                    else:
                        st.caption("Não disponível")
                else:
                    st.caption("Pasta")
            
            st.divider()

    # Paginação numerada no final
    render_pagination_controls(current_page, total_pages, drive_type_prefix)

def _sync_central_library_action() -> None:
    """
    Inicia o processo de sincronização da biblioteca central.
    
    Raises:
        None: Função não levanta exceções
    """
    st.session_state.sync_central_library_in_progress = True
    st.session_state.sync_central_library_error = False
    st.session_state.sync_central_library_status = "Iniciando sincronização..."
    st.session_state.sync_central_library_progress = 0
    st.rerun()

def render_page() -> None:
    """
    Renderiza a página da biblioteca de documentos com carregamento otimizado.
    
    Raises:
        None: Função não levanta exceções
    """
    # Título principal com ícone
    st.markdown(f'# {_get_material_icon_html(THEME["icons"]["library_books"])} {THEME["phrases"]["document_library"]}', unsafe_allow_html=True)
    
    # CSS customizado para tabs mais visíveis
    st.markdown("""
    <style>
    /* Tabs mais destacadas */
    .stTabs [data-testid="stTab"] button {
        background: linear-gradient(135deg, #27ae60 0%, #2ecc71 100%) !important;
        color: white !important;
        border: none !important;
        border-radius: 10px 10px 0 0 !important;
        padding: 15px 30px !important;
        font-weight: 600 !important;
        font-size: 1.1em !important;
        margin-right: 10px !important;
        box-shadow: 0 4px 8px rgba(39, 174, 96, 0.3) !important;
        transition: all 0.3s ease !important;
    }
    
    .stTabs [data-testid="stTab"] button:hover {
        background: linear-gradient(135deg, #2ecc71 0%, #27ae60 100%) !important;
        transform: translateY(-2px) !important;
        box-shadow: 0 6px 12px rgba(39, 174, 96, 0.4) !important;
    }
    
    .stTabs [data-testid="stTab"] button[aria-selected="true"] {
        background: linear-gradient(135deg, #1e8449 0%, #239b56 100%) !important;
        border-bottom: 3px solid #27ae60 !important;
        transform: translateY(-1px) !important;
    }
    
    .stTabs [data-testid="stTabContent"] {
        background: linear-gradient(135deg, #0d1117 0%, #161b22 100%) !important;
        border: 2px solid #27ae60 !important;
        border-top: none !important;
        border-radius: 0 0 15px 15px !important;
        padding: 25px !important;
        box-shadow: 0 8px 16px rgba(0, 0, 0, 0.3) !important;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Tabs com design aprimorado
    tab1, tab2 = st.tabs([
        "Biblioteca Central",
        "Doação de Conteúdo"
    ])

    with tab1:
        if not st.session_state.get("app_drive_service"):
            _render_info_like_message("warning", "Serviço indisponível. Verifique as configurações.", THEME["icons"]["warning_sign"])
            return

        # Botão de sincronização destacado
        st.markdown("""
        <style>
        /* Botão de sincronização destacado */
        div[data-testid*="stButton-sync_btn_enhanced"] > button {
            background: linear-gradient(135deg, #3498db 0%, #2980b9 100%) !important;
            color: white !important;
            border: none !important;
            border-radius: 12px !important;
            padding: 15px 30px !important;
            font-weight: 600 !important;
            font-size: 1.1em !important;
            box-shadow: 0 6px 12px rgba(52, 152, 219, 0.4) !important;
            transition: all 0.3s ease !important;
            width: 100% !important;
        }
        
        div[data-testid*="stButton-sync_btn_enhanced"] > button:hover:not(:disabled) {
            background: linear-gradient(135deg, #2980b9 0%, #3498db 100%) !important;
            transform: translateY(-3px) !important;
            box-shadow: 0 8px 16px rgba(52, 152, 219, 0.5) !important;
        }
        
        div[data-testid*="stButton-sync_btn_enhanced"] > button:disabled {
            background: linear-gradient(135deg, #7f8c8d 0%, #95a5a6 100%) !important;
            transform: none !important;
            box-shadow: none !important;
        }
        </style>
        """, unsafe_allow_html=True)

        # Seção de sincronização destacada
        st.markdown("### Sincronização da Biblioteca")
        
        sync_label = "Sincronizando..." if st.session_state.get("sync_central_library_in_progress") else "Sincronizar Biblioteca Central"
        if st.session_state.get("sync_central_library_error"):
            sync_label = "Tentar Sincronizar Novamente"

        if st.button(
            sync_label,
            key="sync_btn_enhanced",
            disabled=st.session_state.get("sync_central_library_in_progress", False),
            help="Sincroniza todos os documentos da biblioteca central com a base de conhecimento da IA",
            icon=":material/sync:"
        ):
            _sync_central_library_action()

        # Status da sincronização
        if st.session_state.get("sync_central_library_in_progress"):
            st.progress(st.session_state.get("sync_central_library_progress", 0) / 100)
            st.info(st.session_state.get("sync_central_library_status", "Processando..."))
            
            try:
                sync_result = synchronize_app_central_library_to_chroma(
                    st.session_state.get("app_drive_service"), 
                    st.session_state.nr_qa
                )
                st.session_state.sync_central_library_error = False
                st.session_state.sync_central_library_status = sync_result
                st.session_state.sync_central_library_progress = 100
            except Exception as e:
                st.session_state.sync_central_library_error = True
                st.session_state.sync_central_library_status = f"Erro: {e}"
                logger.error(f"Erro na sincronização: {e}")
            finally:
                st.session_state.sync_central_library_in_progress = False
                st.rerun()

        if not st.session_state.get("sync_central_library_in_progress") and st.session_state.get("sync_central_library_status"):
            if st.session_state.get("sync_central_library_error"):
                _render_info_like_message("error", st.session_state.sync_central_library_status, THEME["icons"]["error_x"])
            elif st.session_state.get("sync_central_library_progress") == 100:
                _render_info_like_message("success", f"Sincronização concluída! {st.session_state.sync_central_library_status}", THEME["icons"]["success_check"])

        st.markdown("---")

        # Lista de arquivos - CARREGAMENTO RÁPIDO
        with st.spinner("Carregando lista de arquivos..."):
            app_files = get_processable_drive_files_in_folder(
                st.session_state["app_drive_service"], 
                st.session_state.get("OUR_DRIVE_FOLDER_ID")
            )
        
        if app_files:
            st.markdown("### Arquivos Disponíveis para Download")
            st.info(f"Total de {len(app_files)} arquivos encontrados. Downloads são realizados sob demanda.")
            display_file_list("app_drive_service", app_files, "app", items_per_page=20)
        else:
            _render_info_like_message("error", "Nenhum arquivo encontrado na biblioteca central.", THEME["icons"]["error_x"])

    with tab2:
        # INICIALIZAR ESTADO DE DOAÇÕES
        initialize_donation_session_state()
        
        # VERIFICAÇÃO DE LOGIN
        user_logged_in = False
        user_service = None
        service_type = None
        
        # Verificar se o usuário tem nome (está logado)
        user_has_name = st.session_state.get("user_name") and st.session_state.get("user_name") != ""
        
        # Verificar serviços disponíveis
        if st.session_state.get("user_drive_service"):
            user_logged_in = True
            user_service = st.session_state["user_drive_service"]
            service_type = "user_drive_service"
            logger.info("Usando user_drive_service para doações (permissões completas)")
        elif user_has_name and st.session_state.get("app_drive_service"):
            user_logged_in = True
            user_service = st.session_state["app_drive_service"]
            service_type = "app_drive_service"
            logger.info("Usando app_drive_service temporariamente para doações")
        else:
            logger.warning("Nenhum serviço disponível para doações")

        if not user_logged_in:
            _render_info_like_message("warning", "Nenhum serviço do Google Drive disponível. Verifique as configurações.", THEME["icons"]["warning_sign"])
            
            # Verificar se precisa de autenticação
            if st.session_state.get('user_drive_auth_needed'):
                st.warning("Autenticação do Google Drive necessária para doações.")
                if st.session_state.get('user_drive_auth_url'):
                    st.markdown(f"**Clique aqui para autenticar seu Google Drive: {st.session_state['user_drive_auth_url']}**")
                else:
                    st.error("URL de autenticação não disponível. Recarregue a página.")
            
            # Botão para tentar reautenticar
            if st.button("Tentar Reautenticar", icon=":material/refresh:", type="primary"):
                st.session_state.pop('user_drive_auth_error', None)
                st.session_state.pop('user_drive_auth_url', None)
                st.session_state['user_drive_auth_needed'] = True
                st.rerun()
            
            return

        st.markdown("### Contribua com a Comunidade")
        st.markdown("Doe documentos valiosos de SST para enriquecer nossa biblioteca compartilhada!")

        # Mostrar status do serviço
        if service_type == "user_drive_service":
            st.success("Serviço do Google Drive do usuário ativo com permissões completas!")
        else:
            st.warning("Usando serviço da aplicação temporariamente. Algumas limitações podem ocorrer.")

        can_upload = st.session_state['daily_donations_count'] < MAX_DAILY_DONATIONS
        uploads_left = MAX_DAILY_DONATIONS - st.session_state['daily_donations_count']

        # Info sobre limites ATUALIZADA
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Doações restantes hoje", uploads_left, f"de {MAX_DAILY_DONATIONS}")
        with col2:
            st.metric("Tamanho máximo por arquivo", f"{MAX_DONATION_SIZE_MB} MB", "Limite técnico")

        # HISTÓRICO DE DOAÇÕES - SEMPRE VISÍVEL SE HOUVER - CORRIGIDO
        if st.session_state['donation_history']:
            st.markdown("---")
            st.markdown(f"### {_get_material_icon_html(THEME['icons']['history'])} Histórico de Doações de Hoje", unsafe_allow_html=True)
            
            # Container com borda para o histórico
            with st.container():
                st.markdown("""
                <div style="
                    border: 2px solid #27ae60; 
                    border-radius: 10px; 
                    padding: 15px; 
                    background: linear-gradient(135deg, #0d1117 0%, #161b22 100%);
                    margin: 10px 0;
                ">
                """, unsafe_allow_html=True)
                
                for i, donation in enumerate(st.session_state['donation_history'], 1):
                    col1, col2, col3 = st.columns([0.1, 0.6, 0.3])
                    with col1:
                        st.markdown(f"**{i}.**")
                    with col2:
                        st.markdown(f"**{donation['filename']}**")
                        st.caption(f"Tamanho: {format_file_size(donation['size'])}")
                    with col3:
                        st.markdown(f"<div style='color: #27ae60; font-weight: bold;'>{_get_material_icon_html(THEME['icons']['success_check'])} {donation['timestamp']}</div>", unsafe_allow_html=True)
                    
                    if i < len(st.session_state['donation_history']):
                        st.divider()
                
                st.markdown("</div>", unsafe_allow_html=True)
        else:
            # MOSTRAR MENSAGEM QUANDO NÃO HÁ HISTÓRICO
            st.markdown("---")
            _render_info_like_message("info", "Nenhuma doação realizada hoje. Seja o primeiro a contribuir!", THEME['icons']['donation_hands'])

        if can_upload:
            st.markdown("---")
            
            uploaded_files = st.file_uploader(
                "Selecione seus documentos de SST (PDF, DOCX, TXT):",
                type=['pdf', 'docx', 'txt'],
                accept_multiple_files=True,
                key="donation_uploader",
                help="Selecione documentos relevantes para Saúde e Segurança do Trabalho"
            )
            
            if uploaded_files:
                st.markdown("### Arquivos Selecionados para Doação")
                
                # Verificar duplicatas no histórico local
                existing_files = [d['filename'] for d in st.session_state['donation_history']]
                
                for i, up_file in enumerate(uploaded_files):
                    file_too_large = up_file.size > MAX_DONATION_SIZE_BYTES
                    is_duplicate_local = up_file.name in existing_files
                    
                    # Verificar duplicata no Drive
                    is_duplicate_drive = False
                    if not is_duplicate_local and not file_too_large:
                        donation_folder_id = st.session_state.get("OUR_DRIVE_DONATION_FOLDER_ID")
                        if donation_folder_id:
                            is_duplicate_drive = check_file_exists_in_drive(
                                user_service, 
                                donation_folder_id, 
                                up_file.name
                            )
                    
                    col1, col2 = st.columns([0.7, 0.3])
                    with col1:
                        if is_duplicate_local:
                            status_text = "Já doado hoje"
                            st.markdown(f"**{up_file.name}** {_get_material_icon_html(THEME['icons']['warning_sign'])}", unsafe_allow_html=True)
                        elif is_duplicate_drive:
                            status_text = "Já existe no Drive"
                            st.markdown(f"**{up_file.name}** {_get_material_icon_html(THEME['icons']['warning_sign'])}", unsafe_allow_html=True)
                        elif file_too_large:
                            status_text = "Muito grande"
                            st.markdown(f"**{up_file.name}**")
                        else:
                            status_text = "Pronto para doar"
                            st.markdown(f"**{up_file.name}**")
                        st.caption(f"{format_file_size(up_file.size)} • {status_text}")
                    
                    with col2:
                        if is_duplicate_local:
                            st.button("Já Doado", disabled=True, use_container_width=True, key=f"duplicate_local_{i}")
                        elif is_duplicate_drive:
                            st.button("Já Existe", disabled=True, use_container_width=True, key=f"duplicate_drive_{i}")
                        elif not file_too_large:
                            # BOTÃO DE DOAÇÃO COM RECAPTCHA
                            if st.button("Doar Agora", key=f"donate_{i}", type="primary", use_container_width=True, icon=":material/upload:"):
                                # MOSTRAR RECAPTCHA - CORRIGIDO
                                security_icon = THEME['icons'].get('security', 'security')
                                st.markdown(f"### {_get_material_icon_html(security_icon)} Verificação de Segurança", unsafe_allow_html=True)
                                st.markdown("Complete a verificação abaixo para confirmar que você não é um robô:")
                                
                                # Renderizar reCAPTCHA
                                recaptcha_response = render_recaptcha()
                                
                                col_captcha1, col_captcha2 = st.columns(2)
                                with col_captcha1:
                                    if st.button("Confirmar Doação", key=f"confirm_{i}", type="primary", icon=":material/check_circle:"):
                                        # Verificar reCAPTCHA
                                        if not recaptcha_response:
                                            _render_info_like_message("error", "Por favor, complete a verificação reCAPTCHA.", THEME['icons']['error_x'])
                                        elif not verify_recaptcha(recaptcha_response):
                                            _render_info_like_message("error", "Verificação reCAPTCHA falhou. Tente novamente.", THEME['icons']['error_x'])
                                        else:
                                            try:
                                                with st.spinner(f"Enviando {up_file.name} para a pasta de doações..."):
                                                    # VERIFICAR SE A PASTA DE DOAÇÃO EXISTE
                                                    donation_folder_id = st.session_state.get("OUR_DRIVE_DONATION_FOLDER_ID")
                                                    if not donation_folder_id:
                                                        _render_info_like_message("error", "Pasta de doação não configurada. Contate o administrador.", THEME['icons']['error_x'])
                                                        logger.error("OUR_DRIVE_DONATION_FOLDER_ID não está configurado")
                                                        continue
                                                    
                                                    logger.info(f"Tentando fazer upload para pasta de doação: {donation_folder_id}")
                                                    
                                                    # VERIFICAÇÃO FINAL DE DUPLICATA NO DRIVE
                                                    if check_file_exists_in_drive(user_service, donation_folder_id, up_file.name):
                                                        _render_info_like_message("error", f"Arquivo '{up_file.name}' já existe na pasta de doações.", THEME['icons']['warning_sign'])
                                                        continue
                                                    
                                                    # UPLOAD PARA A PASTA CORRETA
                                                    file_id = upload_file_to_drive(
                                                        user_service,
                                                        up_file, 
                                                        parent_folder_id=donation_folder_id
                                                    )
                                                    
                                                    if file_id:
                                                        # ATUALIZAR CONTADOR E HISTÓRICO - CORRIGIDO
                                                        st.session_state['daily_donations_count'] += 1
                                                        logger.info(f"Contador atualizado: {st.session_state['daily_donations_count']}/{MAX_DAILY_DONATIONS}")
                                                        
                                                        # Adicionar ao histórico
                                                        donation_record = {
                                                            'filename': up_file.name,
                                                            'file_id': file_id,
                                                            'size': up_file.size,
                                                            'timestamp': datetime.now().strftime("%H:%M:%S"),
                                                            'date': str(date.today())
                                                        }
                                                        st.session_state['donation_history'].append(donation_record)
                                                        logger.info(f"Histórico atualizado: {len(st.session_state['donation_history'])} doações")
                                                        
                                                        logger.info(f"Arquivo {up_file.name} doado com sucesso. ID: {file_id}")
                                                        _render_info_like_message("success", f"'{up_file.name}' doado com sucesso! Obrigado pela contribuição!", THEME['icons']['success_check'])
                                                        
                                                        # Limpar resposta do reCAPTCHA
                                                        if 'recaptcha_response' in st.session_state:
                                                            del st.session_state['recaptcha_response']
                                                        
                                                        # Aguardar um pouco antes de recarregar
                                                        time.sleep(1)
                                                        st.rerun()
                                                    else:
                                                        _render_info_like_message("error", "Falha no upload. Tente novamente.", THEME['icons']['error_x'])
                                                        logger.error(f"Upload falhou para {up_file.name} - file_id retornado foi None")
                                                        
                                            except Exception as e:
                                                error_msg = str(e)
                                                logger.error(f"Erro na doação de {up_file.name}: {e}")
                                                
                                                if "403" in error_msg and "insufficientPermissions" in error_msg:
                                                    _render_info_like_message("error", "Erro de permissões: O serviço não tem autorização para escrever no Google Drive.", THEME['icons']['error_x'])
                                                    
                                                    # Mostrar instruções para o usuário
                                                    with st.expander(f"{_get_material_icon_html(THEME['icons']['generic_info'])} Instruções para Resolver o Problema", expanded=True):
                                                        st.markdown("""
                                                        **O que aconteceu:**
                                                        - Permissões insuficientes para escrever no Google Drive
                                                        
                                                        **Como resolver:**
                                                        1. Faça logout da aplicação
                                                        2. Faça login novamente
                                                        3. Certifique-se de autorizar todas as permissões do Google Drive
                                                        4. Tente doar novamente
                                                        """)
                                                elif "quota" in error_msg.lower():
                                                    _render_info_like_message("error", "Limite de quota do Google Drive atingido. Tente novamente mais tarde.", THEME['icons']['error_x'])
                                                elif "network" in error_msg.lower() or "connection" in error_msg.lower():
                                                    _render_info_like_message("error", "Erro de conexão. Verifique sua internet e tente novamente.", THEME['icons']['error_x'])
                                                elif "notFound" in error_msg or "404" in error_msg:
                                                    _render_info_like_message("error", "Pasta de doação não encontrada. Contate o administrador.", THEME['icons']['error_x'])
                                                else:
                                                    _render_info_like_message("error", f"Erro ao doar: {e}", THEME['icons']['error_x'])
                                
                                with col_captcha2:
                                    if st.button("Cancelar", key=f"cancel_{i}", icon=":material/cancel:"):
                                        # Limpar resposta do reCAPTCHA
                                        if 'recaptcha_response' in st.session_state:
                                            del st.session_state['recaptcha_response']
                                        st.rerun()
                                
                                st.stop()  # Para não mostrar outros arquivos enquanto o reCAPTCHA está ativo
                        else:
                            st.button("Muito Grande", disabled=True, use_container_width=True, key=f"large_{i}")
        else:
            st.markdown("---")
            _render_info_like_message("warning", "Limite diário de doações atingido. Volte amanhã para continuar contribuindo!", THEME['icons']['warning_sign'])
            _render_info_like_message("info", "Enquanto isso, que tal explorar nossa biblioteca e baixar alguns documentos úteis?", THEME['icons']['bulb'])
            
            # Mostrar quando poderá doar novamente
            _render_info_like_message("info", f"Você poderá fazer novas doações amanhã. Doações realizadas hoje: {st.session_state['daily_donations_count']}/{MAX_DAILY_DONATIONS}", THEME['icons']['chart_bar'])