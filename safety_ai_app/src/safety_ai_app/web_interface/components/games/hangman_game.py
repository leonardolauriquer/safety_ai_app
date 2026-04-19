import streamlit as st
import json
import os
import random
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

try:
    from safety_ai_app.theme_config import _get_material_icon_html, THEME
except ImportError:
    _get_material_icon_html = lambda icon: f"<span>{icon}</span>"
    THEME = {"phrases": {}, "icons": {}, "colors": {"accent_green": "#4ADE80"}}

SCRIPT_DIR = os.path.dirname(__file__)
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, '..', '..', '..', '..', '..'))
HANGMAN_WORDS_PATH = os.path.join(PROJECT_ROOT, 'data', 'games', 'hangman_words.json')

HANGMAN_STAGES = [
    "```\n  +---+\n  |   |\n      |\n      |\n      |\n      |\n=========\n```",
    "```\n  +---+\n  |   |\n  O   |\n      |\n      |\n      |\n=========\n```",
    "```\n  +---+\n  |   |\n  O   |\n  |   |\n      |\n      |\n=========\n```",
    "```\n  +---+\n  |   |\n  O   |\n /|   |\n      |\n      |\n=========\n```",
    "```\n  +---+\n  |   |\n  O   |\n /|\\  |\n      |\n      |\n=========\n```",
    "```\n  +---+\n  |   |\n  O   |\n /|\\  |\n /    |\n      |\n=========\n```",
    "```\n  +---+\n  |   |\n  O   |\n /|\\  |\n / \\  |\n      |\n=========\n```",
]

MAX_WRONG_GUESSES = 6


