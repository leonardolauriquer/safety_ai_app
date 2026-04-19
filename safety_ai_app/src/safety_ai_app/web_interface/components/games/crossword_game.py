import streamlit as st
import json
import os
import logging
import random
from typing import List, Dict, Any, Tuple

logger = logging.getLogger(__name__)

# Importa o tema para ícones e frases
try:
    from safety_ai_app.theme_config import _get_material_icon_html, THEME
except ImportError:
    st.error("Erro ao carregar configurações de tema. Verifique 'theme_config.py'.")
    _get_material_icon_html = lambda icon: f"<span>{icon}</span>" # Fallback
    THEME = {"phrases": {}, "icons": {}, "colors": {}} # Fallback para evitar KeyError

# Importa a função de integração com o Google Drive
from safety_ai_app.google_drive_integrator import download_and_parse_crossword_excel

# Caminho para o arquivo JSON que agora contém TODOS os layouts
SCRIPT_DIR = os.path.dirname(__file__)
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, '..', '..', '..', '..', '..')) # Subir 5 níveis
CROSSWORD_DATA_JSON_PATH = os.path.join(PROJECT_ROOT, 'data', 'games', 'crossword_data.json')

# Caminho da planilha no Google Drive para o conteúdo das palavras
# AGORA É APENAS O NOME DO ARQUIVO, A LÓGICA DE PASTA ESTÁ NO google_drive_integrator.py
CROSSWORD_EXCEL_DRIVE_PATH = "palavrascruzadas.xlsx"

# Constantes para o grid, inspiradas no código pycross
FILLER = '#' # Célula bloqueada (preta)
BLANK = '_'  # Célula vazia (para preencher)

