import streamlit as st
import logging
from typing import Any, Dict, List, Optional, Tuple

from safety_ai_app.sesmt_data_processor import get_sesmt_dimensioning, PROFESSIONAL_NAMES, EMPLOYEE_RANGE_COLUMNS
from safety_ai_app.cnae_risk_data_processor import CNAERiskDataProcessor
from safety_ai_app.theme_config import _get_material_icon_html, THEME
from safety_ai_app.web_interface.shared_styles import inject_glass_styles, glass_marker

logger = logging.getLogger(__name__)

EMPLOYEE_RANGE_OPTIONS = list(EMPLOYEE_RANGE_COLUMNS.keys()) + ["Mais de 5.000"]

def get_num_employees_from_selection(selected_range_str: str, exact_num_employees_above_5000: Optional[int]) -> int:
    """
    Converte a string da faixa de funcionários selecionada em um número inteiro
    para ser usado no cálculo. Para faixas, usa o limite superior.
    Para "Mais de 5.000", usa o número exato fornecido.
    """
    if selected_range_str == "Mais de 5.000":
        if exact_num_employees_above_5000 is None or exact_num_employees_above_5000 <= 5000:
            return 5001 if exact_num_employees_above_5000 is None else exact_num_employees_above_5000
        return exact_num_employees_above_5000
    
    return EMPLOYEE_RANGE_COLUMNS[selected_range_str][1]

def _aggregate_regional_data(establishments_data: List[Dict[str, Any]], cnae_processor: CNAERiskDataProcessor) -> Tuple[Optional[int], Optional[int], List[str]]:
    """
    Aggregates data from multiple establishments for regional SESMT calculation.
    Returns (aggregated_grau_risco, aggregated_num_employees, errors_list).
    """
    total_effective_employees = 0
    max_grau_risco = 0
    errors = []

    if not establishments_data:
        errors.append("Nenhum estabelecimento adicionado para o cálculo regionalizado.")
        return None, None, errors

    for i, est in enumerate(establishments_data):
        cnae = est.get('cnae')
        num_employees = est.get('num_employees')
        is_me_epp = est.get('is_me_epp', False)

        if not cnae or not str(cnae).isdigit():
            errors.append(f"Estabelecimento {i+1}: CNAE '{cnae}' inválido. Deve conter apenas números.")
            continue
        if not isinstance(num_employees, int) or num_employees <= 0:
            errors.append(f"Estabelecimento {i+1}: Número de funcionários '{num_employees}' inválido. Deve ser um valor positivo.")
            continue

        est_grau_risco = cnae_processor.get_risk_level(cnae)
        if est_grau_risco is None:
            errors.append(f"Estabelecimento {i+1}: Não foi possível determinar o Grau de Risco para o CNAE '{cnae}'. Por favor, verifique.")
            continue

        if est_grau_risco > max_grau_risco:
            max_grau_risco = est_grau_risco

        effective_employees = num_employees
        if is_me_epp and (est_grau_risco == 1 or est_grau_risco == 2):
            effective_employees = num_employees // 2
            logger.info(f"Estabelecimento {i+1} (CNAE {cnae}, GR {est_grau_risco}, ME/EPP): Funcionários reduzidos para {effective_employees} (metade de {num_employees}).")
        
        total_effective_employees += effective_employees

    if errors:
        return None, None, errors
    
    if max_grau_risco == 0:
        errors.append("Não foi possível determinar um Grau de Risco válido para o cálculo regionalizado a partir dos estabelecimentos fornecidos.")
        return None, None, errors

    return max_grau_risco, total_effective_employees, []


