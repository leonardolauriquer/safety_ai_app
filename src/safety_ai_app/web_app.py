import os
import sys
import streamlit as st
import logging
from dotenv import load_dotenv
from datetime import date
import re
import markdown
import base64
import mimetypes
import streamlit.components.v1 as components
import json

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s', stream=sys.stderr)
logger = logging.getLogger(__name__)
logger.info("Iniciando carregamento do web_app.py")

logger.info(f"Python executable (dentro do Streamlit): {sys.executable}")
logger.info(f"Python Path (dentro do Streamlit): {sys.path}")

script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(script_dir, '..', '..'))
src_path = os.path.join(project_root, 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)
logger.info(f"Adicionado {src_path} ao sys.path para importações locais.")

try:
    load_dotenv(os.path.join(project_root, '.env'))
    logger.info("Variáveis de ambiente carregadas.")
except Exception as e:
    logger.critical(f"[ERRO CRÍTICO] Falha ao carregar variáveis de ambiente do .env: {e}.")
    st.error(f"Erro crítico: Não foi possível carregar as variáveis de ambiente. Detalhes: {e}")
    # st.stop() # Comentado para permitir funcionamento sem RAG

try:
    from safety_ai_app.theme_config import GLOBAL_STYLES, THEME, _get_material_icon_html_for_button_css, _get_material_icon_html
    logger.info("Configurações de tema (GLOBAL_STYLES, THEME, _get_material_icon_html_for_button_css, _get_material_icon_html) importadas com sucesso.")
except ImportError as e:
    logger.critical(f"[ERRO CRÍTICO] Falha ao importar theme_config: {e}. Verifique o arquivo.")
    st.error(f"Erro crítico: Não foi possível carregar as configurações de tema. Detalhes: {e}")
    # st.stop() # Comentado para permitir funcionamento sem RAG
except KeyError as e:
    logger.critical(f"[ERRO CRÍTICO] Chave ausente em THEME ou GLOBAL_STYLES após importação de theme_config: {e}. Verifique se as chaves 'app_title', 'icons', 'phrases' e 'images' existem.")
    st.error(f"Erro crítico: Chave ausente em THEME ou GLOBAL_STYLES. Verifique 'theme_config.py' e se as chaves 'app_title', 'icons', 'phrases' e 'images' existem. Detalhes: {e}")
    # st.stop() # Comentado para permitir funcionamento sem RAG
except Exception as e:
    logger.critical(f"[ERRO CRÍTICO] Erro inesperado ao importar theme_config: {e}. Tipo: {type(e).__name__}")
    st.error(f"Erro crítico inesperado ao carregar as configurações de tema. Detalhes: {e}")
    # st.stop() # Comentado para permitir funcionamento sem RAG

page_icon_relative_path = THEME["images"]["page_icon"]
st.set_page_config(
    page_title=THEME["phrases"]["app_title"],
    page_icon=os.path.join(project_root, page_icon_relative_path),
    layout="wide",
    initial_sidebar_state="expanded"
)
logger.info("st.set_page_config executado com sucesso no nível superior.")

def get_image_base64(image_path: str) -> str:
    """
    Converte uma imagem para base64 para uso em HTML.
    
    Args:
        image_path: Caminho relativo da imagem
        
    Returns:
        str: String base64 da imagem ou string vazia em caso de erro
        
    Raises:
        None: Trata erros internamente
    """
    try:
        abs_image_path = os.path.join(project_root, image_path)
        logger.info(f"Tentando carregar imagem: {abs_image_path}")

        if not os.path.exists(abs_image_path):
            logger.error(f"Arquivo de imagem NÃO ENCONTRADO: {abs_image_path}.")
            return ""

        mime_type, _ = mimetypes.guess_type(abs_image_path)
        if mime_type is None:
            if abs_image_path.lower().endswith(".png"):
                mime_type = "image/png"
            elif abs_image_path.lower().endswith(".jpg") or abs_image_path.lower().endswith(".jpeg"):
                mime_type = "image/jpeg"
            else:
                logger.warning(f"Não foi possível determinar o tipo MIME para {image_path}, usando 'image/octet-stream'.")
                mime_type = "image/octet-stream"

        logger.info(f"Imagem: '{image_path}', MIME Type detectado: '{mime_type}'")

        with open(abs_image_path, "rb") as image_file:
            encoded_string = base64.b64encode(image_file.read()).decode()

        logger.debug(f"Base64 prefixo para '{image_path}': '{encoded_string[:50]}...'")
        return f"data:{mime_type};base64,{encoded_string}"
    except FileNotFoundError:
        logger.error(f"Arquivo de imagem NÃO ENCONTRADO (tratado na exceção): {abs_image_path}")
        return ""
    except Exception as e:
        logger.critical(f"[ERRO CRÍTICO] Erro ao codificar imagem Base64 '{image_path}': {e}", exc_info=True)
        return ""

try:
    from safety_ai_app.google_drive_integrator import (
        get_google_drive_user_creds_and_auth_info,
        get_google_drive_service_user,
        get_service_account_drive_service,
        OUR_DRIVE_FOLDER_ID,
        OUR_DRIVE_DONATION_FOLDER_ID
    )
    logger.info("Google Drive Integrator importado com sucesso.")
