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
    _get_material_icon_html = lambda icon: f"<span>{icon}</span>"
    THEME = {"phrases": {}, "icons": {}, "colors": {}}

# Importa a função de integração com o Google Drive
from safety_ai_app.google_drive_integrator import download_and_parse_crossword_excel

# Caminho para o arquivo JSON que agora contém TODOS os layouts
SCRIPT_DIR = os.path.dirname(__file__)
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, '..', '..', '..', '..', '..'))
CROSSWORD_DATA_JSON_PATH = os.path.join(PROJECT_ROOT, 'data', 'games', 'crossword_data.json')

# Caminho da planilha no Google Drive para o conteúdo das palavras
CROSSWORD_EXCEL_DRIVE_PATH = "palavrascruzadas.xlsx"

# Constantes para o grid
FILLER = '#'
BLANK = '_'


def load_crossword_data() -> Dict[str, Any]:
    """
    Carrega os dados das palavras cruzadas.
    Primeiro, seleciona aleatoriamente um layout de grade do arquivo JSON principal.
    Em seguida, baixa e parseia a planilha do Google Drive para obter as palavras e dicas,
    preenchendo os slots do layout selecionado com palavras aleatórias que se encaixem no tamanho
    e sejam compatíveis com as interseções.
    """
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

    selected_layout = random.choice(all_layouts)
    json_data = selected_layout
    logger.info(f"Layout de palavras cruzadas selecionado aleatoriamente (grid_size: {json_data.get('grid_size')}, palavras: {len(json_data.get('words', []))}).")

    excel_words_data = download_and_parse_crossword_excel(CROSSWORD_EXCEL_DRIVE_PATH)

    if not excel_words_data:
        local_vocab_path = os.path.join(PROJECT_ROOT, 'data', 'games', 'crossword_words_local.json')
        try:
            with open(local_vocab_path, 'r', encoding='utf-8') as f:
                excel_words_data = json.load(f)
            logger.info(f'Vocabulário local carregado como fallback: {len(excel_words_data)} palavras.')
        except Exception as e:
            logger.warning(f'Não foi possível carregar vocabulário local: {e}')

    if excel_words_data:
        words_by_length: Dict[int, List[Dict[str, Any]]] = {}
        for entry in excel_words_data:
            actual_length = len(entry['Resposta'])
            if actual_length not in words_by_length:
                words_by_length[actual_length] = []
            words_by_length[actual_length].append(entry)

        for length in words_by_length:
            random.shuffle(words_by_length[length])

        logger.info(f"Palavras do Excel agrupadas por tamanho: { {k: len(v) for k, v in words_by_length.items()} }")

        updated_words = []
        words_filled_from_excel = 0

        current_available_excel_words = {length: list(words) for length, words in words_by_length.items()}

        temp_grid_size = json_data["grid_size"]
        temp_grid = [[BLANK for _ in range(temp_grid_size)] for _ in range(temp_grid_size)]

        sorted_json_word_entries = sorted(json_data.get("words", []), key=lambda x: x["number"])

        for json_word_entry in sorted_json_word_entries:
            original_json_word_value = json_word_entry.get("word", "")
            slot_length = len(original_json_word_value)

            logger.info(f"Tentando preencher slot JSON (placeholder: '{original_json_word_value}', comprimento esperado: {slot_length})")

            possible_words_for_slot = current_available_excel_words.get(slot_length, [])

            selected_excel_entry = None

            for excel_entry in possible_words_for_slot:
                word_to_test = excel_entry["Resposta"].upper()
                is_compatible = True

                for i, char_to_place in enumerate(word_to_test):
                    r, c = (json_word_entry["start_y"], json_word_entry["start_x"] + i) if json_word_entry["direction"] == "across" else (json_word_entry["start_y"] + i, json_word_entry["start_x"])

                    if not (0 <= r < temp_grid_size and 0 <= c < temp_grid_size):
                        is_compatible = False
                        logger.error(f"ERRO INTERNO: Palavra '{word_to_test}' excede os limites da grade em ({r},{c}) durante a seleção. Layout JSON inválido.")
                        break

                    if temp_grid[r][c] != BLANK and temp_grid[r][c] != char_to_place:
                        is_compatible = False
                        break

                if is_compatible:
                    selected_excel_entry = excel_entry
                    break

            if selected_excel_entry:
                current_available_excel_words[slot_length].remove(selected_excel_entry)

                json_word_entry["word"] = selected_excel_entry["Resposta"]
                json_word_entry["clue"] = selected_excel_entry["Dica"]
                words_filled_from_excel += 1
                logger.info(f"SUCESSO: Slot preenchido com palavra aleatória do Excel: '{selected_excel_entry['Resposta']}' (Dica: '{selected_excel_entry['Dica']}')")

                for i, char_to_place in enumerate(selected_excel_entry["Resposta"].upper()):
                    r, c = (json_word_entry["start_y"], json_word_entry["start_x"] + i) if json_word_entry["direction"] == "across" else (json_word_entry["start_y"] + i, json_word_entry["start_x"])
                    temp_grid[r][c] = char_to_place
            else:
                logger.warning(f"FALHA: Não há palavras disponíveis com comprimento {slot_length} compatíveis para o slot '{original_json_word_value}'.")
                json_word_entry["word"] = BLANK * slot_length
            updated_words.append(json_word_entry)

        json_data["words"] = updated_words

        if words_filled_from_excel > 0:
            logger.info(f"Total de {words_filled_from_excel} slots preenchidos com palavras aleatórias da planilha do Google Drive.")
        else:
            logger.warning("Nenhum slot foi preenchido com palavras aleatórias da planilha Excel.")
    else:
        logger.warning("Não foi possível carregar dados da planilha do Google Drive. Usando apenas dados do layout JSON selecionado.")

    return json_data


