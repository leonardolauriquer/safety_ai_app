# src/safety_ai_app/quiz_data_processor.py

import pandas as pd
import random
import logging
from typing import List, Dict, Any
import os
import hashlib # Para gerar IDs únicos de forma mais robusta
import json # CORREÇÃO: Importação do módulo json

# Importa a função de download do Google Drive Integrator
# Certifique-se de que o seu google_drive_integrator.py tenha a função download_file_by_path e get_drive_service
try:
    from safety_ai_app.google_drive_integrator import download_file_by_path
except ImportError:
    logging.error("Não foi possível importar 'download_file_by_path' de google_drive_integrator.py. Verifique o arquivo.")
    # Fallback mock para desenvolvimento local sem Drive, REMOVA EM PRODUÇÃO
    def download_file_by_path(drive_path: str, local_save_path: str) -> bool:
        logging.warning("Usando mock para download de arquivo do Google Drive. Substitua pela implementação real.")
        # Cria um arquivo Excel dummy para simular o download
        dummy_data = {
            "Dificuldade": ["easy", "medium", "hard", "expert", "easy", "medium", "hard", "expert", "easy", "medium", "hard", "expert", "easy", "medium"],
            "Tema": ["NRs", "Primeiros socorros", "Combate ao incêndio", "Saúde mental no trabalho", "EPIs", "Dia a dia da segurança do trabalho", "ISO de segurança do trabalho", "NBRs de segurança do trabalho", "NRs", "Primeiros socorros", "Combate ao incêndio", "Saúde mental no trabalho", "EPIs", "Dia a dia da segurança do trabalho"],
            "Pergunta": [
                "Qual NR trata de espaços confinados?",
                "Qual a primeira ação para uma parada cardíaca?",
                "Qual extintor para metais combustíveis?",
                "Qual o termo para esgotamento profissional?",
                "Qual EPI protege a cabeça?",
                "O que é um DDS?",
                "Qual ISO para gestão de SSO?",
                "Qual NBR para cores de segurança?",
                "Qual NR para trabalho em altura?",
                "Em caso de queimadura, o que fazer?",
                "Qual classe de incêndio para líquidos inflamáveis?",
                "O que é Burnout?",
                "Qual EPI para proteção auditiva?",
                "O que é CIPA?"
            ],
            "Opção A": ["NR-10", "Chamar ajuda", "Água", "Depressão", "Óculos", "Reunião mensal", "ISO 9001", "NBR 5410", "NR-18", "Aplicar pomada", "Classe A", "Estresse", "Capacete", "Comissão de Ética"],
            "Opção B": ["NR-12", "RCP", "CO2", "Ansiedade", "Capacete", "Encontro diário", "ISO 14001", "NBR 7198", "NR-33", "Perfurar bolhas", "Classe B", "Ansiedade", "Protetor auricular", "Comissão Interna de Prevenção de Acidentes"],
            "Opção C": ["NR-33", "Oferecer água", "Pó químico especial", "Burnout", "Luvas", "Documento formal", "ISO 45001", "NBR 7500", "NR-35", "Resfriar com água", "Classe C", "Depressão", "Luvas", "Comissão de Qualidade"],
            "Opção D": ["NR-35", "Esperar", "Espuma", "Estresse", "Botas", "Treinamento longo", "ISO 27001", "NBR 14725", "NR-10", "Cobrir com algodão", "Classe D", "Transtorno", "Óculos", "Comissão de Eventos"],
            "Resposta correta": ["NR-33", "RCP", "Pó químico especial", "Burnout", "Capacete", "Encontro diário", "ISO 45001", "NBR 7500", "NR-35", "Resfriar com água", "Classe B", "Burnout", "Protetor auricular", "Comissão Interna de Prevenção de Acidentes"],
            "Explicação": [
                "A NR-33 estabelece requisitos para espaços confinados.",
                "A Reanimação Cardiopulmonar (RCP) é a primeira medida.",
                "Extintores de pó químico especial são para Classe D (metais).",
                "Síndrome de Burnout é o esgotamento profissional.",
                "O capacete de segurança protege a cabeça contra impactos.",
                "DDS é um Diálogo Diário de Segurança.",
                "A ISO 45001 trata de Sistemas de Gestão de Saúde e Segurança Ocupacional.",
                "A NBR 7500 trata da identificação de cores para segurança.",
                "A NR-35 trata de segurança no trabalho em altura.",
                "Em queimaduras, resfriar com água corrente é a primeira medida.",
                "Incêndios de Classe B envolvem líquidos inflamáveis.",
                "Burnout é caracterizado por exaustão física e mental.",
                "Protetor auricular é essencial para proteção auditiva.",
                "CIPA é a Comissão Interna de Prevenção de Acidentes."
            ]
        }
        pd.DataFrame(dummy_data).to_excel(local_save_path, index=False)
        return True
    
logger = logging.getLogger(__name__)