except ImportError as e:
    logger.critical(f"[ERRO CRÍTICO] Falha ao importar google_drive_integrator: {e}.")
    st.error(f"Erro crítico: Não foi possível carregar o integrador do Google Drive. Detalhes: {e}")
    # st.stop() # Comentado para permitir funcionamento sem RAG
except Exception as e:
    logger.critical(f"[ERRO CRÍTICO] Erro inesperado ao importar google_drive_integrator: {e}.")
    st.error(f"Erro crítico inesperado ao carregar o integrador do Google Drive. Detalhes: {e}")
    # st.stop() # Comentado para permitir funcionamento sem RAG

try:
    from safety_ai_app.nr_rag_qa import NRQuestionAnswering
    logger.info("NRQuestionAnswering importado com sucesso.")
except ImportError as e:
    logger.critical(f"[ERRO CRÍTICO] Falha ao importar nr_rag_qa: {e}.")
    st.error(f"Erro crítico: Não foi possível carregar o módulo RAG QA. Detalhes: {e}")
    # st.stop() # Comentado para permitir funcionamento sem RAG
except Exception as e:
    logger.critical(f"[ERRO CRÍTICO] Erro inesperado ao importar nr_rag_qa: {e}.")
    st.error(f"Erro crítico inesperado ao carregar o módulo RAG QA. Detalhes: {e}")
    # st.stop() # Comentado para permitir funcionamento sem RAG

try:
    from safety_ai_app.web_interface.pages.chat_page import render_page as render_chat_page
    logger.info("Importado render_page da chat_page (com alias render_chat_page) com sucesso.")
except ImportError as e:
    logger.critical(f"[ERRO CRÍTICO] Falha ao importar render_page da chat_page: {e}.")
    st.error(f"Erro crítico: Não foi possível carregar a página de chat. Detalhes: {e}")
    # st.stop() # Comentado para permitir funcionamento sem RAG

try:
    from safety_ai_app.web_interface.pages.library_page import render_page as render_library_page
    logger.info("Importado render_page da library_page (com alias render_library_page) com sucesso.")
except ImportError as e:
    logger.critical(f"[ERRO CRÍTICO] Falha ao importar render_page da library_page: {e}.")
    st.error(f"Erro crítico: Não foi possível carregar a página de biblioteca. Detalhes: {e}")
    # st.stop() # Comentado para permitir funcionamento sem RAG

try:
    from safety_ai_app.web_interface.pages.knowledge_base_page import render_page as render_knowledge_base_page
    logger.info("Importado render_page da knowledge_base_page (com alias render_knowledge_base_page) com sucesso.")
except ImportError as e:
    logger.critical(f"[ERRO CRÍTICO] Falha ao importar render_page da knowledge_base_page: {e}.")
    st.error(f"Erro crítico: Não foi possível carregar a página de base de conhecimento. Detalhes: {e}")
    # st.stop() # Comentado para permitir funcionamento sem RAG

try:
    from safety_ai_app.web_interface.pages.jobs_board_page import render_page as render_jobs_board_page
    logger.info("Importado render_page da jobs_board_page (com alias render_jobs_board_page) com sucesso.")
except ImportError as e:
    logger.critical(f"[ERRO CRÍTICO] Falha ao importar render_page da jobs_board_page: {e}.")
    st.error(f"Erro crítico: Não foi possível carregar a página de vagas. Detalhes: {e}")
    # st.stop() # Comentado para permitir funcionamento sem RAG

def render_home_page() -> None:
    """
    Renderiza a página inicial do aplicativo.
    
    Raises:
        None: Função não levanta exceções
    """
    logger.info("Renderizando conteúdo da página inicial diretamente em web_app.py.")
    st.markdown(f"<h1>{THEME['phrases']['welcome_message']}</h1>", unsafe_allow_html=True)
    st.markdown(
        f"""
        <p style="color:{THEME['colors']['text_primary']};">
        Sou seu assistente de IA especializado em Saúde e Segurança do Trabalho (SST) no Brasil,
        com foco em Normas Regulamentadoras (NRs).
        {_get_material_icon_html(THEME['icons']['ai_robot'])} Estou aqui para te auxiliar com as **Normas Regulamentadoras** e diversos outros
        tópicos cruciais da área. {_get_material_icon_html(THEME['icons']['magic_pencil'])} Pode me perguntar sobre legislação,
        boas práticas, dimensionamento e muito mais!
        </p>
        <p style="color:{THEME['colors']['text_primary']};">
        **Como posso te ajudar hoje?** {_get_material_icon_html(THEME['icons']['rocket_launch'])} Conte-me!
        </p>
        """, unsafe_allow_html=True
    )

    st.markdown("<br>", unsafe_allow_html=True)

    st.markdown(f"<h2>{_get_material_icon_html(THEME['icons']['bulb'])} {THEME['phrases']['our_tools_title']}</h2>", unsafe_allow_html=True)
    st.markdown(
        f"""
        <ul style="color:{THEME['colors']['text_primary']};">
            <li>{_get_material_icon_html(THEME['icons']['chat_bubble'])} **{THEME['phrases']['chat_smart']}**: Pergunte sobre NRs, legislação e boas práticas em SST.</li>
            <li>{_get_material_icon_html(THEME['icons']['file_document'])} **{THEME['phrases']['document_management']}**: Carregue e consulte seus documentos internos.</li>
            <li>{_get_material_icon_html(THEME['icons']['search_magnifying_glass'])} **{THEME['phrases']['quick_consults']}**: Acesse informações sobre CBO, CID, CNAE e mais.</li>
            <li>{_get_material_icon_html(THEME['icons']['calculator'])} **{THEME['phrases']['sizing']}**: Auxílio no cálculo de SESMT e CIPA.</li>
            <li>{_get_material_icon_html(THEME['icons']['news_paper'])} **{THEME['phrases']['news_and_notices']}**: Mantenha-se atualizado com o mundo da SST.</li>
        </ul>
        """, unsafe_allow_html=True
    )

    st.markdown("<br>", unsafe_allow_html=True)

    st.markdown(f"""
        <div class="st-info-like">
            {_get_material_icon_html(THEME['icons']['info_circular_outline'])} **{THEME['phrases']['tip_sidebar_navigation']}**
        </div>
    """, unsafe_allow_html=True)

