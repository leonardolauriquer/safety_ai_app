import logging

logger = logging.getLogger(__name__)

GLOBAL_STYLES = """
<style>
html, body {
    margin: 0;
    padding: 0;
    height: 100vh;
    width: 100vw;
    overflow-x: hidden !important;
    font-family: 'Inter', sans-serif;
    background-color: #0d1117 !important;
}

@keyframes neon-flicker {
    0%, 100% {
        text-shadow:
            0 0 5px rgba(39, 174, 96, 0.4),
            0 0 10px rgba(39, 174, 96, 0.4),
            0 0 20px rgba(39, 174, 96, 0.4);
        color: #27ae60;
    }
    50% {
        text-shadow:
            0 0 10px rgba(39, 174, 96, 0.4),
            0 0 20px rgba(39, 174, 96, 0.4),
            0 0 40px rgba(39, 174, 96, 0.4);
            color: #39d353;
    }
}

.neon-title {
    animation: neon-flicker 2s ease-in-out infinite alternate;
    font-family: 'Inter', sans-serif;
}

.material-symbols-outlined {
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
}

.stApp {
    color: #c9d1d9;
    font-family: 'Inter', sans-serif;
    position: relative;
    min-height: 100vh;
    width: 100vw;
    background-color: transparent !important;
    padding: 0 !important;
    margin: 0 !important;
    max-width: 100vw !important;
}

header, footer {
    display: none !important;
}

/* Estilos de login */
html.streamlit-login-page, body.streamlit-login-page {
    overflow-y: hidden !important;
    background-color: transparent !important;
}

.stApp.streamlit-login-page [data-testid="stAppViewContainer"] {
    padding: 0 !important;
    margin: 0 !important;
    width: 100% !important;
    max-width: 100% !important;
    min-height: 100vh !important;
    overflow-y: hidden !important;
    background-color: transparent !important;
}

.stApp.streamlit-login-page [data-testid="stVerticalBlock"],
.stApp.streamlit-login-page [data-testid="stHorizontalBlock"] {
    padding: 0 !important;
    margin: 0 !important;
    width: 100% !important;
    max-width: 100% !important;
}

.stApp.streamlit-login-page main {
    padding: 0 !important;
    margin: 0 !important;
    width: 100% !important;
    max-width: 100% !important;
    min-height: 100vh !important;
    display: flex !important;
    flex-direction: column !important;
    align-items: center !important;
    justify-content: center !important;
    background-color: transparent !important;
}

.stApp.streamlit-login-page [data-testid="stSidebar"],
.stApp.streamlit-login-page [data-testid="stHeader"] {
    display: none !important;
}

/* Estilos do app principal */
html:not(.streamlit-login-page), body:not(.streamlit-login-page) {
    overflow-y: auto !important;
    background-color: #0d1117 !important;
    background-image: none !important;
    filter: none !important;
}

.stApp:not(.streamlit-login-page) {
    padding: 15px !important;
    overflow-y: auto !important;
    background-color: #0d1117 !important;
}
.stApp:not(.streamlit-login-page) [data-testid="stAppViewContainer"] {
    background-color: #0d1117 !important;
}
.stApp:not(.streamlit-login-page) main {
    justify-content: flex-start !important;
    padding: 15px !important;
    overflow-y: auto !important;
    background-color: transparent !important;
}
.stApp:not(.streamlit-login-page) header,
.stApp:not(.streamlit-login-page) footer {
    display: block !important;
}

h1 {
    text-align: center;
    margin-bottom: 25px;
    font-size: 2.5em;
    color: #c9d1d9;
    font-family: 'Inter', sans-serif;
}
h2, h3, h4, h5, h6 {
    color: #27ae60;
    text-align: left;
    border-bottom: 2px solid #30363d;
    padding-bottom: 10px;
    margin-top: 30px;
    margin-bottom: 20px;
    font-family: 'Inter', sans-serif;
}
.stSidebar h2.neon-title {
    text-align: center;
    border-bottom: none;
    padding-bottom: 0;
    margin-top: 0;
    margin-bottom: 20px;
    color: #c9d1d9;
}

/* Estilos de botões Streamlit (geral) */
div[data-testid*="stButton"] > button,
div[data-testid*="stDownloadButton"] > button {
    background-color: #27ae60;
    color: #c9d1d9;
    border-radius: 8px;
    border: 1px solid #27ae60;
    padding: 12px 25px;
    font-weight: bold;
    transition: all 0.3s ease;
    box-shadow: 0 0 15px rgba(39, 174, 96, 0.4);
    cursor: pointer;
    width: fit-content;
    font-family: 'Inter', sans-serif;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
}
div[data-testid*="stButton"] > button:hover,
div[data-testid*="stDownloadButton"] > button:hover {
    background-color: #39d353;
    border-color: #39d353;
    box-shadow: 0 0 20px rgba(39, 174, 96, 0.4);
    transform: translateY(-2px);
}
div[data-testid*="stButton"] > button:disabled,
div[data-testid*="stDownloadButton"] > button:disabled {
    cursor: not-allowed !important;
    opacity: 0.6 !important;
    transform: none !important;
    box-shadow: none !important;
}

/* Estilo específico para st.download_button */
div[data-testid^="stDownloadButton-"] > button {
    background-color: #30363d !important;
    color: #c9d1d9 !important;
    border: 1px solid #30363d !important;
    padding: 8px 15px !important;
    border-radius: 5px !important;
    font-weight: normal !important;
    box-shadow: none !important;
    width: fit-content !important;
    height: 28px !important;
    font-size: 0.8em !important;
}

div[data-testid^="stDownloadButton-"] > button:hover:not(:disabled) {
    background-color: #161b22 !important;
    border-color: #27ae60 !important;
    color: #39d353 !important;
    transform: translateY(-1px) !important;
}

/* Estilos para itens de navegação customizados na sidebar */
.sidebar-navigation-item {
    display: flex;
    align-items: center;
    width: 100%;
    padding: 0.75rem 1rem;
    margin-bottom: 0.25rem;
    border-radius: 0.5rem;
    text-decoration: none !important;
    color: #c9d1d9 !important;
    background-color: transparent !important;
    border: none;
    cursor: pointer;
    transition: background-color 0.2s, color 0.2s, border-left 0.2s;
    font-family: 'Inter', sans-serif;
    font-size: 1rem;
    font-weight: 400;
}
.sidebar-navigation-item:hover {
    background-color: #161b22 !important;
    color: #39d353 !important;
}
.sidebar-navigation-item.active {
    background-color: #30363d !important;
    color: #27ae60 !important;
    border-left: 3px solid #27ae60 !important;
    padding-left: calc(1rem - 3px);
}
.sidebar-navigation-item .material-symbols-outlined {
    margin-right: 0.75rem;
    font-size: 1.25rem;
    color: inherit !important;
    font-family: 'Material Symbols Outlined' !important;
}
.sidebar-navigation-item span:not(.material-symbols-outlined) {
    color: inherit !important;
}

/* Estilos para expanders customizados */
.custom-expander {
    margin-bottom: 10px;
}

.custom-expander-header {
    cursor: pointer;
    padding: 8px 12px;
    background-color: #30363d;
    border-radius: 5px;
    margin-bottom: 5px;
    display: flex;
    align-items: center;
    gap: 8px;
    color: #c9d1d9;
    font-family: 'Inter', sans-serif;
    font-size: 1rem;
    font-weight: 400;
    transition: background-color 0.2s ease;
}

.custom-expander-header:hover {
    background-color: #484f58;
}

.custom-expander-content {
    padding-left: 20px;
    margin-top: 5px;
    display: none;
}

.custom-expander-content.expanded {
    display: block;
}

/* Botões apenas com ícone (icon_only_) */
div[data-testid*="stButton-icon_only_"] > button {
    background-color: #30363d !important;
    border: none !important;
    border-radius: 50% !important;
    width: 45px !important;
    min-width: 45px !important;
    height: 45px !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    color: #c9d1d9 !important;
    font-size: 1.3em !important;
    cursor: pointer !important;
    transition: all 0.2s ease !important;
    box-shadow: none !important;
    flex-shrink: 0;
    padding: 0 !important;
    line-height: 1 !important;
}
div[data-testid*="stButton-icon_only_"] > button:hover:not(:disabled) {
    background-color: #484f58 !important;
    color: #27ae60 !important;
    transform: translateY(-1px) !important;
}

/* Botões small_action_ */
div[data-testid*="stButton-small_action_"] > button,
div[data-testid*="stDownloadButton-small_action_"] > button {
    background-color: #30363d !important;
    color: #c9d1d9 !important;
    border: 1px solid #30363d !important;
    padding: 8px 15px !important;
    border-radius: 5px !important;
    font-weight: normal !important;
    box-shadow: none !important;
    transition: all 0.2s ease !important;
    width: fit-content !important;
    height: 28px !important;
    font-size: 0.8em !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    gap: 5px !important;
}
div[data-testid*="stButton-small_action_"] > button:hover:not(:disabled),
div[data-testid*="stDownloadButton-small_action_"] > button:hover:not(:disabled) {
    background-color: #161b22 !important;
    border-color: #27ae60 !important;
    color: #39d353 !important;
    transform: translateY(-1px) !important;
}

/* Botões full_width_action_ */
div[data-testid*="stButton-full_width_action_"] > button,
div[data-testid*="stDownloadButton-full_width_action_"] > button {
    background-color: #30363d !important;
    color: #c9d1d9 !important;
    border: 1px solid #30363d !important;
    padding: 10px 20px !important;
    border-radius: 8px !important;
    font-weight: 500 !important;
    box-shadow: 0 2px 5px rgba(0, 0, 0, 0.2) !important;
    transition: all 0.2s ease !important;
    width: 100% !important;
    font-size: 1em !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    gap: 8px !important;
    line-height: 1 !important;
}

div[data-testid*="stButton-full_width_action_"] > button:hover:not(:disabled),
div[data-testid*="stDownloadButton-full_width_action_"] > button:hover:not(:disabled) {
    background-color: #484f58 !important;
    border-color: #27ae60 !important;
    color: #39d353 !important;
    transform: translateY(-2px) !important;
    box-shadow: 0 4px 8px rgba(0, 0, 0, 0.3) !important;
}

/* Estilos para o Streamlit Form submit button (chat input) */
.stForm > div > div > button[data-testid="stFormSubmitButton"] {
    background-color: #30363d !important;
    border: none !important;
    border-radius: 50% !important;
    width: 45px !important;
    min-width: 45px !important;
    height: 45px !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    color: #c9d1d9 !important;
    font-size: 1.3em !important;
    cursor: pointer !important;
    transition: all 0.2s ease !important;
    box-shadow: none !important;
    flex-shrink: 0;
    padding: 0 !important;
    line-height: 1 !important;
}
.stForm > div > div > button[data-testid="stFormSubmitButton"]:hover {
    background-color: #484f58 !important;
    color: #27ae60 !important;
    transform: translateY(-1px) !important;
}
/* O ícone para o botão de enviar do chat será definido diretamente via o parâmetro 'icon' do Streamlit,
   usando o shortcode ':material/send:'. Portanto, removemos qualquer pseudo-elemento CSS aqui. */
.stForm > div > div > button[data-testid="stFormSubmitButton"]::before {
    content: none !important; 
    margin-right: 0 !important; 
}


.stForm {
    margin: 0 !important;
    display: flex;
    align-items: center;
    gap: 8px;
}
.stForm > div > div > div[data-testid^="stTextInput"] {
     flex-grow: 1;
     margin-bottom: 0 !important;
}

.stFileUploader {
    background-color: #30363d;
    border: 1px dashed #30363d;
    border-radius: 10px;
    padding: 15px;
    margin-top: 15px;
    margin-left: auto;
    margin-right: auto;
    width: 100%;
}
.stFileUploader label p {
    color: #8b949e;
    font-size: 0.9em;
    margin-bottom: 0;
}
.stFileUploader > div {
    justify-content: center;
}

.drive-selector-area {
    background-color: #161b22;
    border: 1px solid #30363d;
    border-radius: 10px;
    padding: 15px;
    margin-top: 15px;
    box-shadow: 0 0 10px rgba(0,0,0,0.1);
    font-family: 'Inter', sans-serif;
}
.drive-selector-area h3 {
    border-bottom: none;
    margin-top: 0;
    padding-bottom: 0;
}

/* Botões de navegação "Voltar" (back_button_) */
div[data-testid*="stButton-back_button_"] > button {
    background-color: transparent !important;
    color: #8b949e !important;
    border: 1px solid #30363d !important;
    padding: 8px 15px !important;
    border-radius: 5px !important;
    font-weight: normal !important;
    box-shadow: none !important;
    width: fit-content !important;
    margin-top: 20px;
    font-family: 'Inter', sans-serif;
}
div[data-testid*="stButton-back_button_"] > button:hover {
    background-color: #161b22 !important;
    border-color: #27ae60 !important;
    color: #39d353 !important;
    transform: translateY(-1px) !important;
}

/* Estilos para o Streamlit Tab Component */
.stTabs [data-testid="stTab"] button {
    background-color: #161b22;
    color: #8b949e;
    border-radius: 5px 5px 0 0;
    border: 1px solid #30363d;
    border-bottom: none;
    margin-right: 5px;
    padding: 10px 15px;
    font-weight: 500;
    transition: all 0.2s ease;
    font-family: 'Inter', sans-serif;
}
.stTabs [data-testid="stTab"] button:hover {
    color: #39d353;
    background-color: #30363d;
}
.stTabs [data-testid="stTab"] button[aria-selected="true"] {
    background-color: #0d1117;
    color: #27ae60;
    border-top: 2px solid #27ae60;
    border-left-color: #27ae60;
    border-right-color: #27ae60;
    font-weight: 600;
    margin-top: -1px;
}
.stTabs [data-testid="stTabContent"] {
    background-color: #0d1117;
    border: 1px solid #30363d;
    border-top: none;
    border-radius: 0 0 10px 10px;
    padding: 20px;
    font-family: 'Inter', sans-serif;
}

/* Regras para remover motion/fade-out de mensagens e spinners do Streamlit */
.stAlert, .stSpinner,
.stToast, .stProgress,
.stStatus, .stSuccess, .stError, .stWarning, .stInfo {
    transition: none !important;
    animation: none !important;
}
.stAlert > div, .stSpinner > div,
.stToast > div, .stProgress > div,
.stStatus > div, .stSuccess > div, .stError > div, .stWarning > div > div {
    transition: none !important;
    animation: none !important;
}
.stAlert > div > *, .stSpinner > div > *,
.stToast > div > *, .stProgress > div > *,
.stStatus > div > *, .stSuccess > div > *, .stError > div > *, .stWarning > div > * {
    transition: none !important;
    animation: none !important;
}

/* Estilos para mensagens auxiliares via markdown */
.st-info-like {
    background-color: var(--st-info-background-color);
    color: var(--st-info-text-color);
    border-left: 5px solid var(--st-info-border-color);
    padding: 1rem;
    margin-bottom: 1rem;
    border-radius: 0.5rem;
    display: flex;
    align-items: center;
    gap: 0.5rem;
}
.st-warning-like {
    background-color: var(--st-warning-background-color);
    color: var(--st-warning-text-color);
    border-left: 5px solid var(--st-warning-border-color);
    padding: 1rem;
    margin-bottom: 1rem;
    border-radius: 0.5rem;
    display: flex;
    align-items: center;
    gap: 0.5rem;
}
.st-success-like {
    background-color: var(--st-success-background-color);
    color: var(--st-success-text-color);
    border-left: 5px solid var(--st-success-border-color);
    padding: 1rem;
    margin-bottom: 1rem;
    border-radius: 0.5rem;
    display: flex;
    align-items: center;
    gap: 0.5rem;
}
.st-error-like {
    background-color: var(--st-error-background-color);
    color: var(--st-error-text-color);
    border-left: 5px solid var(--st-error-border-color);
    padding: 1rem;
    margin-bottom: 1rem;
    border-radius: 0.5rem;
    display: flex;
    align-items: center;
    gap: 0.5rem;
}

/* Estilos para o spinner */
.stSpinner > div > div > span {
    display: flex;
    align-items: center;
    gap: 0.5rem;
}

</style>
"""