def build_grid_from_words(grid_size: int, words_data: List[Dict[str, Any]]) -> Tuple[List[List[str]], Dict[Tuple[int, int], int]]:
    """
    Constrói o grid de palavras cruzadas a partir dos dados das palavras.
    """
    grid = [[BLANK for _ in range(grid_size)] for _ in range(grid_size)]
    clue_numbers = {}

    for word_data in words_data:
        word_str = word_data["word"].upper()
        start_x = word_data["start_x"]
        start_y = word_data["start_y"]
        direction = word_data["direction"]
        number = word_data["number"]

        if all(c == BLANK for c in word_str):
            logger.info(f"Palavra '{word_str}' (clue #{number}) não foi preenchida, ignorando.")
            continue

        logger.info(f"Colocando palavra: {word_str} (clue #{number}) em (start_y={start_y}, start_x={start_x}, direction={direction})")

        clue_numbers[(start_y, start_x)] = number

        for i, char in enumerate(word_str):
            r, c = (start_y, start_x + i) if direction == "across" else (start_y + i, start_x)

            if not (0 <= r < grid_size and 0 <= c < grid_size):
                logger.error(f"ERRO: Palavra '{word_str}' (clue #{number}) excede os limites da grade em ({r},{c}) durante a construção final.")
                continue

            grid[r][c] = char

    for r in range(grid_size):
        for c in range(grid_size):
            is_part_of_any_word = False
            for word_data_check in words_data:
                word_len_check = len(word_data_check["word"])
                if all(c == BLANK for c in word_data_check["word"]):
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

    if "crossword_hints_remaining" not in st.session_state:
        st.session_state.crossword_hints_remaining = 3

    if 'crossword_check_clicked' not in st.session_state:
        st.session_state.crossword_check_clicked = False
    if 'crossword_finish_clicked' not in st.session_state:
        st.session_state.crossword_finish_clicked = False
    if 'crossword_reset_clicked' not in st.session_state:
        st.session_state.crossword_reset_clicked = False
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
    for _r in range(grid_size):
        for _c in range(grid_size):
            _k = f"cell_{_r}_{_c}"
            if _k in st.session_state:
                del st.session_state[_k]
    st.session_state.crossword_started = True
    st.session_state.crossword_finished = False
    st.session_state.crossword_message = ""
    st.session_state.show_solution = False
    st.session_state.crossword_hints_remaining = 3
    logger.info("Palavras Cruzadas resetadas e iniciadas.")
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

    if total_cells_to_fill > 0 and correct_cells == total_cells_to_fill:
        st.session_state.crossword_message = f"<div class='cw-msg-success'>{_get_material_icon_html('check_circle')} {THEME['phrases'].get('crossword_all_correct_check', 'Todas as suas respostas estão corretas!')}</div>"
    elif total_cells_to_fill > 0:
        st.session_state.crossword_message = f"<div class='cw-msg-warning'>{_get_material_icon_html('info')} {THEME['phrases'].get('crossword_partial_success', 'Você acertou {{correct_count}} de {{total_cells_to_fill}} células preenchidas. Continue tentando!').format(correct_count=correct_cells, total_cells_to_fill=total_cells_to_fill)}</div>"
    else:
        st.session_state.crossword_message = f"<div class='cw-msg-info'>{_get_material_icon_html('info')} {THEME['phrases'].get('crossword_fill_to_check', 'Preencha algumas palavras para verificar suas respostas.')}</div>"

    logger.info(f"Verificação de palavras cruzadas. Acertos: {correct_cells}/{total_cells_to_fill}\n")
    return correct_cells, total_cells_to_fill