def process_markdown_for_external_links(text: str) -> str:
    """
    Processa texto Markdown, convertendo links [texto](url) em tags HTML
    <a href="url" >texto</a> para URLs externas ou de download.
    
    Args:
        text: Texto Markdown a ser processado
        
    Returns:
        str: HTML processado com links externos
        
    Raises:
        None: Função não levanta exceções
    """
    pattern = r'$$([^$$]+)\]$([^)]+)$'

    def replace_link(match):
        link_text = match.group(1)
        link_url = match.group(2)

        if link_url.startswith("http://") or link_url.startswith("https://") or link_url.startswith("/download_library_doc"):
            return f'<a href="{link_url}" >{link_text}</a>'
        else:
            return f'<a href="{link_url}">{link_text}</a>'

    processed_text = re.sub(pattern, replace_link, text)
    final_html = markdown.markdown(processed_text)
    return final_html

@st.cache_resource
def get_qa_instance_cached():
    """
    Inicializa e cacheia a instância do NRQuestionAnswering.
    
    Returns:
        NRQuestionAnswering: Instância inicializada do serviço de QA
        
    Raises:
        Exception: Para erros críticos na inicialização
    """
    logger.info("Tentando inicializar NRQuestionAnswering (get_qa_instance_cached).")
    try:
        instance = NRQuestionAnswering()
        logger.info("[+] NRQuestionAnswering instance inicializada com sucesso.")
        return instance
    except Exception as e:
        logger.critical(f"[ERRO CRÍTICO] ERRO ao inicializar NRQuestionAnswering: {e}")
        st.error(f"Erro crítico ao inicializar o serviço de IA. Detalhes: {e}")
        # st.stop() # Comentado para permitir funcionamento sem RAG

@st.cache_resource
def get_app_drive_service_cached():
    """
    Inicializa e cacheia o serviço da conta de aplicativo do Google Drive.
    
    Returns:
        object: Serviço do Google Drive ou None em caso de erro
        
    Raises:
        None: Trata erros internamente
    """
    logger.info("Tentando inicializar serviço da conta de aplicativo do Google Drive.")
    try:
        service = get_service_account_drive_service()
        if service:
            logger.info("[+] Serviço da conta de aplicativo do Google Drive inicializado e cacheado.")
        else:
            logger.warning("[-] Falha ao inicializar o serviço da conta de aplicativo do Google Drive.")
        return service
    except Exception as e:
        logger.error(f"[!] ERRO ao inicializar o serviço da conta de aplicativo: {e}", exc_info=True)
        return None

def get_user_drive_service_wrapper():
    """
    Wrapper para inicialização do serviço de Google Drive do usuário.
    
    Returns:
        object: Serviço do Google Drive do usuário ou None
        
    Raises:
        None: Trata erros internamente
    """
    logger.info("Tentando inicializar serviço de Google Drive do usuário.")
    creds, auth_url, auth_error_message = get_google_drive_user_creds_and_auth_info()

    st.session_state.user_drive_auth_needed = False
    st.session_state.user_drive_auth_url = None
    st.session_state.user_drive_auth_error = None
    st.session_state.logged_in = False

    if auth_url:
        st.session_state.user_drive_auth_needed = True
        st.session_state.user_drive_auth_url = auth_url
        logger.warning(f"[-] Autenticação de usuário do Google Drive necessária. URL: {auth_url}")
        return None
    elif auth_error_message == "REDIRECTING":
        logger.info("Autenticação do Google Drive bem-sucedida, redirecionando...")
        if st.query_params:
            logger.info(f"Limpando st.query_params: {st.query_params}")
            st.query_params.clear()
        st.rerun()
        return None
    elif auth_error_message:
        st.session_state.user_drive_auth_error = auth_error_message
        logger.error(f"[-] Erro na autenticação do Google Drive: {auth_error_message}")
        return None
    elif creds:
        service = get_google_drive_service_user(creds)
        if service:
            st.session_state.logged_in = True
            # ✅ CORREÇÃO: ARMAZENAR O SERVIÇO NO SESSION_STATE
            st.session_state.user_drive_service = service
            logger.info("[+] Serviço de Google Drive do usuário inicializado e cacheado.")
            logger.info("[+] user_drive_service armazenado no session_state com sucesso.")
            return service
        else:
            logger.error("[-] Falha ao construir o serviço do Google Drive mesmo com credenciais válidas. (Verifique logs)")
            return None
    else:
        st.session_state.user_drive_auth_needed = True
        logger.warning("[-] Estado desconhecido na autenticação do Google Drive ou primeira execução. Exibindo prompt de autenticação.")
        return None

