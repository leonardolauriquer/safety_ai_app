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
        "bg": "rgba(74,222,128,0.07)",
        "border": "rgba(74,222,128,0.20)",
        "glow": "rgba(74,222,128,0.12)",
    },
    {
        "key": "sesmt_sizing",
        "icon": "engineering",
        "title": "SESMT",
        "label": "NR-04",
        "desc": "Calcule a composição do Serviço Especializado em Eng. de Segurança e Medicina do Trabalho.",
        "color": "#22D3EE",
        "bg": "rgba(34,211,238,0.07)",
        "border": "rgba(34,211,238,0.20)",
        "glow": "rgba(34,211,238,0.12)",
    },
    {
        "key": "emergency_brigade_sizing",
        "icon": "fire",
        "title": "Brigada",
        "label": "NBR 14276",
        "desc": "Dimensione a Brigada de Emergência conforme nível de risco e população do local.",
        "color": "#F87171",
        "bg": "rgba(248,113,113,0.07)",
        "border": "rgba(248,113,113,0.20)",
        "glow": "rgba(248,113,113,0.12)",
    },
]

_CARD_CSS = """
<style>
.hub-grid-card {
    background: var(--card-bg);
    border: 1px solid var(--card-border);
    border-radius: 14px;
    padding: 18px 18px 14px 18px;
    margin-bottom: 0;
    transition: box-shadow 0.18s ease, transform 0.15s ease, border-color 0.15s ease;
    min-height: 140px;
    display: flex;
    flex-direction: column;
    gap: 4px;
}
.hub-grid-card:hover {
    box-shadow: 0 0 18px var(--card-glow);
    border-color: var(--card-color);
    transform: translateY(-2px);
}
.hub-grid-icon { margin-bottom: 4px; }
.hub-grid-icon svg { width: 22px; height: 22px; color: var(--card-color); }
.hub-grid-title {
    font-size: 1.08em;
    font-weight: 700;
    color: var(--card-color);
    margin-bottom: 1px;
}
.hub-grid-label {
    color: #94A3B8;
    font-size: 0.70em;
    font-weight: 500;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    margin-bottom: 5px;
}
.hub-grid-desc {
    color: #64748B;
    font-size: 0.78em;
    line-height: 1.45;
    flex: 1;
}
div[data-testid="stButton"][data-key^="go_sz_"] > button {
    border-radius: 0 0 12px 12px !important;
    border-top: 1px solid rgba(255,255,255,0.04) !important;
    margin-top: -3px !important;
    font-size: 0.80em !important;
    padding: 6px 12px !important;
    min-height: 32px !important;
    letter-spacing: 0.02em !important;
    background: rgba(11,18,32,0.55) !important;
    color: #64748B !important;
    border-color: rgba(255,255,255,0.06) !important;
    box-shadow: none !important;
    transition: color 0.12s, background 0.12s !important;
}
div[data-testid="stButton"][data-key^="go_sz_"] > button:hover {
    color: #E2E8F0 !important;
    background: rgba(255,255,255,0.05) !important;
}
</style>
"""


def _render_sz_card(card: dict) -> None:
    icon_html = _get_material_icon_html(card["icon"])
    st.markdown(
        f"""
        <div class="hub-grid-card"
            style="--card-bg:{card['bg']};--card-border:{card['border']};
                   --card-color:{card['color']};--card-glow:{card['glow']};">
            <div class="hub-grid-icon">{icon_html}</div>
            <div class="hub-grid-title">{card['title']}</div>
            <div class="hub-grid-label">{card['label']}</div>
            <div class="hub-grid-desc">{card['desc']}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if st.button(f"→ Abrir {card['title']}", key=f"go_sz_{card['key']}", use_container_width=True):
        st.session_state.current_page = card["key"]
        st.rerun()


def sizing_page() -> None:
    inject_glass_styles()
    st.markdown(_CARD_CSS, unsafe_allow_html=True)

    with st.container():
        st.markdown(glass_marker(), unsafe_allow_html=True)
        st.markdown(
            f"""
            <div class="page-header">
                {_get_material_icon_html('calculator')}
                <h1>{THEME['phrases'].get('sizing', 'Dimensionamentos')}</h1>
            </div>
            <div class="page-subtitle">Ferramentas para dimensionamento de equipes e comissões de SST.</div>
            """,
            unsafe_allow_html=True,
        )

    cols = st.columns(3)
    for col, card in zip(cols, _SIZING_CARDS):
        with col:
            _render_sz_card(card)


if __name__ == "__main__":
    sizing_page()