THEME = {
    "colors": {
        "background_primary": "#0d1117",
        "background_secondary": "#161b22",
        "text_primary": "#c9d1d9",
        "text_secondary": "#8b949e",
        "accent_green": "#27ae60",
        "accent_green_hover": "#39d353",
        "accent_green_shadow": "rgba(39, 174, 96, 0.4)",
        "input_background": "#30363d",
        "border_color": "#30363d",
        "user_message_bg": "#27ae60",
        "ai_message_bg": "#30363d",
        "info_border": "#56d364",
        "error_border": "#f85149",
        "button_action_text": "#c9d1d9",
        "button_action_hover": "#484f58",
        "--st-info-background-color": "rgba(10, 191, 198, 0.1)",
        "--st-info-text-color": "#53bdfd",
        "--st-info-border-color": "#53bdfd",
        "--st-warning-background-color": "rgba(255, 171, 0, 0.1)",
        "--st-warning-text-color": "#ffbe27",
        "--st-warning-border-color": "#ffbe27",
        "--st-success-background-color": "rgba(46, 204, 113, 0.1)",
        "--st-success-text-color": "#27ae60",
        "--st-success-border-color": "#27ae60",
        "--st-error-background-color": "rgba(255, 71, 87, 0.1)",
        "--st-error-text-color": "#e74c3c",
        "--st-error-border-color": "#e74c3c",
    },
    "fonts": {
        "primary_family": "Inter, sans-serif",
        "primary_url": "https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap"
    },
    "icons": {
        # NAVEGAÇÃO PRINCIPAL - ÍCONES CONTEXTUAIS CORRETOS
        "safety_shield": "security",                 # Safety AI - SST (segurança)
        "home_icon": "home",                         # Início
        "chat_bubble": "chat",                       # Chat (conversa)
        "library_books": "library_books",            # Biblioteca de Documentos
        "brain_gear": "psychology",                  # Base de Conhecimento (IA/cérebro)
        "jobs_board": "work",                        # Vagas
        
        # CONSULTAS RÁPIDAS - ÍCONES CONTEXTUAIS
        "news_feed": "feed",                         # Feed de Notícias
        "cbo_consult": "work_history",               # Consulta CBO (histórico profissional)
        "cid_consult": "medical_services",           # Consulta CID (serviços médicos)
        "cnae_consult": "business",                  # Consulta CNAE (negócios/empresas)
        "ca_consult": "verified",                    # Consulta CA (certificado/verificado)
        "fines_consult": "gavel",                    # Consulta de Multas (martelo judicial)
        
        # DIMENSIONAMENTOS - ÍCONES CONTEXTUAIS
        "emergency_brigade": "local_fire_department", # Brigada de Emergência (bombeiros)
        "cipa_sizing": "groups",                     # CIPA (grupos de pessoas)
        
        # ADMINISTRAÇÃO
        "administration": "admin_panel_settings",    # Administração
        "settings": "settings",                      # Configurações
        "logout": "logout",                          # Sair
        
        # ÍCONES FUNCIONAIS (mantidos do original)
        "ai_robot": "smart_toy",                     # Robot/IA (brinquedo inteligente)
        "back_arrow": "arrow_back",
        "magic_pencil": "edit",
        "microphone": "mic",
        "folder_docs": "folder_open",
        "image_frame": "image",
        "send_arrow": "send",
        "waving_hand": "waving_hand",
        "sparkle": "auto_awesome",                   # Sparkle/brilho (auto impressionante)
        "file_doc": "description",
        "download_arrow": "download",
        "loading_hourglass": "hourglass_empty",
        "save_disk": "save",
        "success_check": "check_circle",
        "error_x": "cancel",
        "donation_hands": "volunteer_activism",
        "upload_arrow": "upload",
        "upload_folder": "folder_upload",
        "document": "article",
        "file_document": "description",
        "document_stack": "library_books",
        "rocket_launch": "rocket_launch",
        "medical_services": "medical_services",
        "apartment": "apartment",
        "policy": "policy",
        "fire_truck": "fire_truck",
        "construction": "construction",
        "sync": "sync",
        "login_key": "vpn_key",
        "logout_icon": "logout",
        "arrow_left": "arrow_back",
        "arrow_right": "arrow_forward",
        "delete_trash": "delete",
        "warning_sign": "warning",
        "generic_info": "info",
        "bulb": "lightbulb",
        "info_circular_outline": "info",
        "user_profile": "person",
        "health_cross": "medical_services",
        "building": "business",
        "certified": "verified",
        "group": "groups",
        "tools": "build",
        "search_magnifying_glass": "search",
        "calculator": "calculate",
        "emergency_light": "emergency",
        "news_paper": "newspaper",
        
        # SEÇÕES ESPECÍFICAS - ÍCONES CONTEXTUAIS
        "quick_consults": "search",                  # Consultas Rápidas
        "sizing": "calculate",                       # Dimensionamentos
        "emergency_brigade_sizing": "local_fire_department", # Dimensionamento de Brigada
        "cipa_sizing": "groups",                     # Dimensionamento da CIPA
        
        # ÍCONES ADICIONAIS PARA CHAT - CONTEXTUAIS
        "tune": "tune",                              # Ajustes/configurações
        "visibility": "visibility",                  # Visibilidade
        "visibility_off": "visibility_off",          # Ocultar
        "refresh": "refresh",                        # Atualizar
        "clear": "clear",                            # Limpar
        "add": "add",                                # Adicionar
        "remove": "remove",                          # Remover
        "check": "check",                            # Confirmar
        "close": "close",                            # Fechar
        "expand_more": "expand_more",                # Expandir
        "expand_less": "expand_less",                # Recolher
        
        # ÍCONES ESPECÍFICOS PARA LIBRARY_PAGE
        "security": "security",                      # Segurança/Verificação
        "history": "history",                        # Histórico
        "chart_bar": "bar_chart",                    # Estatísticas/Gráficos
    },
    "material_symbols_unicodes": {
        # NAVEGAÇÃO PRINCIPAL - ÍCONES CONTEXTUAIS CORRETOS
        "security": "\ue32a",                        # Safety AI - SST (segurança)
        "chat": "\ue0b7",                            # Chat (conversa)
        "library_books": "\ue8c3",                   # Biblioteca de Documentos
        "psychology": "\ue9e8",                      # Base de conhecimento/IA
        
        # CONSULTAS RÁPIDAS - ÍCONES CONTEXTUAIS
        "work_history": "\ue85a",                    # CBO (histórico profissional)
        "medical_services": "\ue31f",                # CID (serviços médicos)
        "business": "\ue0af",                        # CNAE (negócios/empresas)
        "verified": "\ue8e8",                        # CA (certificado/verificado)
        
        # DIMENSIONAMENTOS - ÍCONES CONTEXTUAIS
        "local_fire_department": "\ue8c4",           # Brigada de Emergência (bombeiros)
        "groups": "\ue7f0",                          # CIPA (grupos de pessoas)
        
        # ADMINISTRAÇÃO - ÍCONES ESPECÍFICOS
        "admin_panel_settings": "\ue8c9",            # Administração
        
        # ÍCONES EXISTENTES (mantidos e corrigidos)
        "smart_toy": "\ue90e",                       # Robot/IA (brinquedo inteligente)
        "arrow_back": "\ue5c4",
        "edit": "\ue254",
        "mic": "\ue029",
        "folder_open": "\ue2c8",
        "image": "\ue3b0",
        "settings": "\ue8b8",
        "send": "\ue163",
        "description": "\ue871",
        "download": "\ue2c0",
        "hourglass_empty": "\ue87b",
        "save": "\ue161",
        "check_circle": "\ue86c",
        "cancel": "\ue5c9",
        "volunteer_activism": "\ueb49",
        "upload": "\ue2c6",
        "folder_upload": "\ue2c7",
        "article": "\ue871",
        "rocket_launch": "\ue9b5",
        "work": "\ue8f9",
        "apartment": "\ue300",
        "policy": "\ueac0",
        "gavel": "\ue912",
        "fire_truck": "\ue524",
        "construction": "\ueb0c",
        "sync": "\ue627",
        "feed": "\ue8ad",
        "vpn_key": "\ue0da",
        "logout": "\ue9ba",
        "arrow_forward": "\ue5c8",
        "delete": "\ue872",
        "warning": "\ue002",
        "info": "\ue88e",
        "home": "\ue88a",
        "lightbulb": "\ue0f0",
        "person": "\ue7fd",
        "build": "\ue869",
        "search": "\ue8b6",
        "calculate": "\ue8b2",
        "emergency": "\ue1eb",
        "newspaper": "\ue9a0",
        "waving_hand": "\ue787",
        "auto_awesome": "\ue65f",                     # Sparkle/brilho (auto impressionante)
        
        # ÍCONES ADICIONAIS PARA CHAT
        "tune": "\ue429",                            # Ajustes/configurações
        "visibility": "\ue8f4",                      # Visibilidade
        "visibility_off": "\ue8f5",                  # Ocultar
        "refresh": "\ue5d5",                         # Atualizar
        "clear": "\ue14c",                           # Limpar
        "add": "\ue145",                             # Adicionar
        "remove": "\ue15b",                          # Remover
        "check": "\ue5ca",                           # Confirmar
        "close": "\ue5cd",                           # Fechar
        "expand_more": "\ue5cf",                     # Expandir
        "expand_less": "\ue5ce",                     # Recolher
        
        # ÍCONES ESPECÍFICOS PARA LIBRARY_PAGE
        "history": "\ue889",                         # Histórico
        "bar_chart": "\ue26b",                       # Estatísticas/Gráficos
    },
    "phrases": {
        "app_title": "Safety AI - SST",
        "back_to_home": "Voltar para a Página Inicial",
        "chat_with_ai": "Chat com Especialista em SST", 
        "document_library": "Biblioteca de Documentos",
        "refine_edit": "Refinar e Editar",
        "audio_to_text": "Áudio para Texto",
        "use_docs_context": "Usar documentos como contexto",
        "analyze_image": "Analisar Imagem",
        "generate_content": "Gerar Conteúdo",
        "default_placeholder": "Faça qualquer pergunta relacionada a SST...",
        "footer_text": "<span class='material-symbols-outlined'>smart_toy</span> Desenvolvido com IA <span class='material-symbols-outlined'>smart_toy</span> por Eng. Leonardo Lauriquer Ribeiro - Focado em um futuro mais seguro.",
        "chat": "Chat",
        "chat_page_title": "Chat com Especialista em SST",
        "knowledge_base_ai": "Base de Conhecimento",
        "news_feed": "Feed de Notícias",
        "jobs_board": "Vagas",
        "login_button": "Entrar com Google",
        "welcome_login": "Bem-vindo(a) ao SafetyAI!",
        "login_prompt": "Por favor, faça login com sua conta Google para continuar.",
        "cbo_consult": "Consulta CBO",
        "cid_consult": "Consulta CID",
        "cnae_consult": "Consulta CNAE",
        "ca_consult": "Consulta CA",
        "fines_consult": "Consulta de Multas",
        "emergency_brigade_sizing": "Dimensionamento de Brigada de Emergência",
        "cipa_sizing": "Dimensionamento da CIPA",
        "knowledge_base_description": "Aqui você adiciona e gerencia os documentos que o SafetyAI utiliza como base para responder às suas perguntas. Mantenha sua base de conhecimento atualizada para respostas mais precisas!",
        "welcome_message": "Bem-vindo(a) ao SafetyAI!",
        "our_tools_title": "Nossas ferramentas incluem:",
        "chat_smart": "Chat Inteligente",
        "document_management": "Gerenciamento de Documentos",
        "news_and_notices": "Notícias e Avisos",
        "tip_sidebar_navigation": "Dica: Use o menu lateral para navegar entre as seções do aplicativo.",
        "home_page": "Início",
        "administration": "Administração",
        "settings": "Configurações",
        "logout": "Sair",
        "quick_consults": "Consultas Rápidas",
        "sizing": "Dimensionamentos",
        "knowledge_base_page_title": "Base de Conhecimento",
        "admin": "Administração",
    },
    "images": {
        "login_background": "assets/login_background.jpg",
        "app_logo": "assets/app_logo.png",
        "page_icon": "assets/icon_logo.png",
    }
}

