import streamlit as st
import logging

from safety_ai_app.theme_config import THEME, _get_material_icon_html
from safety_ai_app.web_interface.shared_styles import inject_glass_styles, glass_marker

logger = logging.getLogger(__name__)

_SIZING_CARDS = [
    {
        "key": "cipa_sizing",
        "icon": "users",
        "title": "CIPA",
        "label": "NR-05",
        "desc": "Dimensione a Comissão Interna de Prevenção de Acidentes e de Assédio.",
        "color": "#4ADE80",
        "bg": "rgba(74,222,128,0.06)",
        "border": "rgba(74,222,128,0.18)",
    },
    {
        "key": "sesmt_sizing",
        "icon": "engineering",
        "title": "SESMT",
        "label": "NR-04",
        "desc": "Calcule a composição do Serviço Especializado em Eng. de Segurança e Medicina do Trabalho.",
        "color": "#22D3EE",
        "bg": "rgba(34,211,238,0.06)",
        "border": "rgba(34,211,238,0.18)",
    },
    {
        "key": "emergency_brigade_sizing",
        "icon": "fire",
        "title": "Brigada de Emergência",
        "label": "NBR 14276",
        "desc": "Dimensione a Brigada de Incêndio/Emergência conforme nível de risco e população.",
        "color": "#F87171",
        "bg": "rgba(248,113,113,0.06)",
        "border": "rgba(248,113,113,0.18)",
    },
]

_HUB_BTN_CSS = """
<style>
div[data-testid="stButton"]:has(button[kind="secondary"][data-testid*="go_"]) > button,
div[data-testid="stButton"]:has(button[key*="go_"]) > button {
    border-radius: 0 0 12px 12px !important;
    border-top: none !important;
    background: rgba(11,18,32,0.6) !important;
    color: #64748B !important;
    font-size: 0.80em !important;
    font-weight: 500 !important;
    padding: 5px 10px !important;
    min-height: 30px !important;
    letter-spacing: 0.01em !important;
    box-shadow: none !important;
    transition: all 0.12s ease !important;
}
div[data-testid="stButton"]:has(button[kind="secondary"][data-testid*="go_"]) > button:hover,
div[data-testid="stButton"]:has(button[key*="go_"]) > button:hover {
    color: #4ADE80 !important;
    background: rgba(74,222,128,0.06) !important;
    border-color: rgba(74,222,128,0.2) !important;
}
</style>
"""


def _render_sz_card(card: dict) -> None:
    icon_html = _get_material_icon_html(card["icon"])
    st.markdown(f"""
    <div class="hub-card" style="
        background:{card['bg']};
        border:1px solid {card['border']};
        border-bottom-color: rgba(11,18,32,0.4);
        color:{card['color']};
    ">
        <div class="hub-card-icon">{icon_html}</div>
        <div class="hub-card-title">{card['title']}</div>
        <div class="hub-card-label">{card['label']}</div>
        <div class="hub-card-desc">{card['desc']}</div>
    </div>
    """, unsafe_allow_html=True)
    if st.button(f"→ Abrir {card['title']}", key=f"go_{card['key']}", use_container_width=True):
        st.session_state.current_page = card["key"]
        st.rerun()


def sizing_page() -> None:
    inject_glass_styles()

    with st.container():
        st.markdown(glass_marker(), unsafe_allow_html=True)
        st.markdown(f'''
        <div class="page-header">
            {_get_material_icon_html('calculator')}
            <h1>{THEME['phrases'].get('sizing', 'Dimensionamentos')}</h1>
        </div>
        <div class="page-subtitle">Ferramentas para dimensionamento de equipes e comissões de SST.</div>
        ''', unsafe_allow_html=True)

    st.markdown(_HUB_BTN_CSS, unsafe_allow_html=True)

    cols = st.columns(3)
    for col, card in zip(cols, _SIZING_CARDS):
        with col:
            _render_sz_card(card)


if __name__ == "__main__":
    sizing_page()