def sesmt_sizing_page() -> None:
    """
    Renderiza a página de dimensionamento do SESMT.
    """
    inject_glass_styles()

    if st.button("← Dimensionamentos", key="back_from_sesmt"):
        st.session_state.current_page = "sizing_page"
        st.rerun()

    with st.container():
        st.markdown(glass_marker(), unsafe_allow_html=True)
        
        st.markdown(f'''
            <div class="page-header">
                {_get_material_icon_html('medical_services')}
                <h1>Dimensionamento do SESMT</h1>
            </div>
            <div class="page-subtitle">Calcule a composição do SESMT conforme a NR-04</div>
        ''', unsafe_allow_html=True)

    cnae_processor = CNAERiskDataProcessor()

    st.markdown(f'''
        <div class="section-title">
            {_get_material_icon_html('calculate')}
            <span>Cálculo do SESMT</span>
        </div>
    ''', unsafe_allow_html=True)
    st.markdown('<div class="info-hint">Insira os dados da sua empresa para determinar a composição do SESMT.</div>', unsafe_allow_html=True)
    
    calculation_mode = st.radio(
        "Selecione o Modo de Cálculo:",
        ("Dimensionamento Individual", "Dimensionamento Regionalizado/Estadual/Compartilhado"),
        key="calculation_mode_radio",
        help="Escolha entre calcular o SESMT para um único estabelecimento ou para um grupo de estabelecimentos."
    )

    # Initialize session state for results
    if 'sesmt_dimensioning_result' not in st.session_state:
        st.session_state['sesmt_dimensioning_result'] = None
    if 'sesmt_grau_risco' not in st.session_state:
        st.session_state['sesmt_grau_risco'] = None
    if 'individual_sesmt_results' not in st.session_state: # New for individual results in regional mode
        st.session_state['individual_sesmt_results'] = []
    if 'regional_establishments' not in st.session_state:
        st.session_state['regional_establishments'] = []
    if 'add_establishment_form_key_counter' not in st.session_state:
        st.session_state['add_establishment_form_key_counter'] = 0

    # Clear results when switching modes
    if st.session_state.get('last_calculation_mode') != calculation_mode:
        st.session_state['sesmt_dimensioning_result'] = None
        st.session_state['sesmt_grau_risco'] = None
        st.session_state['individual_sesmt_results'] = []
        st.session_state['regional_establishments'] = [] # Clear establishments too
        st.session_state['add_establishment_form_key_counter'] = 0 # Reset form counter
    st.session_state['last_calculation_mode'] = calculation_mode

    with st.container(border=True):
        if calculation_mode == "Dimensionamento Individual":
            with st.form("sesmt_form_individual"):
                col1, col2 = st.columns(2)
                
                with col1:
                    cnae_input: str = st.text_input(
                        "CNAE da Empresa (apenas números)",
                        placeholder="Ex: 8610101",
                        key="individual_cnae_input",
                        help="Informe o CNAE principal da sua empresa para determinar o Grau de Risco."
                    )
                
                with col2:
                    selected_employee_range: str = st.selectbox(
                        "Faixa de Número de Funcionários",
                        options=EMPLOYEE_RANGE_OPTIONS,
                        key="individual_employee_range",
                        help="Selecione a faixa de número de funcionários do estabelecimento."
                    )
                    
                    exact_num_employees_above_5000: Optional[int] = None
                    if selected_employee_range == "Mais de 5.000":
                        exact_num_employees_input = st.text_input(
                            "Número Exato de Funcionários (acima de 5.000)",
                            placeholder="Ex: 7500",
                            key="individual_exact_employees",
                            help="Informe o número exato de funcionários para o cálculo detalhado acima de 5.000."
                        )
                        if exact_num_employees_input:
                            try:
                                exact_num_employees_above_5000 = int(exact_num_employees_input)
                                if exact_num_employees_above_5000 <= 5000:
                                    st.warning("Por favor, insira um número de funcionários acima de 5.000 para esta opção.")
                                    exact_num_employees_above_5000 = None
                            except ValueError:
                                st.error("Por favor, insira um número válido para funcionários.")
                                exact_num_employees_above_5000 = None

                submitted = st.form_submit_button("Calcular Dimensionamento Individual")

            if submitted:
                # Clear previous regional results if any
                st.session_state['individual_sesmt_results'] = []
                st.session_state['sesmt_dimensioning_result'] = None
                st.session_state['sesmt_grau_risco'] = None

                if not cnae_input or not selected_employee_range:
                    st.error("Por favor, preencha o CNAE e selecione a Faixa de Funcionários para realizar o cálculo.")
                    logger.warning("Tentativa de cálculo do SESMT individual com campos vazios.")
                    return
                
                if selected_employee_range == "Mais de 5.000" and exact_num_employees_above_5000 is None:
                    st.error("Por favor, insira o número exato de funcionários para a faixa 'Mais de 5.000'.")
                    logger.warning("Tentativa de cálculo do SESMT individual com faixa 'Mais de 5.000' sem número exato válido.")
                    return

                try:
                    cnae: str = cnae_input.strip()
                    
                    if not cnae.isdigit():
                        st.error("O CNAE deve conter apenas números. Por favor, verifique o valor informado.")
                        logger.warning(f"CNAE inválido fornecido para cálculo individual: {cnae_input}")
                        return
                    
                    num_employees: int = get_num_employees_from_selection(selected_employee_range, exact_num_employees_above_5000)

                    if num_employees < 0:
                        st.error("O número de funcionários deve ser um valor positivo. Por favor, verifique o valor informado.")
                        logger.warning(f"Número de funcionários inválido fornecido para cálculo individual: {num_employees}")
                        return

                    logger.info(f"Iniciando cálculo do SESMT individual para CNAE: {cnae}, Faixa de Funcionários: {selected_employee_range}, Número para cálculo: {num_employees}")

                    grau_risco: Optional[int] = cnae_processor.get_risk_level(cnae)

                    if grau_risco is None:
                        st.warning(f"Não foi possível determinar o Grau de Risco para o CNAE **{cnae}**. Por favor, verifique se o CNAE informado está correto.")
                        logger.warning(f"Grau de Risco não encontrado para CNAE: {cnae} no cálculo individual.")
                        return

                    st.info(f"Grau de Risco determinado para o CNAE **{cnae}**: **{grau_risco}**.")
                    logger.info(f"Grau de Risco para CNAE {cnae} é {grau_risco}.")

                    sesmt_dimensioning: Dict[str, Any] = get_sesmt_dimensioning(grau_risco, num_employees)
                    st.session_state['sesmt_dimensioning_result'] = sesmt_dimensioning
                    st.session_state['sesmt_grau_risco'] = grau_risco

                except ValueError as e:
                    st.error(f"Erro ao processar os dados: {e}. Verifique se os valores estão corretos e são numéricos.")
                    logger.error(f"Erro de ValueError no processamento de dados do SESMT individual: {e}")
                except KeyError as ke:
                    st.error(f"Ocorreu um erro interno ao processar os dados. Por favor, tente novamente ou contate o suporte.")
                    logger.critical(f"[ERRO CRÍTICO] Erro de dados na página SESMT individual: {ke}. Verifique a estrutura do arquivo Excel de dimensionamento.", exc_info=True)
                except Exception as e:
                    st.error(f"Ocorreu um erro inesperado: {e}. Por favor, tente novamente ou contate o suporte.")
                    logger.error(f"Erro inesperado no dimensionamento do SESMT individual: {e}", exc_info=True)

        else: # Dimensionamento Regionalizado/Estadual/Compartilhado
            st.markdown(f'''
                <div class="section-title">
                    {_get_material_icon_html('add_business')}
                    Adicionar Estabelecimento para Cálculo Regionalizado
                </div>
            ''', unsafe_allow_html=True)
            
            # Initialize a counter for the form key to force re-rendering and clearing inputs
            if 'add_establishment_form_key_counter' not in st.session_state:
                st.session_state['add_establishment_form_key_counter'] = 0

            with st.form(key=f"add_establishment_form_{st.session_state['add_establishment_form_key_counter']}"):
                col1, col2, col3 = st.columns([3, 2, 1])
                with col1:
                    est_cnae = st.text_input("CNAE do Estabelecimento", placeholder="Ex: 8610101")
                with col2:
                    est_num_employees = st.number_input("Número de Funcionários", min_value=1, step=1, value=1) # Default value 1
                with col3:
                    st.markdown("<br>", unsafe_allow_html=True)
                    est_is_me_epp = st.checkbox("É ME/EPP?", help="Marque se o estabelecimento for Microempresa (ME) ou Empresa de Pequeno Porte (EPP).")
                
                add_est_button = st.form_submit_button("Adicionar Estabelecimento")

                if add_est_button:
                    if not est_cnae or not str(est_cnae).isdigit():
                        st.error("CNAE inválido. Deve conter apenas números.")
                    elif not est_num_employees or est_num_employees <= 0:
                        st.error("Número de funcionários inválido. Deve ser um valor positivo.")
                    else:
                        st.session_state['regional_establishments'].append({
                            'cnae': est_cnae,
                            'num_employees': est_num_employees,
                            'is_me_epp': est_is_me_epp
                        })
                        st.success(f"Estabelecimento com CNAE {est_cnae} e {est_num_employees} funcionários adicionado.")
                        # Increment the counter to force a new form instance on rerun, clearing inputs
                        st.session_state['add_establishment_form_key_counter'] += 1
                        st.rerun() # Forces a rerun to clear the form inputs

            st.markdown(f'''
                <div class="section-title">
                    {_get_material_icon_html('business')}
                    Estabelecimentos Adicionados
                </div>
            ''', unsafe_allow_html=True)
            if st.session_state['regional_establishments']:
                for i, est in enumerate(st.session_state['regional_establishments']):
                    col_display, col_remove = st.columns([5, 1])
                    with col_display:
                        st.markdown(f"**{i+1}. CNAE:** {est['cnae']}, **Funcionários:** {est['num_employees']}"
                                    f"{' (ME/EPP)' if est['is_me_epp'] else ''}")
                    with col_remove:
                        # Use a unique key for each remove button
                        if st.button(f"Remover", key=f"remove_est_{i}"):
                            st.session_state['regional_establishments'].pop(i)
                            st.rerun()
            else:
                st.info("Nenhum estabelecimento adicionado ainda.")

            calculate_regional_button = st.button("Calcular Dimensionamento Regionalizado")

            if calculate_regional_button:
                # Clear previous individual results if any
                st.session_state['sesmt_dimensioning_result'] = None
                st.session_state['sesmt_grau_risco'] = None
                st.session_state['individual_sesmt_results'] = []

                if not st.session_state['regional_establishments']:
                    st.error("Por favor, adicione pelo menos um estabelecimento para calcular o dimensionamento regionalizado.")
                    return

                aggregated_grau_risco, aggregated_num_employees, errors = _aggregate_regional_data(
                    st.session_state['regional_establishments'], cnae_processor
                )

                if errors:
                    for err in errors:
                        st.error(err)
                    return
                
                if aggregated_grau_risco is None or aggregated_num_employees is None:
                    st.error("Erro desconhecido ao agregar os dados dos estabelecimentos. Verifique os logs para mais detalhes.")
                    return

                st.info(f"Grau de Risco Agregado: **{aggregated_grau_risco}**")
                st.info(f"Número Total de Funcionários Agregado: **{aggregated_num_employees}**")
                logger.info(f"Iniciando cálculo do SESMT regionalizado para GR: {aggregated_grau_risco}, Empregados: {aggregated_num_employees}")

                sesmt_dimensioning: Dict[str, Any] = get_sesmt_dimensioning(aggregated_grau_risco, aggregated_num_employees)
                st.session_state['sesmt_dimensioning_result'] = sesmt_dimensioning
                st.session_state['sesmt_grau_risco'] = aggregated_grau_risco

                # NEW: Calculate and store individual SESMT dimensioning for each establishment
                individual_sesmt_results = []
                for i, est in enumerate(st.session_state['regional_establishments']):
                    est_cnae = est.get('cnae')
                    est_num_employees = est.get('num_employees')
                    
                    individual_grau_risco = cnae_processor.get_risk_level(est_cnae)
                    
                    if individual_grau_risco is None:
                        individual_sesmt_results.append({
                            'establishment_info': f"Estabelecimento {i+1} (CNAE: {est_cnae}, Funcionários: {est_num_employees})",
                            'error': f"Não foi possível determinar o Grau de Risco para o CNAE {est_cnae}."
                        })
                        continue

                    individual_dim = get_sesmt_dimensioning(individual_grau_risco, est_num_employees)
                    individual_sesmt_results.append({
                        'establishment_info': f"Estabelecimento {i+1} (CNAE: {est_cnae}, Funcionários: {est_num_employees})",
                        'grau_risco': individual_grau_risco,
                        'dimensioning': individual_dim
                    })
                st.session_state['individual_sesmt_results'] = individual_sesmt_results


    # Exibe o resultado do dimensionamento se houver
    if 'sesmt_dimensioning_result' in st.session_state and st.session_state['sesmt_dimensioning_result'] is not None:
        sesmt_dimensioning = st.session_state['sesmt_dimensioning_result']

        if "error" in sesmt_dimensioning:
            st.error(sesmt_dimensioning["error"])
        else:
            is_regional = calculation_mode != "Dimensionamento Individual"
            section_label = "Composição do SESMT Total (Agregado)" if is_regional else "Composição do SESMT"
            info_text = (
                "O cálculo representa o SESMT único que a organização precisa constituir para todos os "
                "estabelecimentos informados, baseado no somatório de funcionários e maior Grau de Risco (NR-04)."
                if is_regional else
                "Cálculo baseado no Anexo II da NR-04 (Portaria MTP nº 4.219/2022). Discrepâncias podem ocorrer "
                "por interpretações específicas ou versões diferentes da norma."
            )

            st.markdown(f"""
                <div class="section-title">
                    {_get_material_icon_html('assignment_ind')}
                    {section_label}
                </div>
                <div class="info-hint">{info_text}</div>
            """, unsafe_allow_html=True)

            professional_keys_order = ['tecnico_seguranca', 'engenheiro_seguranca', 'aux_tec_enfermagem', 'enfermeiro', 'medico']

            rows_html = ""
            for key in professional_keys_order:
                professional_data = sesmt_dimensioning.get(key)
                if professional_data:
                    qty_display = professional_data['qty']
                    specific_observation = professional_data['specific_observation']
                    display_name = PROFESSIONAL_NAMES.get(key, key)
                    obs_html = f'<div class="result-meta" style="margin-top:3px;font-style:italic;">{specific_observation}</div>' if specific_observation else ""
                    rows_html += f"""
                        <div class="detail-row">
                            {_get_material_icon_html('check')}
                            <div>
                                <span class="detail-label">{display_name}:</span>
                                <span class="detail-value result-code">{qty_display}</span>
                                {obs_html}
                            </div>
                        </div>
                    """

            if rows_html:
                st.markdown(f'<div class="result-card">{rows_html}</div>', unsafe_allow_html=True)

            if sesmt_dimensioning['general_observations']:
                st.markdown(f"""
                    <div class="section-title">
                        {_get_material_icon_html('info')}
                        Observações e Modos de Contratação
                    </div>
                """, unsafe_allow_html=True)
                for obs in sesmt_dimensioning['general_observations']:
                    st.markdown(f'<div class="info-hint">{obs}</div>', unsafe_allow_html=True)

            st.markdown(f"""
                <div class="info-hint" style="background:rgba(74,222,128,0.08);border-color:rgba(74,222,128,0.2);color:#4ADE80;">
                    {_get_material_icon_html('check')}
                    {"Dimensionamento do SESMT agregado realizado com sucesso conforme NR-04." if is_regional else "Dimensionamento do SESMT realizado com sucesso conforme NR-04."}
                </div>
            """, unsafe_allow_html=True)

            # Display individual SESMT results if in regional mode
            if is_regional and st.session_state['individual_sesmt_results']:
                st.markdown(f"""
                    <div class="section-title" style="margin-top:20px;">
                        {_get_material_icon_html('business')}
                        Dimensionamento Individual por Estabelecimento
                    </div>
                    <div class="info-hint">
                        Requisitos de SESMT caso cada estabelecimento fosse dimensionado individualmente —
                        útil para planejamento e distribuição de recursos.
                    </div>
                """, unsafe_allow_html=True)

                for individual_result in st.session_state['individual_sesmt_results']:
                    if 'error' in individual_result:
                        st.markdown(f"""
                            <div class="result-card">
                                <div class="result-title">{_get_material_icon_html('location_on')} {individual_result['establishment_info']}</div>
                                <div class="info-hint" style="margin-top:8px;">{individual_result['error']}</div>
                            </div>
                        """, unsafe_allow_html=True)
                    else:
                        individual_dim = individual_result['dimensioning']
                        ind_rows = ""
                        for key in professional_keys_order:
                            pd_data = individual_dim.get(key)
                            if pd_data:
                                dname = PROFESSIONAL_NAMES.get(key, key)
                                obs_html = f'<div class="result-meta" style="font-style:italic;">{pd_data["specific_observation"]}</div>' if pd_data['specific_observation'] else ""
                                ind_rows += f"""
                                    <div class="detail-row">
                                        {_get_material_icon_html('check')}
                                        <div>
                                            <span class="detail-label">{dname}:</span>
                                            <span class="detail-value result-code">{pd_data['qty']}</span>
                                            {obs_html}
                                        </div>
                                    </div>
                                """
                        st.markdown(f"""
                            <div class="result-card">
                                <div class="result-title">
                                    {_get_material_icon_html('location_on')} {individual_result['establishment_info']}
                                </div>
                                <div class="result-meta">Grau de Risco: <b>{individual_result['grau_risco']}</b></div>
                                {ind_rows}
                            </div>
                        """, unsafe_allow_html=True)

    st.markdown(f"""
        <div class="section-title" style="margin-top:24px;">
            {_get_material_icon_html('info')}
            Informações Adicionais sobre o SESMT (NR-04)
        </div>
    """, unsafe_allow_html=True)

    with st.expander("O que é o SESMT e qual seu Objetivo?"):
        st.markdown(
            """
            O **Serviço Especializado em Segurança e Medicina do Trabalho (SESMT)**, regulamentado pela NR-04,
            tem como objetivo **promover a saúde e proteger a integridade do trabalhador** no local de trabalho.
            É composto por profissionais da área de saúde e segurança que atuam de forma integrada para prevenir
            acidentes e doenças ocupacionais.
            *(NR-04, item 4.1.1)*.
            """
        )

    with st.expander("Quem deve constituir o SESMT?"):
        st.markdown(
            """
            Organizações e órgãos públicos da administração direta e indireta, bem como os órgãos dos Poderes
            Legislativo e Judiciário e do Ministério Público, que possuam empregados regidos pela CLT, devem
            constituir e manter o SESMT, no local de trabalho, nos termos definidos na NR-04.
            *(NR-04, item 4.2.1)*.
            """
        )

    with st.expander("Quais são as Competências do SESMT?"):
        st.markdown(
            """
            Compete aos SESMT, entre outras atribuições:
            *   Elaborar ou participar da elaboração do inventário de riscos.
            *   Acompanhar a implementação do plano de ação do Programa de Gerenciamento de Riscos (PGR).
            *   Implementar medidas de prevenção de acordo com a classificação de risco do PGR.
            *   Elaborar plano de trabalho e monitorar metas, indicadores e resultados de segurança e saúde no trabalho.
            *   Responsabilizar-se tecnicamente pela orientação quanto ao cumprimento das NR aplicáveis.
            *   Manter permanente interação com a CIPA.
            *   Promover atividades de orientação, informação e conscientização dos trabalhadores.
            *   Propor, imediatamente, a interrupção das atividades em caso de grave e iminente risco.
            *   Conduzir ou acompanhar as investigações de acidentes e doenças relacionadas ao trabalho.
            *   Compartilhar informações relevantes para a prevenção de acidentes e doenças.
            *   Acompanhar e participar nas ações do PCMSO.
            *(NR-04, item 4.3.1)*.
            """
        )

    with st.expander("Composição e Carga Horária dos Profissionais do SESMT"):
        st.markdown(
            """
            O SESMT deve ser composto por médico do trabalho, engenheiro de segurança do trabalho, técnico de
            segurança do trabalho, enfermeiro do trabalho e auxiliar/técnico em enfermagem do trabalho,
            obedecido o Anexo II da NR-04 (utilizado para o cálculo nesta página).
            *   **Técnico de Segurança do Trabalho e Auxiliar/Técnico de Enfermagem do Trabalho**: Devem dedicar
                quarenta e quatro horas por semana para as atividades do SESMT (tempo integral).
            *   **Engenheiro de Segurança do Trabalho, Médico do Trabalho e Enfermeiro do Trabalho**: Podem atuar
                em tempo parcial (mínimo de quinze horas semanais) ou tempo integral (trinta horas semanais),
                conforme o dimensionamento. A indicação de tempo parcial é feita com um asterisco (*) na tabela
                de dimensionamento.
            *   **Substituição**: O empregador pode optar pela contratação de um Enfermeiro do Trabalho em tempo
                parcial (mínimo de quinze horas semanais), em substituição ao Auxiliar ou Técnico de Enfermagem
                do Trabalho, quando indicado por três asteriscos (***) na tabela.
            *(NR-04, itens 4.3.2, 4.3.5, 4.3.7)*.
            """
        )
        st.markdown(
            """
            **Importante**: Aos profissionais do SESMT é vedado o exercício de atividades que não façam parte
            das atribuições previstas na NR-04 e em outras NR, durante o horário de atuação neste serviço.
            *(NR-04, item 4.3.8)*.
            """
        )

    with st.expander("Modalidades de Constituição do SESMT e Regionalização"):
        st.markdown(
            """
            O SESMT pode ser constituído em diferentes modalidades, que impactam o dimensionamento:
            *   **SESMT Individual**: Aplicável a um único estabelecimento que se enquadra nos critérios do Anexo II da NR-04.
            *   **SESMT Regionalizado**: Uma organização com múltiplos estabelecimentos pode constituir um SESMT regionalizado. Isso ocorre quando um estabelecimento se enquadra no Anexo II e outros não. O SESMT do estabelecimento que se enquadra estende a assistência aos demais. O dimensionamento considera o **somatório de trabalhadores** de todos os estabelecimentos atendidos e o maior Grau de Risco entre eles.
            *   **SESMT Estadual**: Aplicável quando o somatório de trabalhadores de *todos* os estabelecimentos da mesma unidade da federação atinge os limites do Anexo II, mas *nenhum* estabelecimento individualmente se enquadra. O dimensionamento também considera o somatório de trabalhadores e o maior Grau de Risco.
            *   **SESMT Compartilhado**: Uma ou mais organizações de mesma atividade econômica, localizadas em um mesmo município ou em municípios limítrofes, podem constituir SESMT compartilhado. O dimensionamento considera o somatório dos trabalhadores assistidos.

            **Como funciona o cálculo para modalidades Regionalizadas/Estaduais/Compartilhadas nesta ferramenta:**
            Ao selecionar o modo "Dimensionamento Regionalizado/Estadual/Compartilhado", você adicionará cada estabelecimento individualmente. A ferramenta então irá:
            1.  Determinar o Grau de Risco de cada CNAE.
            2.  Aplicar a regra de redução de 50% dos funcionários para estabelecimentos ME/EPP com Grau de Risco 1 ou 2.
            3.  Somar o número de funcionários *efetivos* de todos os estabelecimentos.
            4.  Identificar o *maior* Grau de Risco entre todos os estabelecimentos.
            5.  Realizar o cálculo final do SESMT utilizando o **somatório total de funcionários** e o **maior Grau de Risco** encontrados.
            
            Além disso, para fins de comparação e planejamento interno, esta ferramenta também apresentará o dimensionamento que cada estabelecimento individualmente exigiria, caso não fizesse parte de um SESMT regionalizado.
            *(NR-04, itens 4.4.1 a 4.4.5 e 4.5.1 a 4.5.3)*.
            """
        )

if __name__ == "__main__":
    sesmt_sizing_page()