def load_crossword_data() -> Dict[str, Any]:
    """
    Carrega os dados das palavras cruzadas.
    Primeiro, seleciona aleatoriamente um layout de grade do arquivo JSON principal.
    Em seguida, baixa e parseia a planilha do Google Drive para obter as palavras e dicas,
    preenchendo os slots do layout selecionado com palavras aleatórias que se encaixem no tamanho
    e sejam compatíveis com as interseções.
    """
    # 1. Carregar TODOS os layouts do JSON principal e selecionar um aleatoriamente
    all_layouts: List[Dict[str, Any]] = []
    try:
        with open(CROSSWORD_DATA_JSON_PATH, 'r', encoding='utf-8') as f:
            all_layouts = json.load(f)
        logger.info(f"Total de {len(all_layouts)} layouts de palavras cruzadas carregados de {CROSSWORD_DATA_JSON_PATH}")
    except FileNotFoundError:
        logger.error(f"Arquivo de layouts de palavras cruzadas não encontrado: {CROSSWORD_DATA_JSON_PATH}")
        st.error("Erro: Arquivo de layouts de palavras cruzadas não encontrado. Por favor, verifique a instalação.")
        return {"grid_size": 0, "words": []}
    except json.JSONDecodeError:
        logger.error(f"Erro ao decodificar JSON dos layouts de palavras cruzadas: {CROSSWORD_DATA_JSON_PATH}")
        st.error("Erro: Formato inválido no arquivo de layouts de palavras cruzadas.")
        return {"grid_size": 0, "words": []}

    if not all_layouts:
        logger.error("Nenhum layout encontrado no arquivo crossword_data.json.")
        st.error("Erro: Nenhum layout de palavras cruzadas encontrado no arquivo principal.")
        return {"grid_size": 0, "words": []}

    # Seleciona um layout aleatoriamente
    selected_layout = random.choice(all_layouts)
    json_data = selected_layout # json_data agora é o layout selecionado
    logger.info(f"Layout de palavras cruzadas selecionado aleatoriamente (grid_size: {json_data.get('grid_size')}, palavras: {len(json_data.get('words', []))}).")

    # 2. Baixar e parsear a planilha do Google Drive (fonte das palavras e dicas)
    # Passa apenas o nome do arquivo, a lógica de pasta é interna ao integrator
    excel_words_data = download_and_parse_crossword_excel(CROSSWORD_EXCEL_DRIVE_PATH)

    # Fallback: vocabulário local quando Drive não está disponível
    if not excel_words_data:
        local_vocab_path = os.path.join(PROJECT_ROOT, 'data', 'games', 'crossword_words_local.json')
        try:
            with open(local_vocab_path, 'r', encoding='utf-8') as f:
                excel_words_data = json.load(f)
            logger.info(f'Vocabulário local carregado como fallback: {len(excel_words_data)} palavras.')
        except Exception as e:
            logger.warning(f'Não foi possível carregar vocabulário local: {e}')

    if excel_words_data:
        # Agrupar palavras do Excel por tamanho para seleção eficiente
        words_by_length: Dict[int, List[Dict[str, Any]]] = {}
        for entry in excel_words_data:
            # Usar o comprimento REAL da resposta, não a coluna 'Caracteres da resposta'
            actual_length = len(entry['Resposta']) 
            if actual_length not in words_by_length:
                words_by_length[actual_length] = []
            words_by_length[actual_length].append(entry)
        
        # Embaralhar as listas de palavras para garantir aleatoriedade na seleção
        for length in words_by_length:
            random.shuffle(words_by_length[length])
        
        logger.info(f"Palavras do Excel agrupadas por tamanho (baseado no comprimento real da 'Resposta'): { {k: len(v) for k, v in words_by_length.items()} }")

        # 3. Preencher os slots do layout JSON com palavras aleatórias do Excel
        updated_words = []
        words_filled_from_excel = 0
        
        # Criar uma cópia das listas de palavras disponíveis para cada comprimento
        # para que possamos remover palavras já usadas e evitar repetições na mesma grade
        current_available_excel_words = {length: list(words) for length, words in words_by_length.items()}

        # Temporary grid to track occupied cells and their letters during word selection
        # This is crucial for checking intersections
        temp_grid_size = json_data["grid_size"]
        temp_grid = [[BLANK for _ in range(temp_grid_size)] for _ in range(temp_grid_size)]
        
        # Sort words by number to process them in order, or by length (longest first) for better fit
        # Processing order can impact which words get placed if there are conflicts.
        # For now, let's stick to the order defined in the JSON (by 'number').
        sorted_json_word_entries = sorted(json_data.get("words", []), key=lambda x: x["number"])

        for json_word_entry in sorted_json_word_entries:
            original_json_word_value = json_word_entry.get("word", "")
            slot_length = len(original_json_word_value)
            
            logger.info(f"Tentando preencher slot JSON (placeholder: '{original_json_word_value}', comprimento esperado: {slot_length})")
            
            possible_words_for_slot = current_available_excel_words.get(slot_length, [])
            
            selected_excel_entry = None
            
            # Try to find a compatible word from the shuffled list
            for excel_entry in possible_words_for_slot:
                word_to_test = excel_entry["Resposta"].upper()
                is_compatible = True
                
                # Check for compatibility with already "placed" words in temp_grid
                for i, char_to_place in enumerate(word_to_test):
                    r, c = (json_word_entry["start_y"], json_word_entry["start_x"] + i) if json_word_entry["direction"] == "across" else (json_word_entry["start_y"] + i, json_word_entry["start_x"])
                    
                    # Boundary check (should be handled by layout design, but good to have)
                    if not (0 <= r < temp_grid_size and 0 <= c < temp_grid_size):
                        is_compatible = False
                        logger.error(f"ERRO INTERNO: Palavra '{word_to_test}' excede os limites da grade em ({r},{c}) durante a seleção. Layout JSON inválido.")
                        break

                    # Check for conflict with already placed letters
                    if temp_grid[r][c] != BLANK and temp_grid[r][c] != char_to_place:
                        is_compatible = False
                        # logger.debug(f"Conflito detectado para '{word_to_test}' em ({r},{c}). Célula contém '{temp_grid[r][c]}', tentando colocar '{char_to_place}'.")
                        break # This word is not compatible, try next one
                
                if is_compatible:
                    selected_excel_entry = excel_entry
                    break # Found a compatible word
            
            if selected_excel_entry:
                # Remove the selected word from the available list
                current_available_excel_words[slot_length].remove(selected_excel_entry)
                
                json_word_entry["word"] = selected_excel_entry["Resposta"]
                json_word_entry["clue"] = selected_excel_entry["Dica"]
                words_filled_from_excel += 1
                logger.info(f"SUCESSO: Slot preenchido com palavra aleatória do Excel: '{selected_excel_entry['Resposta']}' (Dica: '{selected_excel_entry['Dica']}')")
                
                # "Place" the word in the temporary grid
                for i, char_to_place in enumerate(selected_excel_entry["Resposta"].upper()):
                    r, c = (json_word_entry["start_y"], json_word_entry["start_x"] + i) if json_word_entry["direction"] == "across" else (json_word_entry["start_y"] + i, json_word_entry["start_x"])
                    temp_grid[r][c] = char_to_place
            else:
                # If no compatible word is found, the word in json_word_entry remains its placeholder value.
                # This will result in a blank space in the grid for this word.
                logger.warning(f"FALHA: Não há palavras disponíveis na planilha Excel com comprimento {slot_length} que sejam compatíveis com as interseções para preencher o slot (placeholder: '{original_json_word_value}'). O slot ficará vazio.")
                json_word_entry["word"] = BLANK * slot_length # Preenche com BLANKs para indicar que não foi preenchido
            updated_words.append(json_word_entry)
        
        json_data["words"] = updated_words
        
        if words_filled_from_excel > 0:
            logger.info(f"Total de {words_filled_from_excel} slots preenchidos com palavras aleatórias da planilha do Google Drive.")
        else:
            logger.warning("Nenhum slot foi preenchido com palavras aleatórias da planilha Excel (não havia palavras de comprimento correspondente ou compatíveis com interseções).")
    else:
        logger.warning("Não foi possível carregar dados da planilha do Google Drive. Usando apenas dados do layout JSON selecionado (palavras e dicas).")

    return json_data

