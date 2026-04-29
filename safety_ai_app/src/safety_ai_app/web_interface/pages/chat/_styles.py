"""
Módulo de Estilos Visuais — SafetyAI Chat
Responsabilidade: Injeção de CSS Neon e componentes visuais do chat.
"""

import streamlit as st
from safety_ai_app.theme_config import _get_material_icon_html

def inject_chat_styles():
    """Injeta o CSS customizado do tema Cyber-Neon."""
    st.markdown("""
    <style>
        /* === CYBER-NEON CHAT === */
        :root {
            --neon-green: #4ADE80;
            --neon-green-dark: #22C55E;
            --neon-glow: rgba(74, 222, 128, 0.4);
            --bg-void: #020617;
            --bg-space: #0B1220;
            --bg-nebula: #0F172A;
            --glass-bg: rgba(15, 23, 42, 0.85);
            --glass-border: rgba(74, 222, 128, 0.15);
            --text-primary: #F8FAFC;
            --text-secondary: #94A3B8;
            --text-muted: #64748B;
        }

        @keyframes fadeInUp { from { opacity: 0; transform: translateY(15px); } to { opacity: 1; transform: translateY(0); } }
        @keyframes pulse { 0%, 100% { opacity: 0.4; } 50% { opacity: 1; } }
        @keyframes glow { 0%, 100% { box-shadow: 0 0 5px var(--neon-glow); } 50% { box-shadow: 0 0 20px var(--neon-glow), 0 0 30px var(--neon-glow); } }

        .chat-main-container { display: flex; flex-direction: column; height: calc(100vh - 200px); min-height: 500px; }
        
        .chat-header {
            display: flex; align-items: center; gap: 12px; padding: 16px 20px;
            background: linear-gradient(135deg, var(--bg-nebula) 0%, var(--bg-space) 100%);
            border: 1px solid var(--glass-border); border-radius: 16px; margin-bottom: 16px;
        }
        .chat-header-icon {
            width: 48px; height: 48px; border-radius: 12px;
            background: linear-gradient(135deg, var(--neon-green) 0%, var(--neon-green-dark) 100%);
            display: flex; align-items: center; justify-content: center; animation: glow 3s ease-in-out infinite;
        }
        .chat-header-icon svg { width: 28px; height: 28px; color: #000; }
        .chat-header-text h1 { margin: 0; font-size: 1.5rem; font-weight: 700; color: var(--text-primary); font-family: 'Orbitron', sans-serif; }
        .chat-header-text p { margin: 4px 0 0 0; font-size: 0.85rem; color: var(--text-muted); }

        .messages-container { flex: 1; overflow-y: auto; padding: 16px; background: var(--bg-void); border: 1px solid var(--glass-border); border-radius: 16px; margin-bottom: 16px; }

        .msg-user { display: flex; justify-content: flex-end; margin-bottom: 16px; animation: fadeInUp 0.3s ease-out; }
        .msg-user-bubble { max-width: 75%; padding: 14px 18px; background: linear-gradient(135deg, #166534 0%, #15803D 100%); color: #fff; border-radius: 18px 18px 4px 18px; font-size: 0.95rem; line-height: 1.5; box-shadow: 0 4px 12px rgba(22, 101, 52, 0.3); }

        .msg-ai { display: flex; gap: 12px; margin-bottom: 20px; animation: fadeInUp 0.4s ease-out; }
        .msg-ai-avatar { flex-shrink: 0; width: 40px; height: 40px; border-radius: 12px; background: linear-gradient(135deg, var(--neon-green) 0%, var(--neon-green-dark) 100%); display: flex; align-items: center; justify-content: center; box-shadow: 0 0 15px var(--neon-glow); }
        .msg-ai-avatar svg { width: 22px; height: 22px; color: #000; }
        .msg-ai-content { flex: 1; padding: 16px 20px; background: var(--glass-bg); border: 1px solid var(--glass-border); border-radius: 4px 18px 18px 18px; color: var(--text-primary); font-size: 0.95rem; line-height: 1.6; backdrop-filter: blur(10px); }
        .msg-ai-content strong { color: var(--neon-green); }
        .msg-ai-content a { color: var(--neon-green); text-decoration: underline; }

        .typing-indicator { display: flex; gap: 12px; align-items: center; margin-bottom: 16px; }
        .typing-dots { display: flex; gap: 6px; padding: 12px 16px; background: var(--glass-bg); border: 1px solid var(--glass-border); border-radius: 18px; }
        .typing-dots span { width: 8px; height: 8px; background: var(--neon-green); border-radius: 50%; animation: pulse 1.4s infinite; }
        .typing-dots span:nth-child(2) { animation-delay: 0.2s; }
        .typing-dots span:nth-child(3) { animation-delay: 0.4s; }

        .welcome-screen { display: flex; flex-direction: column; align-items: center; justify-content: center; padding: 40px 20px; text-align: center; }
        .welcome-icon { width: 80px; height: 80px; border-radius: 20px; background: linear-gradient(135deg, var(--neon-green) 0%, var(--neon-green-dark) 100%); display: flex; align-items: center; justify-content: center; margin-bottom: 24px; animation: glow 3s ease-in-out infinite; }
        .welcome-icon svg { width: 44px; height: 44px; color: #000; }
        .welcome-title { font-size: 1.4rem; font-weight: 600; color: var(--text-primary); margin-bottom: 8px; }
        .welcome-subtitle { font-size: 0.95rem; color: var(--text-secondary); max-width: 400px; line-height: 1.5; margin-bottom: 24px; }

        .suggestions-container { display: flex; flex-wrap: wrap; gap: 10px; justify-content: center; max-width: 600px; }
        .input-container { background: var(--glass-bg); border: 1px solid var(--glass-border); border-radius: 16px; padding: 12px 16px; }
        
        @media (max-width: 768px) {
            .msg-user-bubble, .msg-ai-content { max-width: 90%; }
        }
    </style>
    """, unsafe_allow_html=True)

def render_welcome_header():
    """Renderiza o cabeçalho de boas-vindas na tela inicial do chat."""
    st.markdown(f"""
    <div class="welcome-screen">
        <div class="welcome-icon">
            {_get_material_icon_html("smart_toy")}
        </div>
        <div class="welcome-title">Olá! Como posso ajudar?</div>
        <div class="welcome-subtitle">
            Sou seu assistente especializado em Saúde e Segurança do Trabalho.<br>
            Pergunte sobre NRs, dimensionamento, EPIs, documentos e muito mais.
        </div>
        <div class="suggestions-container">
    """, unsafe_allow_html=True)
