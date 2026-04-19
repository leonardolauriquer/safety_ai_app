import logging
import pandas as pd
import os
import re
from typing import Dict, Any, Tuple, Union, Optional
from functools import lru_cache

from src.safety_ai_app.google_drive_integrator import GoogleDriveIntegrator

logger = logging.getLogger(__name__)

GOOGLE_DRIVE_SESMT_FOLDER_ID = "12ecb1RkbBuZ0GkoXGjux4wsZP7iqE_Tr"
SESMT_EXCEL_FILE_NAME = "Dimensionamento_SESMT.xlsx"
LOCAL_TEMP_DIR = "temp_docs_local"
LOCAL_SESMT_FILE_PATH = os.path.join(LOCAL_TEMP_DIR, SESMT_EXCEL_FILE_NAME)

PROFESSIONAL_NAMES = {
    'tecnico_seguranca': 'Técnico de Segurança do Trabalho',
    'engenheiro_seguranca': 'Engenheiro de Segurança do Trabalho',
    'aux_tec_enfermagem': 'Auxiliar/Técnico de Enfermagem do Trabalho',
    'enfermeiro': 'Enfermeiro do Trabalho',
    'medico': 'Médico do Trabalho',
}

EMPLOYEE_RANGE_COLUMNS = {
    "50 a 100": (50, 100),
    "101 a 250": (101, 250),
    "251 a 500": (251, 500),
    "501 a 1.000": (501, 1000),
    "1.001 a 2.000": (1001, 2000),
    "2.001 a 3.500": (2001, 3500),
    "3.501 a 5.000": (3501, 5000),
}

PROFESSIONAL_COLUMN_MAP = {
    "Técnico Seg. Trabalho": "tecnico_seguranca",
    "Engenheiro Seg. Trabalho": "engenheiro_seguranca",
    "Aux./Tec. Enferm. do Trabalho": "aux_tec_enfermagem",
    "Enfermeiro do Trabalho": "enfermeiro",
    "Médico do Trabalho": "medico",
}

def _clean_text(text: Any) -> str:
    if pd.isna(text):
        return ""
    cleaned = str(text).replace('\n', ' ').strip()
    return re.sub(r'\s+', ' ', cleaned)

