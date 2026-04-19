import streamlit as st
import logging
from typing import Any, Dict, List

from safety_ai_app.theme_config import THEME, get_icon, render_hero_section, render_feature_card
from safety_ai_app.web_interface.shared_styles import inject_glass_styles, glass_marker

logger = logging.getLogger(__name__)

def home_page() -> None:
    """
    Renderiza a página inicial da aplicação SafetyAI com o novo design Cyber-Neon.
    """
    inject_glass_styles()
    
    st.markdown(render_hero_section(
        title="Bem-vindo ao SafetyAI!",
        subtitle="Seu assistente de IA especializado em Saúde e Segurança do Trabalho (SST) no Brasil. Tenha acesso rápido a NRs, dimensionamentos, consultas e muito mais!",
        icon_key="robot"
    ), unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("🚀 Começar a Conversar", key="start_chat_button", use_container_width=True):
            st.session_state.current_page = 'chat'
            st.query_params["page"] = 'chat'
            st.query_params["sync_done"] = "true"
            st.rerun()

    with st.container():
        st.markdown(glass_marker(), unsafe_allow_html=True)
        st.markdown(f"""
        <div class="section-title">
            {get_icon('tools')} Nossas Ferramentas
        </div>
        """, unsafe_allow_html=True)

        features = [
            {
                "icon": "chat",
                "title": "Chat Inteligente",
                "description": "Pergunte sobre NRs, legislação, boas práticas em SST e obtenha respostas rápidas e precisas.",
                "page_key": "chat"
            },
            {
                "icon": "library",
                "title": "Gestão de Documentos",
                "description": "Carregue e consulte seus documentos internos, integrando-os à base de conhecimento da IA.",
                "page_key": "library"
            },
            {
                "icon": "search",
                "title": "Consultas Rápidas",
                "description": "Acesse informações sobre CBO, CID, CNAE, CA e multas de forma instantânea.",
                "page_key": "quick_queries_page"
            },
            {
                "icon": "calculator",
                "title": "Dimensionamentos",
                "description": "Calcule SESMT, CIPA e Brigada de Emergência conforme as normas regulamentadoras.",
                "page_key": "sizing_page"
            },
            {
                "icon": "news",
                "title": "Notícias e Avisos",
                "description": "Mantenha-se atualizado com as últimas notícias do mundo da Saúde e Segurança do Trabalho.",
                "page_key": "news_feed"
            },
            {
                "icon": "gamepad",
                "title": "Jogos e Desafios",
                "description": "Teste seus conhecimentos em SST com quizzes e palavras cruzadas interativas.",
                "page_key": "games_page"
            }
        ]

        cols = st.columns(3)
        for i, feature in enumerate(features):
            with cols[i % 3]:
                st.markdown(f'<div class="result-card">', unsafe_allow_html=True)
                st.markdown(render_feature_card(
                    icon_key=feature['icon'],
                    title=feature['title'],
                    description=feature['description']
                ), unsafe_allow_html=True)
                
                if st.button(f"Explorar", key=f"explore_{feature['page_key']}_button", use_container_width=True):
                    st.session_state.current_page = feature['page_key']
                    st.query_params["page"] = feature['page_key']
                    st.query_params["sync_done"] = "true"
                    st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)

    with st.container():
        st.markdown(glass_marker(), unsafe_allow_html=True)
        st.markdown(f"""
        <div class="section-title">
            {get_icon('lightbulb')} Por que escolher o SafetyAI?
        </div>
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 16px; margin-top: 10px;">
            <div class="result-card">
                <div class="detail-row">
                    {get_icon('check')}
                    <div class="result-title">Conformidade</div>
                </div>
                <div class="result-detail">Mantenha-se atualizado com as últimas NRs e legislações vigentes.</div>
            </div>
            <div class="result-card">
                <div class="detail-row">
                    {get_icon('speed')}
                    <div class="result-title">Eficiência</div>
                </div>
                <div class="result-detail">Automatize consultas complexas e economize tempo precioso na sua rotina.</div>
            </div>
            <div class="result-card">
                <div class="detail-row">
                    {get_icon('brain')}
                    <div class="result-title">Inteligência</div>
                </div>
                <div class="result-detail">Utilize o poder da IA para análises profundas e insights estratégicos em SST.</div>
            </div>
            <div class="result-card">
                <div class="detail-row">
                    {get_icon('shield')}
                    <div class="result-title">Segurança</div>
                </div>
                <div class="result-detail">Promova um ambiente de trabalho mais seguro e saudável para todos.</div>
            </div>
            <div class="result-card">
                <div class="detail-row">
                    {get_icon('rocket')}
                    <div class="result-title">Inovação</div>
                </div>
                <div class="result-detail">Acesso a ferramentas modernas para o aprendizado contínuo e evolução.</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown(f"""
    <div class="info-hint">
        <b>Dica:</b> Use o menu lateral para navegar rapidamente entre todas as funcionalidades do SafetyAI.
    </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    home_page()