def render_crossword_game() -> None:
    """Renderiza a interface do jogo de palavras cruzadas."""
    initialize_crossword_state()

    crossword_icon = THEME['icons'].get('crossword_icon', 'extension')
    crossword_title = THEME['phrases'].get('crossword_game', 'Palavras Cruzadas SST')

    st.markdown(
        f"<h1 class='neon-title'>{_get_material_icon_html(crossword_icon)} {crossword_title}</h1>",
        unsafe_allow_html=True,
    )

    C = THEME['colors']
    GREEN = C.get('accent_green', '#4ADE80')
    CYAN  = C.get('accent_cyan',  '#22D3EE')
    BG2   = C.get('background_secondary', '#0B1220')
    TXT1  = C.get('text_primary',  '#F1F5F9')
    TXT2  = C.get('text_secondary', '#94A3B8')

    st.markdown(f"""
    <style>
    /* ── Scoped resets: only columns that hold a crossword cell ── */
    div[data-testid="stColumn"]:has(.cw-cell-marker) {{
        padding: 0 !important;
        margin: 0 !important;
        min-width: 0 !important;
        flex-grow: 0 !important;
        flex-shrink: 0 !important;
        width: 42px !important;
        height: 42px !important;
        position: relative !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        border: none !important;
        box-shadow: none !important;
        background-color: transparent !important;
        overflow: hidden !important;
        box-sizing: border-box !important;
    }}
    /* Grid rows that contain cell markers */
    div[data-testid="stHorizontalBlock"]:has(.cw-cell-marker) {{
        margin-bottom: 0 !important;
        gap: 1px !important;
        background: transparent !important;
        border: none !important;
        box-shadow: none !important;
    }}
    /* Inner wrappers inside grid cell columns */
    div[data-testid="stColumn"]:has(.cw-cell-marker) div[data-testid="stElementContainer"],
    div[data-testid="stColumn"]:has(.cw-cell-marker) div[data-testid="stVerticalBlock"],
    div[data-testid="stColumn"]:has(.cw-cell-marker) div[data-testid="stMarkdown"],
    div[data-testid="stColumn"]:has(.cw-cell-marker) div[data-testid="stMarkdownContainer"] {{
        padding: 0 !important;
        margin: 0 !important;
        height: 100% !important;
        width: 100% !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        border: none !important;
        box-shadow: none !important;
        background: transparent !important;
    }}

    /* ── Cell marker & inner visual layer ── */
    .cw-cell-marker {{
        position: absolute;
        inset: 0;
        display: flex;
        align-items: center;
        justify-content: center;
    }}
    .cw-cell-inner {{
        position: absolute;
        inset: 0;
        display: flex;
        align-items: center;
        justify-content: center;
        box-sizing: border-box;
        border-radius: 2px;
    }}
    .cw-cell-black .cw-cell-inner {{
        background: #040d1a;
        border: 1px solid #040d1a;
    }}
    .cw-cell-white .cw-cell-inner {{
        background: rgba(15, 25, 50, 0.92);
        border: 1.5px solid rgba(34, 211, 238, 0.22);
        transition: border-color .18s, box-shadow .18s;
    }}
    .cw-cell-white .cw-cell-inner:hover {{
        border-color: rgba(34, 211, 238, 0.55);
        box-shadow: 0 0 8px rgba(34, 211, 238, 0.2);
    }}
    .cw-cell-correct .cw-cell-inner {{
        background: rgba(74, 222, 128, 0.11);
        border: 1.5px solid {GREEN};
        box-shadow: 0 0 8px rgba(74, 222, 128, 0.32), inset 0 0 4px rgba(74, 222, 128, 0.08);
    }}
    .cw-cell-incorrect .cw-cell-inner {{
        background: rgba(239, 68, 68, 0.11);
        border: 1.5px solid #EF4444;
        box-shadow: 0 0 8px rgba(239, 68, 68, 0.32);
    }}

    /* ── Clue number badge ── */
    .cw-num {{
        position: absolute;
        top: 2px;
        left: 3px;
        font-size: 9px;
        font-weight: 700;
        line-height: 1;
        color: {CYAN};
        z-index: 20;
        pointer-events: none;
        font-family: 'Orbitron', monospace;
    }}

    /* ── Text input inside cell ── */
    div[data-testid="stColumn"]:has(.cw-cell-marker) .stTextInput,
    div[data-testid="stColumn"]:has(.cw-cell-marker) .stTextInput > div,
    div[data-testid="stColumn"]:has(.cw-cell-marker) .stTextInput > div > div {{
        height: 100% !important;
        width: 100% !important;
        padding: 0 !important;
        margin: 0 !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        border: none !important;
        box-shadow: none !important;
        background: transparent !important;
    }}
    div[data-testid="stColumn"]:has(.cw-cell-marker) .stTextInput label {{
        display: none !important;
    }}
    div[data-testid="stColumn"]:has(.cw-cell-marker) .stTextInput input {{
        width: 100% !important;
        height: 34px !important;
        text-align: center !important;
        font-size: 1rem !important;
        font-weight: 700 !important;
        text-transform: uppercase !important;
        border: none !important;
        background: transparent !important;
        color: {TXT1} !important;
        padding: 0 !important;
        margin: 0 !important;
        box-shadow: none !important;
        font-family: 'Orbitron', monospace !important;
        z-index: 10 !important;
        position: relative !important;
        letter-spacing: 1px;
    }}
    div[data-testid="stColumn"]:has(.cw-cell-marker) .stTextInput input:focus {{
        outline: none !important;
        background: rgba(34, 211, 238, 0.06) !important;
    }}
    div[data-testid="stColumn"]:has(.cw-cell-marker) .stTextInput input:disabled {{
        opacity: 0.75 !important;
        cursor: default !important;
    }}

    /* ── Solution letter overlay ── */
    .cw-solution-char {{
        font-size: 1rem;
        font-weight: 700;
        text-transform: uppercase;
        color: {GREEN};
        font-family: 'Orbitron', monospace;
        text-shadow: 0 0 10px rgba(74, 222, 128, 0.65);
        z-index: 10;
        position: relative;
        letter-spacing: 1px;
    }}

    /* ── Stats bar ── */
    .cw-stats {{
        display: flex;
        align-items: center;
        gap: 18px;
        padding: 10px 18px;
        margin-bottom: 18px;
        background: rgba(11, 18, 32, 0.82);
        border: 1px solid rgba(34, 211, 238, 0.13);
        border-radius: 12px;
        backdrop-filter: blur(8px);
        flex-wrap: wrap;
    }}
    .cw-stat-item {{
        display: flex;
        align-items: center;
        gap: 6px;
        font-size: 0.82rem;
        color: {TXT2};
        font-family: 'Inter', sans-serif;
        white-space: nowrap;
    }}
    .cw-stat-value {{
        font-weight: 700;
        color: {CYAN};
        font-family: 'Orbitron', monospace;
        font-size: 0.88rem;
    }}
    .cw-stat-value.green {{ color: {GREEN}; }}
    .cw-progress-bar-bg {{
        flex: 1;
        min-width: 80px;
        height: 6px;
        border-radius: 3px;
        background: rgba(255, 255, 255, 0.07);
        overflow: hidden;
    }}
    .cw-progress-bar-fill {{
        height: 100%;
        border-radius: 3px;
        background: linear-gradient(90deg, {CYAN}, {GREEN});
        transition: width .5s ease;
    }}

    /* ── Grid wrapper ── */
    .cw-grid-wrapper {{
        display: inline-block;
        border: 1px solid rgba(34, 211, 238, 0.1);
        border-radius: 12px;
        padding: 10px;
        background: rgba(4, 13, 26, 0.65);
        box-shadow: 0 0 30px rgba(34, 211, 238, 0.04), 0 8px 32px rgba(0, 0, 0, 0.4);
    }}

    /* ── Clues panel ── */
    .cw-clues-panel {{
        background: rgba(11, 18, 32, 0.88);
        border: 1px solid rgba(34, 211, 238, 0.11);
        border-radius: 14px;
        padding: 16px 14px;
        backdrop-filter: blur(10px);
        max-height: 600px;
        overflow-y: auto;
    }}
    .cw-clues-panel::-webkit-scrollbar {{ width: 4px; }}
    .cw-clues-panel::-webkit-scrollbar-track {{ background: transparent; }}
    .cw-clues-panel::-webkit-scrollbar-thumb {{ background: rgba(34,211,238,0.25); border-radius: 2px; }}
    .cw-clues-title {{
        display: flex;
        align-items: center;
        gap: 6px;
        font-family: 'Orbitron', monospace;
        font-size: 0.74rem;
        font-weight: 700;
        letter-spacing: 1.8px;
        text-transform: uppercase;
        margin-bottom: 8px;
        color: {CYAN};
        border-bottom: 1px solid rgba(34, 211, 238, 0.14);
        padding-bottom: 6px;
    }}
    .cw-clue-item {{
        display: flex;
        gap: 8px;
        align-items: flex-start;
        padding: 5px 0;
        border-bottom: 1px solid rgba(255, 255, 255, 0.04);
    }}
    .cw-clue-item:last-child {{ border-bottom: none; }}
    .cw-clue-num {{
        min-width: 22px;
        font-weight: 700;
        font-size: 0.75rem;
        color: {GREEN};
        font-family: 'Orbitron', monospace;
        padding-top: 1px;
        flex-shrink: 0;
    }}
    .cw-clue-text {{
        font-size: 0.8rem;
        color: {TXT2};
        line-height: 1.45;
        font-family: 'Inter', sans-serif;
    }}
    .cw-clues-divider {{
        height: 1px;
        background: rgba(255, 255, 255, 0.06);
        margin: 10px 0;
    }}

    /* ── Feedback messages ── */
    .cw-msg-success, .cw-msg-warning, .cw-msg-info {{
        padding: 10px 16px;
        border-radius: 8px;
        margin: 12px 0;
        font-weight: 600;
        font-size: 0.9rem;
        display: flex;
        align-items: center;
        gap: 8px;
        font-family: 'Inter', sans-serif;
    }}
    .cw-msg-success {{
        background: rgba(74, 222, 128, 0.10);
        border: 1px solid {GREEN};
        color: {GREEN};
    }}
    .cw-msg-warning {{
        background: rgba(251, 191, 36, 0.09);
        border: 1px solid #FBBF24;
        color: #FBBF24;
    }}
    .cw-msg-info {{
        background: rgba(34, 211, 238, 0.07);
        border: 1px solid {CYAN};
        color: {CYAN};
    }}

    /* ── Confirmation dialog ── */
    .cw-confirm {{
        background: rgba(11, 18, 32, 0.96);
        border: 1px solid rgba(239, 68, 68, 0.38);
        border-radius: 12px;
        padding: 20px;
        margin: 12px 0;
        text-align: center;
        box-shadow: 0 0 20px rgba(239, 68, 68, 0.12);
    }}
    .cw-confirm p {{
        color: {TXT1};
        font-size: 0.92rem;
        margin-bottom: 14px;
        font-family: 'Inter', sans-serif;
    }}

    /* ── Start card ── */
    .cw-start-card {{
        background: rgba(11, 18, 32, 0.88);
        border: 1px solid rgba(34, 211, 238, 0.16);
        border-radius: 18px;
        padding: 44px 36px;
        text-align: center;
        max-width: 500px;
        margin: 40px auto;
        backdrop-filter: blur(14px);
        box-shadow: 0 8px 40px rgba(0, 0, 0, 0.5);
    }}
    .cw-start-card h3 {{
        color: {CYAN};
        font-family: 'Orbitron', monospace;
        font-size: 1.15rem;
        margin-bottom: 12px;
        letter-spacing: 1px;
    }}
    .cw-start-card p {{
        color: {TXT2};
        font-size: 0.9rem;
        margin-bottom: 28px;
        line-height: 1.65;
        font-family: 'Inter', sans-serif;
    }}

    /* ── Responsive ── */
    @media (max-width: 768px) {{
        div[data-testid="stColumn"]:has(.cw-cell-marker) {{
            width: 30px !important;
            height: 30px !important;
        }}
        div[data-testid="stColumn"]:has(.cw-cell-marker) .stTextInput input {{
            font-size: 0.78rem !important;
            height: 26px !important;
        }}
        .cw-clues-panel {{ max-height: 350px; }}
    }}
    @media (max-width: 480px) {{
        div[data-testid="stColumn"]:has(.cw-cell-marker) {{
            width: 24px !important;
            height: 24px !important;
        }}
        div[data-testid="stColumn"]:has(.cw-cell-marker) .stTextInput input {{
            font-size: 0.65rem !important;
            height: 20px !important;
        }}
    }}
    </style>
    """, unsafe_allow_html=True)

    # ── Start screen ──────────────────────────────────────────────────────────
    if not st.session_state.crossword_started:
        st.markdown("""
        <div class='cw-start-card'>
            <h3>🧩 Palavras Cruzadas SST</h3>
            <p>
                Teste seus conhecimentos em Saúde e Segurança do Trabalho!
                Preencha o grid com base nas dicas horizontais e verticais.
                Você tem <strong>3 dicas</strong> disponíveis por rodada.
            </p>
        </div>
        """, unsafe_allow_html=True)
        c1, c2, c3 = st.columns([1, 2, 1])
        with c2:
            if st.button(
                f"▶ {THEME['phrases'].get('crossword_start_game', 'Iniciar Palavras Cruzadas')}",
                key="start_crossword_btn",
                type="primary",
                use_container_width=True,
            ):
                reset_crossword()
                st.rerun()
        return

    # ── Game active ───────────────────────────────────────────────────────────
    grid_size = st.session_state.crossword_data.get("grid_size", 10)
    words_data = st.session_state.crossword_data.get("words", [])

    # ── Compute progress stats ────────────────────────────────────────────────
    total_cells = sum(
        1 for r in range(grid_size) for c in range(grid_size)
        if st.session_state.crossword_grid_state[r][c] != FILLER
    )
    filled_cells = sum(
        1 for r in range(grid_size) for c in range(grid_size)
        if st.session_state.crossword_grid_state[r][c] != FILLER
        and st.session_state.crossword_user_inputs.get(f"cell_{r}_{c}", "").strip() != ""
    )
    correct_count = sum(1 for v in st.session_state.crossword_feedback.values() if v is True)
    pct_filled = int((filled_cells / total_cells) * 100) if total_cells else 0
    hints_left = st.session_state.get("crossword_hints_remaining", 3)

    correct_badge = (
        f"<div class='cw-stat-item'><span>✅</span><span>Corretas:</span>"
        f"<span class='cw-stat-value green'>{correct_count}</span></div>"
        if correct_count > 0 else ""
    )

    # ── Stats bar ─────────────────────────────────────────────────────────────
    st.markdown(f"""
    <div class="cw-stats">
        <div class="cw-stat-item">
            <span>📝</span>
            <span>Preenchidas:</span>
            <span class="cw-stat-value">{filled_cells}/{total_cells}</span>
        </div>
        <div class="cw-progress-bar-bg">
            <div class="cw-progress-bar-fill" style="width:{pct_filled}%"></div>
        </div>
        <div class="cw-stat-item">
            <span>💡</span>
            <span>Dicas:</span>
            <span class="cw-stat-value">{hints_left}/3</span>
        </div>
        {correct_badge}
    </div>
    """, unsafe_allow_html=True)

    # ── Main 2-panel layout: grid left / clues right ──────────────────────────
    grid_col, clues_col = st.columns([1.6, 1], gap="large")

    with grid_col:
        st.markdown("<div class='cw-grid-wrapper'>", unsafe_allow_html=True)
        for r in range(grid_size):
            cols = st.columns(grid_size)
            for c in range(grid_size):
                with cols[c]:
                    cell_key  = f"cell_{r}_{c}"
                    clue_num  = st.session_state.crossword_clue_numbers.get((r, c), "")
                    cell_val  = st.session_state.crossword_grid_state[r][c]
                    feedback  = st.session_state.crossword_feedback.get(cell_key)

                    if cell_val == FILLER:
                        cell_cls = "cw-cell-black"
                    elif feedback is True:
                        cell_cls = "cw-cell-correct"
                    elif feedback is False:
                        cell_cls = "cw-cell-incorrect"
                    else:
                        cell_cls = "cw-cell-white"

                    if cell_val == FILLER:
                        st.markdown(
                            f"<div class='cw-cell-marker {cell_cls}'>"
                            f"<div class='cw-cell-inner'></div>"
                            f"</div>",
                            unsafe_allow_html=True,
                        )
                    else:
                        num_html = f"<span class='cw-num'>{clue_num}</span>" if clue_num else ""
                        st.markdown(
                            f"<div class='cw-cell-marker {cell_cls}'>"
                            f"<div class='cw-cell-inner'>{num_html}</div>"
                            f"</div>",
                            unsafe_allow_html=True,
                        )
                        if st.session_state.show_solution:
                            display_char = cell_val if cell_val != BLANK else ""
                            st.markdown(
                                f"<div class='cw-solution-char'>{display_char}</div>",
                                unsafe_allow_html=True,
                            )
                        else:
                            current_val = st.session_state.crossword_user_inputs.get(cell_key, "")
                            st.session_state.crossword_user_inputs[cell_key] = st.text_input(
                                label=" ",
                                value=current_val,
                                max_chars=1,
                                key=cell_key,
                                disabled=st.session_state.crossword_finished,
                                label_visibility="collapsed",
                            )
        st.markdown("</div>", unsafe_allow_html=True)

    with clues_col:
        across_items = sorted(
            [w for w in words_data if w['direction'] == 'across'
             and not all(ch == BLANK for ch in w['word'])],
            key=lambda x: x['number'],
        )
        down_items = sorted(
            [w for w in words_data if w['direction'] == 'down'
             and not all(ch == BLANK for ch in w['word'])],
            key=lambda x: x['number'],
        )
        across_html = "".join(
            f"<div class='cw-clue-item'>"
            f"<span class='cw-clue-num'>{w['number']}.</span>"
            f"<span class='cw-clue-text'>{w['clue']}</span>"
            f"</div>"
            for w in across_items
        )
        down_html = "".join(
            f"<div class='cw-clue-item'>"
            f"<span class='cw-clue-num'>{w['number']}.</span>"
            f"<span class='cw-clue-text'>{w['clue']}</span>"
            f"</div>"
            for w in down_items
        )
        st.markdown(f"""
        <div class='cw-clues-panel'>
            <div class='cw-clues-title'>→ Horizontais</div>
            {across_html}
            <div class='cw-clues-divider'></div>
            <div class='cw-clues-title'>↓ Verticais</div>
            {down_html}
        </div>
        """, unsafe_allow_html=True)

    # ── Feedback message placeholder ──────────────────────────────────────────
    msg_placeholder = st.empty()
    if st.session_state.crossword_message:
        msg_placeholder.markdown(st.session_state.crossword_message, unsafe_allow_html=True)

    # ── Action buttons row ────────────────────────────────────────────────────
    btn_c1, btn_c2, btn_c3, btn_c4 = st.columns(4)
    with btn_c1:
        if st.button(
            "✅ Verificar",
            key="check_crossword_btn",
            type="primary",
            disabled=st.session_state.crossword_finished,
            use_container_width=True,
        ):
            st.session_state.crossword_check_clicked = True

    with btn_c2:
        if st.button(
            "🏁 Concluir",
            key="finish_crossword_btn",
            disabled=st.session_state.crossword_finished,
            use_container_width=True,
        ):
            st.session_state.crossword_finish_clicked = True

    with btn_c3:
        sol_label = "🙈 Ocultar" if st.session_state.show_solution else "👁 Solução"
        if st.button(
            sol_label,
            key="show_solution_btn",
            disabled=st.session_state.crossword_finished,
            use_container_width=True,
        ):
            st.session_state.show_solution = not st.session_state.show_solution
            st.rerun()

    with btn_c4:
        if st.button(
            "🔄 Reiniciar",
            key="reset_crossword_btn",
            use_container_width=True,
        ):
            st.session_state.show_reset_confirmation = True
            st.rerun()

    # ── Hint button (centred, below main row) ─────────────────────────────────
    if not st.session_state.crossword_finished and hints_left > 0:
        h1, h2, h3 = st.columns([1, 2, 1])
        with h2:
            plural = "s" if hints_left != 1 else ""
            if st.button(
                f"💡 Usar Dica  ({hints_left} restante{plural})",
                key="crossword_hint_btn",
                use_container_width=True,
            ):
                import random as _random
                candidates = [
                    (f"cell_{r}_{c}", st.session_state.crossword_grid_state[r][c])
                    for r in range(grid_size)
                    for c in range(grid_size)
                    if st.session_state.crossword_grid_state[r][c] not in (FILLER, BLANK)
                    and st.session_state.crossword_user_inputs.get(
                        f"cell_{r}_{c}", ""
                    ).strip().upper() != st.session_state.crossword_grid_state[r][c]
                ]
                if candidates:
                    chosen_key, chosen_char = _random.choice(candidates)
                    st.session_state.crossword_user_inputs[chosen_key] = chosen_char
                    st.session_state[chosen_key] = chosen_char
                    st.session_state.crossword_hints_remaining = hints_left - 1
                    st.rerun()
                else:
                    st.info("Não há células para revelar.")

    # ── Confirmation dialog ───────────────────────────────────────────────────
    if st.session_state.show_reset_confirmation:
        st.markdown(f"""
        <div class='cw-confirm'>
            <p>{THEME['phrases'].get(
                'crossword_confirm_reset',
                'Tem certeza que deseja reiniciar com um novo layout e novas palavras?'
            )}</p>
        </div>
        """, unsafe_allow_html=True)
        cc1, cc2 = st.columns(2)
        with cc1:
            if st.button("✔ Sim, Reiniciar", key="confirm_reset_yes", type="primary", use_container_width=True):
                st.session_state.crossword_reset_clicked = True
                st.session_state.show_reset_confirmation = False
                st.rerun()
        with cc2:
            if st.button("✖ Cancelar", key="confirm_reset_no", use_container_width=True):
                st.session_state.show_reset_confirmation = False
                st.rerun()

    # ── Post-game: play again ─────────────────────────────────────────────────
    if st.session_state.crossword_finished:
        pa1, pa2, pa3 = st.columns([1, 2, 1])
        with pa2:
            if st.button(
                "▶ Jogar Novamente",
                key="play_again_after_finish",
                type="primary",
                use_container_width=True,
            ):
                reset_crossword()
                st.rerun()

    # ── Deferred click processing ─────────────────────────────────────────────
    if st.session_state.crossword_check_clicked:
        check_crossword_answers()
        st.session_state.crossword_check_clicked = False
        st.rerun()

    if st.session_state.crossword_finish_clicked:
        correct_cells, total_cells_to_fill = check_crossword_answers()
        st.session_state.crossword_finish_clicked = False
        st.session_state.crossword_finished = True
        st.session_state.show_solution = True
        if total_cells_to_fill > 0 and correct_cells == total_cells_to_fill:
            msg_placeholder.markdown(
                f"<div class='cw-msg-success'>{_get_material_icon_html('trophy')} "
                f"{THEME['phrases'].get('crossword_congratulations', 'Parabéns! Você completou as palavras cruzadas!')}</div>",
                unsafe_allow_html=True,
            )
        elif total_cells_to_fill > 0:
            msg_placeholder.markdown(
                f"<div class='cw-msg-warning'>{_get_material_icon_html('sentiment_dissatisfied')} "
                f"{THEME['phrases'].get('crossword_defeat', 'Que pena! Você acertou {{correct_count}} de {{total_cells_to_fill}}. Tente novamente!').format(correct_count=correct_cells, total_cells_to_fill=total_cells_to_fill)}</div>",
                unsafe_allow_html=True,
            )
        else:
            msg_placeholder.markdown(
                f"<div class='cw-msg-info'>{_get_material_icon_html('info')} "
                f"{THEME['phrases'].get('crossword_no_answers_yet', 'Você não preencheu nenhuma palavra. Que tal tentar um novo jogo?')}</div>",
                unsafe_allow_html=True,
            )
        st.rerun()

    if st.session_state.crossword_reset_clicked:
        reset_crossword()
        st.session_state.crossword_reset_clicked = False
        st.rerun()