def _get_material_icon_html(icon_key: str) -> str:
    """
    Retorna o HTML para um ícone Material Symbol baseado na chave, usando seu caractere Unicode.
    
    Args:
        icon_key: Chave do ícone no dicionário THEME['material_symbols_unicodes']
        
    Returns:
        str: HTML do ícone Material Symbol
        
    Raises:
        None: Usa fallback em caso de erro
    """
    icon_char = THEME['material_symbols_unicodes'].get(icon_key)
    if not icon_char:
        logger.warning(f"Material Symbol '{icon_key}' not found in THEME['material_symbols_unicodes']. Falling back to 'info'.")
        icon_char = THEME['material_symbols_unicodes'].get('info', '\u2139')

    if not isinstance(icon_char, str) or len(icon_char) != 1:
        logger.error(f"Fallback icon for '{icon_key}' is not a single character. Returning generic info HTML entity.")
        return "<span class='material-symbols-outlined'>&#x2139;</span>"

    code_point = ord(icon_char)
    unicode_hex = f"{code_point:x}"

    return f'<span class="material-symbols-outlined" style="font-family: \'Material Symbols Outlined\' !important;">&#x{unicode_hex};</span>'

def _get_material_icon_html_for_button_css(button_key: str, icon_material_symbol_name: str) -> str:
    """
    Gera um bloco <style> CSS para injetar um ícone Material Symbol em um botão Streamlit
    específico, usando pseudo-elementos ::before.
    
    Args:
        button_key: Chave identificadora do botão
        icon_material_symbol_name: Nome do ícone Material Symbol
        
    Returns:
        str: Código CSS para o ícone do botão
        
    Raises:
        None: Retorna string vazia em caso de erro
    """
    icon_char = THEME['material_symbols_unicodes'].get(icon_material_symbol_name)
    if not icon_char:
        logger.warning(f"Material Symbol '{icon_material_symbol_name}' not found in THEME['material_symbols_unicodes']. Cannot generate CSS for it.")
        return ""

    if not isinstance(icon_char, str) or len(icon_char) != 1:
        logger.error(f"Icon '{icon_material_symbol_name}' for CSS generation is not a single character.")
        return ""

    code_point = ord(icon_char)
    css_unicode_escape = f'{code_point:x}'

    css_selector_button = f"div[data-testid^='stButton-{button_key}'] > button"
    css_selector_download_button = f"div[data-testid^='stDownloadButton-{button_key}'] > button"

    return f"""
    <style>
    {css_selector_button}::before,
    {css_selector_download_button}::before {{
        content: '{css_unicode_escape}';
        font-family: 'Material Symbols Outlined' !important;
        font-size: 1.2em !important;
        font-variation-settings: 'FILL' 0, 'wght' 400, 'GRAD' 0, 'opsz' 24 !important;
        color: inherit !important;
        line-height: 1 !important;
        order: -1;
        margin-right: 8px;
    }}
    div[data-testid^='stButton-icon_only_{button_key}'] > button::before,
    div[data-testid^='stDownloadButton-icon_only_{button_key}'] > button::before {{
        margin-right: 0 !important;
    }}
    </style>
    """