@lru_cache(maxsize=1)
def _load_sesmt_data_from_drive() -> Tuple[
    Dict[int, Dict[Tuple[int, int], Dict[str, Union[int, str]]]],
    Dict[int, Dict[str, Union[int, str]]]
]:
    logger.info(f"Tentando carregar dados do SESMT do Google Drive: {SESMT_EXCEL_FILE_NAME}")
    
    os.makedirs(LOCAL_TEMP_DIR, exist_ok=True)

    drive_integrator = GoogleDriveIntegrator()
    downloaded_path = drive_integrator.download_file_from_folder(
        GOOGLE_DRIVE_SESMT_FOLDER_ID,
        SESMT_EXCEL_FILE_NAME,
        LOCAL_SESMT_FILE_PATH
    )

    if not downloaded_path:
        logger.error(f"Falha ao baixar '{SESMT_EXCEL_FILE_NAME}' do Google Drive. Usando tabelas vazias.")
        return {}, {}

    try:
        df_raw = pd.read_excel(downloaded_path, sheet_name=0, header=None)
        logger.debug(f"DataFrame raw (primeiras 5 linhas):\n{df_raw.head()}")

        header_row = df_raw.iloc[0]
        cleaned_header_names = [_clean_text(col_name) for col_name in header_row]

        if len(cleaned_header_names) > 9 and "Acima de 5.000" in cleaned_header_names[9]:
            cleaned_header_names[9] = "Acima de 5.000 Para cada grupo De 4.000 ou fração acima 2.000**"
        
        df = df_raw.iloc[1:].copy()
        df.columns = cleaned_header_names[:len(df.columns)]

        logger.debug(f"Colunas do DataFrame renomeadas (single-level, após limpeza e correção):\n{df.columns.tolist()}")
        logger.debug(f"DataFrame após atribuição de cabeçalho (primeiras 5 linhas):\n{df.head()}")

        expected_grau_risco_col = 'Grau de Risco'
        expected_profissionais_col = 'Profissionais'
        expected_above_5000_col = 'Acima de 5.000 Para cada grupo De 4.000 ou fração acima 2.000**'

        critical_columns = [expected_grau_risco_col, expected_profissionais_col, expected_above_5000_col] + list(EMPLOYEE_RANGE_COLUMNS.keys())
        for col_name in critical_columns:
            if col_name not in df.columns:
                logger.error(f"CRÍTICO: Coluna essencial '{col_name}' não encontrada no DataFrame. Estrutura do Excel inesperada. Colunas disponíveis: {df.columns.tolist()}")
                raise KeyError(f"Coluna '{col_name}' não encontrada. A estrutura do Excel 'Dimensionamento_SESMT.xlsx' não corresponde ao esperado.")

        df[expected_grau_risco_col] = df[expected_grau_risco_col].ffill()
        df = df.dropna(subset=[expected_grau_risco_col, expected_profissionais_col])
        
        logger.debug(f"DataFrame após ffill e dropna (primeiras 5 linhas):\n{df.head()}")

        parsed_dimensioning_table: Dict[int, Dict[Tuple[int, int], Dict[str, Union[int, str]]]] = {gr: {} for gr in range(1, 5)}
        parsed_above_5000_rule: Dict[int, Dict[str, Union[int, str]]] = {gr: {} for gr in range(1, 5)}

        for index, row in df.iterrows():
            grau_risco = int(row[expected_grau_risco_col])
            professional_name = _clean_text(row[expected_profissionais_col])
            internal_professional_key = PROFESSIONAL_COLUMN_MAP.get(professional_name)

            if not internal_professional_key:
                logger.warning(f"Nome de profissional desconhecido '{professional_name}' encontrado no Excel. Pulando linha {index}.")
                logger.warning(f"Nomes disponíveis no mapeamento: {list(PROFESSIONAL_COLUMN_MAP.keys())}")
                continue

            logger.debug(f"Processando linha: Index={index}, Grau de Risco={grau_risco}, Profissional='{professional_name}'")
            logger.debug(f"Conteúdo completo da linha: {row.to_dict()}")
            
            for col_name_range, emp_range_tuple in EMPLOYEE_RANGE_COLUMNS.items():
                if emp_range_tuple not in parsed_dimensioning_table[grau_risco]:
                    parsed_dimensioning_table[grau_risco][emp_range_tuple] = {pk: '0' for pk in PROFESSIONAL_COLUMN_MAP.values()}
                
                if col_name_range in df.columns and pd.notna(row[col_name_range]):
                    value = str(row[col_name_range]).strip()
                    logger.debug(f"  - Faixa '{col_name_range}': Valor bruto='{row[col_name_range]}', Valor limpo='{value}'")
                    parsed_dimensioning_table[grau_risco][emp_range_tuple][internal_professional_key] = value
                else:
                    logger.debug(f"  - Faixa '{col_name_range}': Valor não presente ou é NaN para o profissional '{professional_name}'. Definindo como '0'.")
                    parsed_dimensioning_table[grau_risco][emp_range_tuple][internal_professional_key] = '0'

            if expected_above_5000_col in df.columns and pd.notna(row[expected_above_5000_col]):
                value = str(row[expected_above_5000_col]).strip()
                parsed_above_5000_rule[grau_risco][internal_professional_key] = value
            else:
                parsed_above_5000_rule[grau_risco][internal_professional_key] = '0'

        logger.info("Dados do SESMT carregados e analisados com sucesso do Google Drive.")
        logger.debug(f"parsed_dimensioning_table carregado: {parsed_dimensioning_table}")
        logger.debug(f"parsed_above_5000_rule carregado: {parsed_above_5000_rule}")
        return parsed_dimensioning_table, parsed_above_5000_rule

    except Exception as e:
        logger.error(f"Erro ao analisar o arquivo Excel do SESMT '{downloaded_path}': {e}", exc_info=True)
        return {}, {}
    finally:
        pass

