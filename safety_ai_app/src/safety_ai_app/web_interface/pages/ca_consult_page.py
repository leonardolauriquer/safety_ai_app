import html as html_module
import streamlit as st
import logging
from typing import Optional, Any
import pandas as pd
from datetime import datetime

# Importa a função _get_material_icon_html e o dicionário THEME
from safety_ai_app.theme_config import _get_material_icon_html, THEME

# Importa CADataProcessor (assumindo que está no mesmo nível ou acessível via sys.path)
from safety_ai_app.ca_data_processor import CADataProcessor
from safety_ai_app.web_interface.shared_styles import inject_glass_styles, glass_marker, render_back_button

logger = logging.getLogger(__name__)

def _display_ca_details(ca_data: pd.Series) -> None:
    """
    Exibe os detalhes de um Certificado de Aprovação (CA) de forma formatada.
    """
    # Função auxiliar para padronizar a exibição de valores nulos/ausentes
    def _get_display_value(value: Any) -> str:
        if pd.isna(value) or value is None or (isinstance(value, str) and value.strip() == ''):
            return 'N/A'
        return str(value)

    ca_numero = _get_display_value(ca_data.get('ca_numero'))
    equipamento_tipo = _get_display_value(ca_data.get('equipamento_tipo'))
    situacao_ca = _get_display_value(ca_data.get('situacao_ca'))
    validade_ca_raw = ca_data.get('validade_ca') # Mantém o valor bruto para formatação de data
    descricao_detalhada = _get_display_value(ca_data.get('descricao_detalhada'))
    
    # Lógica para fabricante: prioriza razao_social, depois nome, depois N/A
    raw_fabricante_razao_social = ca_data.get('fabricante_razao_social')
    raw_fabricante_nome = ca_data.get('fabricante_nome')
    fabricante_nome_display = _get_display_value(raw_fabricante_razao_social if raw_fabricante_razao_social is not None else raw_fabricante_nome)
    
    fabricante_cnpj = _get_display_value(ca_data.get('fabricante_cnpj'))
    
    natureza_equipamento = _get_display_value(ca_data.get('natureza_equipamento'))
    # Removido 'aprovacao_ca' pois não há campo correspondente na API e é redundante com 'aprovado_laudo'
    marca_ca = _get_display_value(ca_data.get('marca_ca'))
    cor_equipamento = _get_display_value(ca_data.get('cor_equipamento'))
    nr_processo = _get_display_value(ca_data.get('processo_numero', ca_data.get('NR DO PROCESSO'))) # Mapeamento alternativo
    data_registro_ca_raw = ca_data.get('data_registro_ca') # Mantém o valor bruto para formatação de data
    
    aprovado_laudo = _get_display_value(ca_data.get('aprovado_laudo'))
    restricao_laudo = _get_display_value(ca_data.get('restricao_laudo'))
    observacao_laudo = _get_display_value(ca_data.get('observacao_laudo'))
    cnpj_laboratorio = _get_display_value(ca_data.get('cnpj_laboratorio'))
    razao_social_laboratorio = _get_display_value(ca_data.get('razao_social_laboratorio'))
    nr_laudo = _get_display_value(ca_data.get('nr_laudo'))
    norma_referencia = _get_display_value(ca_data.get('norma_referencia'))

    # Formatação da data de validade
    validade_formatada = "N/A"
    if pd.notna(validade_ca_raw):
        try:
            validade_formatada = validade_ca_raw.strftime("%d/%m/%Y")
        except AttributeError: # Caso validade_ca_raw já seja uma string ou outro formato
            validade_formatada = str(validade_ca_raw)

    # Formatação da data de registro
    data_registro_formatada = "N/A"
    if pd.notna(data_registro_ca_raw):
        try:
            data_registro_formatada = data_registro_ca_raw.strftime("%d/%m/%Y")
        except AttributeError:
            data_registro_formatada = str(data_registro_ca_raw)

    # Determinar classe de badge
    badge_class = "badge-neutral"
    if situacao_ca == 'VÁLIDO':
        badge_class = "badge-valid"
    elif situacao_ca == 'VENCIDO':
        badge_class = "badge-expired"

    # Card principal do resultado
    st.markdown(f"""
    <div class="result-card">
        <div class="result-title">
            <span class="result-code">CA {ca_numero}</span> - {equipamento_tipo}
        </div>
        <div class="result-meta">
            Situação: <span class="{badge_class}">{situacao_ca}</span> | 
            Validade: <b>{validade_formatada}</b>
        </div>
    </div>
    """, unsafe_allow_html=True)

    with st.expander(f"Ver detalhes técnicos"):
        # Detalhes principais
        st.markdown(f"""
        <div class="detail-row">
            {_get_material_icon_html('description')}
            <div>
                <span class="detail-label">Descrição:</span>
                <span class="detail-value">{descricao_detalhada}</span>
            </div>
        </div>
        <div class="detail-row">
            {_get_material_icon_html('manufacturer')}
            <div>
                <span class="detail-label">Fabricante:</span>
                <span class="detail-value">{fabricante_nome_display} (CNPJ: {fabricante_cnpj})</span>
            </div>
        </div>
        <div class="detail-row">
            {_get_material_icon_html('equipment_nature')}
            <div>
                <span class="detail-label">Natureza:</span>
                <span class="detail-value">{natureza_equipamento}</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

        if marca_ca != 'N/A':
            st.markdown(f'<div class="detail-row">{_get_material_icon_html("brand")}<div><span class="detail-label">Marca:</span> <span class="detail-value">{marca_ca}</span></div></div>', unsafe_allow_html=True)
        if cor_equipamento != 'N/A':
            st.markdown(f'<div class="detail-row">{_get_material_icon_html("color")}<div><span class="detail-label">Cor:</span> <span class="detail-value">{cor_equipamento}</span></div></div>', unsafe_allow_html=True)
        if nr_processo != 'N/A':
            st.markdown(f'<div class="detail-row">{_get_material_icon_html("process_number")}<div><span class="detail-label">Nº Processo:</span> <span class="detail-value">{nr_processo}</span></div></div>', unsafe_allow_html=True)
        if data_registro_formatada != 'N/A':
            st.markdown(f'<div class="detail-row">{_get_material_icon_html("registration_date")}<div><span class="detail-label">Registro:</span> <span class="detail-value">{data_registro_formatada}</span></div></div>', unsafe_allow_html=True)

        # Informações de Laudo
        st.markdown(f'<div class="section-title" style="margin-top: 15px;">{_get_material_icon_html("lab_report")} Informações de Laudo</div>', unsafe_allow_html=True)
        
        laudo_details = []
        if aprovado_laudo != 'N/A': laudo_details.append(f"<b>Aprovado:</b> {aprovado_laudo}")
        if nr_laudo != 'N/A': laudo_details.append(f"<b>Nº Laudo:</b> {nr_laudo}")
        if norma_referencia != 'N/A': laudo_details.append(f"<b>Norma:</b> {norma_referencia}")
        
        if laudo_details:
            st.markdown(f"<div class='result-meta'>{' | '.join(laudo_details)}</div>", unsafe_allow_html=True)

        if razao_social_laboratorio != 'N/A':
            st.markdown(f"<div class='result-meta' style='margin-top: 5px;'>Laboratório: {razao_social_laboratorio} ({cnpj_laboratorio})</div>", unsafe_allow_html=True)

    # Link externo
    if ca_numero != 'N/A':
        mte_link = f"https://www.gov.br/trabalho-e-emprego/pt-br/servicos/seguranca-e-saude-no-trabalho/consulta-de-ca?p_p_id=br_gov_mte_caepi_web_portlet_CaepiPortlet&p_p_lifecycle=0&p_p_state=normal&p_p_mode=view&p_p_col_id=column-1&p_p_col_count=1&_br_gov_mte_caepi_web_portlet_CaepiPortlet_ca={ca_numero}"
        st.markdown(f"""
        <div style="margin-top: 8px; font-size: 0.82em;">
            <a href="{mte_link}" target="_blank" style="color: #4ADE80; text-decoration: none; display: flex; align-items: center; gap: 4px;">
                {_get_material_icon_html('external')} Consultar no site oficial do MTE
            </a>
        </div>
        """, unsafe_allow_html=True)


def ca_consult_page() -> None:
    """Página de consulta de Certificado de Aprovação (CA) de EPIs."""
    inject_glass_styles()

    render_back_button("← Consultas Rápidas", "quick_queries_page", "back_from_ca")

    with st.container():
        st.markdown(glass_marker(), unsafe_allow_html=True)
        
        # Cabeçalho compacto
        st.markdown(f"""
        <div class="page-header">
            {_get_material_icon_html('ca_consult')}
            <h1>Consulta de CA</h1>
        </div>
        <div class="page-subtitle">
            Pesquise por Certificados de Aprovação de Equipamentos de Proteção Individual.
        </div>
        """, unsafe_allow_html=True)

        ca_processor: Optional[CADataProcessor] = None
        try:
            ca_processor = CADataProcessor()
        except Exception as e:
            logger.critical(f"Erro crítico ao inicializar CADataProcessor: {e}", exc_info=True)
            st.markdown(f"""
            <div class="info-hint" style="background:rgba(239,68,68,0.08);border-color:rgba(239,68,68,0.25);color:#F87171;">
                {_get_material_icon_html('alert')}
                <b>Erro crítico:</b> Não foi possível carregar o serviço de dados de CA. {e}
            </div>
            """, unsafe_allow_html=True)
            st.stop()
            return

        # Campo de busca simples
        search_term = st.text_input(
            "Buscar CA",
            key="ca_search_input",
            placeholder="Nº do CA, fabricante ou tipo de EPI...",
            label_visibility="collapsed"
        ).strip()

        st.markdown(f"""
        <div class="info-hint">
            {_get_material_icon_html('info')} 
            <b>Dica:</b> Você pode buscar pelo número exato do CA ou palavras-chave como "3M", "Capacete", "Luva".
        </div>
        """, unsafe_allow_html=True)

        if search_term:
            with st.spinner(f"Buscando..."):
                try:
                    results_df = ca_processor.search_ca(search_term)
                except Exception as e:
                    logger.error(f"Ocorreu um erro ao buscar CA: {e}", exc_info=True)
                    st.markdown(f"""
                    <div class="info-hint" style="background:rgba(239,68,68,0.08);border-color:rgba(239,68,68,0.25);color:#F87171;">
                        {_get_material_icon_html('alert')}
                        <b>Erro ao realizar busca:</b> {e}
                    </div>
                    """, unsafe_allow_html=True)
                    return
            
            CA_LIMIT = 50
            if results_df.empty:
                st.markdown(f"""
                <div class="empty-state">
                    {_get_material_icon_html('search_off')}
                    <p>Nenhum resultado encontrado para "{html_module.escape(search_term)}".</p>
                </div>
                """, unsafe_allow_html=True)
            else:
                total_found = len(results_df)
                displayed_df = results_df.iloc[:CA_LIMIT]
                truncated = total_found > CA_LIMIT

                if truncated:
                    st.markdown(f'<div class="stats-line">Exibindo <b>{CA_LIMIT}</b> de <b>{total_found}</b> certificados encontrados &mdash; refine sua busca para ver resultados mais específicos.</div>', unsafe_allow_html=True)
                else:
                    st.markdown(f'<div class="stats-line">Encontrados <b>{total_found}</b> certificado{"s" if total_found != 1 else ""}</div>', unsafe_allow_html=True)

                for index, row in displayed_df.iterrows():
                    _display_ca_details(row)

