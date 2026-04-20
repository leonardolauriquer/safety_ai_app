import streamlit as st
import logging
from typing import Any, Dict, List, Optional
from datetime import date, timedelta

from safety_ai_app.cipa_data_processor import (
    get_cipa_dimensioning,
    calculate_election_schedule,
    BRAZILIAN_NATIONAL_HOLIDAYS
)
from safety_ai_app.cnae_risk_data_processor import CNAERiskDataProcessor
from safety_ai_app.theme_config import _get_material_icon_html, THEME
from safety_ai_app.web_interface.shared_styles import inject_glass_styles, glass_marker, render_back_button

logger = logging.getLogger(__name__)

_RISK_COLORS = {"1": "#4ADE80", "2": "#22D3EE", "3": "#F59E0B", "4": "#EF4444"}


def _alert(msg: str, kind: str = "info") -> None:
    styles = {
        "error":   ("rgba(239,68,68,0.08)",   "rgba(239,68,68,0.25)",   "#F87171", "alert"),
        "warning": ("rgba(245,158,11,0.08)",  "rgba(245,158,11,0.25)",  "#FBBF24", "warning"),
        "info":    ("rgba(34,211,238,0.06)",  "rgba(34,211,238,0.20)",  "#22D3EE", "info"),
        "success": ("rgba(74,222,128,0.08)",  "rgba(74,222,128,0.25)",  "#4ADE80", "check"),
    }
    bg, border, color, icon = styles.get(kind, styles["info"])
    st.markdown(
        f'<div class="info-hint" style="background:{bg};border-color:{border};color:{color};">'
        f'{_get_material_icon_html(icon)} {msg}</div>',
        unsafe_allow_html=True,
    )