def do_logout() -> None:
    """
    Realiza o logout do usuário, limpando credenciais e resetando o estado de sessão.
    
    Raises:
        None: Trata erros internamente
    """
    logger.info("Executando logout do usuário.")
    try:
        if os.path.exists(os.path.join(project_root, "token_user.pickle")):
            os.remove(os.path.join(project_root, "token_user.pickle"))
            logger.info("token_user.pickle removido com sucesso.")
        st.session_state.logged_in = False
        st.session_state.user_drive_service = None
        st.session_state.user_drive_auth_needed = False
        st.session_state.user_drive_auth_url = None
        st.session_state.user_drive_auth_error = None
        if "messages" in st.session_state:
            st.session_state.messages = []
        st.session_state.current_page = "home"
        st.query_params.clear()
        logger.info("Estado de sessão limpo para logout.")
    except Exception as e:
        logger.error(f"Erro durante o logout: {e}", exc_info=True)
        st.error(f"Ocorreu um erro ao tentar fazer logout. Detalhes: {e}")
    st.rerun()

def _initialize_session_state_common() -> None:
    """
    Inicializa o estado de sessão comum para todos os usuários.
    
    Raises:
        None: Função não levanta exceções
    """
    logger.info("Iniciando _initialize_session_state_common.")
    if "current_page" not in st.session_state:
        st.session_state.current_page = "home"
    if "user_name" not in st.session_state:
        st.session_state.user_name = "Leo"
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False

    if "OUR_DRIVE_FOLDER_ID" not in st.session_state:
        st.session_state.OUR_DRIVE_FOLDER_ID = os.getenv("GOOGLE_DRIVE_CENTRAL_LIBRARY_FOLDER_ID")
    if "OUR_DRIVE_DONATION_FOLDER_ID" not in st.session_state:
        st.session_state.OUR_DRIVE_DONATION_FOLDER_ID = os.getenv("GOOGLE_DRIVE_DONATION_FOLDER_ID")

    if "nr_qa" not in st.session_state:
        st.session_state.nr_qa = get_qa_instance_cached()
    if "app_drive_service" not in st.session_state:
        st.session_state.app_drive_service = get_app_drive_service_cached()

    if "user_drive_service" not in st.session_state:
        st.session_state.user_drive_service = None
    if "user_drive_auth_needed" not in st.session_state:
        st.session_state.user_drive_auth_url = None
    if "user_drive_auth_error" not in st.session_state:
        st.session_state.user_drive_auth_error = None

    if "trigger_login_flow_rerun_from_iframe" not in st.session_state:
        st.session_state.trigger_login_flow_rerun_from_iframe = False
    
    if "nav_request" not in st.session_state:
        st.session_state.nav_request = ""

    logger.info("_initialize_session_state_common concluído.")

def _initialize_session_state_post_login() -> None:
    """
    Inicializa o estado de sessão específico para usuários logados.
    
    Raises:
        None: Função não levanta exceções
    """
    logger.info("Iniciando _initialize_session_state_post_login.")

    if "messages" not in st.session_state:
        st.session_state.messages = []
        welcome_message = (
            f"Olá, **{st.session_state.user_name}**! {_get_material_icon_html(THEME['icons']['waving_hand'])} Seja muito bem-vindo(a) ao **SafetyAI**!\n\n"
            f"Sou seu **assistente de IA especializado** em *Saúde e Segurança do Trabalho (SST)* no Brasil. {_get_material_icon_html(THEME['icons']['ai_robot'])}\n"
            f"Estou aqui para te auxiliar com as **Normas Regulamentadoras** e diversos outros tópicos cruciais da área. {_get_material_icon_html(THEME['icons']['magic_pencil'])} Pode me perguntar sobre legislação, "
            f"boas práticas, dimensionamento e muito mais!\n\n"
            f"**Como posso te ajudar hoje?** {_get_material_icon_html(THEME['icons']['rocket_launch'])} Conte-me!"
        )
        st.session_state.messages.append({"role": "ai", "content": welcome_message})

    if "user_query_input" not in st.session_state:
        st.session_state.user_query_input = ""

    if "processed_documents" not in st.session_state:
        st.session_state.processed_documents = []
    if "dynamic_context_texts" not in st.session_state:
        st.session_state.dynamic_context_texts = []
    if "show_document_context_selector" not in st.session_state:
        st.session_state.show_document_context_selector = False
    if "active_context_files" not in st.session_state:
        st.session_state.active_context_files = []

    if 'last_donation_date' not in st.session_state:
        st.session_state['last_donation_date'] = date.min

    today = date.today()
    if st.session_state['last_donation_date'] != today:
        st.session_state['daily_donations_count'] = 0
        st.session_state['last_donation_date'] = today

    if "sync_central_library_in_progress" not in st.session_state:
        st.session_state.sync_central_library_in_progress = False
    if "sync_central_library_status" not in st.session_state:
        st.session_state.sync_central_library_status = ""
    if "sync_central_library_error" not in st.session_state:
        st.session_state.sync_central_library_error = False
    if "sync_central_library_progress" not in st.session_state:
        st.session_state.sync_central_library_progress = 0

    logger.info("_initialize_session_state_post_login concluído.")

