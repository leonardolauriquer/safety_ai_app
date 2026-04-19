import streamlit as st
import logging
from safety_ai_app.theme_config import THEME, _get_material_icon_html
from safety_ai_app.web_interface.shared_styles import inject_glass_styles, glass_marker

logger = logging.getLogger(__name__)

_CARDS = [
    {
        "key": "cbo_consult",
        "icon": "briefcase",
        "title": "CBO",
        "label": "Ocupações",
        "desc": "Classificação Brasileira de Ocupações — busque por código ou nome do cargo.",
        "color": "#4ADE80",
        "bg": "rgba(74,222,128,0.06)",
        "border": "rgba(74,222,128,0.18)",
    },
    {
        "key": "cid_consult",
        "icon": "medical",
        "title": "CID",
        "label": "Doenças",
        "desc": "Classificação Internacional de Doenças — CID-10 local ou CID-11 via API.",
        "color": "#22D3EE",
        "bg": "rgba(34,211,238,0.06)",
        "border": "rgba(34,211,238,0.18)",
    },
    {
        "key": "cnae_consult",
        "icon": "building",
        "title": "CNAE",
        "label": "Atividades Econômicas",
        "desc": "Classificação Nacional de Atividades Econômicas com grau de risco (IBGE).",
        "color": "#818CF8",
        "bg": "rgba(129,140,248,0.06)",
        "border": "rgba(129,140,248,0.18)",
    },
    {
        "key": "ca_consult",
        "icon": "certificate",
        "title": "CA / EPI",
        "label": "Certificados de Aprovação",
        "desc": "Consulte CAs de EPIs por número, fabricante ou tipo de equipamento.",
        "color": "#F59E0B",
        "bg": "rgba(245,158,11,0.06)",
        "border": "rgba(245,158,11,0.18)",
    },
    {
        "key": "fines_consult",
        "icon": "gavel",
        "title": "Multas NR 28",
        "label": "Penalidades",
        "desc": "Calcule multas por infrações a NRs com base no porte da empresa.",
        "color": "#F87171",
        "bg": "rgba(248,113,113,0.06)",
        "border": "rgba(248,113,113,0.18)",
    },
]

_HUB_CSS = """
<style>
.qq-card {
    border-radius: 12px;
    padding: 18px 16px 42px 16px;
    position: relative;
    overflow: hidden;
    margin-bottom: 2px;
    transition: all 0.15s ease;
    min-height: 150px;
}
.qq-card:hover { transform: translateY(-1px); }
.qq-card-icon { margin-bottom: 10px; }
.qq-card-icon svg { width: 22px; height: 22px; }
.qq-card-title {
    font-size: 1.1em;
    font-weight: 700;
    margin-bottom: 2px;
}
.qq-card-label {
    color: #94A3B8;
    font-size: 0.72em;
    font-weight: 500;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    margin-bottom: 8px;
}
.qq-card-desc {
    color: #64748B;
    font-size: 0.79em;
    line-height: 1.45;
}
</style>
"""


def _render_card(card: dict) -> None:
    icon_html = _get_material_icon_html(card["icon"])
    st.markdown(f"""
    <div class="qq-card" style="
        background:{card['bg']};
        border:1px solid {card['border']};
        color:{card['color']};
    ">
        <div class="qq-card-icon">{icon_html}</div>
        <div class="qq-card-title">{card['title']}</div>
        <div class="qq-card-label">{card['label']}</div>
        <div class="qq-card-desc">{card['desc']}</div>
    </div>
    """, unsafe_allow_html=True)
    if st.button(f"→ Abrir {card['title']}", key=f"go_{card['key']}", use_container_width=True):
        st.session_state.current_page = card["key"]
        st.rerun()


def quick_queries_page() -> None:
    inject_glass_styles()
    st.markdown(_HUB_CSS, unsafe_allow_html=True)

    with st.container():
        st.markdown(glass_marker(), unsafe_allow_html=True)
        st.markdown(f'''
        <div class="page-header">
            {_get_material_icon_html('search')}
            <h1>{THEME['phrases']['quick_consults']}</h1>
        </div>
        <div class="page-subtitle">Acesso rápido às ferramentas de consulta em SST.</div>
        ''', unsafe_allow_html=True)

    row1 = st.columns(3)
    row2_left, row2_center, row2_right = st.columns([1, 1, 1])

    with row1[0]:
        _render_card(_CARDS[0])
    with row1[1]:
        _render_card(_CARDS[1])
    with row1[2]:
        _render_card(_CARDS[2])

    with row2_left:
        _render_card(_CARDS[3])
    with row2_center:
        _render_card(_CARDS[4])


if __name__ == "__main__":
    quick_queries_page()
