import html as html_module
import streamlit as st
import logging
from typing import List, Dict, Optional
import re

from safety_ai_app.cid_data_processor import CIDDatabase
from safety_ai_app.theme_config import _get_material_icon_html, THEME
from safety_ai_app.web_interface.shared_styles import inject_glass_styles, glass_marker, render_back_button
from safety_ai_app.security.rate_limiter import check_rate_limit, RateLimitExceeded
from safety_ai_app.security.security_logger import log_security_event, SecurityEvent

logger = logging.getLogger(__name__)

_MAX_RESULTS = 50


def strip_html_tags(text: str) -> str:
    clean = re.compile('<.*?>')
    return re.sub(clean, '', text)


def cid_consult_page() -> None:
    inject_glass_styles()

    render_back_button("← Consultas Rápidas", "quick_queries_page", "back_from_cid")

    medical_icon = _get_material_icon_html(THEME['icons'].get('cid_consult', 'medical'))
    search_icon = _get_material_icon_html(THEME['icons'].get('search_magnifying_glass', 'search'))

    cid_db: Optional[CIDDatabase] = None
    try:
        cid_db = CIDDatabase()
    except Exception as e:
        logger.critical(f"Erro ao inicializar CIDDatabase: {e}", exc_info=True)
        st.markdown(f'''
        <div class="info-hint" style="background:rgba(239,68,68,0.08);border-color:rgba(239,68,68,0.25);color:#F87171;">
            {_get_material_icon_html("alert")}
            <b>Erro:</b> Não foi possível carregar os dados do CID. {e}
        </div>
        ''', unsafe_allow_html=True)
        return

    if cid_db is None:
        st.markdown(f'''
        <div class="info-hint" style="background:rgba(239,68,68,0.08);border-color:rgba(239,68,68,0.25);color:#F87171;">
            {_get_material_icon_html("alert")}
            <b>Erro:</b> Serviço de dados do CID não disponível.
        </div>
        ''', unsafe_allow_html=True)
        return

    with st.container():
        st.markdown(glass_marker(), unsafe_allow_html=True)

        st.markdown(f'''
        <div class="page-header">
            {medical_icon}
            <h1>Consulta CID</h1>
        </div>
        <div class="page-subtitle">Pesquise na Classificação Internacional de Doenças (CID-10 ou CID-11)</div>
        ''', unsafe_allow_html=True)

        c1, c2 = st.columns([0.3, 0.7])
        with c1:
            version = st.radio(
                "Versão",
                ("CID-11", "CID-10"),
                key="cid_version",
                horizontal=True,
                label_visibility="collapsed"
            )
        with c2:
            placeholder = "Ex: Cólera, Diabetes, A00.0" if version == "CID-11" else "Código ou descrição CID-10"
            search = st.text_input("Buscar", placeholder=placeholder, label_visibility="collapsed").strip()

        if not search:
            st.markdown(f'''
            <div class="info-hint">
                <b>Dica:</b> Digite um código ou descrição para pesquisar CIDs.
                {f'Use a versão CID-11 para a classificação mais atual.' if version == "CID-11" else 'CID-10 usa dados locais — busca instantânea.'}
            </div>
            ''', unsafe_allow_html=True)
            return

        results: List[Dict[str, str]] = []
        fallback_msg = ""

        with st.spinner(""):
            if version == "CID-11":
                try:
                    check_rate_limit("icd_api")
                except RateLimitExceeded:
                    try:
                        log_security_event(
                            SecurityEvent.RATE_LIMIT_EXCEEDED,
                            feature="icd_api",
                            extra={"version": version},
                        )
                    except Exception as log_err:
                        logger.warning(f"Falha ao registrar rate-limit (CID): {log_err}")
                    st.markdown('''
                    <div class="info-hint" style="background:rgba(245,158,11,0.1);border-color:rgba(245,158,11,0.3);color:#F59E0B;">
                        <b>Limite atingido:</b> Muitas consultas em pouco tempo. Aguarde alguns segundos e tente novamente.
                    </div>
                    ''', unsafe_allow_html=True)
                    return
                results, fallback_msg = cid_db.search_cid11_text(search)
            else:
                results = cid_db.search_cid10_local(search)

        if fallback_msg:
            st.markdown(f'''
            <div class="info-hint">
                <b>Aviso:</b> {fallback_msg}
            </div>
            ''', unsafe_allow_html=True)

        if not results:
            st.markdown(f'''
            <div class="empty-state">
                {search_icon}
                <div>Nenhum CID encontrado para <b>"{html_module.escape(search)}"</b>.</div>
            </div>
            ''', unsafe_allow_html=True)
            return

        total = len(results)
        shown = results[:_MAX_RESULTS]
        truncated_hint = f" · exibindo primeiros {_MAX_RESULTS}" if total > _MAX_RESULTS else ""
        st.markdown(f'<div class="stats-line"><b>{total}</b> resultado{"s" if total != 1 else ""} encontrado{"s" if total != 1 else ""}{truncated_hint}</div>', unsafe_allow_html=True)

        for cid in shown:
            code = cid.get('COD_CID', 'N/A')
            desc = strip_html_tags(cid.get('DESCRICAO_CID', ''))
            st.markdown(f'''
            <div class="result-card">
                <div class="result-title">{desc}</div>
                <div class="result-code">{code}</div>
            </div>
            ''', unsafe_allow_html=True)

        if total > _MAX_RESULTS:
            st.markdown(f'''
            <div class="info-hint">
                <b>Dica:</b> Há {total - _MAX_RESULTS} resultados adicionais. Refine a busca para ver outros CIDs.
            </div>
            ''', unsafe_allow_html=True)