def build_grid_from_words(grid_size: int, words_data: List[Dict[str, Any]]) -> Tuple[List[List[str]], Dict[Tuple[int, int], int]]:
    """
    Constrói o grid de palavras cruzadas a partir dos dados das palavras.
    Preenche as palavras e marca as células bloqueadas.
    Esta função agora assume que a `words_data` já foi pré-processada para compatibilidade de interseções.
    """
    grid = [[BLANK for _ in range(grid_size)] for _ in range(grid_size)]
    clue_numbers = {}
    
    for word_data in words_data:
        word_str = word_data["word"].upper()
        start_x = word_data["start_x"]
        start_y = word_data["start_y"]
        direction = word_data["direction"]
        number = word_data["number"]

        # Se a palavra for apenas BLANKs (indicando que não foi preenchida), não a colocamos
        if all(c == BLANK for c in word_str):
            logger.info(f"Palavra '{word_str}' (clue #{number}) não foi preenchida, ignorando.")
            continue

        logger.info(f"Colocando palavra: {word_str} (clue #{number}) em (start_y={start_y}, start_x={start_x}, direction={direction})")

        clue_numbers[(start_y, start_x)] = number

        for i, char in enumerate(word_str):
            r, c = (start_y, start_x + i) if direction == "across" else (start_y + i, start_x)
            
            # Uma verificação final de limites, embora a lógica de seleção já deva ter garantido isso
            if not (0 <= r < grid_size and 0 <= c < grid_size):
                logger.error(f"ERRO: Palavra '{word_str}' (clue #{number}) excede os limites da grade em ({r},{c}) durante a construção final. Isso não deveria acontecer.")
                continue # Pula este caractere, mas a palavra já foi considerada "colocada"

            grid[r][c] = char
        
    # Preenche as células restantes que não fazem parte de nenhuma palavra com FILLER
    for r in range(grid_size):
        for c in range(grid_size):
            is_part_of_any_word = False
            for word_data_check in words_data:
                word_len_check = len(word_data_check["word"])
                if all(c == BLANK for c in word_data_check["word"]): # Ignora palavras não preenchidas
                    continue

                if word_data_check["direction"] == "across":
                    if r == word_data_check["start_y"] and c >= word_data_check["start_x"] and c < word_data_check["start_x"] + word_len_check:
                        is_part_of_any_word = True
                        break
                elif word_data_check["direction"] == "down":
                    if c == word_data_check["start_x"] and r >= word_data_check["start_y"] and r < word_data_check["start_y"] + word_len_check:
                        is_part_of_any_word = True
                        break
            
            if not is_part_of_any_word and grid[r][c] == BLANK:
                grid[r][c] = FILLER
                
    return grid, clue_numbers

def initialize_crossword_state() -> None:
    """Inicializa o estado da sessão para as palavras cruzadas."""
    if "crossword_data" not in st.session_state:
        st.session_state.crossword_data = load_crossword_data()
        logger.info(f"Dados de palavras cruzadas carregados na inicialização: {st.session_state.crossword_data}")
    
    if "crossword_started" not in st.session_state:
        st.session_state.crossword_started = False
    
    if "show_solution" not in st.session_state:
        st.session_state.show_solution = False

    # Initialize button flags for Streamlit rerun management
    if 'crossword_check_clicked' not in st.session_state:
        st.session_state.crossword_check_clicked = False
    if 'crossword_finish_clicked' not in st.session_state: # NEW: for "Concluir" button
        st.session_state.crossword_finish_clicked = False
    if 'crossword_reset_clicked' not in st.session_state:
        st.session_state.crossword_reset_clicked = False
    # NEW: Flag for showing reset confirmation
    if 'show_reset_confirmation' not in st.session_state:
        st.session_state.show_reset_confirmation = False

    if not st.session_state.crossword_started:
        grid_size = st.session_state.crossword_data.get("grid_size", 10)
        words_data = st.session_state.crossword_data.get("words", [])
        
        initial_grid, clue_numbers = build_grid_from_words(grid_size, words_data)
        
        st.session_state.crossword_grid_state = initial_grid
        st.session_state.crossword_clue_numbers = clue_numbers
        st.session_state.crossword_user_inputs = {f"cell_{r}_{c}": "" for r in range(grid_size) for c in range(grid_size)}
        st.session_state.crossword_feedback = {f"cell_{r}_{c}": None for r in range(grid_size) for c in range(grid_size)}
        st.session_state.crossword_finished = False
        st.session_state.crossword_message = ""

        logger.info("Grid de Palavras Cruzadas Gerado (Solução):\n")
        for row in st.session_state.crossword_grid_state:
            logger.info("".join(row))

