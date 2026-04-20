import html as html_module
import streamlit as st
import logging
from typing import Optional, Any
import pandas as pd

from safety_ai_app.theme_config import _get_material_icon_html, THEME
from safety_ai_app.ca_data_processor import CADataProcessor
from safety_ai_app.web_interface.shared_styles import inject_glass_styles, glass_marker, render_back_button

logger = logging.getLogger(__name__)

_CA_LIMIT = 50


def _get_val(ca_data: pd.Series, *keys: str) -> str:
    for k in keys:
        v = ca_data.get(k)
        if v is not None and not (isinstance(v, float) and pd.isna(v)):
            s = str(v).strip()
            if s:
                return s
    return "N/A"


def _fmt_date(val: Any) -> str:
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return "N/A"
    try:
        return val.strftime("%d/%m/%Y")
    except AttributeError:
        return str(val)


def _display_ca_details(ca_data: pd.Series) -> None:
    ca_numero = _get_val(ca_data, 'ca_numero')
    equipamento_tipo = _get_val(ca_data, 'equipamento_tipo')
    situacao_ca = _get_val(ca_data, 'situacao_ca')
    validade_formatada = _fmt_date(ca_data.get('validade_ca'))
    descricao_detalhada = _get_val(ca_data, 'descricao_detalhada')
    fabricante_nome_display = _get_val(
        ca_data, 'fabricante_razao_social', 'fabricante_nome'
    )
    fabricante_cnpj = _get_val(ca_data, 'fabricante_cnpj')
    natureza_equipamento = _get_val(ca_data, 'natureza_equipamento')
    marca_ca = _get_val(ca_data, 'marca_ca')
    cor_equipamento = _get_val(ca_data, 'cor_equipamento')
    nr_processo = _get_val(ca_data, 'processo_numero', 'NR DO PROCESSO')
    data_registro_formatada = _fmt_date(ca_data.get('data_registro_ca'))
    aprovado_laudo = _get_val(ca_data, 'aprovado_laudo')
    restricao_laudo = _get_val(ca_data, 'restricao_laudo')
    observacao_laudo = _get_val(ca_data, 'observacao_laudo')
    cnpj_laboratorio = _get_val(ca_data, 'cnpj_laboratorio')
    razao_social_laboratorio = _get_val(ca_data, 'razao_social_laboratorio')
    nr_laudo = _get_val(ca_data, 'nr_laudo')
    norma_referencia = _get_val(ca_data, 'norma_referencia')

    badge_class = "badge-neutral"
    if situacao_ca == 'VÁLIDO':
        badge_class = "badge-valid"
    elif situacao_ca == 'VENCIDO':
        badge_class = "badge-expired"

    st.markdown(
        f"""
        <div class="result-card">
            <div style="display:flex;align-items:flex-start;justify-content:space-between;
                gap:10px;flex-wrap:wrap;">
                <div>
                    <span class="result-code" style="font-size:1em;">CA {ca_numero}</span>
                    <div class="result-title" style="margin-top:3px;">{equipamento_tipo}</div>
                </div>
                <div style="text-align:right;">
                    <span class="{badge_class}">{situacao_ca}</span>
                    <div class="result-meta" style="margin-top:4px;">
                        Válido até <b>{validade_formatada}</b>
                    </div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.expander("Ver detalhes técnicos"):
        rows = [
            ("description", "Descrição", descricao_detalhada),
            ("manufacturer", "Fabricante", f"{fabricante_nome_display} · CNPJ: {fabricante_cnpj}"),
            ("equipment_nature", "Natureza", natureza_equipamento),
        ]
        if marca_ca != 'N/A':
            rows.append(("brand", "Marca", marca_ca))
        if cor_equipamento != 'N/A':
            rows.append(("color", "Cor", cor_equipamento))
        if nr_processo != 'N/A':
            rows.append(("process_number", "Nº Processo", nr_processo))
        if data_registro_formatada != 'N/A':
            rows.append(("registration_date", "Registro", data_registro_formatada))

        rows_html = "".join([
            f"""<div class="detail-row">
                {_get_material_icon_html(icon)}
                <div>
                    <span class="detail-label">{label}:</span>
                    <span class="detail-value">{html_module.escape(value)}</span>
                </div>
            </div>"""
            for icon, label, value in rows
        ])
        st.markdown(rows_html, unsafe_allow_html=True)

        st.markdown(
            f"""
            <div class="section-title" style="margin-top:12px;">
                {_get_material_icon_html("lab_report")} Informações de Laudo
            </div>
            """,
            unsafe_allow_html=True,
        )

        laudo_parts = []
        if aprovado_laudo != 'N/A':
            laudo_parts.append(f"<b>Aprovado:</b> {html_module.escape(aprovado_laudo)}")
        if nr_laudo != 'N/A':
            laudo_parts.append(f"<b>Nº Laudo:</b> {html_module.escape(nr_laudo)}")
        if norma_referencia != 'N/A':
            laudo_parts.append(f"<b>Norma:</b> {html_module.escape(norma_referencia)}")
        if laudo_parts:
            st.markdown(
                f"<div class='result-meta'>{' &nbsp;|&nbsp; '.join(laudo_parts)}</div>",
                unsafe_allow_html=True,
            )
        if restricao_laudo != 'N/A':
            st.markdown(
                f"<div class='result-meta' style='margin-top:4px;color:#F59E0B;'>"
                f"⚠️ Restrição: {html_module.escape(restricao_laudo)}</div>",
                unsafe_allow_html=True,
            )
        if razao_social_laboratorio != 'N/A':
            st.markdown(
                f"<div class='result-meta' style='margin-top:4px;'>"
                f"Laboratório: {html_module.escape(razao_social_laboratorio)} "
                f"({html_module.escape(cnpj_laboratorio)})</div>",
                unsafe_allow_html=True,
            )

        if ca_numero != 'N/A':
            mte_link = (
                "https://www.gov.br/trabalho-e-emprego/pt-br/servicos/"
                "seguranca-e-saude-no-trabalho/consulta-de-ca?"
                "p_p_id=br_gov_mte_caepi_web_portlet_CaepiPortlet&p_p_lifecycle=0"
                f"&p_p_state=normal&p_p_mode=view&p_p_col_id=column-1"
                f"&p_p_col_count=1&_br_gov_mte_caepi_web_portlet_CaepiPortlet_ca={ca_numero}"
            )
            st.markdown(
                f"""
                <div style="margin-top:10px;font-size:0.82em;">
                    <a href="{mte_link}" target="_blank"
                        style="color:#4ADE80;text-decoration:none;
                               display:flex;align-items:center;gap:4px;">
                        {_get_material_icon_html('external')} Consultar no site oficial do MTE
                    </a>
                </div>
                """,
                unsafe_allow_html=True,
            )


def ca_consult_page() -> None:
    inject_glass_styles()

    render_back_button("← Consultas Rápidas", "quick_queries_page", "back_from_ca")

    with st.container():
        st.markdown(glass_marker(), unsafe_allow_html=True)

        st.markdown(
            f"""
            <div class="page-header">
                {_get_material_icon_html('ca_consult')}
                <h1>Consulta de CA / EPI</h1>
            </div>
            <div class="page-subtitle">
                Pesquise Certificados de Aprovação de Equipamentos de Proteção Individual.
            </div>
            """,
            unsafe_allow_html=True,
        )

        ca_processor: Optional[CADataProcessor] = None
        try:
            ca_processor = CADataProcessor()
        except Exception as e:
            logger.critical(f"Erro ao inicializar CADataProcessor: {e}", exc_info=True)
            st.markdown(
                f"""
                <div class="info-hint" style="background:rgba(239,68,68,0.08);
                    border-color:rgba(239,68,68,0.25);color:#F87171;">
                    {_get_material_icon_html('alert')}
                    <b>Erro crítico:</b> Não foi possível carregar os dados de CA. {e}
                </div>
                """,
                unsafe_allow_html=True,
            )
            st.stop()
            return

        search_term = st.text_input(
            "Buscar CA",
            key="ca_search_input",
            placeholder="Nº do CA, fabricante ou tipo de EPI — ex: 3M, Capacete, 12345...",
            label_visibility="collapsed",
        ).strip()

        st.markdown(
            f"""
            <div class="info-hint">
                {_get_material_icon_html('info')}
                <b>Dica:</b> Busque pelo número exato do CA ou palavras-chave como
                "3M", "Capacete" ou "Luva".
            </div>
            """,
            unsafe_allow_html=True,
        )

        if not search_term:
            return

    with st.spinner("Buscando..."):
        try:
            results_df = ca_processor.search_ca(search_term)
        except Exception as e:
            logger.error(f"Erro ao buscar CA: {e}", exc_info=True)
            st.markdown(
                f"""
                <div class="info-hint" style="background:rgba(239,68,68,0.08);
                    border-color:rgba(239,68,68,0.25);color:#F87171;">
                    {_get_material_icon_html('alert')}
                    <b>Erro ao realizar busca:</b> {e}
                </div>
                """,
                unsafe_allow_html=True,
            )
            return

    if results_df.empty:
        st.markdown(
            f"""
            <div class="empty-state">
                {_get_material_icon_html('search_off')}
                <p>Nenhum resultado encontrado para
                <b>"{html_module.escape(search_term)}"</b>.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        return

    total_found = len(results_df)
    displayed_df = results_df.iloc[:_CA_LIMIT]
    truncated = total_found > _CA_LIMIT

    if truncated:
        st.markdown(
            f"""
            <div class="stats-line">
                Exibindo <b>{_CA_LIMIT}</b> de <b>{total_found}</b> certificados —
                refine sua busca para ver mais específicos.
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            f"""
            <div class="stats-line">
                <b>{total_found}</b> certificado{"s" if total_found != 1 else ""} encontrado{"s" if total_found != 1 else ""}
            </div>
            """,
            unsafe_allow_html=True,
        )

    for _, row in displayed_df.iterrows():
        _display_ca_details(row)
