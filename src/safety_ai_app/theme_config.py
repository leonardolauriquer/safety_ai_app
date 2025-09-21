# src/safety_ai_app/theme_config.py

# Define o tema da aplicação, incluindo cores, fontes, emojis e frases.
# Este dicionário centraliza as variáveis de design para fácil modificação.
THEME = {
    "colors": {
        "background_primary": "#0d1117",  # Fundo principal escuro (quase preto, GitHub-like)
        "background_secondary": "#161b22", # Fundo de cards/containers (um pouco mais claro que o primário)
        "text_primary": "#c9d1d9",        # Cor principal do texto (branco acinzentado claro)
        "text_secondary": "#8b949e",       # Cor de texto mais suave (descrições, rodapé, placeholders)
        "accent_green": "#27ae60",        # Verde principal (destaque, botões primários)
        "accent_green_hover": "#39d353",  # Verde mais claro (hover de botões primários, neon mais intenso)
        "accent_green_shadow": "rgba(39, 174, 96, 0.4)", # Sombra para destaque verde (efeito neon)
        "input_background": "#30363d",     # Fundo de campos de input e botões de ação
        "border_color": "#30363d",        # Cor de bordas e divisores
        "user_message_bg": "#27ae60",     # Fundo da bolha de mensagem do usuário (verde principal)
        "ai_message_bg": "#30363d",       # Fundo da bolha de mensagem da IA (fundo do input)
        "info_border": "#56d364",         # Borda de alertas de informação (verde claro para info)
        "error_border": "#f85149",        # Borda de alertas de erro (vermelho)
        "button_action_text": "#c9d1d9",  # Texto dos botões de ação (Anexar, Gerar, etc.)
        "button_action_hover": "#484f58", # Fundo de hover para botões de ação
    },
    "fonts": {
        "primary_family": "Inter, sans-serif", # Fonte principal: Inter
        "primary_url": "https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap"
    },
    "emojis": {
        "ai_robot": "🤖",
        "back_arrow": "⬅️",
        "chat_bubble": "💬",
        "library_books": "📚",
        "procedures_clipboard": "📋",
        "magic_pencil": "🪄",
        "microphone": "🎤",
        "folder_docs": "📁",
        "image_frame": "🖼️",
        "settings_gear": "⚙️",
        "send_arrow": "➡️",
        "welcome_wave": "👋",
        "info_sparkle": "✨",
        "file_doc": "📄",
        "download_arrow": "⬇️",
        "loading_hourglass": "⏳",
        "save_disk": "💾",
        "success_check": "✅",
        "error_x": "❌",
        "donation_hands": "🙏", # Para o toast de doação
        "upload_arrow": "⬆️", # Para o botão de doação
        "upload_folder": "📤",  # Para a seção de upload local
        "document_icon": "📄"   # Para o título de documentos processados
    },
    "phrases": {
        "back_to_home": "Voltar para a Página Inicial",
        "chat_with_ai": "Conversar com a IA",
        "document_library": "Biblioteca de Documentos",
        "procedures": "Procedimentos",
        "refine_edit": "Refinar e Editar",
        "audio_to_text": "Áudio para Texto",
        "use_docs_context": "Usar documentos como contexto",
        "analyze_image": "Analisar Imagem",
        "generate_content": "Gerar Conteúdo",
        "default_placeholder": "Ex: Quais são as responsabilidades do empregador segundo a NR-35?",
        "footer_text": "Desenvolvido com IA 🤖 por Eng. Leonardo Lauriquer Ribeiro - Focado em um futuro mais seguro."
    }
}