SESMT_DIMENSIONING_TABLE, SESMT_ABOVE_5000_RULE_ADDITIONAL = _load_sesmt_data_from_drive()

def get_sesmt_dimensioning(grau_risco: int, num_employees: int) -> Dict[str, Any]:
    logger.info(f"Iniciando dimensionamento do SESMT para GR: {grau_risco}, Empregados: {num_employees}")

    if not (1 <= grau_risco <= 4):
        logger.error(f"Grau de Risco inválido: {grau_risco}. Deve ser entre 1 e 4.")
        return {"error": "Grau de Risco inválido. Deve ser entre 1 e 4."}
    
    if num_employees < 0:
        logger.error(f"Número de empregados inválido: {num_employees}. Deve ser um valor positivo.")
        return {"error": "Número de empregados inválido. Deve ser um valor positivo."}

    if not SESMT_DIMENSIONING_TABLE or not SESMT_ABOVE_5000_RULE_ADDITIONAL:
        logger.error("Dados de dimensionamento do SESMT não carregados. Não é possível realizar o cálculo.")
        return {"error": "Dados de dimensionamento do SESMT não carregados. Verifique o arquivo Excel no Google Drive e as permissões."}

    result: Dict[str, Any] = {
        'tecnico_seguranca': {'qty': '0', 'specific_observation': None},
        'engenheiro_seguranca': {'qty': '0', 'specific_observation': None},
        'aux_tec_enfermagem': {'qty': '0', 'specific_observation': None},
        'enfermeiro': {'qty': '0', 'specific_observation': None},
        'medico': {'qty': '0', 'specific_observation': None},
        'general_observations': []
    }

    if num_employees < 50:
        result['general_observations'].append("Para estabelecimentos com menos de 50 empregados, a constituição do SESMT pode não ser obrigatória, dependendo de outras condições da NR-04 (ex: SESMT compartilhado, etc.). Consulte a NR-04 para casos específicos.")
        logger.info(f"SESMT não obrigatório para {num_employees} empregados (GR {grau_risco}).")
        return result

    base_roles: Dict[str, str] = {}
    found_range = False

    for (min_emp, max_emp), roles in SESMT_DIMENSIONING_TABLE[grau_risco].items():
        if min_emp <= num_employees <= max_emp:
            base_roles = roles.copy()
            found_range = True
            break
    
    if not found_range and num_employees > 5000:
        base_roles = SESMT_DIMENSIONING_TABLE[grau_risco][(3501, 5000)].copy()
        
        excess_employees = num_employees - 5000
        num_additional_groups = 0
        
        if excess_employees > 0:
            num_additional_groups = ((excess_employees - 1) // 4000) + 1
        
        logger.info(f"Empregados acima de 5000: {excess_employees}, Grupos adicionais: {num_additional_groups}")
        
        if num_additional_groups > 0:
            for role_key in PROFESSIONAL_COLUMN_MAP.values():
                original_base_qty_str = str(base_roles.get(role_key, '0'))
                additional_qty_str = str(SESMT_ABOVE_5000_RULE_ADDITIONAL[grau_risco].get(role_key, '0'))

                base_val = int(original_base_qty_str.replace('*', '').replace('***', ''))
                add_val = int(additional_qty_str.replace('*', '').replace('***', ''))

                current_num_full_time = 0
                current_num_part_time_star = 0
                current_num_part_time_triple_star = 0

                if '*' not in original_base_qty_str and '***' not in original_base_qty_str:
                    current_num_full_time += base_val
                elif '***' in original_base_qty_str:
                    current_num_part_time_triple_star += base_val
                elif '*' in original_base_qty_str:
                    current_num_part_time_star += base_val

                if '*' not in additional_qty_str and '***' not in additional_qty_str:
                    current_num_full_time += add_val * num_additional_groups
                elif '***' in additional_qty_str:
                    current_num_part_time_triple_star += add_val * num_additional_groups
                elif '*' in additional_qty_str:
                    current_num_part_time_star += add_val * num_additional_groups

                # Construção da string de quantidade (qty)
                qty_parts_display = []
                if current_num_full_time > 0:
                    qty_parts_display.append(str(current_num_full_time))
                if current_num_part_time_star > 0:
                    qty_parts_display.append(f"{current_num_part_time_star}*")
                if current_num_part_time_triple_star > 0:
                    qty_parts_display.append(f"{current_num_part_time_triple_star}***")
                
                final_qty_str = " + ".join(qty_parts_display)
                if not final_qty_str: # Caso todos sejam 0
                    final_qty_str = '0'
                
                # Construção da observação específica
                specific_observation = None
                obs_details_parts = []
                if current_num_full_time > 0:
                    obs_details_parts.append(f"{current_num_full_time} profissional(is) em tempo integral")
                if current_num_part_time_star > 0:
                    obs_details_parts.append(f"{current_num_part_time_star} profissional(is) em tempo parcial (mín. 15h semanais)")
                if current_num_part_time_triple_star > 0:
                    obs_details_parts.append(f"{current_num_part_time_triple_star} profissional(is) com opção de substituição (tempo parcial)")
                
                if obs_details_parts: # Se há alguma observação a ser feita
                    specific_observation = "Inclui " + ", ".join(obs_details_parts) + "."
                
                # Adiciona a observação específica para Auxiliar/Técnico de Enfermagem do Trabalho se houver ***
                if current_num_part_time_triple_star > 0 and role_key == 'aux_tec_enfermagem':
                    aux_obs_text = "O empregador pode optar pela contratação de um Enfermeiro do Trabalho em tempo parcial (mín. 15h semanais), em substituição ao auxiliar ou técnico de enfermagem do trabalho."
                    if specific_observation and aux_obs_text not in specific_observation:
                        specific_observation += " " + aux_obs_text
                    elif not specific_observation:
                        specific_observation = aux_obs_text

                base_roles[role_key] = final_qty_str
                result[role_key]['specific_observation'] = specific_observation
        
        result['general_observations'].append(
            "Para o dimensionamento acima de 5.000 empregados, a NR-04 estabelece que o cálculo é feito "
            "com base na faixa de 3.501 a 5.000, acrescido de profissionais para cada grupo de 4.000 "
            "ou fração acima de 2.000. Esta ferramenta interpreta células vazias na coluna 'Acima de 5.000' "
            "como '0' profissionais adicionais para aquele grupo. Consulte a NR-04 na íntegra para interpretações específicas."
        )

    for role_key, qty_str in base_roles.items():
        # Se a lógica acima já definiu a observação, não sobrescreve
        if result[role_key]['specific_observation'] is None:
            if '***' in qty_str and role_key == 'aux_tec_enfermagem':
                result[role_key]['specific_observation'] = "O empregador pode optar pela contratação de um Enfermeiro do Trabalho em tempo parcial (mín. 15h semanais), em substituição."
            elif '*' in qty_str and role_key in ['engenheiro_seguranca', 'enfermeiro', 'medico']:
                result[role_key]['specific_observation'] = "Tempo Parcial (mín. 15h semanais)."
        
        result[role_key]['qty'] = qty_str
    
    result['general_observations'].append("Observação: Hospitais, ambulatórios, maternidades, casas de saúde e repouso, clínicas e estabelecimentos similares deverão contratar um Enfermeiro do Trabalho em tempo integral (30h semanais) quando possuírem mais de quinhentos trabalhadores.")
    result['general_observations'].append("Observação: Em virtude das características das atribuições do SESMT, não se faz necessária a supervisão do técnico de enfermagem do trabalho por enfermeiro do trabalho, salvo quando a atividade for executada em hospitais, ambulatórios, maternidades, casas de saúde e repouso, clínicas e estabelecimentos similares.")

    logger.info(f"Dimensionamento final para GR {grau_risco}, {num_employees} empregados: {result}")
    return result