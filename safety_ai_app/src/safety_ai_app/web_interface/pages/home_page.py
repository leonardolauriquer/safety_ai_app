import streamlit as st
import logging

from safety_ai_app.theme_config import THEME, get_icon, render_hero_section
from safety_ai_app.web_interface.shared_styles import inject_glass_styles, glass_marker

logger = logging.getLogger(__name__)

_FEATURES = [
    {
        "icon": "chat",
        "title": "Chat Inteligente",
        "description": "Pergunte sobre NRs, legislação e boas práticas em SST.",
        "page_key": "chat",
        "color": "#4ADE80",
    },
    {
        "icon": "library",
        "title": "Base de Conhecimento",
        "description": "Gerencie documentos e integre-os à IA via Google Drive.",
        "page_key": "library",
        "color": "#22D3EE",
    },
    {
        "icon": "search",
        "title": "Consultas Rápidas",
        "description": "CBO, CID, CNAE, CA/EPI e multas NR 28 em segundos.",
        "page_key": "quick_queries_page",
        "color": "#818CF8",
    },
    {
        "icon": "calculator",
        "title": "Dimensionamentos",
        "description": "Calcule SESMT, CIPA e Brigada conforme as NRs.",
        "page_key": "sizing_page",
        "color": "#F59E0B",
    },
    {
        "icon": "document",
        "title": "Geradores de Documentos",
        "description": "Gere APR e ATA de CIPA automaticamente.",
        "page_key": "apr_generator",
        "color": "#34D399",
    },
    {
        "icon": "news",
        "title": "Notícias SST",
        "description": "Mantenha-se atualizado com as últimas novidades em SST.",
        "page_key": "news_feed",
        "color": "#F472B6",
    },
]

_WHY_CARDS = [
    ("check",   "Conformidade",  "Atualizado com as últimas NRs e legislações vigentes."),
    ("speed",   "Eficiência",    "Automatize consultas complexas e economize tempo."),
    ("brain",   "Inteligência",  "IA para análises profundas e insights estratégicos."),
    ("shield",  "Segurança",     "Promova ambientes de trabalho mais seguros."),
    ("rocket",  "Inovação",      "Ferramentas modernas para aprendizado contínuo."),
]

_HUB_BTN_CSS = """
<style>
div[data-testid="stButton"][data-key^="feature_"] > button {
    border-radius: 0 0 10px 10px !important;
    border-top: 1px solid rgba(255,255,255,0.04) !important;
    background: rgba(11,18,32,0.5) !important;
    color: #64748B !important;
    font-size: 0.80em !important;
    font-weight: 500 !important;
    padding: 5px 10px !important;
    min-height: 30px !important;
    letter-spacing: 0.01em !important;
    box-shadow: none !important;
    transition: all 0.12s ease !important;
}
div[data-testid="stButton"][data-key^="feature_"] > button:hover {
    color: #4ADE80 !important;
    background: rgba(74,222,128,0.06) !important;
}
div[data-testid="stButton"][data-key="start_chat"] > button {
    background: linear-gradient(135deg, #4ADE80, #22D3EE) !important;
    color: #020617 !important;
    font-weight: 700 !important;
    font-size: 1em !important;
    border: none !important;
    border-radius: 10px !important;
    box-shadow: 0 0 18px rgba(74,222,128,0.35) !important;
    letter-spacing: 0.03em !important;
}
div[data-testid="stButton"][data-key="start_chat"] > button:hover {
    box-shadow: 0 0 28px rgba(74,222,128,0.55) !important;
    transform: translateY(-1px) !important;
}
</style>
"""


def home_page() -> None:
    inject_glass_styles()
    st.markdown(_HUB_BTN_CSS, unsafe_allow_html=True)

    st.markdown(render_hero_section(
        title="Bem-vindo ao SafetyAI!",
        subtitle="Seu assistente especializado em Saúde e Segurança do Trabalho no Brasil — NRs, dimensionamentos, documentos e muito mais.",
        icon_key="robot"
    ), unsafe_allow_html=True)

    _, col_btn, _ = st.columns([1, 2, 1])
    with col_btn:
        if st.button("Começar a Conversar", key="start_chat", use_container_width=True):
            st.session_state.current_page = "chat"
            st.query_params["page"] = "chat"
            st.query_params["sync_done"] = "true"
            st.rerun()

    with st.container():
        st.markdown(glass_marker(), unsafe_allow_html=True)
        st.markdown(f"""
        <div class="section-title">
            {get_icon('tools')} Ferramentas Disponíveis
        </div>
        """, unsafe_allow_html=True)

        cols = st.columns(3)
        for i, feature in enumerate(_FEATURES):
            with cols[i % 3]:
                st.markdown(f"""
                <div class="hub-card" style="
                    background:rgba(15,23,42,0.5);
                    border:1px solid rgba(148,163,184,0.1);
                    border-bottom-color:rgba(11,18,32,0.4);
                    color:{feature['color']};
                ">
                    <div class="hub-card-icon">{get_icon(feature['icon'])}</div>
                    <div class="hub-card-title">{feature['title']}</div>
                    <div class="hub-card-desc">{feature['description']}</div>
                </div>
                """, unsafe_allow_html=True)
                if st.button("→ Explorar", key=f"feature_{feature['page_key']}", use_container_width=True):
                    st.session_state.current_page = feature["page_key"]
                    st.query_params["page"] = feature["page_key"]
                    st.query_params["sync_done"] = "true"
                    st.rerun()

    with st.container():
        st.markdown(glass_marker(), unsafe_allow_html=True)
        cards_html = "".join([
            f"""<div class="result-card" style="margin-bottom:8px;">
                    <div class="detail-row">
                        {get_icon(icon)}
                        <div class="result-title">{title}</div>
                    </div>
                    <div class="result-detail">{desc}</div>
                </div>"""
            for icon, title, desc in _WHY_CARDS
        ])
        st.markdown(f"""
        <div class="section-title">
            {get_icon('lightbulb')} Por que usar o SafetyAI?
        </div>
        <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:10px;margin-top:8px;">
            {cards_html}
        </div>
        """, unsafe_allow_html=True)

    st.markdown(f"""
    <div class="info-hint">
        {get_icon('info')} <b>Dica:</b> Use o menu lateral para navegar rapidamente entre todas as funcionalidades.
    </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
    home_page()
