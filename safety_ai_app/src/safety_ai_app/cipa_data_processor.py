import logging
from datetime import date, timedelta
from typing import Dict, Any, Tuple, Optional, List

logger = logging.getLogger(__name__)

# Quadro I da NR-05 - Dimensionamento da CIPA (mantido como está)
CIPA_DIMENSIONING_TABLE: Dict[int, Dict[Tuple[int, int], Dict[str, Any]]] = {
    1: {
        (20, 29): {'efetivos': 1, 'suplentes': 1},
        (30, 50): {'efetivos': 1, 'suplentes': 1},
        (51, 80): {'efetivos': 1, 'suplentes': 1},
        (81, 100): {'efetivos': 1, 'suplentes': 1},
        (101, 120): {'efetivos': 1, 'suplentes': 1},
        (121, 140): {'efetivos': 1, 'suplentes': 1},
        (141, 300): {'efetivos': 1, 'suplentes': 1},
        (301, 500): {'efetivos': 2, 'suplentes': 2},
        (501, 1000): {'efetivos': 4, 'suplentes': 3},
        (1001, 2500): {'efetivos': 5, 'suplentes': 4},
        (2501, 5000): {'efetivos': 6, 'suplentes': 5},
        (5001, 10000): {'efetivos': 8, 'suplentes': 6},
        (10001, float('inf')): {'base_efetivos': 8, 'base_suplentes': 6, 'increment_base': 10000, 'increment_per_group': 2500, 'efetivos_add': 1, 'suplentes_add': 1}
    },
    2: {
        (20, 29): {'efetivos': 1, 'suplentes': 1},
        (30, 50): {'efetivos': 2, 'suplentes': 1},
        (51, 80): {'efetivos': 2, 'suplentes': 1},
        (81, 100): {'efetivos': 2, 'suplentes': 1},
        (101, 120): {'efetivos': 2, 'suplentes': 1},
        (121, 140): {'efetivos': 2, 'suplentes': 1},
        (141, 300): {'efetivos': 3, 'suplentes': 2},
        (301, 500): {'efetivos': 4, 'suplentes': 3},
        (501, 1000): {'efetivos': 5, 'suplentes': 4},
        (1001, 2500): {'efetivos': 6, 'suplentes': 5},
        (2501, 5000): {'efetivos': 8, 'suplentes': 6},
        (5001, 10000): {'efetivos': 10, 'suplentes': 8},
        (10001, float('inf')): {'base_efetivos': 10, 'base_suplentes': 8, 'increment_base': 10000, 'increment_per_group': 2500, 'efetivos_add': 1, 'suplentes_add': 1}
    },
    3: {
        (20, 29): {'efetivos': 1, 'suplentes': 1},
        (30, 50): {'efetivos': 3, 'suplentes': 2},
        (51, 80): {'efetivos': 3, 'suplentes': 2},
        (81, 100): {'efetivos': 3, 'suplentes': 2},
        (101, 120): {'efetivos': 3, 'suplentes': 2},
        (121, 140): {'efetivos': 3, 'suplentes': 2},
        (141, 300): {'efetivos': 4, 'suplentes': 2},
        (301, 500): {'efetivos': 5, 'suplentes': 4},
        (501, 1000): {'efetivos': 6, 'suplentes': 4},
        (1001, 2500): {'efetivos': 8, 'suplentes': 6},
        (2501, 5000): {'efetivos': 10, 'suplentes': 8},
        (5001, 10000): {'efetivos': 12, 'suplentes': 8},
        (10001, float('inf')): {'base_efetivos': 12, 'base_suplentes': 8, 'increment_base': 10000, 'increment_per_group': 2500, 'efetivos_add': 2, 'suplentes_add': 2}
    },
    4: {
        (20, 29): {'efetivos': 1, 'suplentes': 1},
        (30, 50): {'efetivos': 4, 'suplentes': 2},
        (51, 80): {'efetivos': 4, 'suplentes': 2},
        (81, 100): {'efetivos': 4, 'suplentes': 2},
        (101, 120): {'efetivos': 4, 'suplentes': 2},
        (121, 140): {'efetivos': 4, 'suplentes': 2},
        (141, 300): {'efetivos': 4, 'suplentes': 3},
        (301, 500): {'efetivos': 5, 'suplentes': 4},
        (501, 1000): {'efetivos': 6, 'suplentes': 5},
        (1001, 2500): {'efetivos': 9, 'suplentes': 7},
        (2501, 5000): {'efetivos': 11, 'suplentes': 8},
        (5001, 10000): {'efetivos': 13, 'suplentes': 10},
        (10001, float('inf')): {'base_efetivos': 13, 'base_suplentes': 10, 'increment_base': 10000, 'increment_per_group': 2500, 'efetivos_add': 2, 'suplentes_add': 2}
    }
}

