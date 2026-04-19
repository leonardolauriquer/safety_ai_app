import streamlit as st
import json
import os
import random
import logging
import time
from typing import List, Dict, Any, Optional, Tuple

logger = logging.getLogger(__name__)

try:
    from safety_ai_app.theme_config import _get_material_icon_html, THEME
except ImportError:
    _get_material_icon_html = lambda icon: f"<span>{icon}</span>"
    THEME = {"phrases": {}, "icons": {}, "colors": {"accent_green": "#4ADE80"}}

SCRIPT_DIR = os.path.dirname(__file__)
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, '..', '..', '..', '..', '..'))
MEMORY_PAIRS_PATH = os.path.join(PROJECT_ROOT, 'data', 'games', 'memory_pairs.json')

DIFFICULTY_CONFIG = {
    "Fácil (12 cartas)": 6,
    "Médio (20 cartas)": 10,
    "Difícil (30 cartas)": 15,
}


def load_memory_pairs() -> List[Dict[str, Any]]:
    try:
        from safety_ai_app.google_drive_integrator import download_game_json_from_drive
        drive_data = download_game_json_from_drive("memory_pairs.json")
        if drive_data:
            logger.info(f"Memory game: loaded {len(drive_data)} pairs from Drive.")
            return drive_data
    except Exception as e:
        logger.warning(f"Memory game Drive load failed, using local: {e}")

    try:
        with open(MEMORY_PAIRS_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Erro ao carregar pares de memória: {e}")
        return [
            {"card_a": "EPI", "card_b": "Equipamento de Proteção Individual"},
            {"card_a": "CIPA", "card_b": "Comissão Interna de Prevenção de Acidentes"},
            {"card_a": "CAT", "card_b": "Comunicação de Acidente de Trabalho"},
        ]


def initialize_memory_state() -> None:
    if "mem_started" not in st.session_state:
        st.session_state.mem_started = False
    if "mem_finished" not in st.session_state:
        st.session_state.mem_finished = False
    if "mem_cards" not in st.session_state:
        st.session_state.mem_cards = []
    if "mem_flipped" not in st.session_state:
        st.session_state.mem_flipped = []
    if "mem_matched" not in st.session_state:
        st.session_state.mem_matched = set()
    if "mem_flip_count" not in st.session_state:
        st.session_state.mem_flip_count = 0
    if "mem_start_time" not in st.session_state:
        st.session_state.mem_start_time = None
    if "mem_elapsed" not in st.session_state:
        st.session_state.mem_elapsed = 0
    if "mem_difficulty" not in st.session_state:
        st.session_state.mem_difficulty = "Fácil (12 cartas)"
    if "mem_pairs_count" not in st.session_state:
        st.session_state.mem_pairs_count = 6
    if "mem_lock" not in st.session_state:
        st.session_state.mem_lock = False


def start_memory_game(num_pairs: int) -> None:
    all_pairs = load_memory_pairs()
    random.shuffle(all_pairs)
    selected_pairs = all_pairs[:num_pairs]

    cards = []
    for i, pair in enumerate(selected_pairs):
        cards.append({"id": i * 2, "pair_id": i, "text": pair["card_a"], "face": "A"})
        cards.append({"id": i * 2 + 1, "pair_id": i, "text": pair["card_b"], "face": "B"})

    random.shuffle(cards)
    st.session_state.mem_cards = cards
    st.session_state.mem_flipped = []
    st.session_state.mem_matched = set()
    st.session_state.mem_flip_count = 0
    st.session_state.mem_started = True
    st.session_state.mem_finished = False
    st.session_state.mem_start_time = time.time()
    st.session_state.mem_elapsed = 0
    st.session_state.mem_lock = False
    st.session_state.mem_pairs_count = num_pairs


def handle_card_click(card_idx: int) -> None:
    card = st.session_state.mem_cards[card_idx]
    card_id = card["id"]

    if st.session_state.mem_lock:
        return
    if card_id in st.session_state.mem_matched:
        return
    if card_id in st.session_state.mem_flipped:
        return
    if len(st.session_state.mem_flipped) >= 2:
        return

    st.session_state.mem_flipped.append(card_id)
    st.session_state.mem_flip_count += 1

    if len(st.session_state.mem_flipped) == 2:
        id1, id2 = st.session_state.mem_flipped
        card1 = next(c for c in st.session_state.mem_cards if c["id"] == id1)
        card2 = next(c for c in st.session_state.mem_cards if c["id"] == id2)

        if card1["pair_id"] == card2["pair_id"]:
            st.session_state.mem_matched.add(id1)
            st.session_state.mem_matched.add(id2)
            st.session_state.mem_flipped = []
            if len(st.session_state.mem_matched) == len(st.session_state.mem_cards):
                st.session_state.mem_finished = True
                st.session_state.mem_elapsed = int(time.time() - st.session_state.mem_start_time)
        else:
            st.session_state.mem_lock = True


def resolve_lock() -> None:
    if st.session_state.mem_lock and len(st.session_state.mem_flipped) == 2:
        st.session_state.mem_flipped = []
        st.session_state.mem_lock = False


def render_memory_game() -> None:
    initialize_memory_state()

    st.markdown(f"<h1 class='neon-title'>{_get_material_icon_html('grid_view')} Jogo da Memória SST</h1>", unsafe_allow_html=True)
    st.markdown("Encontre os pares de cartas relacionando siglas, EPIs e Normas Regulamentadoras!")

    st.markdown("""
    <style>
    .mem-card {
        display: flex;
        align-items: center;
        justify-content: center;
        min-height: 80px;
        padding: 8px;
        border-radius: 10px;
        font-size: 0.78em;
        font-weight: 600;
        text-align: center;
        cursor: pointer;
        transition: all 0.15s;
        line-height: 1.3;
        word-break: break-word;
        border: 2px solid transparent;
    }
    .mem-card-hidden {
        background: linear-gradient(135deg, rgba(74,222,128,0.1), rgba(34,211,238,0.1));
        border-color: rgba(74,222,128,0.2);
        color: #4ADE80;
    }
    .mem-card-flipped {
        background: rgba(34,211,238,0.15);
        border-color: #22D3EE;
        color: #E2E8F0;
    }
    .mem-card-matched {
        background: rgba(74,222,128,0.2);
        border-color: #4ADE80;
        color: #4ADE80;
        opacity: 0.7;
    }
    .mem-stats {
        display: flex;
        gap: 16px;
        align-items: center;
        margin-bottom: 12px;
    }
    .mem-stat {
        background: rgba(15,23,42,0.5);
        border: 1px solid rgba(74,222,128,0.15);
        border-radius: 8px;
        padding: 6px 14px;
        font-size: 0.85em;
        color: #94A3B8;
    }
    .mem-stat b { color: #4ADE80; }
    </style>
    """, unsafe_allow_html=True)

    if not st.session_state.mem_started:
        st.markdown("**Escolha a dificuldade:**")
        difficulty = st.selectbox(
            "Dificuldade",
            options=list(DIFFICULTY_CONFIG.keys()),
            key="mem_difficulty_select",
            label_visibility="collapsed"
        )
        num_pairs = DIFFICULTY_CONFIG[difficulty]
        st.info(f"O jogo terá **{num_pairs * 2} cartas** ({num_pairs} pares). Memorize a posição das cartas e encontre todos os pares!")
        if st.button("Iniciar Jogo da Memória", key="mem_start_btn", use_container_width=True):
            st.session_state.mem_difficulty = difficulty
            start_memory_game(num_pairs)
            st.rerun()
        return

    elapsed = st.session_state.mem_elapsed if st.session_state.mem_finished else int(time.time() - st.session_state.mem_start_time)
    mins = elapsed // 60
    secs = elapsed % 60
    matched_pairs = len(st.session_state.mem_matched) // 2
    total_pairs = st.session_state.mem_pairs_count

    st.markdown(f"""
    <div class='mem-stats'>
        <div class='mem-stat'>⏱ Tempo: <b>{mins:02d}:{secs:02d}</b></div>
        <div class='mem-stat'>🔄 Viradas: <b>{st.session_state.mem_flip_count}</b></div>
        <div class='mem-stat'>✅ Pares: <b>{matched_pairs}/{total_pairs}</b></div>
    </div>
    """, unsafe_allow_html=True)

    if st.session_state.mem_finished:
        st.success(f"🎉 Parabéns! Você encontrou todos os {total_pairs} pares em {mins:02d}:{secs:02d} com {st.session_state.mem_flip_count} viradas!")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Jogar Novamente (mesma dificuldade)", key="mem_replay_btn", use_container_width=True):
                start_memory_game(total_pairs)
                st.rerun()
        with col2:
            if st.button("Mudar Dificuldade", key="mem_change_diff_btn", use_container_width=True):
                st.session_state.mem_started = False
                st.rerun()
        return

    cards = st.session_state.mem_cards
    flipped_ids = set(st.session_state.mem_flipped)
    matched_ids = st.session_state.mem_matched

    num_cards = len(cards)
    cols_per_row = 6 if total_pairs <= 6 else (5 if total_pairs <= 10 else 6)

    for row_start in range(0, num_cards, cols_per_row):
        row_cards = cards[row_start:row_start + cols_per_row]
        cols = st.columns(len(row_cards))
        for ci, card in enumerate(row_cards):
            card_id = card["id"]
            with cols[ci]:
                is_matched = card_id in matched_ids
                is_flipped = card_id in flipped_ids
                is_lock = st.session_state.mem_lock

                if is_matched:
                    st.markdown(f"<div class='mem-card mem-card-matched'>{card['text']}</div>", unsafe_allow_html=True)
                elif is_flipped:
                    st.markdown(f"<div class='mem-card mem-card-flipped'>{card['text']}</div>", unsafe_allow_html=True)
                    if not is_lock and len(flipped_ids) < 2:
                        pass
                else:
                    card_idx = next(i for i, c in enumerate(cards) if c["id"] == card_id)
                    can_click = not is_lock and len(flipped_ids) < 2
                    if can_click:
                        if st.button("?", key=f"mem_card_{card_id}", use_container_width=True, help=f"Carta {card_id + 1}"):
                            handle_card_click(card_idx)
                            st.rerun()
                    else:
                        st.markdown("<div class='mem-card mem-card-hidden'>?</div>", unsafe_allow_html=True)

    if st.session_state.mem_lock:
        st.info("Cartas não combinam. Clique em 'Continuar' para virar de volta.")
        if st.button("Continuar", key="mem_continue_btn"):
            resolve_lock()
            st.rerun()
