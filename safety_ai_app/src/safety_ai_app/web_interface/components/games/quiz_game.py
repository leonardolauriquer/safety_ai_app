# src/safety_ai_app/web_interface/components/games/quiz_game.py

import streamlit as st
import json
import os
import random
import logging
import time
from typing import List, Dict, Any, Optional

# Importa o novo processador de dados
from safety_ai_app.quiz_data_processor import get_quiz_questions_from_drive

# Importa a biblioteca para auto-refresh
from streamlit_autorefresh import st_autorefresh # <--- NOVA IMPORTAÇÃO

# Configuração do logger para facilitar a depuração
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO) # Define o nível de log

# Importa o tema para ícones e frases
try:
    from safety_ai_app.theme_config import _get_material_icon_html, _get_material_icon_html_for_button_css, THEME
except ImportError:
    # Fallback caso o tema não possa ser carregado, para evitar quebra total
    st.error("Erro ao carregar configurações de tema. Verifique 'theme_config.py'.")
    _get_material_icon_html = lambda icon: f"<span>{icon}</span>"
    _get_material_icon_html_for_button_css = lambda btn_key, icon_key: ""
    THEME = {"phrases": {}, "icons": {}, "colors": {"accent_green": "#4CAF50", "error_border": "#F44336", "background_primary": "#FFFFFF", "accent_green_shadow": "rgba(76, 175, 80, 0.5)"}}

# Degraus de pontuação do Show do Milhão
SCORE_STEPS = [0, 1000, 2000, 3000, 5000, 10000, 20000, 30000, 50000, 100000, 200000, 300000, 500000, 750000, 1000000]

# Tempo limite fixo para todas as perguntas
DEFAULT_TIME_LIMIT = 60
# TIME_LIMITS = [DEFAULT_TIME_LIMIT] * (len(SCORE_STEPS) - 1) # Garante que todas as 14 perguntas tenham 60 segundos - não usado diretamente

# Opções de Ligas (Níveis de Dificuldade)
LEAGUES = {
    "iniciante": "Liga Iniciante",
    "bronze": "Liga Bronze",
    "prata": "Liga Prata",
    "ouro": "Liga Ouro",
    "platina": "Liga Platina",
    "diamante": "Liga Diamante",
    "safety_ai": "Liga Safety AI", # Nome da liga final
}

# Contagem de Lifelines e Dificuldades Permitidas por Liga
# Define quantas vezes cada lifeline pode ser usada e quais dificuldades de pergunta são aceitáveis
LIFELINE_CONFIG_BY_LEAGUE = {
    "iniciante": {"50_50": 7, "audience": 7, "cards": 7, "skip": 7, "allowed_difficulties": ["easy", "medium"]},
    "bronze":    {"50_50": 6, "audience": 6, "cards": 6, "skip": 6, "allowed_difficulties": ["easy", "medium"]},
    "prata":     {"50_50": 5, "audience": 5, "cards": 5, "skip": 5, "allowed_difficulties": ["easy", "medium", "hard"]},
    "ouro":      {"50_50": 4, "audience": 4, "cards": 4, "skip": 4, "allowed_difficulties": ["medium", "hard"]},
    "platina":   {"50_50": 3, "audience": 3, "cards": 3, "skip": 3, "allowed_difficulties": ["hard"]},
    "diamante":  {"50_50": 2, "audience": 2, "cards": 2, "skip": 2, "allowed_difficulties": ["hard", "expert"]},
    "safety_ai": {"50_50": 1, "audience": 1, "cards": 1, "skip": 1, "allowed_difficulties": ["expert"]},
}

