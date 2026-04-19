import html as html_module
import streamlit as st
import logging
from typing import List, Dict, Any, Optional
import unicodedata

from safety_ai_app.cbo_data_processor import CBODatabase
from safety_ai_app.theme_config import _get_material_icon_html, THEME
from safety_ai_app.web_interface.shared_styles import inject_glass_styles, glass_marker, render_back_button

logger = logging.getLogger(__name__)

_MAX_RESULTS = 40


def normalize_text(text: str) -> str:
    if not isinstance(text, str):
        return ""
    text = text.lower()
    text = unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode('utf-8')
    return text


def cbo_consult_page() -> None:
    inject_glass_styles()

    render_back_button("← Consultas Rápidas", "quick_queries_page", "back_from_cbo")

    with st.container():
        st.markdown(glass_marker(), unsafe_allow_html=True)

        st.markdown(f"""
            <div class="page-header">
                {_get_material_icon_html('briefcase')}
                <h1>Consulta CBO</h1>
            </div>
            <div class="page-subtitle">
                Pesquise cargos da Classificação Brasileira de Ocupações por código ou nome.
            </div>
        """, unsafe_allow_html=True)

        cbo_db: Optional[CBODatabase] = None
        with st.spinner("Carregando dados da CBO..."):
            try:
                cbo_db = CBODatabase()
            except Exception as e:
                logger.critical(f"Erro crítico ao inicializar CBODatabase: {e}", exc_info=True)
                st.markdown(f"""
                    <div class="info-hint">
                        {_get_material_icon_html('alert')}
                        <b>Erro Crítico:</b> Não foi possível carregar os dados da CBO. Detalhes: {e}
                    </div>
                """, unsafe_allow_html=True)
                st.stop()
                return

        if cbo_db is None or not cbo_db._cargos_dict:
            st.markdown(f"""
                <div class="info-hint">
                    {_get_material_icon_html('warning')}
                    <b>Aviso:</b> Dados da CBO não disponíveis. Verifique se o arquivo 'CBO2025.xlsx' está acessível.
                </div>
            """, unsafe_allow_html=True)
            return

        all_cargos = cbo_db.get_all_cargos()

        search_term = st.text_input(
            "Pesquise um cargo:",
            key="cbo_search_input",
            placeholder="Ex: Engenheiro de Segurança, 212315...",
            label_visibility="collapsed"
        ).strip()

        normalized_search = normalize_text(search_term)

        if not normalized_search or len(normalized_search) < 2:
            st.markdown(f"""
                <div class="info-hint">
                    {_get_material_icon_html('lightbulb')}
                    <b>Dica:</b> Digite ao menos 2 caracteres para pesquisar entre <b>{len(all_cargos)}</b> cargos disponíveis.
                </div>
            """, unsafe_allow_html=True)
            return

        filtered = [
            c for c in all_cargos
            if normalized_search in normalize_text(c["CARGO"])
            or normalized_search in normalize_text(c["COD_OCUPACAO"])
        ]

        total = len(filtered)
        shown = filtered[:_MAX_RESULTS]

        if total == 0:
            st.markdown(f"""
                <div class="empty-state">
                    {_get_material_icon_html('search_off')}
                    <div>Nenhum cargo encontrado para <b>"{html_module.escape(search_term)}"</b>.</div>
                </div>
            """, unsafe_allow_html=True)
            return

        truncated_hint = f" · mostrando primeiros {_MAX_RESULTS}" if total > _MAX_RESULTS else ""
        st.markdown(f"""
            <div class="stats-line">
                <b>{total}</b> cargo{"s" if total != 1 else ""} encontrado{"s" if total != 1 else ""}{truncated_hint}
                {f'— refine a busca para ver menos resultados' if total > _MAX_RESULTS else ''}
            </div>
        """, unsafe_allow_html=True)

        cargo_options = ["-- Selecione um Cargo --"] + [
            f"{c['CARGO']} (Cód: {c['COD_OCUPACAO']})" for c in shown
        ]
        code_map = {
            f"{c['CARGO']} (Cód: {c['COD_OCUPACAO']})": c["COD_OCUPACAO"]
            for c in shown
        }

        selected_display = st.selectbox(
            "Cargo:",
            options=cargo_options,
            index=0,
            key="cbo_cargo_select",
            label_visibility="collapsed"
        )

        selected_code = code_map.get(selected_display)

        if not selected_code:
            st.markdown(f"""
                <div class="info-hint">
                    {_get_material_icon_html('info')}
                    <b>Dica:</b> Selecione um cargo na lista acima para ver detalhes e atividades.
                </div>
            """, unsafe_allow_html=True)
            return

        cargo_name = cbo_db.get_cargo_name_by_code(selected_code)

        st.markdown(f"""
            <div class="result-card">
                <div class="result-title">{cargo_name}</div>
                <div class="result-code">CBO: {selected_code}</div>
                <div class="result-meta">Áreas de atuação e atividades regulamentadas</div>
            </div>
        """, unsafe_allow_html=True)

        st.markdown(f"""
            <div class="section-title">
                {_get_material_icon_html('category')}
                Áreas de Atuação
            </div>
        """, unsafe_allow_html=True)

        areas_dict = cbo_db._cargos_dict[selected_code].get("AREAS_DE_ATUACAO", {})

        if not areas_dict:
            st.markdown(f"""
                <div class="info-hint">
                    {_get_material_icon_html('info')}
                    Nenhuma área de atuação registrada para este cargo.
                </div>
            """, unsafe_allow_html=True)
            return

        for area_name in sorted(areas_dict.keys()):
            activities = cbo_db.get_activities_by_cargo_and_area(selected_code, area_name)
            with st.expander(f"📍 {area_name} ({len(activities)} atividade{'s' if len(activities) != 1 else ''})"):
                if activities:
                    rows_html = "".join([
                        f"""<div class="detail-row">
                                {_get_material_icon_html('check')}
                                <span><b>{a['NOME_ATIVIDADE']}</b>
                                <small class="result-meta"> · Cód: {a['COD_ATIVIDADE']}</small></span>
                            </div>"""
                        for a in activities
                    ])
                    st.markdown(rows_html, unsafe_allow_html=True)
                else:
                    st.markdown('<div class="result-meta">Nenhuma atividade detalhada disponível.</div>', unsafe_allow_html=True)
