import streamlit as st
import json
import os
import random
import logging
import time
from typing import List, Dict, Any, Optional, Tuple, Set

try:
    from streamlit_autorefresh import st_autorefresh
except ImportError:
    st_autorefresh = None

logger = logging.getLogger(__name__)

try:
    from safety_ai_app.theme_config import _get_material_icon_html, THEME
except ImportError:
    _get_material_icon_html = lambda icon: f"<span>{icon}</span>"
    THEME = {"phrases": {}, "icons": {}, "colors": {"accent_green": "#4ADE80"}}

SCRIPT_DIR = os.path.dirname(__file__)
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, '..', '..', '..', '..', '..'))
WORD_SEARCH_WORDS_PATH = os.path.join(PROJECT_ROOT, 'data', 'games', 'word_search_words.json')

GRID_SIZE = 12
NUM_WORDS_TARGET = 10
TIMER_SECONDS = 300

DIRECTIONS = [
    (0, 1), (1, 0), (0, -1), (-1, 0),
    (1, 1), (-1, -1), (1, -1), (-1, 1),
]


def load_word_search_words() -> List[Dict[str, Any]]:
    try:
        from safety_ai_app.google_drive_integrator import download_game_json_from_drive
        drive_data = download_game_json_from_drive("word_search_words.json")
        if drive_data:
            logger.info(f"Word search: loaded {len(drive_data)} words from Drive.")
            return [e for e in drive_data if 3 <= len(e.get("word", "")) <= GRID_SIZE]
    except Exception as e:
        logger.warning(f"Word search Drive load failed, using local: {e}")

    try:
        with open(WORD_SEARCH_WORDS_PATH, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return [e for e in data if 3 <= len(e["word"]) <= GRID_SIZE]
    except Exception as e:
        logger.error(f"Word search local load failed: {e}")
        return [
            {"word": "EPI", "clue": "Equipamento de Proteção Individual"},
            {"word": "CIPA", "clue": "Comissão Interna de Prevenção de Acidentes"},
            {"word": "RISCO", "clue": "Possibilidade de dano ao trabalhador"},
        ]


def can_place_word(grid: List[List[str]], word: str, row: int, col: int, dr: int, dc: int) -> bool:
    for i, ch in enumerate(word):
        r, c = row + i * dr, col + i * dc
        if not (0 <= r < GRID_SIZE and 0 <= c < GRID_SIZE):
            return False
        if grid[r][c] not in ('.', ch):
            return False
    return True


def place_word(grid: List[List[str]], word: str, row: int, col: int, dr: int, dc: int) -> List[Tuple[int, int]]:
    cells = []
    for i, ch in enumerate(word):
        r, c = row + i * dr, col + i * dc
        grid[r][c] = ch
        cells.append((r, c))
    return cells


def generate_grid(words: List[str]) -> Tuple[List[List[str]], Dict[str, List[Tuple[int, int]]]]:
    grid = [['.' for _ in range(GRID_SIZE)] for _ in range(GRID_SIZE)]
    word_cells: Dict[str, List[Tuple[int, int]]] = {}

    for word in words:
        placed = False
        for _ in range(200):
            dr, dc = random.choice(DIRECTIONS)
            row = random.randint(0, GRID_SIZE - 1)
            col = random.randint(0, GRID_SIZE - 1)
            if can_place_word(grid, word, row, col, dr, dc):
                cells = place_word(grid, word, row, col, dr, dc)
                word_cells[word] = cells
                placed = True
                break
        if not placed:
            logger.warning(f"Could not place word '{word}' in grid.")

    letters = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    for r in range(GRID_SIZE):
        for c in range(GRID_SIZE):
            if grid[r][c] == '.':
                grid[r][c] = random.choice(letters)

    return grid, word_cells


def initialize_word_search_state() -> None:
    if "ws_started" not in st.session_state:
        st.session_state.ws_started = False
    if "ws_finished" not in st.session_state:
        st.session_state.ws_finished = False
    if "ws_grid" not in st.session_state:
        st.session_state.ws_grid = []
    if "ws_word_entries" not in st.session_state:
        st.session_state.ws_word_entries = []
    if "ws_word_cells" not in st.session_state:
        st.session_state.ws_word_cells = {}
    if "ws_found_words" not in st.session_state:
        st.session_state.ws_found_words = set()
    if "ws_first_click" not in st.session_state:
        st.session_state.ws_first_click = None
    if "ws_start_time" not in st.session_state:
        st.session_state.ws_start_time = None
    if "ws_revealed" not in st.session_state:
        st.session_state.ws_revealed = False


def start_word_search() -> None:
    all_entries = load_word_search_words()
    random.shuffle(all_entries)
    selected_entries = all_entries[:NUM_WORDS_TARGET]
    words = [e["word"].upper() for e in selected_entries]
    grid, word_cells = generate_grid(words)
    # Only include entries whose words were successfully placed in the grid
    placed_words = set(word_cells.keys())
    placed_entries = [e for e in selected_entries if e["word"].upper() in placed_words]
    st.session_state.ws_grid = grid
    st.session_state.ws_word_entries = placed_entries
    st.session_state.ws_word_cells = word_cells
    st.session_state.ws_found_words = set()
    st.session_state.ws_first_click = None
    st.session_state.ws_started = True
    st.session_state.ws_finished = False
    st.session_state.ws_start_time = time.time()
    st.session_state.ws_revealed = False


def get_cells_between(r1: int, c1: int, r2: int, c2: int) -> Optional[List[Tuple[int, int]]]:
    dr = r2 - r1
    dc = c2 - c1
    length = max(abs(dr), abs(dc))
    if length == 0:
        return None
    if dr != 0 and dc != 0 and abs(dr) != abs(dc):
        return None
    step_r = 0 if dr == 0 else dr // abs(dr)
    step_c = 0 if dc == 0 else dc // abs(dc)
    return [(r1 + i * step_r, c1 + i * step_c) for i in range(length + 1)]


def check_selection(cells: List[Tuple[int, int]]) -> Optional[str]:
    for word, word_cell_list in st.session_state.ws_word_cells.items():
        if set(word_cell_list) == set(cells):
            forward = list(cells) == word_cell_list
            backward = list(reversed(cells)) == word_cell_list
            if forward or backward:
                return word
    return None


def handle_cell_click(r: int, c: int) -> None:
    first = st.session_state.ws_first_click
    if first is None:
        st.session_state.ws_first_click = (r, c)
        return

    r1, c1 = first
    if (r1, c1) == (r, c):
        st.session_state.ws_first_click = None
        return

    cells = get_cells_between(r1, c1, r, c)
    if cells:
        word = check_selection(cells)
        if word and word not in st.session_state.ws_found_words:
            st.session_state.ws_found_words.add(word)
            if len(st.session_state.ws_found_words) == len(st.session_state.ws_word_entries):
                st.session_state.ws_finished = True
    st.session_state.ws_first_click = None


def render_word_search_game() -> None:
    initialize_word_search_state()

    st.markdown(f"<h1 class='neon-title'>{_get_material_icon_html('search')} Caça-Palavras SST</h1>", unsafe_allow_html=True)
    st.markdown("Encontre os termos de SST na grade! Clique na **primeira letra** e depois na **última letra** de cada palavra.")

    st.markdown("""
    <style>
    .ws-found-word { text-decoration: line-through; color: #4ADE80 !important; }
    .ws-word-list-item { color: #E2E8F0; font-size: 0.85em; margin: 3px 0; }
    .ws-timer { font-size: 1.2em; font-weight: 700; text-align: center; margin: 8px 0; }
    .ws-clue { color: #64748B; font-size: 0.75em; margin-left: 6px; }
    div[data-testid="stButton"] button {
        padding: 2px !important;
        min-height: 30px !important;
        font-size: 0.8em !important;
        font-weight: 700 !important;
    }
    </style>
    """, unsafe_allow_html=True)

    if not st.session_state.ws_started:
        st.info("Encontre 10 termos de SST na grade clicando na primeira e na última letra de cada palavra. Você tem 5 minutos!")
        if st.button("Iniciar Caça-Palavras", key="ws_start_btn", use_container_width=True):
            start_word_search()
            st.rerun()
        return

    if st.session_state.ws_finished and not st.session_state.ws_revealed:
        found = len(st.session_state.ws_found_words)
        total = len(st.session_state.ws_word_entries)
        if found == total:
            st.success(f"Parabéns! Você encontrou todas as {total} palavras!")
        else:
            st.warning(f"Tempo esgotado! Você encontrou {found} de {total} palavras.")
        if st.button("Jogar Novamente", key="ws_play_again", use_container_width=True):
            start_word_search()
            st.rerun()
        st.markdown("**Palavras e definições:**")
        for entry in st.session_state.ws_word_entries:
            word = entry["word"].upper()
            found_mark = "✅" if word in st.session_state.ws_found_words else "❌"
            st.markdown(f"{found_mark} **{word}** — {entry['clue']}")
        return

    if st_autorefresh is not None and not st.session_state.ws_finished:
        st_autorefresh(interval=1000, key="ws_timer_refresh")

    elapsed = int(time.time() - st.session_state.ws_start_time)
    remaining = max(0, TIMER_SECONDS - elapsed)
    mins = remaining // 60
    secs = remaining % 60
    timer_color = "#F87171" if remaining < 60 else "#F97316" if remaining < 120 else "#4ADE80"
    st.markdown(f"<div class='ws-timer' style='color:{timer_color};'>⏱ {mins:02d}:{secs:02d}</div>", unsafe_allow_html=True)

    if remaining <= 0 and not st.session_state.ws_finished:
        st.session_state.ws_finished = True
        st.rerun()

    grid = st.session_state.ws_grid
    found_words = st.session_state.ws_found_words
    found_cells: Set[Tuple[int, int]] = set()
    for word in found_words:
        for cell in st.session_state.ws_word_cells.get(word, []):
            found_cells.add(cell)

    first_click = st.session_state.ws_first_click

    col_grid, col_words = st.columns([3, 1])

    with col_grid:
        if first_click:
            st.info(f"Primeira letra selecionada: linha {first_click[0]+1}, coluna {first_click[1]+1}. Clique na última letra da palavra.")
        else:
            st.info("Clique na **primeira letra** de uma palavra.")

        for r in range(GRID_SIZE):
            cols = st.columns(GRID_SIZE)
            for c in range(GRID_SIZE):
                with cols[c]:
                    letter = grid[r][c]
                    is_found = (r, c) in found_cells
                    is_first = first_click == (r, c)

                    if is_found:
                        st.markdown(f"<div style='text-align:center; color:#4ADE80; font-weight:700; font-size:0.85em; padding:4px; background:rgba(74,222,128,0.15); border-radius:4px;'>{letter}</div>", unsafe_allow_html=True)
                    elif is_first:
                        st.markdown(f"<div style='text-align:center; color:#22D3EE; font-weight:700; font-size:0.85em; padding:4px; background:rgba(34,211,238,0.2); border:2px solid #22D3EE; border-radius:4px;'>{letter}</div>", unsafe_allow_html=True)
                        if st.button(letter, key=f"ws_cell_{r}_{c}", use_container_width=True, help="Clique para deselecionar"):
                            st.session_state.ws_first_click = None
                            st.rerun()
                    else:
                        if st.button(letter, key=f"ws_cell_{r}_{c}", use_container_width=True):
                            handle_cell_click(r, c)
                            st.rerun()

    with col_words:
        found_count = len(found_words)
        total_count = len(st.session_state.ws_word_entries)
        st.markdown(f"**Palavras ({found_count}/{total_count}):**")

        if st.session_state.ws_revealed:
            for entry in st.session_state.ws_word_entries:
                word = entry["word"].upper()
                if word in found_words:
                    st.markdown(f"<div class='ws-word-list-item ws-found-word'>✅ {word}</div>", unsafe_allow_html=True)
                else:
                    cells_list = st.session_state.ws_word_cells.get(word, [])
                    pos_info = f"({cells_list[0][0]+1},{cells_list[0][1]+1})→({cells_list[-1][0]+1},{cells_list[-1][1]+1})" if cells_list else ""
                    st.markdown(f"<div class='ws-word-list-item' style='color:#F97316;'>⚠️ {word} <span class='ws-clue'>{pos_info}</span></div>", unsafe_allow_html=True)
        else:
            for entry in st.session_state.ws_word_entries:
                word = entry["word"].upper()
                if word in found_words:
                    st.markdown(f"<div class='ws-word-list-item ws-found-word'>✅ {word}</div>", unsafe_allow_html=True)
                else:
                    st.markdown(f"<div class='ws-word-list-item'>🔍 {word}</div>", unsafe_allow_html=True)
                    st.markdown(f"<div class='ws-clue'>{entry['clue']}</div>", unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        if not st.session_state.ws_revealed:
            if st.button("Revelar Respostas", key="ws_reveal_btn", use_container_width=True):
                st.session_state.ws_revealed = True
                st.session_state.ws_finished = True
                st.rerun()
        if st.button("Novo Jogo", key="ws_new_btn", use_container_width=True):
            start_word_search()
            st.rerun()