def load_hangman_words() -> List[Dict[str, Any]]:
    try:
        from safety_ai_app.google_drive_integrator import download_game_json_from_drive
        drive_data = download_game_json_from_drive("hangman_words.json")
        if drive_data:
            logger.info(f"Hangman: loaded {len(drive_data)} words from Drive.")
            return drive_data
    except Exception as e:
        logger.warning(f"Hangman Drive load failed, using local: {e}")

    try:
        with open(HANGMAN_WORDS_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Hangman: local load failed: {e}")
        return [
            {"term": "CAPACETE", "definition": "EPI de proteção da cabeça contra impactos e queda de objetos.", "nr": "NR-06"},
            {"term": "CIPA", "definition": "Comissão Interna de Prevenção de Acidentes.", "nr": "NR-05"},
            {"term": "EPI", "definition": "Equipamento de Proteção Individual.", "nr": "NR-06"},
        ]


def initialize_hangman_state() -> None:
    if "hangman_words_pool" not in st.session_state:
        st.session_state.hangman_words_pool = load_hangman_words()
    if "hangman_started" not in st.session_state:
        st.session_state.hangman_started = False
    if "hangman_finished" not in st.session_state:
        st.session_state.hangman_finished = False
    if "hangman_won" not in st.session_state:
        st.session_state.hangman_won = False
    if "hangman_word_entry" not in st.session_state:
        st.session_state.hangman_word_entry = None
    if "hangman_guessed_letters" not in st.session_state:
        st.session_state.hangman_guessed_letters = set()
    if "hangman_wrong_guesses" not in st.session_state:
        st.session_state.hangman_wrong_guesses = 0
    if "hangman_session_wins" not in st.session_state:
        st.session_state.hangman_session_wins = 0
    if "hangman_session_losses" not in st.session_state:
        st.session_state.hangman_session_losses = 0


def start_hangman_game() -> None:
    words = st.session_state.hangman_words_pool
    if not words:
        st.error("Nenhuma palavra disponível para o jogo.")
        return
    st.session_state.hangman_word_entry = random.choice(words)
    st.session_state.hangman_guessed_letters = set()
    st.session_state.hangman_wrong_guesses = 0
    st.session_state.hangman_started = True
    st.session_state.hangman_finished = False
    st.session_state.hangman_won = False


def guess_letter(letter: str) -> None:
    letter = letter.upper()
    if letter in st.session_state.hangman_guessed_letters:
        return
    st.session_state.hangman_guessed_letters.add(letter)
    word_alpha = ''.join(c for c in st.session_state.hangman_word_entry["term"].upper() if c.isalpha())
    if letter not in word_alpha:
        st.session_state.hangman_wrong_guesses += 1

    revealed = all(
        not c.isalpha() or c in st.session_state.hangman_guessed_letters
        for c in st.session_state.hangman_word_entry["term"].upper()
    )
    if revealed:
        st.session_state.hangman_won = True
        st.session_state.hangman_finished = True
        st.session_state.hangman_session_wins += 1
    elif st.session_state.hangman_wrong_guesses >= MAX_WRONG_GUESSES:
        st.session_state.hangman_won = False
        st.session_state.hangman_finished = True
        st.session_state.hangman_session_losses += 1


def get_display_word(term: str, guessed: set) -> str:
    result = []
    for ch in term.upper():
        if not ch.isalpha():
            # Auto-reveal digits, hyphens, spaces, and other non-letter chars
            result.append(ch)
        elif ch in guessed:
            result.append(ch)
        else:
            result.append('_')
    return ' '.join(result)


def render_hangman_game() -> None:
    initialize_hangman_state()

    st.markdown(f"<h1 class='neon-title'>{_get_material_icon_html('sports_esports')} Jogo da Forca SST</h1>", unsafe_allow_html=True)
    st.markdown("Descubra o termo de Saúde e Segurança do Trabalho letra por letra antes que o boneco seja completado!")

    st.markdown(f"""
    <style>
    .hangman-display {{
        font-family: monospace;
        font-size: 0.95em;
        color: #4ADE80;
        background: rgba(15,23,42,0.5);
        border: 1px solid rgba(74,222,128,0.15);
        border-radius: 10px;
        padding: 12px 20px;
        display: inline-block;
        white-space: pre;
    }}
    .hangman-word {{
        font-size: 2em;
        font-weight: 700;
        letter-spacing: 0.3em;
        color: #E2E8F0;
        margin: 16px 0;
        text-align: center;
    }}
    .hangman-score-box {{
        background: rgba(15,23,42,0.5);
        border: 1px solid rgba(74,222,128,0.15);
        border-radius: 8px;
        padding: 8px 16px;
        font-size: 0.85em;
        color: #94A3B8;
        margin-bottom: 12px;
    }}
    .hangman-score-box b {{ color: #4ADE80; }}
    </style>
    """, unsafe_allow_html=True)

    st.markdown(f"""
    <div class='hangman-score-box'>
        Vitórias na sessão: <b>{st.session_state.hangman_session_wins}</b> &nbsp;|&nbsp;
        Derrotas na sessão: <b>{st.session_state.hangman_session_losses}</b>
    </div>
    """, unsafe_allow_html=True)

    if not st.session_state.hangman_started:
        st.info("Clique em 'Iniciar Jogo' para revelar a primeira palavra oculta.")
        if st.button("Iniciar Jogo", key="hangman_start_btn", use_container_width=True):
            start_hangman_game()
            st.rerun()
        return

    entry = st.session_state.hangman_word_entry
    wrong = st.session_state.hangman_wrong_guesses
    guessed = st.session_state.hangman_guessed_letters

    col_fig, col_word = st.columns([1, 2])

    with col_fig:
        stage_index = min(wrong, len(HANGMAN_STAGES) - 1)
        st.markdown(f"<div class='hangman-display'>{HANGMAN_STAGES[stage_index]}</div>", unsafe_allow_html=True)
        st.markdown(f"<div style='text-align:center; color:#F97316; font-size:0.9em; margin-top:6px;'>Erros: {wrong} / {MAX_WRONG_GUESSES}</div>", unsafe_allow_html=True)

    with col_word:
        display = get_display_word(entry["term"], guessed)
        st.markdown(f"<div class='hangman-word'>{display}</div>", unsafe_allow_html=True)
        st.markdown(f"<div style='color:#64748B; font-size:0.8em; text-align:center;'>NR relacionada: <b style='color:#22D3EE;'>{entry['nr']}</b></div>", unsafe_allow_html=True)

        if st.session_state.hangman_finished:
            if st.session_state.hangman_won:
                st.success(f"Parabéns! Você acertou: **{entry['term']}**")
            else:
                st.error(f"Que pena! A palavra era: **{entry['term']}**")
            st.info(f"**Definição:** {entry['definition']}")
            if st.button("Jogar Novamente", key="hangman_play_again", use_container_width=True):
                start_hangman_game()
                st.rerun()
            return

    if not st.session_state.hangman_finished:
        st.markdown("**Escolha uma letra:**")
        alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        rows = [alphabet[i:i+9] for i in range(0, len(alphabet), 9)]
        for row in rows:
            cols = st.columns(len(row))
            for i, letter in enumerate(row):
                with cols[i]:
                    already_guessed = letter in guessed
                    if already_guessed:
                        word_clean = entry["term"].upper().replace("-", "").replace(" ", "")
                        color = "#4ADE80" if letter in word_clean else "#F87171"
                        st.markdown(f"<div style='text-align:center; font-size:1em; font-weight:700; color:{color}; opacity:0.6; padding:6px;'>{letter}</div>", unsafe_allow_html=True)
                    else:
                        if st.button(letter, key=f"hangman_letter_{letter}"):
                            guess_letter(letter)
                            st.rerun()
