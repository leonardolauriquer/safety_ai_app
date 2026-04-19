import streamlit as st
import logging

from safety_ai_app.theme_config import THEME, _get_material_icon_html
from safety_ai_app.web_interface.shared_styles import inject_glass_styles, glass_marker

logger = logging.getLogger(__name__)


def sizing_page() -> None:
    inject_glass_styles()
    
    calc_icon = _get_material_icon_html('calculator')
    users_icon = _get_material_icon_html('users')
    eng_icon = _get_material_icon_html('engineering')
    fire_icon = _get_material_icon_html('fire')
    
    with st.container():
        st.markdown(glass_marker(), unsafe_allow_html=True)
        
        st.markdown(f'''
        <div class="page-header">
            {calc_icon}
            <h1>{THEME['phrases'].get('sizing', 'Dimensionamentos')}</h1>
        </div>
        <div class="page-subtitle">Ferramentas para dimensionamento de equipes e comissões de SST</div>
        ''', unsafe_allow_html=True)
        
        sizing_options = [
            {"icon": users_icon, "title": THEME['phrases'].get('cipa_sizing', 'CIPA'), "desc": "Dimensione a CIPA conforme NR-05", "page": "cipa_sizing"},
            {"icon": eng_icon, "title": THEME['phrases'].get('sesmt_sizing', 'SESMT'), "desc": "Dimensione o SESMT conforme NR-04", "page": "sesmt_sizing"},
            {"icon": fire_icon, "title": THEME['phrases'].get('emergency_brigade_sizing', 'Brigada'), "desc": "Dimensione a Brigada de Emergência", "page": "emergency_brigade_sizing"},
        ]
        
        cols = st.columns(3)
        for i, opt in enumerate(sizing_options):
            with cols[i]:
                st.markdown(f'''
                <div class="result-card" style="text-align: center; padding: 20px;">
                    <div style="margin-bottom: 10px;">{opt["icon"]}</div>
                    <div class="result-title" style="font-size: 1.1em;">{opt["title"]}</div>
                    <div class="result-meta">{opt["desc"]}</div>
                </div>
                ''', unsafe_allow_html=True)
                
                if st.button("Acessar", key=f"go_{opt['page']}", use_container_width=True):
                    st.session_state.current_page = opt['page']
                    st.rerun()
        
        st.markdown('''
        <div class="info-hint" style="margin-top: 20px;">
            <b>Dica:</b> Escolha uma ferramenta acima para calcular o dimensionamento
        </div>
        ''', unsafe_allow_html=True)


if __name__ == "__main__":
    sizing_page()
