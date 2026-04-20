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
        "bg": "rgba(74,222,128,0.07)",
        "border": "rgba(74,222,128,0.20)",
        "glow": "rgba(74,222,128,0.12)",
    },
    {
        "key": "cid_consult",
        "icon": "medical",
        "title": "CID",
        "label": "Doenças",
        "desc": "Classificação Internacional de Doenças — CID-10 local ou CID-11 via API.",
        "color": "#22D3EE",
        "bg": "rgba(34,211,238,0.07)",
        "border": "rgba(34,211,238,0.20)",
        "glow": "rgba(34,211,238,0.12)",
    },
    {
        "key": "cnae_consult",
        "icon": "building",
        "title": "CNAE",
        "label": "Atividades Econômicas",
        "desc": "Classificação Nacional de Atividades Econômicas com grau de risco (IBGE).",
        "color": "#818CF8",
        "bg": "rgba(129,140,248,0.07)",
        "border": "rgba(129,140,248,0.20)",
        "glow": "rgba(129,140,248,0.12)",
    },
    {
        "key": "ca_consult",
        "icon": "certificate",
        "title": "CA / EPI",
        "label": "Certificados de Aprovação",
        "desc": "Consulte CAs de EPIs por número, fabricante ou tipo de equipamento.",
        "color": "#F59E0B",
        "bg": "rgba(245,158,11,0.07)",
        "border": "rgba(245,158,11,0.20)",
        "glow": "rgba(245,158,11,0.12)",
    },
    {
        "key": "fines_consult",
        "icon": "gavel",
        "title": "Multas NR 28",
        "label": "Penalidades",
        "desc": "Calcule multas por infrações a NRs com base no porte da empresa.",
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
    cursor: pointer;
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
/* Hub button full-width bottom flush */
div[data-testid="stButton"][data-key^="go_"] > button {
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
div[data-testid="stButton"][data-key^="go_"] > button:hover {
    color: #E2E8F0 !important;
    background: rgba(255,255,255,0.05) !important;
}
</style>
"""


def _render_card(card: dict) -> None:
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
    if st.button(f"→ Abrir {card['title']}", key=f"go_{card['key']}", use_container_width=True):
        st.session_state.current_page = card["key"]
        st.rerun()


def quick_queries_page() -> None:
    inject_glass_styles()
    st.markdown(_CARD_CSS, unsafe_allow_html=True)

    with st.container():
        st.markdown(glass_marker(), unsafe_allow_html=True)
        st.markdown(
            f"""
            <div class="page-header">
                {_get_material_icon_html('search')}
                <h1>{THEME['phrases']['quick_consults']}</h1>
            </div>
            <div class="page-subtitle">Acesso rápido às ferramentas de consulta em SST.</div>
            """,
            unsafe_allow_html=True,
        )

    row1 = st.columns(3)
    row2_left, row2_center, _ = st.columns([1, 1, 1])

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
