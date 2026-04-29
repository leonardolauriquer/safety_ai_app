import streamlit as st
import os
import base64
from typing import Optional

@st.cache_data
def _get_logo_base64_cached(logo_path: str) -> Optional[str]:
    """Lê e codifica a logo em Base64 com cache para evitar IO repetitivo."""
    if not os.path.exists(logo_path):
        return None
    try:
        with open(logo_path, "rb") as f:
            data = base64.b64encode(f.read()).decode()
        ext = logo_path.split('.')[-1]
        return f"data:image/{ext};base64,{data}"
    except Exception:
        return None


def render_login_page(project_root: str, theme: dict, get_user_drive_service_wrapper) -> None:
    st.sidebar.empty()

    accent_green = theme['colors']['accent_green']
    accent_cyan = theme['colors'].get('accent_cyan', '#22D3EE')
    accent_orange = theme['colors'].get('accent_orange', '#F97316')
    text_secondary = theme['colors'].get('text_secondary', '#94A3B8')
    text_muted = theme['colors'].get('text_muted', '#64748B')

    login_styles = f"""
    <style>
        /* Fontes carregadas globalmente pelo web_app.py */

        [data-testid="stSidebar"], section[data-testid="stSidebarContent"],
        .css-1d391kg, .css-1lcbmhc, .css-vk3wp9 {{
            display: none !important;
        }}

        .main .block-container {{
            max-width: 100% !important;
            padding: 0 !important;
        }}

        .login-background {{
            position: fixed;
            top: 0;
            left: 0;
            width: 100vw;
            height: 100vh;
            background: radial-gradient(ellipse at center, #0B1220 0%, #020617 100%);
            z-index: 0;
            pointer-events: none;
        }}

        .stApp {{
            background: transparent !important;
        }}

        .main .block-container {{
            background: transparent !important;
            position: relative;
            z-index: 10;
            padding-top: 3rem !important;
        }}

        .particles {{
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            overflow: hidden;
            z-index: 0;
        }}

        .particle {{
            position: absolute;
            width: 4px;
            height: 4px;
            background: {accent_green};
            border-radius: 50%;
            opacity: 0.6;
            animation: float-particle 15s infinite ease-in-out;
            box-shadow: 0 0 10px {accent_green}, 0 0 20px {accent_green};
        }}

        .particle:nth-child(1) {{ left: 10%; animation-delay: 0s; animation-duration: 20s; }}
        .particle:nth-child(2) {{ left: 20%; animation-delay: 2s; animation-duration: 18s; }}
        .particle:nth-child(3) {{ left: 30%; animation-delay: 4s; animation-duration: 22s; }}
        .particle:nth-child(4) {{ left: 40%; animation-delay: 1s; animation-duration: 16s; }}
        .particle:nth-child(5) {{ left: 50%; animation-delay: 3s; animation-duration: 24s; }}
        .particle:nth-child(6) {{ left: 60%; animation-delay: 5s; animation-duration: 19s; }}
        .particle:nth-child(7) {{ left: 70%; animation-delay: 2.5s; animation-duration: 21s; }}
        .particle:nth-child(8) {{ left: 80%; animation-delay: 4.5s; animation-duration: 17s; }}
        .particle:nth-child(9) {{ left: 90%; animation-delay: 1.5s; animation-duration: 23s; }}
        .particle:nth-child(10) {{ left: 15%; animation-delay: 3.5s; animation-duration: 25s; background: {accent_cyan}; box-shadow: 0 0 10px {accent_cyan}; }}
        .particle:nth-child(11) {{ left: 45%; animation-delay: 0.5s; animation-duration: 20s; background: {accent_cyan}; box-shadow: 0 0 10px {accent_cyan}; }}
        .particle:nth-child(12) {{ left: 75%; animation-delay: 2.8s; animation-duration: 18s; background: {accent_orange}; box-shadow: 0 0 10px {accent_orange}; opacity: 0.4; }}

        @keyframes float-particle {{
            0%, 100% {{ transform: translateY(100vh) scale(0); opacity: 0; }}
            10% {{ opacity: 0.6; transform: scale(1); }}
            90% {{ opacity: 0.6; transform: scale(1); }}
            100% {{ transform: translateY(-100vh) scale(0); opacity: 0; }}
        }}

        .grid-overlay {{
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background-image:
                linear-gradient(rgba(74, 222, 128, 0.03) 1px, transparent 1px),
                linear-gradient(90deg, rgba(74, 222, 128, 0.03) 1px, transparent 1px);
            background-size: 50px 50px;
            z-index: 0;
        }}

        .login-card {{
            display: none !important;
        }}

        [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:nth-child(2) > div {{
            position: relative;
            z-index: 10;
            background: linear-gradient(145deg, rgba(15, 23, 42, 0.95) 0%, rgba(11, 18, 32, 0.98) 100%);
            border-radius: 20px;
            padding: 1.5rem 1.5rem;
            backdrop-filter: blur(20px);
            animation: card-entrance 0.8s ease-out, card-glow 4s ease-in-out infinite;
            box-shadow:
                0 0 0 1px rgba(74, 222, 128, 0.2),
                0 0 40px rgba(74, 222, 128, 0.15),
                0 20px 60px rgba(0, 0, 0, 0.5),
                inset 0 1px 0 rgba(255, 255, 255, 0.05);
        }}

        @keyframes card-entrance {{
            0% {{ opacity: 0; transform: translateY(30px) scale(0.95); }}
            100% {{ opacity: 1; transform: translateY(0) scale(1); }}
        }}

        @keyframes card-glow {{
            0%, 100% {{ box-shadow: 0 0 0 1px rgba(74, 222, 128, 0.2), 0 0 40px rgba(74, 222, 128, 0.15), 0 20px 60px rgba(0, 0, 0, 0.5); }}
            50% {{ box-shadow: 0 0 0 1px rgba(74, 222, 128, 0.4), 0 0 60px rgba(74, 222, 128, 0.25), 0 20px 60px rgba(0, 0, 0, 0.5); }}
        }}

        .login-logo-container {{
            text-align: center;
            margin-bottom: 1rem;
            display: flex;
            justify-content: center;
        }}

        .login-logo-container img {{
            border-radius: 50% !important;
            border: 3px solid {accent_green} !important;
            box-shadow: 0 0 30px rgba(74, 222, 128, 0.5), 0 0 60px rgba(74, 222, 128, 0.2) !important;
            animation: logo-pulse 3s ease-in-out infinite;
            transition: transform 0.3s ease;
        }}

        .login-logo-container img:hover {{
            transform: scale(1.05);
        }}

        [data-testid="stHorizontalBlock"] [data-testid="stColumn"]:nth-child(2) [data-testid="stImage"] {{
            display: flex !important;
            justify-content: center !important;
            width: 100% !important;
        }}

        [data-testid="stHorizontalBlock"] [data-testid="stColumn"]:nth-child(2) [data-testid="stImage"] > img {{
            border-radius: 50% !important;
            border: 3px solid {accent_green} !important;
            box-shadow: 0 0 30px rgba(74, 222, 128, 0.5), 0 0 60px rgba(74, 222, 128, 0.2) !important;
            animation: logo-pulse 3s ease-in-out infinite;
            margin: 0 auto !important;
        }}

        @keyframes logo-pulse {{
            0%, 100% {{ box-shadow: 0 0 30px rgba(74, 222, 128, 0.5), 0 0 60px rgba(74, 222, 128, 0.2); }}
            50% {{ box-shadow: 0 0 40px rgba(74, 222, 128, 0.7), 0 0 80px rgba(74, 222, 128, 0.3); }}
        }}

        .login-title {{
            font-family: 'Orbitron', sans-serif;
            font-size: 2rem;
            font-weight: 800;
            text-align: center;
            background: linear-gradient(135deg, {accent_green} 0%, {accent_cyan} 50%, {accent_green} 100%);
            background-size: 200% auto;
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            animation: gradient-shift 3s ease-in-out infinite;
            margin-bottom: 0.3rem;
            margin-top: 0;
            letter-spacing: 2px;
            text-shadow: 0 0 30px rgba(74, 222, 128, 0.5);
        }}

        @keyframes gradient-shift {{
            0%, 100% {{ background-position: 0% center; }}
            50% {{ background-position: 100% center; }}
        }}

        .login-subtitle {{
            color: {text_secondary};
            text-align: center;
            font-size: 0.9rem;
            font-weight: 400;
            margin-bottom: 0.8rem;
            opacity: 0.9;
        }}

        .login-divider {{
            height: 2px;
            background: linear-gradient(90deg, transparent, {accent_green}, {accent_cyan}, {accent_green}, transparent);
            background-size: 200% 100%;
            animation: divider-flow 3s linear infinite;
            margin: 0.8rem 0;
            border-radius: 2px;
        }}

        @keyframes divider-flow {{
            0% {{ background-position: 100% 0; }}
            100% {{ background-position: -100% 0; }}
        }}

        .login-features {{
            display: flex;
            flex-direction: column;
            gap: 0.5rem;
            margin-bottom: 1rem;
        }}

        .login-feature {{
            display: flex;
            align-items: center;
            gap: 0.8rem;
            padding: 0.5rem 0.8rem;
            background: rgba(74, 222, 128, 0.05);
            border-radius: 10px;
            border: 1px solid rgba(74, 222, 128, 0.1);
            transition: all 0.3s ease;
            animation: feature-slide-in 0.5s ease-out forwards;
            opacity: 0;
            transform: translateX(-20px);
        }}

        .login-feature:nth-child(1) {{ animation-delay: 0.1s; }}
        .login-feature:nth-child(2) {{ animation-delay: 0.2s; }}
        .login-feature:nth-child(3) {{ animation-delay: 0.3s; }}
        .login-feature:nth-child(4) {{ animation-delay: 0.4s; }}
        .login-feature:nth-child(5) {{ animation-delay: 0.5s; }}

        @keyframes feature-slide-in {{
            to {{ opacity: 1; transform: translateX(0); }}
        }}

        .login-feature:hover {{
            background: rgba(74, 222, 128, 0.1);
            border-color: rgba(74, 222, 128, 0.3);
            transform: translateX(5px);
        }}

        .feature-icon {{
            width: 24px;
            height: 24px;
            display: flex;
            align-items: center;
            justify-content: center;
            color: {accent_green};
            font-size: 1.2rem;
            text-shadow: 0 0 10px {accent_green};
        }}

        .feature-text {{
            color: {text_secondary};
            font-size: 0.85rem;
            font-weight: 500;
        }}

        .login-btn-container {{
            margin-top: 1.2rem;
        }}

        .login-btn {{
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 0.75rem;
            width: 100%;
            padding: 1rem 2rem;
            background: linear-gradient(135deg, rgba(74, 222, 128, 0.15) 0%, rgba(34, 211, 238, 0.1) 100%);
            color: {accent_green};
            font-family: 'Orbitron', sans-serif;
            font-weight: 600;
            font-size: 1rem;
            letter-spacing: 1px;
            text-align: center;
            text-decoration: none;
            border-radius: 12px;
            border: 2px solid {accent_green};
            cursor: pointer;
            box-shadow:
                0 0 20px rgba(74, 222, 128, 0.3),
                inset 0 0 20px rgba(74, 222, 128, 0.05);
            transition: all 0.3s ease;
            position: relative;
            overflow: hidden;
        }}

        .login-btn::before {{
            content: '';
            position: absolute;
            top: 0;
            left: -100%;
            width: 100%;
            height: 100%;
            background: linear-gradient(90deg, transparent, rgba(74, 222, 128, 0.2), transparent);
            transition: left 0.6s ease;
        }}

        .login-btn:hover {{
            background: linear-gradient(135deg, rgba(74, 222, 128, 0.25) 0%, rgba(34, 211, 238, 0.15) 100%);
            transform: translateY(-2px);
            box-shadow:
                0 0 35px rgba(74, 222, 128, 0.5),
                0 5px 20px rgba(0, 0, 0, 0.3),
                inset 0 0 30px rgba(74, 222, 128, 0.1);
            text-shadow: 0 0 10px rgba(74, 222, 128, 0.8);
        }}

        .login-btn:hover::before {{
            left: 100%;
        }}

        .login-btn-icon {{
            font-size: 1.2rem;
            filter: drop-shadow(0 0 5px rgba(74, 222, 128, 0.5));
        }}

        .google-logo {{
            width: 20px;
            height: 20px;
            margin-right: 0.3rem;
        }}

        .login-info {{
            text-align: center;
            color: {text_muted};
            font-size: 0.75rem;
            margin-top: 1.5rem;
            opacity: 0.8;
        }}

        .version-badge {{
            position: absolute;
            top: 1rem;
            right: 1rem;
            background: rgba(74, 222, 128, 0.1);
            border: 1px solid rgba(74, 222, 128, 0.4);
            padding: 0.25rem 0.6rem;
            border-radius: 6px;
            font-size: 0.7rem;
            color: {accent_green};
            font-family: 'Orbitron', sans-serif;
            letter-spacing: 1px;
            z-index: 10;
        }}

        [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:nth-child(2) > div {{
            position: relative;
        }}

        .stButton > button {{
            background: linear-gradient(135deg, rgba(74, 222, 128, 0.15) 0%, rgba(34, 211, 238, 0.1) 100%) !important;
            color: {accent_green} !important;
            font-family: 'Orbitron', sans-serif !important;
            font-weight: 600 !important;
            font-size: 1rem !important;
            letter-spacing: 1px !important;
            padding: 1rem 2rem !important;
            border-radius: 12px !important;
            border: 2px solid {accent_green} !important;
            box-shadow: 0 0 20px rgba(74, 222, 128, 0.3) !important;
            transition: all 0.3s ease !important;
        }}

        .stButton > button:hover {{
            background: linear-gradient(135deg, rgba(74, 222, 128, 0.25) 0%, rgba(34, 211, 238, 0.15) 100%) !important;
            transform: translateY(-2px) !important;
            box-shadow: 0 0 35px rgba(74, 222, 128, 0.5) !important;
            text-shadow: 0 0 10px rgba(74, 222, 128, 0.8) !important;
        }}

        @media screen and (max-width: 768px) {{
            [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:nth-child(2) > div {{
                padding: 1rem;
                border-radius: 16px;
                margin: 0.5rem;
            }}
            .login-title {{ font-size: 1.5rem !important; letter-spacing: 1px !important; }}
            .login-subtitle {{ font-size: 0.8rem !important; }}
            .login-feature {{ padding: 0.4rem 0.6rem !important; gap: 0.5rem !important; }}
            .feature-text {{ font-size: 0.75rem !important; }}
            .feature-icon {{ font-size: 1rem !important; }}
            .login-btn {{ padding: 0.8rem 1.2rem !important; font-size: 0.9rem !important; }}
            .google-logo {{ width: 18px !important; height: 18px !important; }}
            .version-badge {{ font-size: 0.6rem !important; padding: 0.2rem 0.4rem !important; top: 0.5rem !important; right: 0.5rem !important; }}
        }}

        @media screen and (max-height: 800px) {{
            [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:nth-child(2) > div {{
                padding: 1rem 1.2rem !important;
                margin-top: 0.5rem !important;
            }}
            .login-title {{ font-size: 1.6rem !important; margin-bottom: 0.2rem !important; }}
            .login-subtitle {{ font-size: 0.8rem !important; margin-bottom: 0.5rem !important; }}
            .login-features {{ gap: 0.4rem !important; margin-bottom: 0.6rem !important; }}
            .login-feature {{ padding: 0.4rem 0.6rem !important; }}
            .login-divider {{ margin: 0.5rem 0 !important; }}
            .login-btn {{ padding: 0.9rem 1.5rem !important; }}
            .login-info {{ margin-top: 1.2rem !important; font-size: 0.7rem !important; }}
        }}

        @media screen and (max-height: 650px) {{
            [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:nth-child(2) > div {{
                padding: 0.8rem 1rem !important;
                margin-top: 0.3rem !important;
            }}
            .login-title {{ font-size: 1.4rem !important; }}
            .login-features {{ gap: 0.25rem !important; margin-bottom: 0.4rem !important; }}
            .login-feature {{ padding: 0.25rem 0.5rem !important; }}
            .feature-text {{ font-size: 0.7rem !important; }}
            .login-divider {{ margin: 0.3rem 0 !important; }}
            .login-btn {{ padding: 0.7rem 1rem !important; font-size: 0.95rem !important; }}
            .login-info {{ margin-top: 0.8rem !important; font-size: 0.65rem !important; }}
        }}
    </style>
    """

    st.markdown(login_styles, unsafe_allow_html=True)

    auth_url = st.session_state.get("user_drive_auth_url", "")

    st.markdown("""
    <div class="login-background">
        <div class="grid-overlay"></div>
        <div class="particles">
            <div class="particle"></div>
            <div class="particle"></div>
            <div class="particle"></div>
            <div class="particle"></div>
            <div class="particle"></div>
            <div class="particle"></div>
            <div class="particle"></div>
            <div class="particle"></div>
            <div class="particle"></div>
            <div class="particle"></div>
            <div class="particle"></div>
            <div class="particle"></div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown('<div class="version-badge">v2.0</div>', unsafe_allow_html=True)

        logo_path = os.path.join(project_root, theme['images']['app_logo'])
        logo_data_uri = _get_logo_base64_cached(logo_path)
        
        if logo_data_uri:
            st.markdown(f'''
                <div style="display: flex; justify-content: center; margin-bottom: 0.5rem;">
                    <div style="width: 140px; height: 140px; display: flex; align-items: center;
                                justify-content: center; overflow: visible;">
                        <img src="{logo_data_uri}"
                             style="width: 140px; height: 140px; object-fit: contain;"
                        />
                    </div>
                </div>
            ''', unsafe_allow_html=True)

        st.markdown("""
            <h1 class="login-title">SafetyAI</h1>
            <p class="login-subtitle">Seu assistente de IA especializado em Saude e Seguranca do Trabalho</p>
            <div class="login-divider"></div>
        """, unsafe_allow_html=True)

        st.markdown("""
            <div class="login-features">
                <div class="login-feature">
                    <span class="feature-icon">&#9889;</span>
                    <span class="feature-text">Normas Regulamentadoras (NRs)</span>
                </div>
                <div class="login-feature">
                    <span class="feature-icon">&#128269;</span>
                    <span class="feature-text">Consultas CBO, CID, CNAE e CA</span>
                </div>
                <div class="login-feature">
                    <span class="feature-icon">&#128202;</span>
                    <span class="feature-text">Dimensionamento CIPA e SESMT</span>
                </div>
                <div class="login-feature">
                    <span class="feature-icon">&#128196;</span>
                    <span class="feature-text">Geracao de documentos e Drive</span>
                </div>
            </div>
        """, unsafe_allow_html=True)

        if auth_url:
            st.markdown(f"""
            <div class="login-btn-container">
                <a href="{auth_url}" target="_self" class="login-btn">
                    <svg class="google-logo" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                        <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
                        <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
                        <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
                        <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
                    </svg>
                    Entrar com Google
                </a>
            </div>
            """, unsafe_allow_html=True)
        else:
            if st.button("Entrar com Google", key="login_google_btn", use_container_width=True, type="primary"):
                get_user_drive_service_wrapper()
                st.rerun()

    if st.session_state.get("user_drive_auth_error"):
        st.error(f"Erro de autenticacao: {st.session_state.user_drive_auth_error}")