def cipa_sizing_page() -> None:
    inject_glass_styles()

    render_back_button("← Dimensionamentos", "sizing_page", "back_from_cipa")

    with st.container():
        st.markdown(glass_marker(), unsafe_allow_html=True)

        st.markdown(f"""
            <div class="page-header">
                {_get_material_icon_html('users')}
                <h1>Dimensionamento e Cronograma da CIPA</h1>
            </div>
            <div class="page-subtitle">Gestão da Comissão Interna de Prevenção de Acidentes e de Assédio (CIPA) conforme NR-05.</div>
        """, unsafe_allow_html=True)

        cnae_processor = CNAERiskDataProcessor()

        st.markdown(f"""
            <div class="section-title">
                {_get_material_icon_html('calculator')}
                <span>Dimensionamento</span>
            </div>
        """, unsafe_allow_html=True)

        with st.container(border=True):
            with st.form("cipa_form"):
                col1, col2 = st.columns(2)

                with col1:
                    cnae_input: str = st.text_input(
                        "CNAE da Empresa (apenas números)",
                        placeholder="Ex: 8610101",
                        help="Informe o CNAE principal da sua empresa para determinar o Grau de Risco."
                    )

                with col2:
                    num_employees_input: str = st.text_input(
                        "Número de Funcionários",
                        placeholder="Ex: 50",
                        help="Informe o número total de funcionários do estabelecimento."
                    )

                submitted = st.form_submit_button("Calcular Dimensionamento")

        if submitted:
            if not cnae_input or not num_employees_input:
                _alert("Preencha o CNAE e o Número de Funcionários para realizar o cálculo.", "warning")
                logger.warning("Tentativa de cálculo da CIPA com campos vazios.")
                st.session_state['cipa_dimensioning_result'] = None
                st.session_state['cipa_grau_risco'] = None
            else:
                try:
                    cnae: str = cnae_input.strip()
                    num_employees: int = int(num_employees_input)

                    if not cnae.isdigit():
                        _alert("O CNAE deve conter apenas números. Verifique o valor informado.", "error")
                        logger.warning(f"CNAE inválido fornecido: {cnae_input}")
                        st.session_state['cipa_dimensioning_result'] = None
                        st.session_state['cipa_grau_risco'] = None
                    elif num_employees <= 0:
                        _alert("O número de funcionários deve ser um valor positivo.", "error")
                        logger.warning(f"Número de funcionários inválido: {num_employees_input}")
                        st.session_state['cipa_dimensioning_result'] = None
                        st.session_state['cipa_grau_risco'] = None
                    else:
                        with st.spinner("Calculando dimensionamento da CIPA..."):
                            grau_risco: Optional[int] = cnae_processor.get_risk_level(cnae)

                            if grau_risco is None:
                                _alert(
                                    f"Não foi possível determinar o Grau de Risco para o CNAE <b>{cnae}</b>. "
                                    "Verifique se o CNAE está correto.",
                                    "warning"
                                )
                                logger.warning(f"Grau de Risco não encontrado para CNAE: {cnae}")
                                st.session_state['cipa_dimensioning_result'] = None
                                st.session_state['cipa_grau_risco'] = None
                            else:
                                cipa_dimensioning: Dict[str, Any] = get_cipa_dimensioning(grau_risco, num_employees)
                                st.session_state['cipa_dimensioning_result'] = cipa_dimensioning
                                st.session_state['cipa_grau_risco'] = grau_risco
                                st.session_state['cipa_num_employees'] = num_employees

                except ValueError as e:
                    _alert(f"Erro ao processar os dados: {e}. Verifique se os valores são numéricos.", "error")
                    logger.error(f"ValueError no dimensionamento da CIPA: {e}")
                    st.session_state['cipa_dimensioning_result'] = None
                    st.session_state['cipa_grau_risco'] = None
                except Exception as e:
                    _alert(f"Erro inesperado: {e}. Tente novamente.", "error")
                    logger.error(f"Erro inesperado no dimensionamento da CIPA: {e}", exc_info=True)
                    st.session_state['cipa_dimensioning_result'] = None
                    st.session_state['cipa_grau_risco'] = None

    if 'cipa_dimensioning_result' in st.session_state and st.session_state['cipa_dimensioning_result'] is not None:
        cipa_dimensioning = st.session_state['cipa_dimensioning_result']
        grau_risco = st.session_state.get('cipa_grau_risco', 'N/A')
        num_employees = st.session_state.get('cipa_num_employees', 'N/A')
        risk_color = _RISK_COLORS.get(str(grau_risco), "#64748B")

        st.markdown(f"""
            <div class="result-card">
                <div class="result-title">{_get_material_icon_html('users')} Resultado do Dimensionamento</div>
                <div class="stats-line">
                    Grau de Risco: <b style="color:{risk_color}">GR {grau_risco}</b>
                    &nbsp;|&nbsp; Funcionários: <b>{num_employees}</b>
                </div>
            </div>
        """, unsafe_allow_html=True)

        if 'observacao' in cipa_dimensioning:
            _alert(cipa_dimensioning['observacao'], "info")
        else:
            col_efetivos, col_suplentes = st.columns(2)
            with col_efetivos:
                st.metric(label="Membros Efetivos", value=cipa_dimensioning['efetivos'])
            with col_suplentes:
                st.metric(label="Membros Suplentes", value=cipa_dimensioning['suplentes'])

            _alert("Dimensionamento realizado com sucesso conforme NR-05.", "success")
            st.markdown("""
            <div class="info-hint">
                <b>Composição:</b> A CIPA é composta por representantes do empregador (designados) e dos empregados (eleitos).
                O número acima é o total de membros titulares e suplentes de cada parte.
                Para estabelecimentos com menos de 20 funcionários, a NR-05 (item 5.4.13) prevê a nomeação de um
                representante da organização para auxiliar nas ações de prevenção.
            </div>
            """, unsafe_allow_html=True)

        st.markdown(f"""
            <div class="section-title">
                {_get_material_icon_html('history')}
                <span>Cronograma do Processo Eleitoral</span>
            </div>
        """, unsafe_allow_html=True)

        with st.container(border=True):
            with st.form("election_schedule_form"):
                mandate_end_date_input: Optional[date] = st.date_input(
                    "Data de Término do Mandato Atual da CIPA (DD/MM/AAAA)",
                    value=None,
                    format="DD/MM/YYYY",
                    help="Informe a data de término do mandato da CIPA atual."
                )

                calculate_schedule_button = st.form_submit_button("Gerar Cronograma")

        if calculate_schedule_button:
            if not mandate_end_date_input:
                _alert("Informe a Data de Término do Mandato Atual para gerar o cronograma.", "warning")
                logger.warning("Tentativa de gerar cronograma sem data de término do mandato.")
            else:
                try:
                    with st.spinner("Gerando cronograma eleitoral..."):
                        schedule_result = calculate_election_schedule(
                            mandate_end_date_input,
                            BRAZILIAN_NATIONAL_HOLIDAYS
                        )

                    st.markdown(f"""
                        <div class="section-title">
                            {_get_material_icon_html('clipboard')}
                            <span>Datas Sugeridas</span>
                        </div>
                    """, unsafe_allow_html=True)

                    for current_date, main_label, explanation, key, icon_name in schedule_result['ordered_items']:
                        day_of_week = current_date.strftime('%A')
                        day_of_week_pt = {
                            'Monday': 'Segunda-feira', 'Tuesday': 'Terça-feira',
                            'Wednesday': 'Quarta-feira', 'Thursday': 'Quinta-feira',
                            'Friday': 'Sexta-feira', 'Saturday': 'Sábado', 'Sunday': 'Domingo'
                        }.get(day_of_week, day_of_week)

                        st.markdown(f"""
                            <div class="result-card">
                                <div style="display:flex;align-items:flex-start;gap:12px;">
                                    <span style="color:#4ADE80;margin-top:2px;">{_get_material_icon_html('timer')}</span>
                                    <div>
                                        <div class="result-title">{day_of_week_pt}, {current_date.strftime('%d/%m/%Y')}</div>
                                        <div class="result-code">{main_label}</div>
                                        <div class="result-meta">{explanation}</div>
                                    </div>
                                </div>
                            </div>
                        """, unsafe_allow_html=True)

                    _alert(schedule_result['observacao_treinamento'], "info")

                    if schedule_result['warnings']:
                        for warning in schedule_result['warnings']:
                            _alert(warning, "warning")
                    else:
                        _alert(
                            "Cronograma gerado com sucesso! Este é um planejamento — ajuste conforme feriados estaduais/municipais.",
                            "success"
                        )

                except Exception as e:
                    _alert(f"Erro ao gerar cronograma: {e}. Verifique as datas informadas.", "error")
                    logger.error(f"Erro ao gerar cronograma eleitoral da CIPA: {e}", exc_info=True)

        st.markdown(f"""
            <div class="section-title">
                {_get_material_icon_html('info')}
                <span>Informações Adicionais (NR-05)</span>
            </div>
        """, unsafe_allow_html=True)

        with st.expander("O que é a CIPA e qual seu Objetivo?"):
            st.markdown(
                """
                A **Comissão Interna de Prevenção de Acidentes e de Assédio (CIPA)**, regulamentada pela NR-05,
                tem como objetivo a **prevenção de acidentes e doenças relacionadas ao trabalho**, de modo a
                tornar compatível permanentemente o trabalho com a preservação da vida e promoção da saúde do trabalhador.
                *(NR-05, item 5.1.1)*.
                """
            )

        with st.expander("Quais são as Atribuições da CIPA?"):
            st.markdown(
                """
                A CIPA tem diversas atribuições importantes, incluindo:
                *   Acompanhar o processo de identificação de perigos e avaliação de riscos.
                *   Registrar a percepção dos riscos dos trabalhadores (mapa de risco ou outra técnica).
                *   Verificar ambientes e condições de trabalho para identificar riscos.
                *   Elaborar e acompanhar plano de trabalho para ações preventivas.
                *   Participar no desenvolvimento e implementação de programas de segurança e saúde.
                *   Acompanhar a análise de acidentes e doenças relacionadas ao trabalho.
                *   Requisitar informações sobre segurança e saúde dos trabalhadores à organização.
                *   Propor análise de condições ou situações de trabalho com risco grave e iminente.
                *   Promover anualmente a **Semana Interna de Prevenção de Acidentes do Trabalho (SIPAT)**.
                *   Incluir temas sobre prevenção e combate ao assédio sexual e outras formas de violência.
                *(NR-05, item 5.3.1)*.
                """
            )

        with st.expander("Composição e Estrutura da CIPA"):
            st.markdown(
                """
                A CIPA é constituída por estabelecimento e composta por representantes da organização e dos empregados.
                *   **Representantes da Organização**: Designados pela organização. O Presidente é designado.
                *   **Representantes dos Empregados**: Eleitos em escrutínio secreto. O Vice-Presidente é escolhido entre os eleitos.
                *   **Mandato**: Um ano, permitida uma reeleição.
                *   **Estabilidade**: Vedada a dispensa arbitrária do empregado eleito desde o registro de candidatura até um ano após o final do mandato.
                *(NR-05, itens 5.4.1–5.4.12)*.

                **Estabelecimentos com Menos de 20 Funcionários:** A organização nomeará um representante
                para auxiliar nas ações de prevenção. O MEI está dispensado desta nomeação.
                *(NR-05, itens 5.4.13 e 5.4.13.2)*.
                """
            )

        with st.expander("Processo Eleitoral da CIPA"):
            st.markdown(
                """
                *   **Convocação**: Mínimo de 60 dias antes do término do mandato em curso.
                *   **Comissão Eleitoral**: Composta pelo Presidente e Vice-Presidente da CIPA.
                *   **Inscrição**: Período mínimo de 15 dias corridos.
                *   **Votação**: Em dia normal de trabalho, voto secreto.
                *   **Apuração**: Em horário normal, com representantes da organização e dos empregados.
                *   **Quórum**: Mínimo 50% na votação; se não atingido, prorroga. Válida com ⅓ no 2º dia ou qualquer número no 3º dia.
                *(NR-05, itens 5.5.1–5.5.4.1)*.
                """
            )

        with st.expander("Funcionamento da CIPA"):
            st.markdown(
                """
                *   **Reuniões Ordinárias**: Mensais (ME/EPP graus 1 e 2 podem ser bimestrais).
                *   **Atas**: Assinadas pelos presentes e disponibilizadas aos empregados.
                *   **Reuniões Extraordinárias**: Em caso de acidente grave, fatal ou por solicitação.
                *   **Perda de Mandato**: Por falta a mais de 4 reuniões ordinárias sem justificativa.
                *(NR-05, itens 5.6.1–5.6.7)*.
                """
            )

        with st.expander("Treinamento da CIPA"):
            st.markdown(
                f"""
                A organização deve promover treinamento para os membros antes da posse, contemplando:
                *   Riscos do processo produtivo e medidas de prevenção.
                *   Metodologia de investigação de acidentes e doenças.
                *   Princípios de higiene do trabalho.
                *   Legislação trabalhista e previdenciária em SST.
                *   Prevenção e combate ao assédio sexual e violência no trabalho.
                *(NR-05, itens 5.7.1–5.7.2)*.

                **Carga Horária Mínima:** GR 1: 8h | GR 2: 12h | GR 3: 16h | GR 4: 20h
                *(NR-05, itens 5.7.4–5.7.4.3)*.
                """
            )

        with st.expander("CIPA em Organizações Contratadas para Prestação de Serviços"):
            st.markdown(
                """
                *   **CIPA Centralizada**: Se o total de empregados na UF se enquadrar no Quadro I.
                *   **CIPA Própria**: Se a contratada atuar em estabelecimento GR 3 ou 4 e o número enquadrar no Quadro I.
                *   **Representante NR-05**: Quando desobrigada de CIPA própria, com 5+ empregados no estabelecimento da contratante.
                *(NR-05, itens 5.8.1–5.8.7)*.
                """
            )


if __name__ == "__main__":
    cipa_sizing_page()
