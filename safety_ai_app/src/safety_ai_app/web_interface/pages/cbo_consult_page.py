import html as html_module
import streamlit as st
import logging
from typing import List, Dict, Any, Optional
import unicodedata

from safety_ai_app.cbo_data_processor import CBODatabase
from safety_ai_app.theme_config import _get_material_icon_html, THEME
from safety_ai_app.web_interface.shared_styles import inject_glass_styles, glass_marker, render_back_button

logger = logging.getLogger(__name__)

_MAX_RESULTS = 30


def normalize_text(text: str) -> str:
    if not isinstance(text, str):
        return ""
    text = text.lower()
    text = unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode('utf-8')
    return text


@st.cache_resource(show_spinner=False)
def _load_cbo_db() -> Optional[CBODatabase]:
    try:
        return CBODatabase()
    except Exception as e:
        logger.critical(f"Erro ao inicializar CBODatabase: {e}", exc_info=True)
        return None


def cbo_consult_page() -> None:
    inject_glass_styles()

    render_back_button("← Consultas Rápidas", "quick_queries_page", "back_from_cbo")

    with st.container():
        st.markdown(glass_marker(), unsafe_allow_html=True)

        st.markdown(
            f"""
            <div class="page-header">
                {_get_material_icon_html('briefcase')}
                <h1>Consulta CBO</h1>
            </div>
            <div class="page-subtitle">
                Pesquise cargos da Classificação Brasileira de Ocupações por código ou nome.
            </div>
            """,
            unsafe_allow_html=True,
        )

        cbo_db = _load_cbo_db()

        if cbo_db is None or not cbo_db._cargos_dict:
            st.markdown(
                f"""
                <div class="info-hint" style="background:rgba(239,68,68,0.08);
                    border-color:rgba(239,68,68,0.25);color:#F87171;">
                    {_get_material_icon_html('alert')}
                    <b>Erro:</b> Dados da CBO não disponíveis.
                    Verifique se o arquivo 'CBO2025.xlsx' está acessível.
                </div>
                """,
                unsafe_allow_html=True,
            )
            return

        all_cargos = cbo_db.get_all_cargos()
        total_db = len(all_cargos)

        search_term = st.text_input(
            "Pesquise um cargo:",
            key="cbo_search_input",
            placeholder=f"Código ou nome — ex: Engenheiro de Segurança, 212315... ({total_db} cargos)",
            label_visibility="collapsed",
        ).strip()

        normalized_search = normalize_text(search_term)

        if not normalized_search or len(normalized_search) < 2:
            st.markdown(
                f"""
                <div class="info-hint">
                    {_get_material_icon_html('lightbulb')}
                    <b>Dica:</b> Digite ao menos 2 caracteres para pesquisar entre
                    <b>{total_db}</b> cargos disponíveis.
                </div>
                """,
                unsafe_allow_html=True,
            )
            return

        filtered = [
            c for c in all_cargos
            if normalized_search in normalize_text(c["CARGO"])
            or normalized_search in normalize_text(c["COD_OCUPACAO"])
        ]

        total = len(filtered)
        shown = filtered[:_MAX_RESULTS]

        if total == 0:
            st.markdown(
                f"""
                <div class="empty-state">
                    {_get_material_icon_html('search_off')}
                    <div>Nenhum cargo encontrado para
                    <b>"{html_module.escape(search_term)}"</b>.</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            return

        truncated_hint = (
            f" · mostrando primeiros {_MAX_RESULTS} — refine para ver mais"
            if total > _MAX_RESULTS else ""
        )
        st.markdown(
            f"""
            <div class="stats-line">
                <b>{total}</b> cargo{"s" if total != 1 else ""} encontrado{"s" if total != 1 else ""}{truncated_hint}
            </div>
            """,
            unsafe_allow_html=True,
        )

    for cargo in shown:
        code = cargo["COD_OCUPACAO"]
        name = cargo["CARGO"]
        areas_dict = cbo_db._cargos_dict[code].get("AREAS_DE_ATUACAO", {})
        area_count = len(areas_dict)
        activity_count = sum(len(v.get("ATIVIDADES", {})) for v in areas_dict.values())

        with st.expander(
            f"**{name}** — CBO {code}"
            + (f"  ·  {area_count} área{'s' if area_count != 1 else ''}" if area_count else ""),
            expanded=False,
        ):
            st.markdown(
                f"""
                <div style="display:flex;align-items:center;gap:10px;margin-bottom:10px;flex-wrap:wrap;">
                    <span class="result-code" style="font-size:1em;">CBO {code}</span>
                    <span class="result-meta">
                        {area_count} área{"s" if area_count != 1 else ""} ·
                        {activity_count} atividade{"s" if activity_count != 1 else ""}
                    </span>
                </div>
                """,
                unsafe_allow_html=True,
            )

            if not areas_dict:
                st.markdown(
                    '<div class="result-meta">Nenhuma área de atuação registrada.</div>',
                    unsafe_allow_html=True,
                )
                continue

            for area_name in sorted(areas_dict.keys()):
                activities = cbo_db.get_activities_by_cargo_and_area(code, area_name)
                st.markdown(
                    f"""
                    <div class="section-title" style="font-size:0.88em;margin:8px 0 6px 0;">
                        {_get_material_icon_html('category')} {area_name}
                        <span class="result-meta" style="margin-left:4px;">
                            ({len(activities)} atividade{"s" if len(activities) != 1 else ""})
                        </span>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                if activities:
                    rows_html = "".join([
                        f"""<div class="detail-row">
                                {_get_material_icon_html('check')}
                                <span><b>{a['NOME_ATIVIDADE']}</b>
                                <small class="result-meta"> · {a['COD_ATIVIDADE']}</small></span>
                            </div>"""
                        for a in activities
                    ])
                    st.markdown(rows_html, unsafe_allow_html=True)
                else:
                    st.markdown(
                        '<div class="result-meta">Nenhuma atividade detalhada.</div>',
                        unsafe_allow_html=True,
                    )