def _render_sidebar_navigation_item(icon_name: str, label: str, page_key: str, current_page: str, is_neon_title: bool = False) -> None:
    """
    Renderiza um item de navegação da barra lateral como um link HTML customizado,
    usando ícones Material Symbols e destacando a página ativa.
    
    Args:
        icon_name: Nome do ícone Material Symbol
        label: Texto do label do item
        page_key: Chave da página para navegação
        current_page: Página atual ativa
        is_neon_title: Se deve aplicar efeito neon ao título
        
    Raises:
        None: Função não levanta exceções
    """
    is_active = (current_page == page_key)
    
    icon_html = _get_material_icon_html(icon_name)
    
    href = f"?page={page_key}"
    
    label_class = "neon-title" if is_neon_title else ""

    link_html = f"""
    <a href="{href}" class="sidebar-navigation-item {'active' if is_active else ''}" target="_self">
        {icon_html} <span class="{label_class}">{label}</span>
    </a>
    """
    st.markdown(link_html, unsafe_allow_html=True)

def _render_custom_expander(expander_id: str, icon_name: str, title: str, content_func) -> None:
    """
    Renderiza um expander customizado com ícones Material Symbols.
    
    Args:
        expander_id: ID único do expander
        icon_name: Nome do ícone Material Symbol
        title: Título do expander
        content_func: Função que renderiza o conteúdo do expander
        
    Raises:
        None: Função não levanta exceções
    """
    # Estado do expander
    if f"expander_{expander_id}_expanded" not in st.session_state:
        st.session_state[f"expander_{expander_id}_expanded"] = False
    
    # HTML do cabeçalho
    icon_html = _get_material_icon_html(icon_name)
    expanded_class = "expanded" if st.session_state[f"expander_{expander_id}_expanded"] else ""
    
    header_html = f"""
    <div class="custom-expander">
        <div class="custom-expander-header" onclick="toggleExpander('{expander_id}')">
            {icon_html} {title}
        </div>
        <div class="custom-expander-content {expanded_class}" id="content_{expander_id}">
    """
    
    st.markdown(header_html, unsafe_allow_html=True)
    
    # Renderizar conteúdo se expandido
    if st.session_state[f"expander_{expander_id}_expanded"]:
        content_func()
    
    st.markdown("</div></div>", unsafe_allow_html=True)
    
    # JavaScript para toggle
    st.markdown(f"""
    <script>
    function toggleExpander(expanderId) {{
        fetch(window.location.href, {{
            method: 'POST',
            headers: {{
                'Content-Type': 'application/json',
            }},
            body: JSON.stringify({{
                'action': 'toggle_expander',
                'expander_id': expanderId
            }})
        }});
    }}
    </script>
    """, unsafe_allow_html=True)

