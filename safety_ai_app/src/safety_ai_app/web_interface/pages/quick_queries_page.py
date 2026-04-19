import streamlit as st
import logging
from safety_ai_app.theme_config import THEME, _get_material_icon_html
from safety_ai_app.web_interface.shared_styles import inject_glass_styles, glass_marker

logger = logging.getLogger(__name__)

def quick_queries_page() -> None:
    """
    Renderiza a página de Consultas Rápidas, servindo como um hub para
    as diversas ferramentas de consulta (CBO, CID, CNAE, CA, Multas).
    """
    inject_glass_styles()

    with st.container():
        st.markdown(glass_marker(), unsafe_allow_html=True)
        st.markdown(f'''
        <div class="page-header">
            {_get_material_icon_html('search')}
            <h1>{THEME['phrases']['quick_consults']}</h1>
        </div>
        <div class="page-subtitle">Acesso rápido às principais ferramentas de consulta em SST.</div>
        ''', unsafe_allow_html=True)

    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button(f"{_get_material_icon_html('briefcase')} {THEME['phrases']['cbo_consult']}", key="go_cbo_consult", use_container_width=True):
            st.session_state.current_page = "cbo_consult"
            st.rerun()
        if st.button(f"{_get_material_icon_html('medical')} {THEME['phrases']['cid_consult']}", key="go_cid_consult", use_container_width=True):
            st.session_state.current_page = "cid_consult"
            st.rerun()
    with col2:
        if st.button(f"{_get_material_icon_html('building')} {THEME['phrases']['cnae_consult']}", key="go_cnae_consult", use_container_width=True):
            st.session_state.current_page = "cnae_consult"
            st.rerun()
        if st.button(f"{_get_material_icon_html('certificate')} {THEME['phrases']['ca_consult']}", key="go_ca_consult", use_container_width=True):
            st.session_state.current_page = "ca_consult"
            st.rerun()
    with col3:
        if st.button(f"{_get_material_icon_html('gavel')} {THEME['phrases']['fines_consult']}", key="go_fines_consult", use_container_width=True):
            st.session_state.current_page = "fines_consult"
            st.rerun()
    
    st.markdown('''
    <div class="info-hint">
        <b>Dica:</b> Clique em uma das opções acima para navegar para a consulta desejada.
    </div>
    ''', unsafe_allow_html=True)

if __name__ == "__main__":
    quick_queries_page()