# Distribuição de dificuldades por liga (total de 14 perguntas para cada liga)
# Garante uma progressão de dificuldade controlada para cada liga
QUIZ_DIFFICULTY_DISTRIBUTION_BY_LEAGUE = {
    "iniciante": {"easy": 10, "medium": 4, "hard": 0, "expert": 0}, # Mais fácil
    "bronze":    {"easy": 4, "medium": 10, "hard": 0, "expert": 0},
    "prata":     {"easy": 2, "medium": 10, "hard": 2, "expert": 0},
    "ouro":      {"easy": 0, "medium": 8, "hard": 6, "expert": 0},
    "platina":   {"easy": 0, "medium": 0, "hard": 14, "expert": 0}, # Apenas perguntas difíceis
    "diamante":  {"easy": 0, "medium": 0, "hard": 10, "expert": 4},
    "safety_ai": {"easy": 0, "medium": 0, "hard": 0, "expert": 14}, # Apenas perguntas expert
}

# Ordem de dificuldade para facilitar a busca e ordenação (não usado diretamente na seleção, mas útil para lógica)
DIFFICULTY_ORDER = {"easy": 1, "medium": 2, "hard": 3, "expert": 4}

def load_all_quiz_questions() -> List[Dict[str, Any]]:
    """
    Carrega TODAS as perguntas do quiz, agora do Google Drive via quiz_data_processor.
    """
    questions = get_quiz_questions_from_drive()
    if not questions:
        st.error("Não foi possível carregar as perguntas do quiz. Verifique a integração com o Google Drive e o arquivo 'Perguntas.xlsx'.")
        logger.error("load_all_quiz_questions: Nenhuma pergunta carregada do Drive.")
    else:
        logger.info(f"load_all_quiz_questions: {len(questions)} perguntas carregadas do Drive.")
    return questions

def initialize_quiz_state() -> None:
    """Inicializa o estado da sessão para o quiz."""
    # Inicializa todas as flags e variáveis básicas primeiro para evitar AttributeError
    if "quiz_started" not in st.session_state:
        st.session_state.quiz_started = False
    if "quiz_finished" not in st.session_state:
        st.session_state.quiz_finished = False
    if "current_question_index" not in st.session_state:
        st.session_state.current_question_index = 0
    if "quiz_score_index" not in st.session_state:
        st.session_state.quiz_score_index = 0
    if "selected_option" not in st.session_state:
        st.session_state.selected_option = None
    if "feedback_message" not in st.session_state:
        st.session_state.feedback_message = ""
    if "show_explanation" not in st.session_state:
        st.session_state.show_explanation = False
    if "available_options" not in st.session_state:
        st.session_state.available_options = [] # Usado para 50/50
    if "show_audience_help" not in st.session_state:
        st.session_state.show_audience_help = False
    if "question_start_time" not in st.session_state:
        st.session_state.question_start_time = time.time()
    if "current_time_limit" not in st.session_state:
        st.session_state.current_time_limit = DEFAULT_TIME_LIMIT
    if "current_league" not in st.session_state:
        st.session_state.current_league = "iniciante" # Liga padrão

    # Carrega todas as perguntas uma única vez
    if "all_quiz_questions" not in st.session_state:
        st.session_state.all_quiz_questions = load_all_quiz_questions()
        
    # Inicializa contagens de lifelines baseadas na liga atual (que agora é garantido que existe)
    league_key = st.session_state.current_league
    if "lifelines_50_50" not in st.session_state:
        st.session_state.lifelines_50_50 = LIFELINE_CONFIG_BY_LEAGUE[league_key]["50_50"]
    if "lifelines_audience" not in st.session_state:
        st.session_state.lifelines_audience = LIFELINE_CONFIG_BY_LEAGUE[league_key]["audience"]
    if "lifelines_skip_count" not in st.session_state:
        st.session_state.lifelines_skip_count = LIFELINE_CONFIG_BY_LEAGUE[league_key]["skip"]
    if "lifelines_cards_count" not in st.session_state:
        st.session_state.lifelines_cards_count = LIFELINE_CONFIG_BY_LEAGUE[league_key]["cards"]

    # Garante que quiz_questions_for_game exista, mesmo que vazio no início
    if "quiz_questions_for_game" not in st.session_state:
        st.session_state.quiz_questions_for_game = [] 
    if "quiz_total_questions" not in st.session_state:
        st.session_state.quiz_total_questions = len(SCORE_STEPS) - 1 # Sempre 14 perguntas

