# src/safety_ai_app/theme_config.py

THEME = {
    "colors": {
        "background_primary": "#0d1117",  # Fundo principal escuro (quase preto)
        "background_secondary": "#161b22", # Fundo de cards/containers (um pouco mais claro que o primário)
        "text_primary": "#c9d1d9",        # Cor principal do texto (branco acinzentado)
        "text_secondary": "#8b949e",       # Cor de texto mais suave (descrições, rodapé)
        "accent_green": "#27ae60",        # Verde principal (destaque, botões primários)
        "accent_green_hover": "#39d353",  # Verde mais claro (hover de botões primários)
        "accent_green_shadow": "rgba(39, 174, 96, 0.4)", # Sombra para destaque verde
        "input_background": "#30363d",     # Fundo de campos de input e botões de ação
        "border_color": "#30363d",        # Cor de bordas e divisores
        "user_message_bg": "#27ae60",     # Fundo da bolha de mensagem do usuário
        "ai_message_bg": "#30363d",       # Fundo da bolha de mensagem da IA
        "info_border": "#56d364",         # Borda de alertas de informação (verde claro)
        "error_border": "#f85149",        # Borda de alertas de erro (vermelho)
        "button_action_text": "#c9d1d9",  # Texto dos botões de ação (Anexar, Gerar, etc.)
        "button_action_hover": "#484f58", # Fundo de hover para botões de ação
    },
    "fonts": {
        "primary_family": "Inter, sans-serif",
        "primary_url": "https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap"
    }
}