def get_cipa_dimensioning(grau_risco: int, num_employees: int) -> Dict[str, Any]:
    """
    Retorna o dimensionamento da CIPA (membros efetivos e suplentes)
    com base no Grau de Risco e no número de funcionários, conforme o Quadro I da NR-05.

    Args:
        grau_risco: O grau de risco do estabelecimento (1, 2, 3 ou 4).
        num_employees: O número total de funcionários do estabelecimento.

    Returns:
        Um dicionário com 'efetivos' e 'suplentes', e opcionalmente 'observacao',
        ou um dicionário indicando que o dimensionamento não é aplicável.
    """
    if num_employees < 20:
        logger.info(f"Estabelecimento com {num_employees} funcionários não se enquadra no Quadro I da NR-05 para constituição de CIPA.")
        return {'efetivos': 0, 'suplentes': 0, 'observacao': 'Estabelecimento com menos de 20 funcionários não se enquadra no Quadro I da NR-05 para constituição de CIPA. A organização deve nomear um representante da organização para auxiliar nas ações de prevenção.'}

    if grau_risco not in CIPA_DIMENSIONING_TABLE:
        logger.error(f"Grau de Risco {grau_risco} inválido ou não encontrado na tabela de dimensionamento da CIPA.")
        return {'efetivos': 0, 'suplentes': 0, 'observacao': 'Grau de Risco inválido ou fora do intervalo esperado (1-4).'}

    risk_table = CIPA_DIMENSIONING_TABLE[grau_risco]

    for (min_emp, max_emp), data in risk_table.items():
        if min_emp <= num_employees <= max_emp:
            if max_emp == float('inf'): # Caso especial para mais de 10.000 funcionários
                efetivos = data['base_efetivos']
                suplentes = data['base_suplentes']
                
                remaining_employees = num_employees - data['increment_base']
                if remaining_employees > 0:
                    # Calcula o número de grupos de incremento, arredondando para cima
                    num_groups = (remaining_employees + data['increment_per_group'] - 1) // data['increment_per_group']
                    efetivos += num_groups * data['efetivos_add']
                    suplentes += num_groups * data['suplentes_add']
                
                return {'efetivos': efetivos, 'suplentes': suplentes}
            else:
                return {'efetivos': data['efetivos'], 'suplentes': data['suplentes']}
    
    logger.warning(f"Não foi possível encontrar dimensionamento para GR {grau_risco} e {num_employees} funcionários.")
    return {'efetivos': 0, 'suplentes': 0, 'observacao': 'Não foi possível determinar o dimensionamento. Verifique os dados de entrada.'}


# --- Funções e Dados para o Cronograma Eleitoral da CIPA ---