def reset_quiz() -> None:
    """Reseta o estado do quiz para iniciar um novo jogo com perguntas selecionadas por liga e dificuldade."""
    all_questions_pool = st.session_state.all_quiz_questions
    
    if not all_questions_pool:
        st.error("Não há perguntas carregadas para iniciar o quiz. Verifique o arquivo de perguntas.")
        st.session_state.quiz_started = False
        return

    league_key = st.session_state.current_league
    league_config = LIFELINE_CONFIG_BY_LEAGUE[league_key]
    allowed_difficulties = league_config["allowed_difficulties"]
    difficulty_distribution = QUIZ_DIFFICULTY_DISTRIBUTION_BY_LEAGUE[league_key]

    # 1. Filtra o pool de perguntas pelas dificuldades permitidas na liga
    filtered_questions = [q for q in all_questions_pool if q.get("difficulty_level") in allowed_difficulties]
    
    if not filtered_questions:
        st.error(f"Não há perguntas disponíveis para a liga '{league_key}' com as dificuldades permitidas: {allowed_difficulties}. Por favor, adicione mais perguntas ou ajuste as configurações de dificuldade.")
        st.session_state.quiz_started = False
        return

    # 2. Agrupa as perguntas filtradas por dificuldade
    grouped_filtered_questions = {
        "easy": [q for q in filtered_questions if q.get("difficulty_level") == "easy"],
        "medium": [q for q in filtered_questions if q.get("difficulty_level") == "medium"],
        "hard": [q for q in filtered_questions if q.get("difficulty_level") == "hard"],
        "expert": [q for q in filtered_questions if q.get("difficulty_level") == "expert"],
    }

    selected_questions_for_game = []
    
    # 3. Seleciona o número exato de perguntas para cada dificuldade conforme a distribuição da liga
    for difficulty_level, count_needed in difficulty_distribution.items():
        if count_needed > 0:
            available_q_of_difficulty = grouped_filtered_questions.get(difficulty_level, [])
            random.shuffle(available_q_of_difficulty) # Embaralha para pegar aleatoriamente
            
            if len(available_q_of_difficulty) < count_needed:
                logger.warning(f"Não há perguntas suficientes de dificuldade '{difficulty_level}' para a liga '{league_key}'. Necessário: {count_needed}, Disponível: {len(available_q_of_difficulty)}. Perguntas podem ser repetidas ou de outras dificuldades.")
                # Pega todas as disponíveis e preenche o restante com repetições do mesmo pool
                selected_questions_for_game.extend(available_q_of_difficulty)
                remaining_to_add = count_needed - len(available_q_of_difficulty)
                if available_q_of_difficulty and remaining_to_add > 0:
                    selected_questions_for_game.extend(random.choices(available_q_of_difficulty, k=remaining_to_add))
            else:
                # Usa random.sample para garantir unicidade se houver perguntas suficientes
                selected_questions_for_game.extend(random.sample(available_q_of_difficulty, count_needed))

    # 4. Fallback: Garante que sempre teremos 14 perguntas.
    # Se, por algum motivo, a seleção acima não resultou em 14 perguntas, preenche com perguntas aleatórias do pool filtrado.
    while len(selected_questions_for_game) < len(SCORE_STEPS) - 1:
        if filtered_questions:
            # Tenta adicionar uma pergunta que ainda não esteja na lista, se possível
            potential_q = random.choice(filtered_questions)
            # Check if question (by ID) is already in selected_questions_for_game
            if potential_q['id'] not in [q['id'] for q in selected_questions_for_game]:
                selected_questions_for_game.append(potential_q)
            else: # If already in list, add a random one (allowing repetition if pool is small)
                selected_questions_for_game.append(random.choice(filtered_questions))
        else:
            st.error("Erro: Não há perguntas disponíveis para o quiz! Verifique o pool de perguntas.")
            st.session_state.quiz_started = False
            return

    # Se por algum motivo selecionou mais de 14 (não deveria acontecer com a lógica acima, mas como segurança)
    selected_questions_for_game = selected_questions_for_game[:len(SCORE_STEPS) - 1]
            
    # 5. Ordena as perguntas selecionadas pelo valor para garantir a progressão de pontuação
    selected_questions_for_game.sort(key=lambda q: q.get("value", 0))

    st.session_state.quiz_questions_for_game = selected_questions_for_game
    st.session_state.current_question_index = 0
    st.session_state.quiz_score_index = 0
    st.session_state.quiz_started = True
    st.session_state.quiz_finished = False
    st.session_state.selected_option = None
    st.session_state.feedback_message = ""
    st.session_state.show_explanation = False
    st.session_state.quiz_total_questions = len(st.session_state.quiz_questions_for_game)
    st.session_state.available_options = []
    
    # Reinicializa contagens de lifelines baseadas na liga atual
    st.session_state.lifelines_50_50 = LIFELINE_CONFIG_BY_LEAGUE[league_key]["50_50"]
    st.session_state.lifelines_audience = LIFELINE_CONFIG_BY_LEAGUE[league_key]["audience"]
    st.session_state.lifelines_skip_count = LIFELINE_CONFIG_BY_LEAGUE[league_key]["skip"]
    st.session_state.lifelines_cards_count = LIFELINE_CONFIG_BY_LEAGUE[league_key]["cards"]

    st.session_state.show_audience_help = False
    st.session_state.question_start_time = time.time() # Reinicia o timer
    st.session_state.current_time_limit = DEFAULT_TIME_LIMIT
    logger.info("Quiz resetado e iniciado com perguntas selecionadas por dificuldade e liga.")