# Define o caminho no Google Drive para a planilha de perguntas
GOOGLE_DRIVE_QUIZ_PATH = "SafetyAI - Conhecimento Base/Jogos/Perguntas.xlsx"
# Define um caminho temporário local para salvar a planilha baixada
LOCAL_QUIZ_TEMP_PATH = "temp_docs_local/Perguntas.xlsx"

# Degraus de pontuação para atribuir 'value' às perguntas
# Usaremos isso para garantir que perguntas de maior dificuldade tenham valores mais altos
SCORE_STEPS_FOR_VALUE_ASSIGNMENT = [1000, 2000, 3000, 5000, 10000, 20000, 30000, 50000, 100000, 200000, 300000, 500000, 750000, 1000000]

# Mapeamento de dificuldade para um "peso" que ajuda a atribuir valores mais altos
DIFFICULTY_WEIGHTS = {
    "easy": 0,
    "medium": 1,
    "hard": 2,
    "expert": 3
}

def generate_question_id(question_data: Dict[str, Any]) -> str:
    """
    Gera um ID único para uma pergunta baseado em seu conteúdo.
    Usa um hash MD5 para garantir unicidade e consistência.
    """
    content_str = json.dumps({
        "question": question_data.get("Pergunta", ""),
        "option_a": question_data.get("Opção A", ""),
        "option_b": question_data.get("Opção B", ""),
        "option_c": question_data.get("Opção C", ""),
        "option_d": question_data.get("Opção D", ""),
        "answer": question_data.get("Resposta correta", ""), # Aqui ainda é a letra
        "difficulty": question_data.get("Dificuldade", ""),
        "theme": question_data.get("Tema", "")
    }, sort_keys=True)
    return hashlib.md5(content_str.encode('utf-8')).hexdigest()

def assign_question_value(difficulty: str) -> int:
    """
    Atribui um 'value' à pergunta com base na sua dificuldade.
    Tenta distribuir os valores dentro de faixas para cada dificuldade.
    """
    difficulty_lower = difficulty.lower()
    
    if difficulty_lower == "easy":
        return random.choice(SCORE_STEPS_FOR_VALUE_ASSIGNMENT[0:4]) # 1k, 2k, 3k, 5k
    elif difficulty_lower == "medium":
        return random.choice(SCORE_STEPS_FOR_VALUE_ASSIGNMENT[4:7]) # 10k, 20k, 30k
    elif difficulty_lower == "hard":
        return random.choice(SCORE_STEPS_FOR_VALUE_ASSIGNMENT[7:10]) # 50k, 100k, 200k
    elif difficulty_lower == "expert":
        return random.choice(SCORE_STEPS_FOR_VALUE_ASSIGNMENT[10:]) # 300k, 500k, 750k, 1M
    return 1000 # Valor padrão para dificuldade desconhecida

def generate_audience_distribution(options: List[str], correct_answer: str) -> Dict[str, int]:
    """
    Gera uma distribuição de votos da audiência plausível para as opções.
    A resposta correta tende a ter a maior porcentagem.
    """
    distribution = {option: 0 for option in options}
    
    if correct_answer not in options:
        logger.warning(f"Resposta correta '{correct_answer}' não encontrada nas opções: {options}. Distribuindo igualmente.")
        if options: # Evita divisão por zero se não houver opções
            for opt in options:
                distribution[opt] = int(100 / len(options))
            distribution[options[-1]] += (100 - sum(distribution.values())) # Ajusta para somar 100
        return distribution

    # Porcentagem base para a resposta correta
    correct_percentage = random.randint(60, 90) # 60-90% para a resposta correta
    distribution[correct_answer] = correct_percentage
    
    remaining_percentage = 100 - correct_percentage
    incorrect_options = [opt for opt in options if opt != correct_answer]
    
    if not incorrect_options:
        return distribution

    # Distribui a porcentagem restante entre as opções incorretas
    # Tenta dar uma fatia maior para uma das incorretas para simular distratores mais fortes
    if len(incorrect_options) > 1:
        random.shuffle(incorrect_options) # Embaralha para variar qual incorreta recebe mais
        
        # A primeira opção incorreta recebe uma fatia maior do restante
        main_incorrect_share = random.randint(int(remaining_percentage * 0.3), int(remaining_percentage * 0.7))
        distribution[incorrect_options[0]] = main_incorrect_share
        
        remaining_for_others = remaining_percentage - main_incorrect_share
        
        # Distribui o que sobrou entre as demais incorretas
        for i in range(1, len(incorrect_options)):
            opt = incorrect_options[i]
            if i == len(incorrect_options) - 1: # A última recebe o restante
                distribution[opt] = remaining_for_others
            else:
                share = random.randint(0, remaining_for_others)
                distribution[opt] = share
                remaining_for_others -= share
    elif incorrect_options: # Se houver apenas uma opção incorreta
        distribution[incorrect_options[0]] = remaining_percentage

    # Ajusta para garantir que a soma seja exatamente 100% devido a arredondamentos
    current_sum = sum(distribution.values())
    if current_sum != 100:
        diff = 100 - current_sum
        # Adiciona/subtrai a diferença da resposta correta ou de uma opção aleatória
        if correct_answer in distribution:
            distribution[correct_answer] += diff
        elif options: # Fallback se a resposta correta não estiver na distribuição (erro anterior)
            distribution[random.choice(options)] += diff

    # Garante que nenhuma opção tenha porcentagem negativa
    for k in distribution:
        if distribution[k] < 0:
            distribution[k] = 0
    
    # Re-normaliza se houver negativos para garantir 100% e não negativos
    final_sum = sum(distribution.values())
    if final_sum != 100 and final_sum > 0:
        for k in distribution:
            distribution[k] = int(distribution[k] * 100 / final_sum)
        if options:
            distribution[options[-1]] += (100 - sum(distribution.values()))

    return distribution