# Feriados Nacionais Brasileiros para 2025, 2026 e 2027
# Fonte: Calendário oficial (adaptado, verificar sempre fontes atualizadas)
BRAZILIAN_NATIONAL_HOLIDAYS: List[date] = [
    # 2025
    date(2025, 1, 1),   # Confraternização Universal
    date(2025, 3, 3),   # Carnaval (segunda-feira - amplamente observado)
    date(2025, 3, 4),   # Carnaval (terça-feira - amplamente observado)
    date(2025, 4, 18),  # Paixão de Cristo
    date(2025, 4, 21),  # Tiradentes
    date(2025, 5, 1),   # Dia do Trabalho
    date(2025, 6, 19),  # Corpus Christi (amplamente observado)
    date(2025, 9, 7),   # Independência do Brasil
    date(2025, 10, 12), # Nossa Senhora Aparecida
    date(2025, 11, 2),  # Finados
    date(2025, 11, 15), # Proclamação da República
    date(2025, 11, 20), # Consciência Negra (Lei 14.759/2023)
    date(2025, 12, 25), # Natal
    # 2026
    date(2026, 1, 1),   # Confraternização Universal
    date(2026, 2, 16),  # Carnaval (segunda-feira)
    date(2026, 2, 17),  # Carnaval (terça-feira)
    date(2026, 4, 3),   # Paixão de Cristo
    date(2026, 4, 21),  # Tiradentes
    date(2026, 5, 1),   # Dia do Trabalho
    date(2026, 6, 4),   # Corpus Christi
    date(2026, 9, 7),   # Independência do Brasil
    date(2026, 10, 12), # Nossa Senhora Aparecida
    date(2026, 11, 2),  # Finados
    date(2026, 11, 15), # Proclamação da República
    date(2026, 11, 20), # Consciência Negra
    date(2026, 12, 25), # Natal
    # 2027
    date(2027, 1, 1),   # Confraternização Universal
    date(2027, 2, 8),   # Carnaval (segunda-feira)
    date(2027, 2, 9),   # Carnaval (terça-feira)
    date(2027, 3, 26),  # Paixão de Cristo
    date(2027, 4, 21),  # Tiradentes
    date(2027, 5, 1),   # Dia do Trabalho
    date(2027, 5, 27),  # Corpus Christi
    date(2027, 9, 7),   # Independência do Brasil
    date(2027, 10, 12), # Nossa Senhora Aparecida
    date(2027, 11, 2),  # Finados
    date(2027, 11, 15), # Proclamação da República
    date(2027, 11, 20), # Consciência Negra
    date(2027, 12, 25)  # Natal
]

def is_working_day(day: date, holidays: List[date]) -> bool:
    """Verifica se um determinado dia é um dia útil (não é fim de semana nem feriado)."""
    return day.weekday() < 5 and day not in holidays

def find_next_working_day(start_day: date, holidays: List[date]) -> date:
    """Encontra o próximo dia útil a partir de (e incluindo) start_day."""
    current_day = start_day
    while not is_working_day(current_day, holidays):
        current_day += timedelta(days=1)
    return current_day

def find_previous_working_day(start_day: date, holidays: List[date]) -> date:
    """Encontra o dia útil anterior a partir de (e incluindo) start_day."""
    current_day = start_day
    while not is_working_day(current_day, holidays):
        current_day -= timedelta(days=1)
    return current_day

def add_working_days(start_day: date, days_to_add: int, holidays: List[date]) -> date:
    """Adiciona um número especificado de dias úteis a uma data de início."""
    current_day = start_day
    # Garante que o dia de início seja um dia útil para começar a contagem
    current_day = find_next_working_day(current_day, holidays)
    
    while days_to_add > 0:
        current_day += timedelta(days=1)
        if is_working_day(current_day, holidays):
            days_to_add -= 1
    return current_day