def check_answer(question: Dict[str, Any], selected_option: str) -> None:
    """Verifica a resposta selecionada e atualiza o score e feedback."""
    st.session_state.selected_option = selected_option
    if selected_option == question["answer"]:
        st.session_state.quiz_score_index = min(st.session_state.quiz_score_index + 1, len(SCORE_STEPS) - 1)
        st.session_state.feedback_message = "Resposta Correta!"
    else:
        st.session_state.feedback_message = "Resposta Incorreta!"
        st.session_state.quiz_finished = True # Fim de jogo se errar
    st.session_state.show_explanation = True
    st.session_state.show_audience_help = False # Esconde ajuda do público após resposta
    logger.info(f"Resposta verificada. Correta: {selected_option == question['answer']}. Score atual: {SCORE_STEPS[st.session_state.quiz_score_index]}")

def next_question() -> None:
    """Avança para a próxima pergunta ou finaliza o quiz."""
    st.session_state.current_question_index += 1
    st.session_state.selected_option = None
    st.session_state.feedback_message = ""
    st.session_state.show_explanation = False
    st.session_state.available_options = []
    st.session_state.show_audience_help = False
    st.session_state.question_start_time = time.time()
    st.session_state.current_time_limit = DEFAULT_TIME_LIMIT

    if st.session_state.current_question_index >= st.session_state.quiz_total_questions:
        st.session_state.quiz_finished = True
        logger.info("Quiz finalizado.")
    else:
        logger.info(f"Avançando para a pergunta {st.session_state.current_question_index + 1}/{st.session_state.quiz_total_questions}")

def use_50_50(question: Dict[str, Any]) -> None:
    """Remove duas opções incorretas."""
    if st.session_state.lifelines_50_50 > 0:
        incorrect_options = [opt for opt in question["options"] if opt != question["answer"]]
        
        if len(incorrect_options) >= 2:
            options_to_remove = random.sample(incorrect_options, 2)
        elif len(incorrect_options) == 1:
            options_to_remove = incorrect_options
        else:
            options_to_remove = []

        st.session_state.available_options = [opt for opt in question["options"] if opt not in options_to_remove]
        st.session_state.lifelines_50_50 -= 1
        st.success(f"{THEME['phrases'].get('quiz_help_50_50')} utilizada! Duas opções incorretas foram removidas.")
        logger.info("Ajuda 50/50 utilizada.")
    else:
        st.warning(f"{THEME['phrases'].get('quiz_help_50_50')} já utilizada ou sem usos restantes.")

