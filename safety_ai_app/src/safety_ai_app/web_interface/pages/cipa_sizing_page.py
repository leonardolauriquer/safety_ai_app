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

def cipa_sizing_page() -> None:
    """
    Renderiza a página de dimensionamento da CIPA.

    Esta página permite ao usuário inserir o CNAE e o número de funcionários
    para calcular o dimensionamento da CIPA conforme a NR-05,
    e fornece informações adicionais sobre a CIPA e um cronograma eleitoral.
    """
    inject_glass_styles()

    render_back_button("← Dimensionamentos", "sizing_page", "back_from_cipa")

    with st.container():
        st.markdown(glass_marker(), unsafe_allow_html=True)
        
        # Compact Header
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
                st.error("Por favor, preencha o CNAE e o Número de Funcionários para realizar o cálculo.")
                logger.warning("Tentativa de cálculo da CIPA com campos vazios.")
                st.session_state['cipa_dimensioning_result'] = None
                st.session_state['cipa_grau_risco'] = None
            else:
                try:
                    cnae: str = cnae_input.strip()
                    num_employees: int = int(num_employees_input)

                    if not cnae.isdigit():
                        st.error("O CNAE deve conter apenas números. Por favor, verifique o valor informado.")
                        logger.warning(f"CNAE inválido fornecido: {cnae_input}")
                        st.session_state['cipa_dimensioning_result'] = None
                        st.session_state['cipa_grau_risco'] = None
                    elif num_employees <= 0:
                        st.error("O número de funcionários deve ser um valor positivo. Por favor, verifique o valor informado.")
                        logger.warning(f"Número de funcionários inválido fornecido: {num_employees_input}")
                        st.session_state['cipa_dimensioning_result'] = None
                        st.session_state['cipa_grau_risco'] = None
                    else:
                        st.success(f"Dados recebidos: CNAE **{cnae}**, Funcionários: **{num_employees}**.")
                        logger.info(f"Iniciando cálculo da CIPA para CNAE: {cnae}, Funcionários: {num_employees}")

                        with st.spinner("Calculando dimensionamento da CIPA..."):
                            grau_risco: Optional[int] = cnae_processor.get_risk_level(cnae)

                            if grau_risco is None:
                                st.warning(f"Não foi possível determinar o Grau de Risco para o CNAE **{cnae}**. Por favor, verifique o CNAE informado ou se o arquivo 'grau_de_risco.xlsx' está configurado corretamente no Google Drive e contém este CNAE.")
                                logger.warning(f"Grau de Risco não encontrado para CNAE: {cnae}")
                                st.session_state['cipa_dimensioning_result'] = None
                                st.session_state['cipa_grau_risco'] = None
                            else:
                                st.info(f"Grau de Risco determinado para o CNAE **{cnae}**: **{grau_risco}**.")
                                logger.info(f"Grau de Risco para CNAE {cnae} é {grau_risco}.")

                                cipa_dimensioning: Dict[str, Any] = get_cipa_dimensioning(grau_risco, num_employees)
                                st.session_state['cipa_dimensioning_result'] = cipa_dimensioning
                                st.session_state['cipa_grau_risco'] = grau_risco
                                st.session_state['cipa_num_employees'] = num_employees

                except ValueError as e:
                    st.error(f"Erro ao processar os dados: {e}. Verifique se os valores estão corretos e são numéricos.")
                    logger.error(f"Erro de ValueError no processamento de dados da CIPA: {e}")
                    st.session_state['cipa_dimensioning_result'] = None
                    st.session_state['cipa_grau_risco'] = None
                except Exception as e:
                    st.error(f"Ocorreu um erro inesperado: {e}. Por favor, tente novamente ou contate o suporte.")
                    logger.error(f"Erro inesperado no dimensionamento da CIPA: {e}", exc_info=True)
                    st.session_state['cipa_dimensioning_result'] = None
                    st.session_state['cipa_grau_risco'] = None

    if 'cipa_dimensioning_result' in st.session_state and st.session_state['cipa_dimensioning_result'] is not None:
        cipa_dimensioning = st.session_state['cipa_dimensioning_result']
        
        st.markdown(f"""
            <div class="result-card">
                <div class="result-title">{_get_material_icon_html('users')} Resultado do Dimensionamento</div>
                <div class="stats-line">Grau de Risco: <b>{st.session_state.get('cipa_grau_risco', 'N/A')}</b> | Funcionários: <b>{st.session_state.get('cipa_num_employees', 'N/A')}</b></div>
            </div>
        """, unsafe_allow_html=True)

        if 'observacao' in cipa_dimensioning:
            st.warning(cipa_dimensioning['observacao'])
        else:
            col_efetivos, col_suplentes = st.columns(2)
            with col_efetivos:
                st.metric(label="Membros Efetivos", value=cipa_dimensioning['efetivos'])
            with col_suplentes:
                st.metric(label="Membros Suplentes", value=cipa_dimensioning['suplentes'])
            st.success("Dimensionamento da CIPA realizado com sucesso conforme NR-05.")
            
            st.info(
                """
                **Observação Importante:**
                *   A CIPA é composta por representantes do empregador (designados) e dos empregados (eleitos).
                *   O número de membros efetivos e suplentes acima refere-se ao total de membros eleitos e designados.
                *   A organização deve designar seus representantes e os empregados elegerão os seus.
                *   Para estabelecimentos com menos de 20 funcionários, a NR-05, item 5.4.13, prevê a nomeação de um representante da organização para auxiliar nas ações de prevenção.
                """
            )

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
                    help="Informe a data de término do mandato da CIPA atual. A partir dela, o cronograma eleitoral será calculado."
                )
                
                calculate_schedule_button = st.form_submit_button("Gerar Cronograma")

        if calculate_schedule_button:
            if not mandate_end_date_input:
                st.error("Por favor, informe a Data de Término do Mandato Atual da CIPA para gerar o cronograma.")
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
                            'Monday': 'Segunda-feira', 'Tuesday': 'Terça-feira', 'Wednesday': 'Quarta-feira',
                            'Thursday': 'Quinta-feira', 'Friday': 'Sexta-feira', 'Saturday': 'Sábado', 'Sunday': 'Domingo'
                        }.get(day_of_week, day_of_week)
                        
                        st.markdown(f"""
                            <div class="result-card">
                                <div style="display: flex; align-items: flex-start; gap: 12px;">
                                    <span style="color: #4ADE80; margin-top: 2px;">{_get_material_icon_html('timer')}</span>
                                    <div>
                                        <div class="result-title">{day_of_week_pt}, {current_date.strftime('%d/%m/%Y')}</div>
                                        <div class="result-code">{main_label}</div>
                                        <div class="result-meta">{explanation}</div>
                                    </div>
                                </div>
                            </div>
                        """, unsafe_allow_html=True)
                    
                    st.info(f"Informação: *{schedule_result['observacao_treinamento']}*")

                    if schedule_result['warnings']:
                        for warning in schedule_result['warnings']:
                            st.warning(warning)
                    else:
                        st.success("Cronograma gerado com sucesso! Lembre-se de que este é um planejamento e pode necessitar de ajustes locais e consideração de feriados estaduais/municipais.")

                except Exception as e:
                    st.error(f"Ocorreu um erro ao gerar o cronograma: {e}. Por favor, verifique as datas informadas.")
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
                *   Propor análise de condições ou situações de trabalho para las quais considere haver risco grave e iminente à segurança e saúde dos trabalhadores e, se for o caso, a interrupção das atividades até a adoção das medidas corretivas e de controle.
                *   Promover anualmente a **Semana Interna de Prevenção de Acidentes do Trabalho (SIPAT)**.
                *   Incluir temas referentes à prevenção e ao combate ao assédio sexual e outras formas de violência no trabalho.
                *(NR-05, item 5.3.1)*.
                """
            )

        with st.expander("Composição e Estrutura da CIPA"):
            st.markdown(
                """
                A CIPA é constituída por estabelecimento e composta por representantes da organização e dos empregados.
                *   **Representantes da Organização**: Titulares e suplentes são designados pela organização. O Presidente da CIPA é designado pela organização.
                *   **Representantes dos Empregados**: Titulares e suplentes são eleitos em escrutínio secreto. O Vice-Presidente é escolhido pelos representantes eleitos dentre os titulares.
                *   **Mandato**: O mandato dos membros eleitos da CIPA tem duração de um ano, permitida uma reeleição.
                *   **Estabilidade**: É vedada a dispensa arbitrária ou sem justa causa do empregado eleito para cargo de direção da CIPA desde o registro de sua candidatura até um ano após the final de seu mandato.
                *(NR-05, itens 5.4.1, 5.4.3, 5.4.4, 5.4.5, 5.4.6, 5.4.12)*.
                """
            )
            st.markdown(
                """
                **Disposições para Estabelecimentos com Menos de 20 Funcionários:**
                Quando o estabelecimento não se enquadrar no Quadro I (ou seja, ter menos de 20 funcionários) e não for atendido por SESMT, a organização nomeará um representante dentre seus empregados para auxiliar nas ações de prevenção em segurança e saúde no trabalho. O microempreendedor individual (MEI) está dispensado desta nomeação.
                *(NR-05, item 5.4.13 e 5.4.13.2)*.
                """
            )

        with st.expander("Processo Eleitoral da CIPA"):
            st.markdown(
                """
                O processo eleitoral para a escolha dos representantes dos empregados na CIPA segue as seguintes condições:
                *   **Convocação**: O empregador deve convocar eleições no prazo mínimo de 60 dias antes do término do mandato em curso.
                *   **Comissão Eleitoral**: Constituída pelo Presidente e Vice-Presidente da CIPA (ou pela organização, se não houver CIPA).
                *   **Inscrição**: Período mínimo para inscrição será de 15 (quinze) dias corridos.
                *   **Liberdade de Inscrição**: Para todos os empregados do estabelecimento, independentemente de setores ou locais de trabalho, com fornecimento de comprovante.
                *   **Garantia de Emprego**: Para todos os empregados inscritos, desde o registro de sua candidatura até a eleição.
                *   **Votação**: Em dia normal de trabalho, respeitando os horários de turnos e em horário que possibilite a participação da maioria dos empregados do estabelecimento, com voto secreto.
                *   **Apuração**: Em horário normal de trabalho, com acompanhamento de representante da organização e dos empregados.
                *   **Quórum**: Se a participação for inferior a 50% na votação, o período é prorrogado. A eleição é válida com a participação de, no mínimo, um terço dos empregados no segundo dia, ou qualquer número no terceiro dia.
                *(NR-05, itens 5.5.1 a 5.5.4.1)*.
                """
            )

        with st.expander("Funcionamento da CIPA"):
            st.markdown(
                """
                A CIPA deve ter um funcionamento organizado para cumprir seus objetivos:
                *   **Reuniões Ordinárias**: Mensais, de acordo com calendário preestabelecido. Em Microempresas (ME) e Empresas de Pequeno Porte (EPP) de graus de risco 1 e 2, as reuniões podem ser bimestrais.
                *   **Atas**: As reuniões terão atas assinadas pelos presentes, que devem ser disponibilizadas aos integrantes da CIPA e aos empregados.
                *   **Reuniões Extraordinárias**: Realizadas em caso de acidente do trabalho grave ou fatal, ou por solicitação de uma das representações.
                *   **Perda de Mandato**: Um membro titular perderá o mandato, sendo substituído por suplente, quando faltar a mais de quatro reuniões ordinárias sem justificativa.
                *   **Vacâncias**: Supridas por suplentes, ou por eleição extraordinária em casos específicos.
                *(NR-05, itens 5.6.1 a 5.6.7)*.
                """
            )

        with st.expander("Treinamento da CIPA"):
            st.markdown(
                f"""
                A organização deve promover treinamento para o representante nomeado da NR-05 e para os membros da CIPA (titulares e suplentes) antes da posse.
                O treinamento deve contemplar, no mínimo, os seguintes itens:
                *   Estudo do ambiente, condições de trabalho e riscos do processo produtivo.
                *   Noções sobre acidentes e doenças relacionadas ao trabalho e suas medidas de prevenção.
                *   Metodologia de investigação e análise de acidentes e doenças.
                *   Princípios gerais de higiene do trabalho e prevenção de riscos.
                *   Noções sobre legislações trabalhista e previdenciária em SST.
                *   Noções sobre inclusão de pessoas com deficiência e reabilitados.
                *   Organização da CIPA e assuntos para o exercício das atribuições.
                *   Prevenção e combate ao assédio sexual e outras formas de violência no trabalho.
                *(NR-05, itens 5.7.1 e 5.7.2)*.

                **Carga Horária Mínima do Treinamento:**
                *   **Grau de Risco 1**: 8 horas
                *   **Grau de Risco 2**: 12 horas
                *   **Grau de Risco 3**: 16 horas
                *   **Grau de Risco 4**: 20 horas
                A carga horária deve ser distribuída em no máximo 8 horas diárias. Parte do treinamento pode ser realizada à distância ou semipresencial, dependendo do grau de risco.
                *(NR-05, itens 5.7.4 a 5.7.4.3)*.
                """
            )

        with st.expander("CIPA em Organizações Contratadas para Prestação de Serviços"):
            st.markdown(
                """
                Organizações que prestam serviços a terceiros também têm regras específicas para a CIPA:
                *   **CIPA Centralizada**: Se o número total de empregados na Unidade da Federação se enquadrar no Quadro I da NR-05.
                *   **CIPA Própria**: Se a contratada atuar em estabelecimento de contratante com grau de risco 3 ou 4, e o número de empregados no estabelecimento da contratante se enquadrar no Quadro I.
                *   **Representante da NR-05**: Quando desobrigada de constituir CIPA própria, a contratada deve nomear um representante da NR-05 se possuir 5 ou mais empregados no estabelecimento da contratante.
                *   **Interação**: A CIPA centralizada da contratada deve manter interação entre os estabelecimentos. A contratante deve exigir a nomeação do representante da NR-05 e convidar a contratada para participar das reuniões da CIPA da contratante para integrar as ações de prevenção.
                *(NR-05, itens 5.8.1 a 5.8.7)*.
                """
            )



if __name__ == "__main__":
    cipa_sizing_page()
