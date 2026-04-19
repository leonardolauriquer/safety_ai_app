import html as html_module
import streamlit as st
import logging
from typing import List, Dict, Any, Optional

from safety_ai_app.cnae_data_processor import CNAEDataProcessor
from safety_ai_app.theme_config import _get_material_icon_html, THEME
from safety_ai_app.web_interface.shared_styles import inject_glass_styles, glass_marker

logger = logging.getLogger(__name__)

_LEVEL_ORDER = ["Seção", "Divisão", "Grupo", "Classe", "Subclasse"]
_RISK_COLORS = {
    "1": "#4ADE80", "2": "#22D3EE", "3": "#F59E0B", "4": "#EF4444",
}


def _build_breadcrumb(entry: Dict[str, Any]) -> str:
    parts = []
    secao = entry.get("secao") or entry.get("divisao", {}).get("secao") or \
            entry.get("grupo", {}).get("divisao", {}).get("secao") or \
            entry.get("classe", {}).get("grupo", {}).get("divisao", {}).get("secao")
    if secao:
        parts.append(f"<span class='bc-part'>{secao.get('id')} {secao.get('descricao', '')[:30]}</span>")

    divisao = entry.get("divisao") or entry.get("grupo", {}).get("divisao") or \
              entry.get("classe", {}).get("grupo", {}).get("divisao")
    if divisao:
        parts.append(f"<span class='bc-part'>{divisao.get('id')} {divisao.get('descricao', '')[:30]}</span>")

    grupo = entry.get("grupo") or entry.get("classe", {}).get("grupo")
    if grupo:
        parts.append(f"<span class='bc-part'>{grupo.get('id')} {grupo.get('descricao', '')[:30]}</span>")

    classe = entry.get("classe")
    if classe:
        parts.append(f"<span class='bc-part'>{classe.get('id')} {classe.get('descricao', '')[:30]}</span>")

    if not parts:
        return ""
    return "<span class='bc-sep'>›</span>".join(parts)