def reset_crossword() -> None:
    """Reseta o estado das palavras cruzadas para iniciar um novo jogo com um novo layout."""
    # Força o recarregamento dos dados para pegar novas palavras aleatórias e um novo layout
    if "crossword_data" in st.session_state:
        del st.session_state.crossword_data 
    st.session_state.crossword_data = load_crossword_data()
    logger.info(f"Dados de palavras cruzadas carregados no reset: {st.session_state.crossword_data}")

    grid_size = st.session_state.crossword_data.get("grid_size", 10)
    words_data = st.session_state.crossword_data.get("words", [])
    
    initial_grid, clue_numbers = build_grid_from_words(grid_size, words_data)

    st.session_state.crossword_grid_state = initial_grid
    st.session_state.crossword_clue_numbers = clue_numbers
    st.session_state.crossword_user_inputs = {f"cell_{r}_{c}": "" for r in range(grid_size) for c in range(grid_size)}
    st.session_state.crossword_feedback = {f"cell_{r}_{c}": None for r in range(grid_size) for c in range(grid_size)}
    st.session_state.crossword_started = True
    st.session_state.crossword_finished = False # Ensure game is not finished on new game
    st.session_state.crossword_message = ""
    st.session_state.show_solution = False # Ensure solution is hidden on new game
    logger.info("Palavras Cruzadas resetadas e iniciadas.")
    logger.info("Grid de Palavras Cruzadas Gerado (Solução) no reset:\n")
    for row in st.session_state.crossword_grid_state:
        logger.info("".join(row))

def check_crossword_answers() -> Tuple[int, int]:
    """Verifica todas as respostas das palavras cruzadas e retorna o número de acertos e o total de células a preencher."""
    correct_cells = 0
    total_cells_to_fill = 0
    grid_size = st.session_state.crossword_data.get("grid_size", 10)
    words_data = st.session_state.crossword_data.get("words", [])

    solution_grid, _ = build_grid_from_words(grid_size, words_data)

    for r in range(grid_size):
        for c in range(grid_size):
            key = f"cell_{r}_{c}"
            user_char = st.session_state.crossword_user_inputs.get(key, "").strip().upper()
            
            if solution_grid[r][c] != FILLER:
                total_cells_to_fill += 1
                correct_char = solution_grid[r][c]
                if user_char == correct_char:
                    st.session_state.crossword_feedback[key] = True
                    correct_cells += 1
                else:
                    st.session_state.crossword_feedback[key] = False
            else:
                st.session_state.crossword_feedback[key] = None
    
    # Update message based on check
    if total_cells_to_fill > 0 and correct_cells == total_cells_to_fill:
        st.session_state.crossword_message = f"<div class='st-success-like'>{_get_material_icon_html('check_circle')} {THEME['phrases'].get('crossword_all_correct_check', 'Todas as suas respostas estão corretas!')}</div>"
    elif total_cells_to_fill > 0:
        st.session_state.crossword_message = f"<div class='st-warning-like'>{_get_material_icon_html('info')} {THEME['phrases'].get('crossword_partial_success', 'Você acertou {correct_count} de {total_cells_to_fill} células preenchidas. Continue tentando!').format(correct_count=correct_cells, total_cells_to_fill=total_cells_to_fill)}</div>"
    else:
        st.session_state.crossword_message = f"<div class='st-info-like'>{_get_material_icon_html('info')} {THEME['phrases'].get('crossword_fill_to_check', 'Preencha algumas palavras para verificar suas respostas.')}</div>"
    
    logger.info(f"Verificação de palavras cruzadas. Acertos: {correct_cells}/{total_cells_to_fill}\n")
    return correct_cells, total_cells_to_fill