def _render_sidebar_menu() -> None:
    """
    Renderiza o menu lateral completo da aplicação.
    
    Raises:
        None: Função não levanta exceções
    """
    logger.info("Iniciando renderização da sidebar.")

    st.sidebar.markdown(f"""
        <div style='text-align: center; margin-bottom: 20px;'>
            <img src="{get_image_base64(THEME['images']['app_logo'])}" style='max-width: 150px; height: auto; display: block; margin: 0 auto;'>
        </div>
    """, unsafe_allow_html=True)

    st.sidebar.markdown(
        f'<h2 class="neon-title" style="text-align: center;">{_get_material_icon_html(THEME["icons"]["safety_shield"])} {THEME["phrases"]["app_title"]} {_get_material_icon_html(THEME["icons"]["safety_shield"])}</h2>',
        unsafe_allow_html=True
    )

    st.sidebar.markdown("<hr/>", unsafe_allow_html=True)

    current_page = st.session_state.get("current_page", "home")

    # Navegação Principal
    _render_sidebar_navigation_item(THEME['icons']['home_icon'], THEME['phrases']['home_page'], "home", current_page)
    _render_sidebar_navigation_item(THEME['icons']['chat_bubble'], THEME['phrases']['chat'], "chat", current_page)
    _render_sidebar_navigation_item(THEME['icons']['library_books'], THEME['phrases']['document_library'], "library", current_page)
    _render_sidebar_navigation_item(THEME['icons']['brain_gear'], THEME['phrases']['knowledge_base_page_title'], "knowledge_base", current_page)
    _render_sidebar_navigation_item(THEME['icons']['jobs_board'], THEME['phrases']['jobs_board'], "jobs_board", current_page)

    st.sidebar.markdown("<hr/>", unsafe_allow_html=True)

    # Consultas Rápidas - USANDO EXPANDER CUSTOMIZADO
    with st.sidebar:
        # Expander customizado para Consultas Rápidas
        st.markdown(f"""
            <div class="custom-expander">
                <div class="custom-expander-header" onclick="window.parent.postMessage({{type: 'streamlit:setComponentValue', value: {{key: 'toggle_quick_consults', value: true}}}}, '*')">
                    {_get_material_icon_html(THEME['icons']['search_magnifying_glass'])} {THEME['phrases']['quick_consults']}
                </div>
            </div>
        """, unsafe_allow_html=True)
        
        # Conteúdo das Consultas Rápidas
        with st.expander("", expanded=False):
            _render_sidebar_navigation_item(THEME['icons']['news_feed'], THEME['phrases']['news_feed'], "news_feed", current_page)
            _render_sidebar_navigation_item(THEME['icons']['cbo_consult'], THEME['phrases']['cbo_consult'], "cbo_consult", current_page)
            _render_sidebar_navigation_item(THEME['icons']['cid_consult'], THEME['phrases']['cid_consult'], "cid_consult", current_page)
            _render_sidebar_navigation_item(THEME['icons']['cnae_consult'], THEME['phrases']['cnae_consult'], "cnae_consult", current_page)
            _render_sidebar_navigation_item(THEME['icons']['ca_consult'], THEME['phrases']['ca_consult'], "ca_consult", current_page)
            _render_sidebar_navigation_item(THEME['icons']['fines_consult'], THEME['phrases']['fines_consult'], "fines_consult", current_page)
        
        # Expander customizado para Dimensionamentos
        st.markdown(f"""
            <div class="custom-expander">
                <div class="custom-expander-header" onclick="window.parent.postMessage({{type: 'streamlit:setComponentValue', value: {{key: 'toggle_sizing', value: true}}}}, '*')">
                    {_get_material_icon_html(THEME['icons']['calculator'])} {THEME['phrases']['sizing']}
                </div>
            </div>
        """, unsafe_allow_html=True)
        
        # Conteúdo dos Dimensionamentos
        with st.expander("", expanded=False):
            _render_sidebar_navigation_item(THEME['icons']['emergency_brigade'], THEME['phrases']['emergency_brigade_sizing'], "emergency_brigade_sizing", current_page)
            _render_sidebar_navigation_item(THEME['icons']['cipa_sizing'], THEME['phrases']['cipa_sizing'], "cipa_sizing", current_page)
    
    # Administração
    _render_sidebar_navigation_item(THEME['icons']['administration'], THEME['phrases']['administration'], "admin", current_page)
    _render_sidebar_navigation_item(THEME['icons']['settings'], THEME['phrases']['settings'], "settings", current_page)
    
    st.sidebar.markdown("<hr/>", unsafe_allow_html=True)
    
    # Logout
    if st.session_state.logged_in:
        _render_sidebar_navigation_item(THEME['icons']['logout'], THEME['phrases']['logout'], "logout_action", current_page)

    logger.info("Sidebar renderizada com sucesso.")