def cnae_consult_page() -> None:
    inject_glass_styles()

    if st.button("← Consultas Rápidas", key="back_from_cnae"):
        st.session_state.current_page = "quick_queries_page"
        st.rerun()

    st.markdown("""
    <style>
    .cnae-card {
        background: rgba(15,23,42,0.5);
        border: 1px solid rgba(74,222,128,0.08);
        border-radius: 10px;
        padding: 12px 14px;
        margin-bottom: 8px;
        transition: all 0.12s;
    }
    .cnae-card:hover { background: rgba(74,222,128,0.04); border-color: rgba(74,222,128,0.15); }
    .cnae-title { color: #E2E8F0; font-size: 0.92em; font-weight: 500; margin-bottom: 5px; }
    .cnae-meta { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; margin-top: 4px; }
    .cnae-code { color: #4ADE80; font-family: monospace; font-size: 0.85em; font-weight: 600; }
    .cnae-level-badge {
        background: rgba(74,222,128,0.08);
        border: 1px solid rgba(74,222,128,0.15);
        border-radius: 4px;
        color: #4ADE80;
        font-size: 0.72em;
        padding: 1px 6px;
        font-weight: 500;
    }
    .risk-badge {
        border-radius: 4px;
        font-size: 0.72em;
        padding: 1px 7px;
        font-weight: 700;
        color: #0F172A;
    }
    .breadcrumb { color: #475569; font-size: 0.75em; margin-top: 5px; line-height: 1.5; }
    .bc-part { color: #64748B; }
    .bc-sep { color: #334155; margin: 0 3px; }
    .act-list { margin-top: 6px; padding-top: 6px; border-top: 1px solid rgba(74,222,128,0.06); }
    .act-item { color: #94A3B8; font-size: 0.78em; padding: 2px 0; }
    .act-more { color: #475569; font-size: 0.75em; font-style: italic; }
    .cnae-tabs div[role="tab"] { font-size: 0.82em !important; }
    </style>
    """, unsafe_allow_html=True)

    cnae_icon = _get_material_icon_html(THEME['icons'].get('cnae_consult', 'building'))
    search_icon = _get_material_icon_html(THEME['icons'].get('search_magnifying_glass', 'search'))

    cnae_processor: Optional[CNAEDataProcessor] = None
    try:
        cnae_processor = CNAEDataProcessor()
    except Exception as e:
        logger.critical(f"Erro ao inicializar CNAEDataProcessor: {e}", exc_info=True)
        st.error(f"Erro ao carregar dados da CNAE: {e}")
        return

    if cnae_processor is None:
        st.error("Serviço de dados da CNAE não disponível.")
        return

    with st.container():
        st.markdown(glass_marker(), unsafe_allow_html=True)

        st.markdown(f'''
        <div class="page-header">
            {cnae_icon}
            <h1>Consulta CNAE</h1>
        </div>
        <div class="page-subtitle">Classificação Nacional de Atividades Econômicas (IBGE)</div>
        ''', unsafe_allow_html=True)

        c1, c2 = st.columns([0.35, 0.65])
        with c1:
            level = st.radio(
                "Nível",
                _LEVEL_ORDER,
                index=1,
                key="cnae_level",
                horizontal=True,
                label_visibility="collapsed"
            )
        with c2:
            search = st.text_input(
                "Buscar",
                placeholder="Ex: 0111-3/01, 01.11-3, A",
                label_visibility="collapsed"
            ).strip()

        results: List[Dict[str, Any]] = []

        if search:
            with st.spinner(""):
                try:
                    level_map = {
                        "Seção": "secoes", "Divisão": "divisoes", "Grupo": "grupos",
                        "Classe": "classes", "Subclasse": "subclasses",
                    }
                    api_level = level_map.get(level)
                    if api_level:
                        cleaned = search.replace('.', '').replace('-', '').replace('/', '')
                        results = cnae_processor.search_cnae_by_id(cleaned, api_level)
                except Exception as e:
                    logger.error(f"Erro ao buscar CNAE: {e}", exc_info=True)
                    st.error(f"Erro na busca: {e}")

            CNAE_LIMIT = 50
            if results:
                total_found = len(results)
                displayed = results[:CNAE_LIMIT]

                if total_found > CNAE_LIMIT:
                    st.markdown(f'<div class="stats-line">Exibindo <b>{CNAE_LIMIT}</b> de <b>{total_found}</b> resultados &mdash; refine para ver mais específicos.</div>', unsafe_allow_html=True)
                else:
                    st.markdown(f'<div class="stats-line"><b>{total_found}</b> resultado{"s" if total_found != 1 else ""} encontrado{"s" if total_found != 1 else ""}</div>', unsafe_allow_html=True)

                for entry in displayed:
                    cnae_id = entry.get('id', 'N/A')
                    desc = html_module.escape(entry.get('descricao', 'N/A'))
                    grau = str(entry.get('grau_de_risco', '') or '')

                    risk_color = _RISK_COLORS.get(grau, "#64748B")
                    risk_badge = (
                        f'<span class="risk-badge" style="background:{risk_color};">GR {grau}</span>'
                        if grau else ''
                    )

                    breadcrumb = _build_breadcrumb(entry)
                    bc_html = f'<div class="breadcrumb">{breadcrumb}</div>' if breadcrumb else ''

                    activities = entry.get('atividades', [])
                    act_html = ''
                    if activities:
                        items = ''.join([f'<div class="act-item">· {html_module.escape(str(a))}</div>' for a in activities[:4]])
                        more = f'<div class="act-more">+ {len(activities)-4} atividade(s)</div>' if len(activities) > 4 else ''
                        act_html = f'<div class="act-list">{items}{more}</div>'

                    st.markdown(f'''
                    <div class="cnae-card">
                        <div class="cnae-title">{desc}</div>
                        <div class="cnae-meta">
                            <span class="cnae-code">{cnae_id}</span>
                            <span class="cnae-level-badge">{level}</span>
                            {risk_badge}
                        </div>
                        {bc_html}
                        {act_html}
                    </div>
                    ''', unsafe_allow_html=True)
            else:
                st.markdown(f'''
                <div class="empty-state">
                    {search_icon}
                    <div>Nenhum CNAE encontrado para "{html_module.escape(search)}" no nível {html_module.escape(level)}</div>
                </div>
                ''', unsafe_allow_html=True)
        else:
            st.markdown(f'''
            <div class="info-hint">
                <b>Dica:</b> Digite um código CNAE e selecione o nível para pesquisar
            </div>
            ''', unsafe_allow_html=True)