def process_quiz_excel_to_json(file_path: str) -> List[Dict[str, Any]]:
    """
    Lê um arquivo Excel, processa seu conteúdo e o converte para o formato
    esperado pelo quiz_game.py (lista de dicionários).
    """
    try:
        df = pd.read_excel(file_path)
        
        # Limpa nomes das colunas (remove espaços extras) e renomeia para chaves internas
        df.columns = [col.strip() for col in df.columns]
        expected_cols = {
            "Dificuldade": "difficulty_level",
            "Tema": "theme",
            "Pergunta": "question",
            "Opção A": "option_a",
            "Opção B": "option_b",
            "Opção C": "option_c",
            "Opção D": "option_d",
            "Resposta correta": "answer_label", # Renomeado para evitar conflito
            "Explicação": "explanation"
        }
        df = df.rename(columns=expected_cols)

        questions_list = []
        for index, row in df.iterrows():
            # Validação básica para garantir dados essenciais
            if pd.isna(row["question"]) or pd.isna(row["answer_label"]) or pd.isna(row["difficulty_level"]):
                logger.warning(f"Pulando linha {index} devido a dados essenciais ausentes: {row.to_dict()}")
                continue

            # Mapeia as opções para seus textos
            options_map = {
                "A": str(row["option_a"]) if pd.notna(row["option_a"]) else "",
                "B": str(row["option_b"]) if pd.notna(row["option_b"]) else "",
                "C": str(row["option_c"]) if pd.notna(row["option_c"]) else "",
                "D": str(row["option_d"]) if pd.notna(row["option_d"]) else ""
            }
            
            # Obtém o texto da resposta correta usando a letra (A, B, C, D)
            correct_answer_label = str(row["answer_label"]).strip().upper()
            actual_correct_answer_text = options_map.get(correct_answer_label, "")

            # Lista de opções de texto válidas (removendo vazias)
            options = [options_map["A"], options_map["B"], options_map["C"], options_map["D"]]
            options = [opt for opt in options if opt] # Remove opções vazias

            # Validação: A resposta correta (texto) deve estar entre as opções válidas
            if not options or actual_correct_answer_text == "" or actual_correct_answer_text not in options:
                logger.warning(f"Pulando linha {index} devido a opções inválidas ou resposta correta não encontrada nas opções: {row.to_dict()}")
                continue

            question_data = {
                "id": generate_question_id(row),
                "question": str(row["question"]),
                "options": options,
                "answer": actual_correct_answer_text, # Agora armazena o TEXTO da resposta correta
                "explanation": str(row["explanation"]) if pd.notna(row["explanation"]) else "Nenhuma explicação fornecida.",
                "value": assign_question_value(str(row["difficulty_level"])),
                "audience_distribution": generate_audience_distribution(options, actual_correct_answer_text),
                "difficulty_level": str(row["difficulty_level"]).lower(),
                "theme": str(row["theme"]).lower() if pd.notna(row["theme"]) else "general"
            }
            questions_list.append(question_data)
        
        logger.info(f"Processadas {len(questions_list)} perguntas do Excel com sucesso.")
        return questions_list
    except FileNotFoundError:
        logger.error(f"Arquivo Excel não encontrado em {file_path}")
        return []
    except Exception as e:
        logger.error(f"Erro ao processar arquivo Excel {file_path}: {e}", exc_info=True)
        return []

def get_quiz_questions_from_drive() -> List[Dict[str, Any]]:
    """
    Baixa o arquivo Excel de perguntas do Google Drive e o processa.
    """
    # Garante que o diretório temporário exista
    os.makedirs(os.path.dirname(LOCAL_QUIZ_TEMP_PATH), exist_ok=True)

    try:
        # Tenta baixar o arquivo do Google Drive
        success = download_file_by_path(GOOGLE_DRIVE_QUIZ_PATH, LOCAL_QUIZ_TEMP_PATH)
        
        if not success:
            logger.error(f"Falha ao baixar perguntas do quiz do Google Drive: {GOOGLE_DRIVE_QUIZ_PATH}")
            return []

        questions = process_quiz_excel_to_json(LOCAL_QUIZ_TEMP_PATH)
        return questions
    except Exception as e:
        logger.error(f"Erro ao obter perguntas do quiz do Drive: {e}", exc_info=True)
        return []