def use_audience_help(question: Dict[str, Any]) -> None:
    """Mostra a distribuição de votos da audiência."""
    if st.session_state.lifelines_audience > 0:
        st.session_state.show_audience_help = True
        st.session_state.lifelines_audience -= 1
        st.success(f"{THEME['phrases'].get('quiz_help_audience')} utilizada! Veja a opinião dos universitários.")
        logger.info("Ajuda Universitários utilizada.")
    else:
        st.warning(f"{THEME['phrases'].get('quiz_help_audience')} já utilizada ou sem usos restantes.")

def use_skip_question() -> None:
    """Pula a pergunta atual sem perder pontos."""
    if st.session_state.lifelines_skip_count > 0:
        st.session_state.lifelines_skip_count -= 1
        st.success(f"{THEME['phrases'].get('quiz_help_skip')} utilizada! Pulando para a próxima pergunta. ({st.session_state.lifelines_skip_count} restantes)")
        next_question()
        logger.info(f"Ajuda Pular utilizada. {st.session_state.lifelines_skip_count} restantes.")
    else:
        st.warning(f"{THEME['phrases'].get('quiz_help_skip')} já utilizada ou sem usos restantes.")

def use_cards_help() -> None:
    """Troca a pergunta atual por uma nova pergunta aleatória."""
    if st.session_state.lifelines_cards_count > 0:
        st.session_state.lifelines_cards_count -= 1
        
        current_question_id = st.session_state.quiz_questions_for_game[st.session_state.current_question_index]['id']
        
        league_config = LIFELINE_CONFIG_BY_LEAGUE[st.session_state.current_league]
        allowed_difficulties = league_config["allowed_difficulties"]
        
        # Filtra perguntas do pool geral que são permitidas pela liga e que não estão no jogo atual
        available_for_swap = [
            q for q in st.session_state.all_quiz_questions
            if q['id'] not in [qq['id'] for qq in st.session_state.quiz_questions_for_game] # Not in the current game's 14 questions
            and q.get("difficulty_level") in allowed_difficulties
        ]
        
        if available_for_swap:
            new_question = random.choice(available_for_swap)
            # Substitui a pergunta atual pela nova pergunta
            st.session_state.quiz_questions_for_game[st.session_state.current_question_index] = new_question
            
            st.session_state.selected_option = None
            st.session_state.feedback_message = ""
            st.session_state.show_explanation = False
            st.session_state.available_options = []
            st.session_state.show_audience_help = False
            st.session_state.question_start_time = time.time()
            st.session_state.current_time_limit = DEFAULT_TIME_LIMIT
            st.success(f"{THEME['phrases'].get('quiz_help_cards')} utilizada! A pergunta foi trocada. ({st.session_state.lifelines_cards_count} restantes)")
            logger.info(f"Ajuda Cartas utilizada. Pergunta trocada. {st.session_state.lifelines_cards_count} restantes.")
        else:
            st.warning("Não há perguntas suficientes para trocar.")
        st.rerun()
    else:
        st.warning(f"{THEME['phrases'].get('quiz_help_cards')} já utilizada ou sem usos restantes.")