def main_app_entrypoint() -> None:
    """
    Ponto de entrada principal da aplicação.
    
    Raises:
        Exception: Para erros críticos na renderização
    """
    logger.info("Iniciando main_app_entrypoint.")

    # Carregamento de fontes e estilos
    st.markdown("""
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
        <link href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:opsz,wght,FILL,GRAD@20..48,100..700,0..1,-50..200" rel="stylesheet">
    """, unsafe_allow_html=True)
    
    st.markdown(GLOBAL_STYLES, unsafe_allow_html=True)

    _initialize_session_state_common()

    # Processamento de navegação via URL
    requested_page_from_url = None
    if "page" in st.query_params:
        requested_page_from_url = st.query_params["page"][0] if isinstance(st.query_params["page"], list) else st.query_params["page"]
        if requested_page_from_url == "logout_action":
            logger.info("Ação de logout detectada via query params. Executando logout.")
            do_logout()
            return

    if requested_page_from_url:
        valid_pages = [
            "home", "chat", "library", "knowledge_base", "jobs_board", 
            "news_feed", "cbo_consult", "cid_consult", "cnae_consult", 
            "ca_consult", "fines_consult", "emergency_brigade_sizing", 
            "cipa_sizing", "admin", "settings"
        ]
        if requested_page_from_url in valid_pages:
            st.session_state.current_page = requested_page_from_url
        else:
            logger.warning(f"Tentativa de navegar para página inválida via URL: {requested_page_from_url}")
            st.session_state.current_page = "home"
        st.query_params.clear()

    user_drive_service_result = get_user_drive_service_wrapper()

    # Tela de Login
    if not st.session_state.logged_in:
        logger.info("Usuário não logado. Renderizando interface da página de login.")

        logo_base64 = get_image_base64(THEME["images"]["app_logo"])
        background_base64 = get_image_base64(THEME["images"]["login_background"])

        show_redirect_uri_warning = os.getenv("SHOW_REDIRECT_URI_WARNING", "false").lower() in ("true", "1")

        redirect_info_html = ""
        if show_redirect_uri_warning and st.session_state.get('user_drive_auth_url'):
            redirect_info_html = f"""<div class='redirect-info'>Após a autorização, você será redirecionado de volta para esta página. Certifique-se de que o URL de redirecionamento no console do Google Cloud seja <code style='background-color:#30363d; padding: 2px 5px; border-radius: 3px;'>http://localhost:8501</code></div>"""
        elif st.session_state.get('user_drive_auth_error'):
            redirect_info_html = f"""<div class='error-info'>Erro na autenticação: {st.session_state.user_drive_auth_error}. Por favor, tente fazer login novamente.</div>"""
            st.session_state.user_drive_auth_error = None

        login_html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
                <meta name="viewport" content="width=device-width, initial-scale=1">
                <style>
                    body {{
                        margin: 0; padding: 0; height: 100vh; width: 100vw;
                        display: flex; align-items: center; justify-content: center;
                        font-family: 'Inter', sans-serif;
                        background-color: transparent;
                        color: #c9d1d9;
                        overflow: hidden;
                    }}
                    @keyframes neon-flicker {{
                        0%, 100% {{
                            text-shadow: 0 0 5px rgba(39, 174, 96, 0.4), 0 0 10px rgba(39, 174, 96, 0.4), 0 0 20px rgba(39, 174, 96, 0.4);
                            color: #27ae60;
                        }}
                        50% {{
                            text-shadow: 0 0 10px rgba(39, 174, 96, 0.4), 0 0 20px rgba(39, 174, 96, 0.4), 0 0 40px rgba(39, 174, 96, 0.4);
                            color: #39d353;
                        }}
                    }}
                    .neon-title {{
                        animation: neon-flicker 2s ease-in-out infinite alternate;
                        font-family: 'Inter', sans-serif;
                    }}
                    .material-symbols-outlined {{
                      font-variation-settings:
                      'FILL' 0,
                      'wght' 400,
                      'GRAD' 0,
                      'opsz' 24;
                      color: inherit;
                      font-size: inherit;
                      display: inline-block;
                      vertical-align: middle;
                      line-height: 1;
                      font-family: 'Material Symbols Outlined' !important;
                      -webkit-font-smoothing: antialiased;
                      text-rendering: optimizeLegibility;
                      white-space: nowrap;
                    }}
                    .login-card {{
                        background-color: rgba(22, 27, 34, 0.9);
                        border-radius: 15px;
                        padding: 40px;
                        text-align: center;
                        box-shadow: 0 10px 30px rgba(39, 174, 96, 0.3);
                        max-width: 600px;
                        width: 90%;
                        display: flex;
                        flex-direction: column;
                        align-items: center;
                        justify-content: center;
                        gap: 20px;
                        margin: 20px;
                        min-height: 300px;
                        box-sizing: border-box;
                    }}
                    @media (max-width: 480px) {{
                        .login-card {{
                            padding: 25px;
                            width: 95%;
                            margin: 10px;
                        }}
                        .login-card img.login-logo {{
                            max-width: 150px;
                        }}
                        h1 {{
                            font-size: 1.8em;
                        }}
                    }}
                    .login-card img.login-logo {{
                        margin-bottom: 0;
                        max-width: 200px;
                        height: auto;
                    }}
                    .google-login-button-container {{
                        width: 100%;
                        display: flex;
                        justify-content: center;
                        margin-top: 20px;
                    }}
                    .google-login-button {{
                        background-color: white;
                        border: 1px solid #ddd;
                        border-radius: 50%;
                        width: 50px;
                        height: 50px;
                        display: flex;
                        align-items: center;
                        justify-content: center;
                        cursor: pointer;
                        text-decoration: none;
                        transition: all 0.3s ease;
                        box-shadow: 0 2px 4px rgba(0,0,0,0.2);
                        padding: 0;
                    }}
                    .google-login-button:hover {{
                        background-color: #f0f0f0;
                        box-shadow: 0 4px 8px rgba(0,0,0,0.3);
                    }}
                    .google-login-button img {{
                        height: 30px;
                        width: 30px;
                        margin: 0;
                    }}
                    .redirect-info, .error-info {{
                        background-color: #161b22;
                        padding: 15px;
                        border-radius: 5px;
                        margin-top: 15px;
                        font-size: 0.9em;
                        text-align: left;
                        width: calc(100% - 30px);
                        color: #c9d1d9;
                        box-sizing: border-box;
                    }}
                    .redirect-info {{
                        border-left: 5px solid #56d364;
                    }}
                    .error-info {{
                        border-left: 5px solid #f85149;
                    }}
                    h1 {{
                        text-align: center;
                        margin-bottom: 25px;
                        font-size: 2.5em;
                        color: {THEME['colors']['text_primary']};
                        font-family: 'Inter', sans-serif;
                    }}
                    p {{
                        color: {THEME['colors']['text_primary']};
                        text-align: center;
                    }}
                </style>
                <link href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:opsz,wght,FILL,GRAD@20..48,100..700,0..1,-50..200" rel="stylesheet">
            </head>
            <body>
                <div class='login-card'>
                    <img src='{logo_base64}' alt='App Logo' class='login-logo'>
                    <h1 class='neon-title'>{THEME['phrases']['welcome_login']}</h1>
                    <p>{THEME['phrases']['login_prompt']}</p>
                    {redirect_info_html}
                    <div class='google-login-button-container'>
                        <a href='{st.session_state.user_drive_auth_url if st.session_state.get('user_drive_auth_url') else "#"}'
                           target='_blank'
                           class='google-login-button'
                           onclick="
                             if(this.href === '#') {{
                               window.parent.postMessage({{ type: 'streamlit:setComponentValue', value: {{ key: 'trigger_login_flow_rerun_from_iframe', value: true }} }}, '*');
                               return false;
                             }}
                           ">
                            <img src='https://www.gstatic.com/images/branding/product/1x/gsa_48dp.png' alt='Google G Logo'>
                        </a>
                    </div>
                </div>
                <script>
                    const parentHtml = window.parent.document.documentElement;
                    const parentBody = window.parent.document.body;

                    parentHtml.classList.add('streamlit-login-page');
                    parentBody.classList.add('streamlit-login-page');

                    const bgBase64 = '{background_base64}';
                    if (bgBase64) {{
                        parentHtml.style.backgroundImage = 'url("{background_base64}")';
                        parentHtml.style.backgroundSize = 'cover';
                        parentHtml.style.backgroundPosition = 'center';
                                                parentHtml.style.backgroundAttachment = 'fixed';
                        parentHtml.style.filter = 'blur(0px)';
                        parentHtml.style.backgroundColor = '#0d1117';
                        
                        parentBody.style.backgroundImage = 'url("{background_base64}")';
                        parentBody.style.backgroundSize = 'cover';
                                                parentBody.style.backgroundPosition = 'center';
                        parentBody.style.backgroundAttachment = 'fixed';
                        parentBody.style.filter = 'blur(0px)';
                        parentBody.style.backgroundColor = '#0d1117';
                    }}
                </script>
            </body>
            </html>
        """
        components.html(
            login_html_content,
            height=650,
            scrolling=False
        )

        if st.session_state.trigger_login_flow_rerun_from_iframe:
            logger.info("Trigger de rerun recebido do iframe do login.")
            st.session_state.trigger_login_flow_rerun_from_iframe = False 
            get_user_drive_service_wrapper()
            st.rerun()

        return

    # Aplicação Principal (Usuário Logado)
    logger.info("Usuário logado e serviço do Drive disponível. Prosseguindo para o aplicativo principal.")

    # Limpeza de estilos de login
    st.markdown(f"""
        <script>
            const parentHtml = window.parent.document.documentElement;
            const parentBody = window.parent.document.body;

            parentHtml.classList.remove('streamlit-login-page');
            parentBody.classList.remove('streamlit-login-page');

            parentHtml.style.backgroundImage = '';
            parentHtml.style.backgroundSize = '';
            parentHtml.style.backgroundPosition = '';
            parentHtml.style.backgroundAttachment = '';
            parentHtml.style.filter = '';
            parentHtml.style.backgroundColor = '#0d1117';

            parentBody.style.backgroundImage = '';
            parentBody.style.backgroundSize = '';
            parentBody.style.backgroundPosition = '';
            parentBody.style.backgroundAttachment = '';
            parentBody.style.filter = '';
            parentBody.style.backgroundColor = '#0d1117';
        </script>
    """, unsafe_allow_html=True)
    
    if st.session_state.nav_request:
        if st.session_state.nav_request == "logout_action":
            do_logout()
        st.session_state.nav_request = ""

    logger.info("Executando _initialize_session_state_post_login para usuário logado.")
    _initialize_session_state_post_login()

    # Renderização da Sidebar
    with st.sidebar:
        _render_sidebar_menu()

    # Roteamento de Páginas
    current_page = st.session_state.current_page
    logger.info(f"Roteando para a página: {current_page}")
    try:
        if current_page == "home":
            render_home_page()
        elif current_page == "chat":
            render_chat_page(process_markdown_for_external_links_func=process_markdown_for_external_links)
        elif current_page == "library":
            render_library_page()
        elif current_page == "knowledge_base":
            render_knowledge_base_page()
        elif current_page == "jobs_board":
            render_jobs_board_page()
        elif current_page in ["news_feed", "cbo_consult", "cid_consult", "cnae_consult", "ca_consult", "fines_consult", "emergency_brigade_sizing", "cipa_sizing", "admin", "settings"]:
            page_title = THEME["phrases"].get(current_page, current_page.replace('_', ' ').title())
            
            # MAPEAMENTO CORRETO DE ÍCONES PARA PÁGINAS
            page_icons_map = {
                "news_feed": "news_feed",
                "cbo_consult": "cbo_consult", 
                "cid_consult": "cid_consult",
                "cnae_consult": "cnae_consult",
                "ca_consult": "ca_consult",
                "fines_consult": "fines_consult",
                "emergency_brigade_sizing": "emergency_brigade",
                "cipa_sizing": "cipa_sizing",
                "admin": "administration",
                "settings": "settings"
            }
            
            page_icon = page_icons_map.get(current_page, "generic_info")
            page_icon_html = _get_material_icon_html(THEME['icons'][page_icon])
            st.markdown(f'<h1 class="neon-title">{page_icon_html} {page_title}</h1>', unsafe_allow_html=True)
            st.markdown(f"<p style='color:{THEME['colors']['text_primary']}; text-align:center;'>Esta seção está em desenvolvimento.</p>", unsafe_allow_html=True)
        elif current_page == "logout_action":
            do_logout()
        else:
            st.session_state.current_page = "home"
            st.rerun()
        logger.info(f"Página '{current_page}' renderizada com sucesso.")
    except Exception as e:
        logger.critical(f"[ERRO CRÍTICO] Erro inesperado ao renderizar a página '{current_page}': {e}. Tipo: {type(e).__name__}")
        st.error(f"Erro crítico ao renderizar a página '{current_page}'. Detalhes: {e}")
        # st.stop() # Comentado para permitir funcionamento sem RAG

if __name__ == "__main__":
    main_app_entrypoint()