def render_crossword_game() -> None:
    """Renderiza a interface do jogo de palavras cruzadas."""
    initialize_crossword_state()

    crossword_icon = THEME['icons'].get('crossword_icon', 'extension')
    crossword_title = THEME['phrases'].get('crossword_game', 'Palavras Cruzadas SST')

    st.markdown(f"<h1 class='neon-title'>{_get_material_icon_html(crossword_icon)} {crossword_title}</h1>", unsafe_allow_html=True)
    st.markdown("Desvende os termos de Saúde e Segurança do Trabalho! Preencha as palavras com base nas pistas.")


    # Inject custom CSS for the crossword game
    st.markdown(f"""
        <style>
            /* --- Streamlit Component Resets --- */
            /* Remove default padding/margin/border from Streamlit columns */
            div[data-testid="stColumn"] {{
                padding: 0px !important;
                margin: 0px !important;
                min-width: 0px !important;
                flex-grow: 0 !important;
                flex-shrink: 0 !important;
                /* Ensure stColumn itself is transparent by default, will be overridden by cell styles */
                background-color: transparent !important;
                border: none !important;
                box-shadow: none !important;
            }}
            /* Remove default margin from Streamlit horizontal blocks (rows of columns) */
            div[data-testid="stHorizontalBlock"] {{
                margin-bottom: 0px !important;
                display: flex;
                justify-content: center; /* Center the grid/buttons/clues */
                background-color: transparent !important;
                border: none !important;
                box-shadow: none !important;
            }}
            /* Ensure stElementContainer (wrapper for most Streamlit elements) is clean */
            div[data-testid="stElementContainer"] {{
                padding: 0 !important;
                margin: 0 !important;
                border: none !important;
                box-shadow: none !important;
                background-color: transparent !important;
                height: 100%; /* Make it fill its parent (stColumn) */
                width: 100%;  /* Make it fill its parent (stColumn) */
                display: flex; /* Use flex to center its content */
                align-items: center;
                justify-content: center;
            }}
            /* Ensure stVerticalBlock (wrapper for st.container, st.columns content) is clean */
            div[data-testid="stVerticalBlock"] {{
                padding: 0 !important;
                margin: 0 !important;
                border: none !important;
                box-shadow: none !important;
                background-color: transparent !important;
            }}
            /* Ensure stMarkdown (wrapper for markdown content) is clean and fills */
            div[data-testid="stMarkdown"] {{
                height: 100%;
                width: 100%;
                display: flex;
                align-items: center;
                justify-content: center;
            }}
            /* Ensure stMarkdownContainer (inner wrapper for markdown content) is clean and fills */
            div[data-testid="stMarkdownContainer"] {{
                height: 100%;
                width: 100%;
                display: flex;
                align-items: center;
                justify-content: center;
            }}


            /* --- Crossword Grid Cell Styling --- */
            /* Global base style for each stColumn representing a cell */
            div[data-testid="stColumn"].crossword-cell {{
                position: relative; /* For positioning clue numbers */
                display: flex;
                justify-content: center;
                align-items: center; /* Vertically center content */
                width: 40px; /* Fixed width for cells */
                height: 40px; /* Fixed height for cells */
                border: 1px solid rgba(255, 255, 255, 0.2);
                background-color: #222; /* Default cell background */
                box-sizing: border-box;
                overflow: hidden;
            }}

            /* Specific styles for feedback/black cells */
            .crossword-cell-black {{
                background-color: #000 !important;
                border-color: #000 !important;
            }}
            .crossword-cell-correct {{
                background-color: rgba(39, 174, 96, 0.3) !important;
                border-color: {THEME['colors'].get('accent_green', '#00ff00')} !important;
            }}
            .crossword-cell-incorrect {{
                background-color: rgba(220, 53, 69, 0.3) !important;
                border-color: #dc3545 !important;
            }}

            /* Style for the actual text input element */
            div[data-testid="stColumn"].crossword-cell .stTextInput > div > div > input {{
                width: 100%;
                height: 100%; /* Fill the entire cell */
                text-align: center;
                font-size: 1.2em;
                font-weight: bold;
                text-transform: uppercase;
                border: none !important;
                background-color: transparent !important;
                color: #fff;
                padding: 0 !important; /* CRÍTICO: Sem padding para o texto ficar centralizado */
                margin: 0 !important;
                box-shadow: none !important;
                line-height: 1; /* Garante que a altura da linha não adicione espaço extra */
            }}

            /* Remove Streamlit's default input label */
            div[data-testid="stColumn"].crossword-cell .stTextInput > label {{
                display: none !important;
            }}
            /* Ensure the stTextInput component itself fills the wrapper */
            div[data-testid="stColumn"].crossword-cell .stTextInput {{
                height: 100%;
                width: 100%;
                display: flex;
                align-items: center;
                justify-content: center;
            }}
            div[data-testid="stColumn"].crossword-cell .stTextInput > div > div {{ /* Inner wrapper of stTextInput */
                height: 100%;
                width: 100%;
                display: flex;
                align-items: center;
                justify-content: center;
                padding: 0 !important;
                margin: 0 !important;
            }}


            /* Focus style for input */
            div[data-testid="stColumn"].crossword-cell .stTextInput > div > div > input:focus {{
                outline: 2px solid {THEME['colors'].get('accent_green', '#00ff00')}; /* Neon green outline on focus */
                outline-offset: -2px;
            }}

            /* --- Clue Number Styling --- */
            /* This will be injected directly as HTML, so no need for complex Streamlit element targeting */
            /* .clue-number-wrapper is defined inline in Python now */

            /* --- Grid Container (wrapper for all rows) --- */
            .crossword-grid-container {{
                margin-top: 20px;
                margin-bottom: 20px;
                display: flex;
                flex-direction: column;
                align-items: center;
                border: none; /* Borda transparente */
                background-color: transparent; /* Fundo transparente */
                padding: 0px;
            }}

            /* --- Solution Cell Styling --- */
            .solution-cell {{
                display: flex;
                justify-content: center;
                align-items: center;
                width: 100%;
                height: 100%;
                font-size: 1.2em;
                font-weight: bold;
                text-transform: uppercase;
                color: {THEME['colors'].get('accent_green', '#00ff00')}; /* Cor da solução */
                background-color: rgba(0, 255, 0, 0.1); /* Fundo sutil */
            }}

            /* --- Clues Section Styling --- */
            .clues-section-wrapper {{ /* Custom class for the div wrapping the clue columns */
                margin-top: 30px;
                padding: 20px;
                background-color: {THEME['colors'].get('background_secondary', '#1a1a1a')};
                border-radius: 10px;
                box-shadow: 0 0 15px {THEME['colors'].get('accent_green_shadow', 'rgba(0, 255, 0, 0.3)')};
            }}
            .clues-section-wrapper h4 {{ /* Para os títulos das dicas */
                color: {THEME['colors'].get('accent_green', '#00ff00')};
                font-size: 1.3em;
                margin-bottom: 15px;
            }}
            .clues-section-wrapper ul {{ /* Para as listas de dicas */
                list-style-type: none;
                padding-left: 0;
            }}
            .clues-section-wrapper ul li {{
                margin-bottom: 8px;
                color: {THEME['colors'].get('text_secondary', '#CCCCCC')};
                font-size: 0.95em;
            }}
            .clues-section-wrapper ul li span {{
                font-weight: bold;
                color: {THEME['colors'].get('text_primary', '#FFFFFF')};
                margin-right: 5px;
            }}

            /* --- Button Styling --- */
            .stButton > button {{
                border-radius: 8px;
                padding: 10px 20px;
                font-size: 1.1em;
                font-weight: bold;
                transition: all 0.3s ease;
            }}
            .stButton > button:hover {{
                transform: translateY(-2px);
                box-shadow: 0 4px 15px rgba(0, 255, 0, 0.4);
            }}
            /* Estilo para o botão primário (Verificar Respostas) */
            div[data-testid*="stVerticalBlock"] button[type="primary"] {{
                background-color: {THEME['colors'].get('accent_green', '#00ff00')} !important;
                border-color: {THEME['colors'].get('accent_green', '#00ff00')} !important;
                color: {THEME['colors'].get('background_primary', '#000000')} !important;
            }}
            div[data-testid*="stVerticalBlock"] button[type="primary"]:hover {{
                background-color: rgba(39, 174, 96, 0.8) !important;
                border-color: rgba(39, 174, 96, 0.8) !important;
            }}
            /* Estilo para o botão secundário (Reiniciar Jogo) */
            div[data-testid*="stVerticalBlock"] button[key="reset_crossword_btn"] {{
                background-color: #dc3545 !important;
                border-color: #dc3545 !important;
                color: white !important;
            }}
            div[data-testid*="stVerticalBlock"] button[key="reset_crossword_btn"]:hover {{
                background-color: #c82333 !important;
                border-color: #c82333 !important;
                box-shadow: 0 4px 15px rgba(255, 0, 0, 0.4);
            }}
            /* Estilo para o botão Concluir */
            div[data-testid*="stVerticalBlock"] button[key="finish_crossword_btn"] {{
                background-color: #007bff !important; /* Azul */
                border-color: #007bff !important;
                color: white !important;
            }}
            div[data-testid*="stVerticalBlock"] button[key="finish_crossword_btn"]:hover {{
                background-color: #0056b3 !important;
                border-color: #0056b3 !important;
                box-shadow: 0 4px 15px rgba(0, 123, 255, 0.4);
            }}
            /* Estilo para o botão Mostrar Solução */
            div[data-testid*="stVerticalBlock"] button[key="show_solution_btn"] {{
                background-color: #6c757d !important; /* Cinza */
                border-color: #6c757d !important;
                color: white !important;
            }}
            div[data-testid*="stVerticalBlock"] button[key="show_solution_btn"]:hover {{
                background-color: #5a6268 !important;
                border-color: #5a6268 !important;
                box-shadow: 0 4px 15px rgba(108, 117, 125, 0.4);
            }}

            /* --- Feedback Messages --- */
            .st-success-like, .st-warning-like, .st-info-like {{
                padding: 10px;
                border-radius: 5px;
                margin-bottom: 15px;
                display: flex;
                align-items: center;
                gap: 10px;
                font-weight: bold;
            }}
            .st-success-like {{
                background-color: rgba(39, 174, 96, 0.2);
                color: {THEME['colors'].get('accent_green', '#00ff00')};
                border: 1px solid {THEME['colors'].get('accent_green', '#00ff00')};
            }}
            .st-warning-like {{
                background-color: rgba(255, 193, 7, 0.2);
                color: #ffc107;
                border: 1px solid #ffc107;
            }}
            .st-info-like {{
                background-color: rgba(23, 162, 184, 0.2);
                color: #17a2b8;
                border: 1px solid #17a2b8;
            }}
            /* NEW: Styles for confirmation dialog */
            .confirmation-dialog {{
                background-color: {THEME['colors'].get('background_secondary', '#1a1a1a')};
                border-radius: 10px;
                padding: 20px;
                margin-top: 20px;
                box-shadow: 0 0 20px {THEME['colors'].get('accent_green_shadow', 'rgba(0, 255, 0, 0.5)')};
                text-align: center;
            }}
            .confirmation-dialog p {{
                font-size: 1.1em;
                color: {THEME['colors'].get('text_primary', '#FFFFFF')};
                margin-bottom: 15px;
            }}
            .confirmation-dialog .stButton > button {{
                margin: 0 10px;
            }}
        </style>
    """, unsafe_allow_html=True)


    if not st.session_state.crossword_started:
        st.info("Clique em 'Iniciar Palavras Cruzadas' para começar o desafio!")
        if st.button(f"{THEME['phrases'].get('crossword_start_game', 'Iniciar Palavras Cruzadas')}", key="start_crossword_btn", type="primary"):
            reset_crossword()
            st.rerun()
    else:
        grid_size = st.session_state.crossword_data.get("grid_size", 10)
        words_data = st.session_state.crossword_data.get("words", [])

        # --- Clues Section (MOVED HERE) ---
        # Construir a seção de dicas como uma única string HTML para controle total do layout
        across_clues_html = f"<h4 class='clues-section-title'>{THEME['phrases'].get('crossword_across_clues', 'Horizontais')}</h4><ul class='clues-section-list'>"
        for word_data in sorted([w for w in words_data if w['direction'] == 'across'], key=lambda x: x['number']):
            # Não mostra dicas para palavras que não foram preenchidas (apenas BLANKs)
            if not all(c == BLANK for c in word_data["word"]):
                across_clues_html += f"<li><span>{word_data['number']}.</span> {word_data['clue']}</li>"
        across_clues_html += "</ul>"

        down_clues_html = f"<h4 class='clues-section-title'>{THEME['phrases'].get('crossword_down_clues', 'Verticais')}</h4><ul class='clues-section-list'>"
        for word_data in sorted([w for w in words_data if w['direction'] == 'down'], key=lambda x: x['number']):
            # Não mostra dicas para palavras que não foram preenchidas (apenas BLANKs)
            if not all(c == BLANK for c in word_data["word"]):
                down_clues_html += f"<li><span>{word_data['number']}.</span> {word_data['clue']}</li>"
        down_clues_html += "</ul>"

        full_clues_section_html = f"""
        <div class='clues-section-wrapper'>
            <div style='display: flex; justify-content: space-around;'>
                <div style='flex: 1; padding-right: 10px;'>{across_clues_html}</div>
                <div style='flex: 1; padding-left: 10px;'>{down_clues_html}</div>
            </div>
        </div>
        """
        st.markdown(full_clues_section_html, unsafe_allow_html=True)
     # Adiciona uma linha divisória entre as dicas e o grid

        # --- Grid Section ---
        st.markdown("<div class='crossword-grid-container'>", unsafe_allow_html=True)
        for r in range(grid_size):
            cols = st.columns(grid_size, gap="small") 
            for c in range(grid_size):
                with cols[c]: # Coloca o conteúdo na coluna atual
                    cell_key = f"cell_{r}_{c}"
                    clue_number = st.session_state.crossword_clue_numbers.get((r, c), "")
                    cell_value = st.session_state.crossword_grid_state[r][c] # Valor do grid inicial (solução)

                    # Determine classes for the stColumn itself
                    column_classes = ["crossword-cell"] # Base class for all cells
                    if cell_value == FILLER:
                        column_classes.append("crossword-cell-black")
                    elif st.session_state.crossword_feedback.get(cell_key) is True:
                        column_classes.append("crossword-cell-correct")
                    elif st.session_state.crossword_feedback.get(cell_key) is False:
                        column_classes.append("crossword-cell-incorrect")
                    
                    # Inject CSS to add these classes to the specific stColumn
                    # This is the correct way to apply dynamic classes to Streamlit's internal divs
                    st.markdown(f"""
                        <style>
                            div[data-testid="stColumn"]:has(div[data-testid="stElementContainer"][class*="st-key-{cell_key}"]) {{
                                {' '.join(column_classes)}
                            }}
                        </style>
                    """, unsafe_allow_html=True)

                    if cell_value == FILLER: # Célula preta (bloqueada)
                        # Não renderiza nada dentro da célula, o background é aplicado ao stColumn
                        pass 
                    else: # Célula para preencher
                        # Render clue number if it exists, using inline style for absolute positioning
                        if clue_number:
                            st.markdown(f"""
                                <div style="
                                    position: absolute;
                                    top: 2px;
                                    left: 2px;
                                    font-size: 0.7em;
                                    color: rgba(255, 255, 255, 0.7);
                                    font-weight: bold;
                                    z-index: 10;
                                    pointer-events: none;
                                ">
                                    {clue_number}
                                </div>
                            """, unsafe_allow_html=True)

                        if st.session_state.show_solution:
                            correct_char = st.session_state.crossword_grid_state[r][c] # A solução está no grid_state
                            display_char = correct_char if correct_char != BLANK else ""
                            # Renderiza a solução como um texto simples dentro de um div estilizado
                            st.markdown(f"<div class='solution-cell'>{display_char}</div>", unsafe_allow_html=True)
                        else:
                            current_input_value = st.session_state.crossword_user_inputs.get(cell_key, "")
                            st.session_state.crossword_user_inputs[cell_key] = st.text_input(
                                label=" ", # Label vazio para não aparecer
                                value=current_input_value,
                                max_chars=1,
                                key=cell_key,
                                disabled=st.session_state.crossword_finished, # Disable inputs if game is finished
                                label_visibility="collapsed" # Esconde o label visualmente
                            )
            st.markdown("</div>", unsafe_allow_html=True) # Fecha o container externo da grade

    
        
        # Mensagens de feedback
        feedback_placeholder = st.empty()
        if st.session_state.crossword_message:
            feedback_placeholder.markdown(st.session_state.crossword_message, unsafe_allow_html=True)

        # --- Buttons Section ---
        col_buttons = st.columns(3) # 3 colunas para 3 botões
        with col_buttons[0]:
            # "Verificar Respostas" button
            if st.button(f"{THEME['phrases'].get('crossword_check_answers', 'Verificar Respostas')}", key="check_crossword_btn", type="primary", disabled=st.session_state.crossword_finished):
                st.session_state.crossword_check_clicked = True
        with col_buttons[1]:
            # "Concluir" button
            if st.button(f"{THEME['phrases'].get('crossword_finish_game', 'Concluir')}", key="finish_crossword_btn", disabled=st.session_state.crossword_finished):
                st.session_state.crossword_finish_clicked = True
        with col_buttons[2]:
            # "Reiniciar Jogo" button (with confirmation)
            if st.button(f"{THEME['phrases'].get('crossword_reset_game', 'Reiniciar Jogo')}", key="reset_crossword_btn"):
                st.session_state.show_reset_confirmation = True
                st.rerun() # Rerun to show the confirmation dialog

        # NEW: Confirmation dialog for reset
        if st.session_state.show_reset_confirmation:
            st.markdown("<div class='confirmation-dialog'>", unsafe_allow_html=True)
            st.markdown(f"<p>{THEME['phrases'].get('crossword_confirm_reset', 'Tem certeza que deseja reiniciar o jogo com um novo layout e novas palavras?')}</p>", unsafe_allow_html=True)
            col_confirm = st.columns(2)
            with col_confirm[0]:
                if st.button(f"{THEME['phrases'].get('crossword_confirm_yes', 'Sim, Reiniciar')}", key="confirm_reset_yes", type="primary"):
                    st.session_state.crossword_reset_clicked = True # Set flag to trigger actual reset
                    st.session_state.show_reset_confirmation = False # Hide confirmation
                    st.rerun() # Rerun to perform reset
            with col_confirm[1]:
                if st.button(f"{THEME['phrases'].get('crossword_confirm_no', 'Não, Cancelar')}", key="confirm_reset_no"):
                    st.session_state.show_reset_confirmation = False # Hide confirmation
                    st.rerun() # Rerun to hide confirmation
            st.markdown("</div>", unsafe_allow_html=True)

        # NEW: "Mostrar Solução" button (separate from Concluir)
        # Only show if game is active and not finished
        if not st.session_state.crossword_finished: 
            if st.button(f"{THEME['phrases'].get('crossword_show_solution', 'Mostrar Solução') if not st.session_state.show_solution else THEME['phrases'].get('crossword_hide_solution', 'Esconder Solução')}", key="show_solution_btn"):
                st.session_state.show_solution = not st.session_state.show_solution
                st.rerun()
            
        # Process clicks and rerun outside the button creation
        if st.session_state.crossword_check_clicked:
            check_crossword_answers()
            st.session_state.crossword_check_clicked = False # Reset flag
            st.rerun()
        
        # NEW: Logic for "Concluir" button
        if st.session_state.crossword_finish_clicked:
            correct_cells, total_cells_to_fill = check_crossword_answers() # Check answers and update crossword_message
            st.session_state.crossword_finish_clicked = False # Reset flag
            
            # Set game as finished to disable inputs
            st.session_state.crossword_finished = True 
            st.session_state.show_solution = True # Show solution automatically on finish

            # Display final message based on result
            if total_cells_to_fill > 0 and correct_cells == total_cells_to_fill:
                feedback_placeholder.markdown(f"<div class='st-success-like'>{_get_material_icon_html('trophy')} {THEME['phrases'].get('crossword_congratulations', 'Parabéns! Você completou as palavras cruzadas!')}</div>", unsafe_allow_html=True)
            elif total_cells_to_fill > 0:
                feedback_placeholder.markdown(f"<div class='st-warning-like'>{_get_material_icon_html('sentiment_dissatisfied')} {THEME['phrases'].get('crossword_defeat', 'Que pena! Você não acertou todas. Mas não desanime, tente novamente!').format(correct_count=correct_cells, total_cells_to_fill=total_cells_to_fill)}</div>", unsafe_allow_html=True)
            else:
                feedback_placeholder.markdown(f"<div class='st-info-like'>{_get_material_icon_html('info')} {THEME['phrases'].get('crossword_no_answers_yet', 'Você não preencheu nenhuma palavra. Que tal tentar um novo jogo?') }</div>", unsafe_allow_html=True)
            
            # After displaying the message and showing solution, offer to play again
            # This will be handled by a new button that appears only when crossword_finished is True
            st.rerun() # Rerun to display the message, disabled inputs, and "Jogar Novamente" button

        # Only perform reset if confirmed
        if st.session_state.crossword_reset_clicked:
            reset_crossword()
            st.session_state.crossword_reset_clicked = False # Reset flag
            st.rerun()

        # Add "Jogar Novamente" button only when game is finished (after "Concluir" was pressed)
        if st.session_state.crossword_finished:
        
            if st.button("Jogar Novamente", key="play_again_after_finish", type="primary"):
                reset_crossword()
                st.rerun()