def render_quiz_game() -> None:
    """Renderiza a interface do jogo de quiz."""
    initialize_quiz_state()

    quiz_icon = THEME['icons'].get('quiz_icon', 'quiz')
    quiz_title = THEME['phrases'].get('quiz_game', 'Quiz SST')
    currency_unit = THEME['phrases'].get('quiz_currency_unit', 'Pontos')

    st.markdown(f"<h1 class='neon-title'>{_get_material_icon_html(quiz_icon)} {quiz_title}</h1>", unsafe_allow_html=True)
    st.markdown("Teste seus conhecimentos em Saúde e Segurança do Trabalho! Responda às perguntas e tente chegar ao milhão!")


    if not st.session_state.quiz_started:
        # Seleção de Liga
        league_options = list(LEAGUES.values())
        selected_league_name = st.selectbox("Selecione sua Liga:", league_options, key="league_selector")
        
        # Encontra a chave da liga selecionada
        for key, value in LEAGUES.items():
            if value == selected_league_name:
                st.session_state.current_league = key
                break

        st.info(f"Clique em 'Iniciar Desafio' para começar o Show do Milhão na {LEAGUES[st.session_state.current_league]}!")
        st.markdown(_get_material_icon_html_for_button_css('start_quiz_btn', THEME['icons']['play_arrow']), unsafe_allow_html=True)
        if st.button(f"{THEME['phrases'].get('quiz_start_challenge', 'Iniciar Desafio')}", key="start_quiz_btn"):
            reset_quiz()
            st.rerun()
    elif st.session_state.quiz_finished:
        st.markdown(f"<div class='quiz-container'>", unsafe_allow_html=True) # Mantém este div para a tela final
        
        # Mensagem de "Perdeu" se o jogo não terminou com uma resposta correta
        if st.session_state.feedback_message != "Resposta Correta!":
            st.markdown(f"<h2>{_get_material_icon_html('error_x')} {THEME['phrases'].get('quiz_game_over_lose', 'Fim de Jogo! Você perdeu.')}</h2>", unsafe_allow_html=True)
        else:
            st.markdown(f"<h2>{_get_material_icon_html('trophy')} {THEME['phrases'].get('quiz_final_score', 'Pontuação Final:')}</h2>", unsafe_allow_html=True)
        
        st.markdown(f"<p style='font-size: 2em; color: {THEME['colors']['accent_green']}; font-weight: bold;'>{currency_unit} {SCORE_STEPS[st.session_state.quiz_score_index]:,.2f}</p>", unsafe_allow_html=True)
        st.markdown(f"<p>Você jogou na {LEAGUES[st.session_state.current_league]}.</p>", unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown(_get_material_icon_html_for_button_css('restart_quiz_btn', THEME['icons']['refresh']), unsafe_allow_html=True)
        if st.button(f"{THEME['phrases'].get('quiz_play_again', 'Jogar Novamente')}", key="restart_quiz_btn"):
            reset_quiz()
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True) # Fecha o div da tela final
    else:
        # Injeta CSS para estilizar o st.container que agrupa o conteúdo principal do quiz
        st.markdown(f"""
            <style>
                /* Target the stVerticalBlock that contains the quiz elements */
                /* This assumes the st.container() below is the first stVerticalBlock in this context
                   after the initial titles and separator. */
                div[data-testid="stVerticalBlock"]:has(p.quiz-question) {{
                    background-color: {THEME['colors']['background_secondary']};
                    border-radius: 15px;
                    padding: 30px;
                    box-shadow: 0 0 25px rgba(39, 174, 96, 0.5);
                    margin-top: 20px;
                    text-align: center;
                }}
            </style>
        """, unsafe_allow_html=True)

        # Usa um Streamlit container para agrupar todos os elementos do quiz
        with st.container(): # Não precisa de key se for o único st.container principal
            current_question = st.session_state.quiz_questions_for_game[st.session_state.current_question_index]
            
            # Lógica do Timer
            time_elapsed = time.time() - st.session_state.question_start_time
            time_remaining = int(st.session_state.current_time_limit - time_elapsed)

            # --- NOVO: Ativa o autorefresh para o timer ---
            # O timer será atualizado a cada 1000ms (1 segundo)
            # A key é importante para que o autorefresh seja redefinido quando a pergunta muda
            st_autorefresh(interval=1000, key=f"quiz_timer_refresh_{st.session_state.current_question_index}")

            if time_remaining <= 0 and not st.session_state.show_explanation:
                st.session_state.feedback_message = "Tempo esgotado!"
                st.session_state.quiz_finished = True
                st.session_state.show_explanation = True
                st.warning("Tempo esgotado! Você não respondeu a tempo.")
                st.rerun() # Força um rerun para exibir a mensagem de fim de jogo

            # Define as opções disponíveis (considerando 50/50)
            options_to_display = st.session_state.available_options if st.session_state.available_options else current_question["options"]
            
            # Formatação da linha de progresso/pontuação
            col_progress, col_league, col_score = st.columns([1, 1, 1])
            with col_progress:
                st.markdown(f"<span>{THEME['phrases'].get('quiz_question_of', 'Pergunta')} {st.session_state.current_question_index + 1} de {st.session_state.quiz_total_questions}</span>", unsafe_allow_html=True)
            with col_league:
                st.markdown(f"<span>Liga: {LEAGUES[st.session_state.current_league]}</span>", unsafe_allow_html=True)
            with col_score:
                st.markdown(f"<span>{THEME['phrases'].get('quiz_current_score', 'Pontuação Atual:')} <span style='color: {THEME['colors']['accent_green']}; font-weight: bold;'>{currency_unit} {SCORE_STEPS[st.session_state.quiz_score_index]:,.2f}</span></span>", unsafe_allow_html=True)
            
            st.markdown(f"<div class='quiz-progress-bar'><div class='quiz-progress-fill' style='width: {st.session_state.quiz_score_index / (len(SCORE_STEPS) - 1) * 100}%;'></div></div>", unsafe_allow_html=True)
            
            # Exibe o timer
            timer_placeholder = st.empty()
            timer_placeholder.markdown(f"<p class='quiz-timer'>{_get_material_icon_html('timer')} {time_remaining}s</p>", unsafe_allow_html=True)

            # Pergunta
            st.markdown(f"<p class='quiz-question'>{current_question['question']}</p>", unsafe_allow_html=True)

            # Lifelines
            col_50_50, col_audience, col_cards, col_skip = st.columns(4)
            with col_50_50:
                st.markdown(_get_material_icon_html_for_button_css('lifeline_50_50', THEME['icons']['help_50_50']), unsafe_allow_html=True)
                if st.button(f"{THEME['phrases'].get('quiz_help_50_50', '50:50')} ({st.session_state.lifelines_50_50})", key="lifeline_50_50", disabled=st.session_state.lifelines_50_50 <= 0 or st.session_state.show_explanation, use_container_width=True, help="Remove duas opções incorretas."):
                    use_50_50(current_question)
                    st.rerun()
            with col_audience:
                st.markdown(_get_material_icon_html_for_button_css('lifeline_audience', THEME['icons']['help_audience']), unsafe_allow_html=True)
                if st.button(f"{THEME['phrases'].get('quiz_help_audience', 'Universitários')} ({st.session_state.lifelines_audience})", key="lifeline_audience", disabled=st.session_state.lifelines_audience <= 0 or st.session_state.show_explanation, use_container_width=True, help="Mostra a porcentagem de votos do público para cada opção."):
                    use_audience_help(current_question)
            with col_cards:
                st.markdown(_get_material_icon_html_for_button_css('lifeline_cards', THEME['icons']['help_cards']), unsafe_allow_html=True)
                if st.button(f"{THEME['phrases'].get('quiz_help_cards', 'Cartas')} ({st.session_state.lifelines_cards_count})", key="lifeline_cards", disabled=st.session_state.lifelines_cards_count <= 0 or st.session_state.show_explanation, use_container_width=True, help="Troca a pergunta atual por uma nova pergunta aleatória."):
                    use_cards_help()
            with col_skip:
                st.markdown(_get_material_icon_html_for_button_css('lifeline_skip', THEME['icons']['help_skip']), unsafe_allow_html=True)
                if st.button(f"{THEME['phrases'].get('quiz_help_skip', 'Pular')} ({st.session_state.lifelines_skip_count})", key="lifeline_skip", disabled=st.session_state.lifelines_skip_count <= 0 or st.session_state.show_explanation, use_container_width=True, help="Pula a pergunta atual sem perder pontos."):
                    use_skip_question()
                    st.rerun()

            if st.session_state.show_audience_help:
                st.markdown(f"<div class='quiz-audience-chart'>"
                            f"<h4>{THEME['phrases'].get('quiz_audience_help_title', 'Ajuda dos Universitários:')}</h4>"
                            f"<p>{THEME['phrases'].get('quiz_audience_help_message', 'Os universitários votaram assim:')}</p>", unsafe_allow_html=True)
                
                audience_votes = current_question.get("audience_distribution", {})
                total_votes = sum(audience_votes.values())
                
                for option_char, option_text in zip(['A', 'B', 'C', 'D'], current_question["options"]):
                    if option_text in options_to_display:
                        votes = audience_votes.get(option_text, 0)
                        percentage = (votes / total_votes) * 100 if total_votes > 0 else 0
                        st.markdown(f"<div class='quiz-audience-bar-container'>"
                                    f"<span class='quiz-audience-bar-label'>{option_char}. {option_text}:</span>"
                                    f"<div class='quiz-audience-bar-fill'>"
                                    f"<div class='quiz-audience-fill-inner' style='width: {percentage:.0f}%;'>{percentage:.0f}%</div>"
                                    f"</div>"
                                    f"</div>", unsafe_allow_html=True)
                st.markdown("</div>", unsafe_allow_html=True)

            # Placeholder para a seção completa de feedback
            feedback_section_placeholder = st.empty()

            st.markdown("<div class='quiz-options'>", unsafe_allow_html=True)
            for i, option in enumerate(current_question["options"]):
                if option not in options_to_display:
                    st.markdown("<div></div>", unsafe_allow_html=True)
                    continue

                is_correct = (option == current_question["answer"])
                is_selected = (option == st.session_state.selected_option)
                
                button_key = f"quiz_option_{i}"
                option_char = chr(65 + i)

                if st.session_state.show_explanation:
                    if is_correct:
                        st.markdown(f"""
                            <style>
                            div[data-testid="stButton-primary"] > button[data-testid="stButton-primary-button-{button_key}"] {{
                                background-color: {THEME['colors']['accent_green']} !important;
                                border-color: {THEME['colors']['accent_green']} !important;
                                color: {THEME['colors']['background_primary']} !important;
                                font-weight: bold !important;
                                box-shadow: 0 0 15px {THEME['colors']['accent_green_shadow']} !important;
                            }}
                            </style>
                        """, unsafe_allow_html=True)
                    elif is_selected and not is_correct:
                        st.markdown(f"""
                            <style>
                            div[data-testid="stButton-primary"] > button[data-testid="stButton-primary-button-{button_key}"] {{
                                background-color: {THEME['colors']['error_border']} !important;
                                border-color: {THEME['colors']['error_border']} !important;
                                color: {THEME['colors']['background_primary']} !important;
                                font-weight: bold !important;
                                box-shadow: 0 0 15px rgba(231, 76, 60, 0.6) !important;
                            }}
                            </style>
                        """, unsafe_allow_html=True)
                
                if st.button(f"{option_char}. {option}", key=button_key, disabled=st.session_state.show_explanation, use_container_width=True):
                    check_answer(current_question, option)
                    st.rerun()
                
            st.markdown("</div>", unsafe_allow_html=True) # Fecha o div quiz-options

            # Renderiza o feedback dentro do placeholder
            if st.session_state.feedback_message:
                with feedback_section_placeholder.container():
                    if st.session_state.selected_option == current_question["answer"]:
                        st.success(st.session_state.feedback_message)
                    else:
                        st.error(f"{st.session_state.feedback_message} A resposta correta era: **{current_question['answer']}**")
                    
                    if st.session_state.show_explanation:
                        st.info(f"**Explicação:** {current_question['explanation']}")
                        
                        if not st.session_state.quiz_finished:
                            st.markdown(_get_material_icon_html_for_button_css('next_question_btn', THEME['icons']['navigate_next']), unsafe_allow_html=True)
                            if st.button(f"{THEME['phrases'].get('quiz_next_question', 'Próxima Pergunta')}", key="next_question_btn"):
                                next_question()
                                st.rerun()
            # O fechamento do div do quiz-container não é mais necessário aqui, pois o st.container() já o envolve.

    # REMOVIDO: time.sleep(1) e st.rerun() para o timer.
    # O timer agora é gerenciado por st_autorefresh.