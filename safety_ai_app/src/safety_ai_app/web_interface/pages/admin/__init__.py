"""
Painel de Administração — SafetyAI
Ponto de entrada do pacote admin/.

Este módulo orquestra as 5 abas do painel, delegando cada uma
para o módulo responsável. Mantém compatibilidade retroativa com
quaisquer imports do `admin_panel_page.render_page`.
"""

import streamlit as st

from safety_ai_app.web_interface.shared_styles import inject_glass_styles
from safety_ai_app.web_interface.pages.admin._helpers import _is_admin
from safety_ai_app.web_interface.pages.admin._tab_overview import _tab_overview
from safety_ai_app.web_interface.pages.admin._tab_logs import _tab_logs
from safety_ai_app.web_interface.pages.admin._tab_plans import _tab_plans
from safety_ai_app.web_interface.pages.admin._tab_advanced_config import _tab_advanced_config
from safety_ai_app.web_interface.pages.admin._tab_ai_pipeline import _tab_ai_pipeline


def render_page() -> None:
    inject_glass_styles()

    if not _is_admin():
        st.markdown("""
            <div style="
                text-align:center; padding:60px 20px;
                background:rgba(239,68,68,0.06);
                border:1px solid rgba(239,68,68,0.2);
                border-radius:16px; margin-top:40px;
            ">
                <div style="font-size:2.5em; margin-bottom:12px;">🔒</div>
                <div style="color:#EF4444; font-size:1.1em; font-weight:600; margin-bottom:8px;">
                    Acesso Restrito
                </div>
                <div style="color:#94A3B8; font-size:0.88em;">
                    Esta página é exclusiva para administradores do SafetyAI.<br>
                    Se acredita ser administrador, verifique se o seu email está configurado.
                </div>
            </div>
        """, unsafe_allow_html=True)
        st.stop()
        return

    st.markdown("""
        <div class="page-header">
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor">
                <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"/>
            </svg>
            <h1>Painel de Administração</h1>
        </div>
        <p class="page-subtitle">Controlo total do SafetyAI — logs, planos, configurações e métricas de IA.</p>
    """, unsafe_allow_html=True)

    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📊 Visão Geral",
        "📋 Logs do Sistema",
        "💳 Planos & Preços",
        "⚙️ Configurações Avançadas",
        "🤖 Pipeline de IA",
    ])

    with tab1:
        _tab_overview()

    with tab2:
        _tab_logs()

    with tab3:
        _tab_plans()

    with tab4:
        _tab_advanced_config()

    with tab5:
        _tab_ai_pipeline()


__all__ = ["render_page"]