# CSS Global para a aplicação
# Esta string contém todo o CSS que será injetado na aplicação Streamlit.
# O uso de f-string permite a interpolação das variáveis definidas em THEME,
# garantindo que as cores e fontes sejam consistentes em todo o CSS.
GLOBAL_STYLES = f"""
    <style>
    /* Importa a fonte principal da aplicação */
    @import url('{THEME["fonts"]["primary_url"]}');

    /* Define a animação de piscar para o efeito neon nos títulos */
    @keyframes neon-flicker {{
        0%, 100% {{
            text-shadow: 
                0 0 5px {THEME["colors"]["accent_green_shadow"]}, 
                0 0 10px {THEME["colors"]["accent_green_shadow"]},
                0 0 20px {THEME["colors"]["accent_green_shadow"]};
            color: {THEME["colors"]["accent_green"]};
        }}
        50% {{
            text-shadow: 
                0 0 10px {THEME["colors"]["accent_green_shadow"]}, 
                0 0 20px {THEME["colors"]["accent_green_shadow"]},
                0 0 40px {THEME["colors"]["accent_green_shadow"]};
            color: {THEME["colors"]["accent_green_hover"]};
        }}
    }}

    /* Aplica a animação neon a elementos com a classe .neon-title */
    .neon-title {{
        animation: neon-flicker 2s ease-in-out infinite alternate;
        font-family: {THEME["fonts"]["primary_family"]}; /* Usa a fonte principal para o título neon */
    }}

    /* Estilos globais para o contêiner principal da aplicação Streamlit */
    .stApp {{
        background-color: {THEME["colors"]["background_primary"]};
        color: {THEME["colors"]["text_primary"]};
        font-family: {THEME["fonts"]["primary_family"]};
        padding: 15px;
    }}

    /* Estilos para cabeçalhos H1 */
    h1 {{
        text-align: center;
        margin-bottom: 25px;
        font-size: 2.5em;
        color: {THEME["colors"]["text_primary"]}; /* Padrão, pode ser sobrescrito por .neon-title */
        font-family: {THEME["fonts"]["primary_family"]};
    }}
    /* Estilos para cabeçalhos H2 a H6 */
    h2, h3, h4, h5, h6 {{
        color: {THEME["colors"]["accent_green"]};
        text-align: left;
        border-bottom: 2px solid {THEME["colors"]["border_color"]};
        padding-bottom: 10px;
        margin-top: 30px;
        margin-bottom: 20px;
        font-family: {THEME["fonts"]["primary_family"]}; /* Corrigido: THEHE para THEME */
    }}

    /* Estilos para botões padrão do Streamlit */
    .stButton>button {{
        background-color: {THEME["colors"]["accent_green"]};
        color: {THEME["colors"]["text_primary"]}; /* Usar text_primary para consistência */
        border-radius: 8px;
        border: 1px solid {THEME["colors"]["accent_green"]};
        padding: 12px 25px;
        font-weight: bold;
        transition: all 0.3s ease;
        box-shadow: 0 0 15px {THEME["colors"]["accent_green_shadow"]};
        cursor: pointer;
        width: fit-content;
        font-family: {THEME["fonts"]["primary_family"]};
    }}
    /* Efeito de hover para botões padrão */
    .stButton>button:hover {{
        background-color: {THEME["colors"]["accent_green_hover"]};
        border-color: {THEME["colors"]["accent_green_hover"]};
        box-shadow: 0 0 20px {THEME["colors"]["accent_green_shadow"]};
        transform: translateY(-2px);
    }}
    
    /* Estilo para o contêiner principal do chat (st.container com border=True e height) */
    div[data-testid="stVerticalBlock"] > div[data-testid="stVerticalBlock"] > div[data-testid="stVerticalBlock"]:nth-child(2) {{ 
        border: 2px solid {THEME["colors"]["border_color"]};
        border-radius: 10px;
        background-color: {THEME["colors"]["background_secondary"]};
        margin-top: 25px;
        box-shadow: 0 0 20px rgba(0,0,0,0.2); /* Sombra mais discreta */
        overflow-y: auto;
        max-height: 480px;
        padding: 20px;
    }}
    
    /* Estilos base para mensagens de chat */
    .chat-message {{
        padding: 12px 18px;
        border-radius: 18px;
        margin-bottom: 12px;
        max-width: 85%;
        color: {THEME["colors"]["text_primary"]};
        word-wrap: break-word;
        line-height: 1.5;
        box-shadow: 0 2px 5px rgba(0,0,0,0.2);
        font-family: {THEME["fonts"]["primary_family"]};
    }}
    /* Estilos específicos para mensagens do usuário */
    .chat-message.user {{
        background-color: {THEME["colors"]["user_message_bg"]};
        margin-left: auto;
        text-align: left;
        border-bottom-right-radius: 4px;
    }}
    /* Estilos específicos para mensagens da IA */
    .chat-message.ai {{
        background-color: {THEME["colors"]["ai_message_bg"]};
        border: 1px solid {THEME["colors"]["border_color"]};
        margin-right: auto;
        text-align: left;
        border-bottom-left-radius: 4px;
    }}
    /* Contêiner para alinhar as bolhas de chat */
    .chat-message-container {{
        display: flex;
        width: 100%;
        margin-top: 5px;
    }}
    /* Remove margem inferior padrão de parágrafos dentro de mensagens */
    .chat-message p {{
        margin-bottom: 0;
    }}
    /* Estilos para listas dentro de mensagens */
    .chat-message ul, .chat-message ol {{
        padding-left: 20px;
        margin-top: 5px;
        margin-bottom: 5px;
    }}
    .chat-message li {{
        margin-bottom: 5px;
    }}
    /* Estilo para texto em negrito dentro de mensagens */
    .chat-message b {{
        color: {THEME["colors"]["accent_green_hover"]}; 
    }}

    /* Estilos para alertas (st.info, st.warning, st.error) */
    .stAlert > div {{
        border-left: 5px solid;
        border-radius: 5px;
        background-color: {THEME["colors"]["background_secondary"]};
        color: {THEME["colors"]["text_primary"]};
        margin-top: 15px;
        padding: 15px;
        font-family: {THEME["fonts"]["primary_family"]};
    }}
    /* Cores de borda específicas para cada tipo de alerta */
    .stAlert.info > div {{ border-color: {THEME["colors"]["info_border"]}; }}
    .stAlert.success > div {{ border-color: {THEME["colors"]["accent_green_hover"]}; }} /* Sucesso usa o verde neon hover */
    .stAlert.error > div {{ border-color: {THEME["colors"]["error_border"]}; }}

    /* Garante que o texto dentro de alertas use a cor primária */
    .stAlert p {{
        color: {THEME["colors"]["text_primary"]} !important;
    }}

    /* Estilos para o rodapé */
    .footer {{
        text-align: center;
        color: {THEME["colors"]["text_secondary"]};
        font-size: 0.85em;
        margin-top: 40px;
        padding-top: 20px;
        border-top: 1px dashed {THEME["colors"]["border_color"]};
        font-family: {THEME["fonts"]["primary_family"]};
    }}

    /* Área de input do chat */
    .chat-input-area {{
        background-color: {THEME["colors"]["background_secondary"]};
        border-radius: 12px;
        padding: 15px 20px;
        margin-top: 25px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.3);
        display: flex;
        flex-direction: column;
        gap: 8px; /* Espaçamento entre os elementos (icones e form) */
    }}
    
    /* Linha de botões de ícone */
    .icon-buttons-row {{ 
        display: flex;
        align-items: center;
        justify-content: flex-start;
        gap: 8px;
        margin-bottom: 0 !important;
    }}
    /* Garante que colunas Streamlit dentro da linha de ícones não adicionem padding */
    .icon-buttons-row > div[data-testid^="stColumn"] {{
        padding: 0px !important;
    }}

    /* Estilo para campos de input de texto do Streamlit (incluindo o st.text_input principal) */
    .stTextInput>div>div>input {{ 
        background-color: {THEME["colors"]["input_background"]};
        color: {THEME["colors"]["text_primary"]};
        border: none;
        border-radius: 8px;
        padding: 15px 20px;
        font-size: 1.1em;
        height: auto;
        box-shadow: none;
        transition: box-shadow 0.2s ease;
        font-family: {THEME["fonts"]["primary_family"]};
    }}
    /* Efeito de foco para campos de input de texto */
    .stTextInput>div>div>input:focus {{
        box-shadow: 0 0 0 2px {THEME["colors"]["accent_green"]};
        outline: none;
    }}

    /* Estilo para botões que atuam como ícones (aqueles com 'key' começando com 'btn_icon_') */
    .stButton[data-testid*="btn_icon_"] > button {{
        background-color: {THEME["colors"]["input_background"]} !important;
        border: none !important;
        border-radius: 50% !important;
        width: 45px !important;
        min-width: 45px !important;
        height: 45px !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        color: {THEME["colors"]["button_action_text"]} !important; /* Cor de texto para botões de ação */
        font-size: 1.3em !important;
        cursor: pointer !important;
        transition: all 0.2s ease !important;
        box-shadow: none !important;
        flex-shrink: 0;
        padding: 0 !important;
        line-height: 1 !important;
    }}
    /* Efeito de hover para botões de ícone */
    .stButton[data-testid*="btn_icon_"] > button:hover {{
        background-color: {THEME["colors"]["button_action_hover"]} !important;
        color: {THEME["colors"]["accent_green"]} !important; /* Ícone verde neon no hover */
        transform: translateY(-1px) !important;
    }}
    /* Garante que o span (onde o emoji geralmente fica) herde a cor */
    .stButton[data-testid*="btn_icon_"] > button span {{
        color: inherit !important;
        font-size: 1em !important;
        line-height: 1 !important;
        display: flex;
        align-items: center;
        justify-content: center;
    }}

    /* Estilo para o botão de submissão de formulário (st.form_submit_button) */
    .stButton[data-testid="stFormSubmitButton"] > button {{
        background-color: {THEME["colors"]["input_background"]} !important;
        border: none !important;
        border-radius: 50% !important;
        width: 45px !important;
        min-width: 45px !important;
        height: 45px !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        color: {THEME["colors"]["button_action_text"]} !important;
        font-size: 1.3em !important;
        cursor: pointer !important;
        transition: all 0.2s ease !important;
        box-shadow: none !important;
        flex-shrink: 0;
        padding: 0 !important;
        line-height: 1 !important;
    }}
    /* Efeito de hover para o botão de submissão */
    .stButton[data-testid="stFormSubmitButton"] > button:hover {{
        background-color: {THEME["colors"]["button_action_hover"]} !important;
        color: {THEME["colors"]["accent_green"]} !important;
        transform: translateY(-1px) !important;
    }}
    /* Garante que o span (onde o emoji geralmente fica) herde a cor */
    .stButton[data-testid="stFormSubmitButton"] > button span {{
        color: inherit !important;
        font-size: 1em !important;
        line-height: 1 !important;
        display: flex;
        align-items: center;
        justify-content: center;
    }}

    /* Estilo para o formulário do Streamlit (st.form) */
    .stForm {{
        margin: 0 !important;
        display: flex;
        align-items: center;
        gap: 8px;
    }}
    /* Garante que o stTextInput dentro do form ocupe o espaço restante */
    .stForm > div > div > div[data-testid^="stTextInput"] {{ 
         flex-grow: 1;
         margin-bottom: 0 !important;
    }}

    /* Estilos para o componente st.file_uploader */
    div[data-testid="stFileUploader"] {{
        background-color: {THEME["colors"]["input_background"]};
        border: 1px dashed {THEME["colors"]["border_color"]};
        border-radius: 10px;
        padding: 15px;
        margin-top: 15px;
        margin-left: auto;
        margin-right: auto;
        /* width: fit-content; REMOVIDO PARA OCUPAR LARGURA TOTAL DA TAB */
        width: 100%;
    }}
    /* Estilo para o texto do label do st.file_uploader */
    div[data-testid="stFileUploader"] label p {{
        color: {THEME["colors"]["text_secondary"]};
        font-size: 0.9em;
        margin-bottom: 0;
    }}
    /* Centraliza o conteúdo do st.file_uploader */
    div[data-testid="stFileUploader"] > div {{
        justify-content: center;
    }}

    /* Estilo para a área de seleção de arquivos do Drive no chat_page */
    .drive-selector-area {{
        background-color: {THEME["colors"]["background_secondary"]};
        border: 1px solid {THEME["colors"]["border_color"]};
        border-radius: 10px;
        padding: 15px;
        margin-top: 15px;
        box-shadow: 0 0 10px rgba(0,0,0,0.1);
        font-family: {THEME["fonts"]["primary_family"]};
    }}
    .drive-selector-area h3 {{
        border-bottom: none;
        margin-top: 0;
        padding-bottom: 0;
    }}

    /* Estilo para o botão de "Voltar para a Página Inicial" e similares */
    .stButton[key="btn_back_home"] > button, /* Home Page */
    .stButton[key="btn_back_home_from_chat"] > button, /* Chat Page */
    .stButton[key="back_to_home_library"] > button, /* Library Page */
    .stButton[key="back_home_procedures"] > button {{ /* Procedures Page */
        background-color: transparent !important; /* Fundo transparente */
        color: {THEME["colors"]["text_secondary"]} !important; /* Cor secundária do texto */
        border: 1px solid {THEME["colors"]["border_color"]} !important; /* Borda discreta */
        padding: 8px 15px !important; /* Espaçamento menor */
        border-radius: 5px !important; /* Cantos levemente arredondados */
        font-weight: normal !important; /* Texto normal */
        box-shadow: none !important; /* Sem sombra */
        transition: all 0.2s ease !important;
        width: fit-content !important; /* Ajusta a largura ao conteúdo */
        margin-top: 20px; /* Margem para separar do conteúdo */
        font-family: {THEME["fonts"]["primary_family"]};
    }}
    .stButton[key="btn_back_home"] > button:hover,
    .stButton[key="btn_back_home_from_chat"] > button:hover,
    .stButton[key="back_to_home_library"] > button:hover,
    .stButton[key="back_home_procedures"] > button:hover {{
        background-color: {THEME["colors"]["background_secondary"]} !important;
        border-color: {THEME["colors"]["accent_green"]} !important;
        color: {THEME["colors"]["accent_green_hover"]} !important;
        transform: translateY(-1px) !important;
    }}

    /* Estilos para o componente st.tabs */
    .stTabs [data-testid="stTab"] button {{
        background-color: {THEME["colors"]["background_secondary"]};
        color: {THEME["colors"]["text_secondary"]};
        border-radius: 5px 5px 0 0;
        border: 1px solid {THEME["colors"]["border_color"]};
        border-bottom: none;
        margin-right: 5px;
        padding: 10px 15px;
        font-weight: 500;
        transition: all 0.2s ease;
        font-family: {THEME["fonts"]["primary_family"]};
    }}
    .stTabs [data-testid="stTab"] button:hover {{
        color: {THEME["colors"]["accent_green_hover"]};
        background-color: {THEME["colors"]["input_background"]};
    }}
    .stTabs [data-testid="stTab"] button[aria-selected="true"] {{
        background-color: {THEME["colors"]["background_primary"]}; /* Aba ativa um pouco mais escura */
        color: {THEME["colors"]["accent_green"]};
        border-top: 2px solid {THEME["colors"]["accent_green"]}; /* Borda superior verde */
        border-left-color: {THEME["colors"]["accent_green"]};
        border-right-color: {THEME["colors"]["accent_green"]};
        font-weight: 600;
        margin-top: -1px; /* Para 'grudar' na borda superior */
    }}
    .stTabs [data-testid="stTabContent"] {{
        background-color: {THEME["colors"]["background_primary"]}; /* Conteúdo da aba no fundo principal */
        border: 1px solid {THEME["colors"]["border_color"]};
        border-top: none;
        border-radius: 0 0 10px 10px;
        padding: 20px;
        font-family: {THEME["fonts"]["primary_family"]};
    }}
    </style>
"""