def calculate_election_schedule(
    mandate_end_date: date, # Agora este é o input principal
    holidays: List[date] = BRAZILIAN_NATIONAL_HOLIDAYS
) -> Dict[str, Any]:
    """
    Calcula o cronograma eleitoral da CIPA com base na NR-05,
    a partir da data de término do mandato atual.

    Args:
        mandate_end_date: A data de término do mandato atual da CIPA.
        holidays: Uma lista de datas consideradas feriados.

    Returns:
        Um dicionário com as datas calculadas e quaisquer avisos relevantes.
    """
    schedule = {}
    warnings = []
    today = date.today()

    # --- Etapas calculadas retroativamente a partir da data de término do mandato ---

    # 1. Data da Posse (primeiro dia útil após o término do mandato anterior - NR-05, item 5.4.7)
    schedule['data_posse'] = find_next_working_day(mandate_end_date + timedelta(days=1), holidays)

    # 2. Data da Eleição (mínimo 30 dias antes do término do mandato - NR-05, item 5.5.3 f)
    # Calculamos a data limite para a eleição e ajustamos para o dia útil anterior.
    latest_election_date_nr = mandate_end_date - timedelta(days=30)
    schedule['data_eleicao'] = find_previous_working_day(latest_election_date_nr, holidays)

    # 3. Apuração dos Votos e Divulgação do Resultado (mesmo dia da eleição)
    schedule['apuracao_votos'] = schedule['data_eleicao']
    schedule['divulgacao_resultado'] = schedule['data_eleicao']

    # 4. Publicação da Relação de Candidatos Inscritos (deve ser após o fim das inscrições e antes da eleição)
    # Sugerimos 1 dia útil antes da eleição para dar tempo de divulgação.
    schedule['publicacao_relacao_inscritos'] = find_previous_working_day(schedule['data_eleicao'] - timedelta(days=1), holidays)

    # 5. Término do Período de Inscrição (deve ser antes da publicação da relação de inscritos)
    # Sugerimos 1 dia útil antes da publicação da relação de inscritos.
    schedule['fim_inscricoes'] = find_previous_working_day(schedule['publicacao_relacao_inscritos'] - timedelta(days=1), holidays)
    
    # 6. Início do Período de Inscrições (15 dias corridos antes do fim das inscrições - NR-05, item 5.5.3 b)
    schedule['inicio_inscricoes'] = schedule['fim_inscricoes'] - timedelta(days=14)
    # Garante que o início das inscrições seja um dia útil
    schedule['inicio_inscricoes'] = find_next_working_day(schedule['inicio_inscricoes'], holidays)

    # 7. Data de Publicação do Edital de Convocação (mínimo 60 dias antes do término do mandato - NR-05, item 5.5.1)
    # Calculamos a data limite para a publicação do edital e ajustamos para o dia útil anterior.
    latest_edital_date_nr = mandate_end_date - timedelta(days=60)
    
    # O edital deve ser publicado no mínimo 60 dias antes do término do mandato,
    # E também deve ser antes do início das inscrições.
    # Escolhemos a data mais antiga entre essas duas condições.
    edital_date_by_60_days = find_previous_working_day(latest_edital_date_nr, holidays)
    edital_date_by_inscriptions = find_previous_working_day(schedule['inicio_inscricoes'] - timedelta(days=1), holidays) # 1 dia útil antes do início das inscrições
    
    schedule['data_publicacao_edital'] = min(edital_date_by_60_days, edital_date_by_inscriptions)

    # 8. Constituição da Comissão Eleitoral (NR-05, item 5.5.2)
    # Esta é uma ação interna, geralmente logo após a convocação.
    schedule['constituicao_comissao_eleitoral'] = schedule['data_publicacao_edital'] # Ação a ser tomada a partir desta data.

    # 9. Comunicação do Início do Processo ao Sindicato (NR-05, item 5.5.1.1)
    # Deve ser com antecedência, vamos sugerir o próximo dia útil após o edital.
    schedule['comunicacao_sindicato'] = find_next_working_day(schedule['data_publicacao_edital'] + timedelta(days=1), holidays)
    
    # --- Etapas calculadas progressivamente a partir da data de término do mandato ---

    # 10. Prazo Final para Denúncias sobre o Processo Eleitoral (30 dias após a divulgação do resultado - NR-05, item 5.5.5)
    prazo_final_denuncias_corridos = schedule['divulgacao_resultado'] + timedelta(days=30)
    schedule['prazo_final_denuncias'] = find_next_working_day(prazo_final_denuncias_corridos, holidays)

    # 11. Prazo para Treinamento
    # NR-05, item 5.7.1: "A organização deve promover treinamento... antes da posse."
    # NR-05, item 5.7.1.1: "O treinamento de CIPA em primeiro mandato será realizado no prazo máximo de 30 (trinta) dias, contados a partir da data da posse."
    
    # Para CIPA em mandatos subsequentes, o treinamento deve ser concluído ANTES da posse.
    # Sugerimos o dia útil anterior à posse como prazo final.
    schedule['prazo_final_treinamento_mandato_subsequente'] = find_previous_working_day(schedule['data_posse'] - timedelta(days=1), holidays)
    
    # Para CIPA em primeiro mandato ou eleição extraordinária, o prazo é até 30 dias após a posse.
    schedule['prazo_final_treinamento_primeiro_mandato'] = add_working_days(schedule['data_posse'], 30, holidays)
    
    schedule['observacao_treinamento'] = (
        "Para CIPA em primeiro mandato ou eleição extraordinária, o treinamento deve ser realizado no prazo máximo de 30 dias contados da posse. "
        "Para os demais casos (mandatos subsequentes), o treinamento deve ser realizado ANTES da posse."
    )

    # 12. Ata da Posse (documento gerado após a posse)
    schedule['ata_da_posse'] = find_next_working_day(schedule['data_posse'] + timedelta(days=1), holidays) # Sugerimos o dia útil seguinte à posse

    # 13. Criar Calendário Pré-estabelecido de Reuniões Mensais
    schedule['criar_calendario_reunioes'] = find_next_working_day(schedule['data_posse'] + timedelta(days=1), holidays) # Ação a ser tomada a partir da posse
    
    # --- Validações e Avisos ---

    # Validação: Data de Término do Mandato no passado
    if mandate_end_date < today:
        warnings.append("Atenção: A Data de Término do Mandato Atual da CIPA está no passado. O cronograma será calculado, mas as datas podem não ser práticas e os prazos da NR-05 podem não ser atendidos.")

    # Validação: Edital no passado ou não respeitando 60 dias
    if schedule['data_publicacao_edital'] < today:
        warnings.append(
            f"CRÍTICO: A data de publicação do edital ({schedule['data_publicacao_edital'].strftime('%d/%m/%Y')}) "
            f"calculada para respeitar o prazo de 60 dias antes do término do mandato já passou. "
            f"O processo eleitoral está atrasado e em não conformidade com a NR-05 (item 5.5.1)."
        )
    elif (mandate_end_date - schedule['data_publicacao_edital']).days < 60:
         warnings.append(
            f"Atenção: A Data de Publicação do Edital ({schedule['data_publicacao_edital'].strftime('%d/%m/%Y')}) "
            f"está a menos de 60 dias do Término do Mandato Atual ({mandate_end_date.strftime('%d/%m/%Y')}). "
            f"A NR-05 (item 5.5.1) exige um prazo mínimo de 60 dias para a convocação. "
            f"Isso indica que o processo eleitoral foi iniciado tarde demais em relação ao término do mandato."
        )

    # Validação: Eleição no passado ou não respeitando 30 dias
    if schedule['data_eleicao'] < today:
        warnings.append(
            f"CRÍTICO: A data da eleição ({schedule['data_eleicao'].strftime('%d/%m/%Y')}) "
            f"calculada para respeitar o prazo de 30 dias antes do término do mandato já passou. "
            f"O processo eleitoral está atrasado e em não conformidade com a NR-05 (item 5.5.3 f)."
        )
    elif (mandate_end_date - schedule['data_eleicao']).days < 30:
        warnings.append(
            f"Atenção: A Data da Eleição ({schedule['data_eleicao'].strftime('%d/%m/%Y')}) "
            f"está a menos de 30 dias do Término do Mandato Atual ({mandate_end_date.strftime('%d/%m/%Y')}). "
            f"A NR-05 (item 5.5.3 f) exige um prazo mínimo de 30 dias para a realização da eleição. "
            f"Isso indica que o processo eleitoral foi iniciado tarde demais em relação ao término do mandato."
        )
    
    # Validação: Inscrições antes do edital
    if schedule['inicio_inscricoes'] < schedule['data_publicacao_edital']:
        warnings.append(f"Erro Lógico: O Início do Período de Inscrições ({schedule['inicio_inscricoes'].strftime('%d/%m/%Y')}) não pode ser anterior à Publicação do Edital ({schedule['data_publicacao_edital'].strftime('%d/%m/%Y')}). Verifique a data de término do mandato.")

    # Validação: Eleição antes do fim das inscrições
    if schedule['data_eleicao'] <= schedule['fim_inscricoes']:
        warnings.append(f"Erro Lógico: A Data da Eleição ({schedule['data_eleicao'].strftime('%d/%m/%Y')}) deve ser posterior ao Término do Período de Inscrições ({schedule['fim_inscricoes'].strftime('%d/%m/%Y')}). Verifique a data de término do mandato.")

    # Validação: Posse antes da eleição
    if schedule['data_posse'] <= schedule['data_eleicao']:
        warnings.append(f"Erro Lógico: A Data da Posse ({schedule['data_posse'].strftime('%d/%m/%Y')}) deve ser posterior à Data da Eleição ({schedule['data_eleicao'].strftime('%d/%m/%Y')}). Verifique a data de término do mandato.")

    # Validação: Publicação da relação de inscritos antes do fim das inscrições
    if schedule['publicacao_relacao_inscritos'] <= schedule['fim_inscricoes']:
        warnings.append(f"Erro Lógico: A Publicação da Relação de Candidatos Inscritos ({schedule['publicacao_relacao_inscritos'].strftime('%d/%m/%Y')}) deve ser posterior ao Término do Período de Inscrições ({schedule['fim_inscricoes'].strftime('%d/%m/%Y')}). Verifique a data de término do mandato.")


    # Ordenar as datas para exibição cronológica
    # Criamos uma lista de tuplas (data, main_label, explanation, key) para ordenar e depois exibir
    # A 'key' é usada para desempatar a ordem quando as datas são iguais, mantendo a lógica de sequência.
    ordered_items_raw = []
    ordered_items_raw.append((schedule['data_publicacao_edital'], "Data de Publicação do Edital de Convocação", "NR-05, item 5.5.1 - Mínimo de 60 dias antes do término do mandato e antes do início das inscrições", '01_edital_convocacao', 'calendar_month'))
    ordered_items_raw.append((schedule['constituicao_comissao_eleitoral'], "Constituição da Comissão Eleitoral", "NR-05, item 5.5.2 - Ação recomendada a partir da publicação do edital", '02_comissao_eleitoral', 'group_add'))
    ordered_items_raw.append((schedule['comunicacao_sindicato'], "Comunicar Início do Processo ao Sindicato", "NR-05, item 5.5.1.1 - Sugerido 1 dia útil após a publicação do edital", '03_comunicacao_sindicato', 'mail'))
    ordered_items_raw.append((schedule['inicio_inscricoes'], "Início do Período de Inscrições de Candidatos", "NR-05, item 5.5.3 b - 15 dias corridos antes do término das inscrições", '04_inicio_inscricoes', 'how_to_reg'))
    ordered_items_raw.append((schedule['fim_inscricoes'], "Término do Período de Inscrições de Candidatos", "NR-05, item 5.5.3 b - 1 dia útil antes da publicação da relação de inscritos", '05_fim_inscricoes', 'event_busy'))
    ordered_items_raw.append((schedule['publicacao_relacao_inscritos'], "Publicação e Divulgação da Relação de Candidatos Inscritos", "NR-05, item 5.5.3 e - 1 dia útil antes da eleição", '06_publicacao_inscritos', 'list_alt'))
    ordered_items_raw.append((schedule['data_eleicao'], "Data da Eleição", "NR-05, item 5.5.3 f - Mínimo de 30 dias antes do término do mandato", '07_data_eleicao', 'how_to_vote'))
    ordered_items_raw.append((schedule['apuracao_votos'], "Apuração dos Votos e Divulgação do Resultado", "NR-05, item 5.5.3 i - No mesmo dia da eleição", '08_apuracao_divulgacao', 'analytics'))
    ordered_items_raw.append((schedule['prazo_final_denuncias'], "Prazo Final para Denúncias", "NR-05, item 5.5.5 - 30 dias corridos após a divulgação do resultado", '09_prazo_denuncias', 'gavel'))
    ordered_items_raw.append((schedule['data_posse'], "Data da Posse dos Membros da CIPA", "NR-05, item 5.4.7 - Primeiro dia útil após o término do mandato anterior", '10_data_posse', 'handshake'))
    ordered_items_raw.append((schedule['ata_da_posse'], "Ata da Posse", "NR-05, item 5.4.8 - Documento gerado após a posse, sugerido 1 dia útil após a posse", '11_ata_posse', 'description'))
    ordered_items_raw.append((schedule['criar_calendario_reunioes'], "Criar Calendário Pré-estabelecido de Reuniões Mensais", "NR-05, item 5.6.1 - Ação a ser tomada a partir da posse", '12_calendario_reunioes', 'event'))
    ordered_items_raw.append((schedule['prazo_final_treinamento_mandato_subsequente'], "Prazo Final para Treinamento (Mandatos Subsequentes)", "NR-05, item 5.7.1 - ANTES da posse", '13_treinamento_subsequente', 'school'))
    ordered_items_raw.append((schedule['prazo_final_treinamento_primeiro_mandato'], "Prazo Final para Treinamento (Primeiro Mandato/Extraordinário)", "NR-05, item 5.7.1.1 - ATÉ 30 dias corridos após posse", '14_treinamento_primeiro_mandato', 'school'))
    
    # Ordena pela data, e se as datas forem iguais, pela ordem de inserção (que é a ordem lógica definida pelas chaves)
    schedule['ordered_items'] = sorted(ordered_items_raw, key=lambda x: (x[0], x[3])) # Usando o key para ordenação
    schedule['warnings'] = warnings
    return schedule
