import streamlit as st
import json
import os
import random
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

try:
    from safety_ai_app.theme_config import _get_material_icon_html, THEME
except ImportError:
    _get_material_icon_html = lambda icon: f"<span>{icon}</span>"
    THEME = {"phrases": {}, "icons": {}, "colors": {"accent_green": "#4ADE80"}}

SCRIPT_DIR = os.path.dirname(__file__)
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, '..', '..', '..', '..', '..'))
SCENARIOS_PATH = os.path.join(PROJECT_ROOT, 'data', 'games', 'accident_scenarios.json')

ALL_NRS = [
    "NR-01", "NR-04", "NR-05", "NR-06", "NR-07", "NR-10",
    "NR-12", "NR-13", "NR-15", "NR-16", "NR-17", "NR-18",
    "NR-23", "NR-26", "NR-33", "NR-35",
]

ALL_EPIS = [
    "Capacete", "Luva de raspa", "Luva nitrílica", "Luva dielétrica", "Luva de malha de aço",
    "Luva térmica de alta temperatura", "Cinto paraquedista", "Talabarte", "Óculos de segurança",
    "Óculos de solda", "Protetor auditivo", "Máscara respiratória", "Máscara de solda com filtro P3",
    "Máscara autônoma (SCBA)", "Máscara de fuga", "Bota de segurança", "Bota de borracha",
    "Botina dielétrica", "Avental de raspa", "Avental de couro", "Avental impermeável",
    "Protetor facial (visor)", "Colete refletivo", "Colete salva-vidas tipo resgate",
    "Capacete classe B", "Munhequeira de suporte", "Apoio de pulso", "Rádio comunicador",
    "Detector de gases", "Cinto de resgate",
]


def load_scenarios() -> List[Dict[str, Any]]:
    try:
        from safety_ai_app.google_drive_integrator import download_game_json_from_drive
        drive_data = download_game_json_from_drive("accident_scenarios.json")
        if drive_data:
            logger.info(f"Accident investigation: loaded {len(drive_data)} scenarios from Drive.")
            return drive_data
    except Exception as e:
        logger.warning(f"Accident investigation Drive load failed, using local: {e}")

    try:
        with open(SCENARIOS_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Erro ao carregar cenários: {e}")
        return []


def initialize_accident_state() -> None:
    if "acc_scenarios_pool" not in st.session_state:
        st.session_state.acc_scenarios_pool = load_scenarios()
    if "acc_started" not in st.session_state:
        st.session_state.acc_started = False
    if "acc_current_scenario" not in st.session_state:
        st.session_state.acc_current_scenario = None
    if "acc_submitted" not in st.session_state:
        st.session_state.acc_submitted = False
    if "acc_session_score" not in st.session_state:
        st.session_state.acc_session_score = 0
    if "acc_session_rounds" not in st.session_state:
        st.session_state.acc_session_rounds = 0
    if "acc_played_ids" not in st.session_state:
        st.session_state.acc_played_ids = []
    if "acc_nr_selections" not in st.session_state:
        st.session_state.acc_nr_selections = {}
    if "acc_epi_selections" not in st.session_state:
        st.session_state.acc_epi_selections = {}
    if "acc_nr_distractors" not in st.session_state:
        st.session_state.acc_nr_distractors = []
    if "acc_epi_distractors" not in st.session_state:
        st.session_state.acc_epi_distractors = []


def start_new_round() -> None:
    pool = st.session_state.acc_scenarios_pool
    if not pool:
        return
    remaining = [s for s in pool if s["id"] not in st.session_state.acc_played_ids]
    if not remaining:
        st.session_state.acc_played_ids = []
        remaining = pool

    scenario = random.choice(remaining)
    st.session_state.acc_current_scenario = scenario
    st.session_state.acc_played_ids.append(scenario["id"])
    st.session_state.acc_submitted = False

    correct_nrs = set(scenario["violated_nrs"])
    distractor_nrs = random.sample([n for n in ALL_NRS if n not in correct_nrs], min(4, len(ALL_NRS) - len(correct_nrs)))
    all_nrs_displayed = list(correct_nrs) + distractor_nrs
    random.shuffle(all_nrs_displayed)
    st.session_state.acc_nr_distractors = all_nrs_displayed
    st.session_state.acc_nr_selections = {nr: False for nr in all_nrs_displayed}

    correct_epis = set(scenario["missing_epis"])
    distractor_epis = random.sample([e for e in ALL_EPIS if e not in correct_epis], min(6, len(ALL_EPIS) - len(correct_epis)))
    all_epis_displayed = list(correct_epis) + distractor_epis
    random.shuffle(all_epis_displayed)
    st.session_state.acc_epi_distractors = all_epis_displayed
    st.session_state.acc_epi_selections = {epi: False for epi in all_epis_displayed}
    st.session_state.acc_started = True


def calculate_round_score(scenario: Dict[str, Any]) -> int:
    correct_nrs = set(scenario["violated_nrs"])
    correct_epis = set(scenario["missing_epis"])
    selected_nrs = {k for k, v in st.session_state.acc_nr_selections.items() if v}
    selected_epis = {k for k, v in st.session_state.acc_epi_selections.items() if v}

    nr_hits = len(correct_nrs & selected_nrs)
    nr_false = len(selected_nrs - correct_nrs)
    epi_hits = len(correct_epis & selected_epis)
    epi_false = len(selected_epis - correct_epis)

    score = max(0, nr_hits * 10 - nr_false * 5 + epi_hits * 10 - epi_false * 5)
    return score


def render_accident_investigation_game() -> None:
    initialize_accident_state()

    st.markdown(f"<h1 class='neon-title'>{_get_material_icon_html('search')} Investigação de Acidente</h1>", unsafe_allow_html=True)
    st.markdown("Analise o cenário de acidente e identifique quais NRs foram violadas e quais EPIs estavam faltando.")

    st.markdown("""
    <style>
    .acc-scenario-box {
        background: rgba(15,23,42,0.6);
        border: 1px solid rgba(74,222,128,0.2);
        border-radius: 12px;
        padding: 20px;
        margin: 12px 0;
        font-size: 0.95em;
        line-height: 1.7;
        color: #CBD5E1;
    }
    .acc-scenario-title {
        color: #F97316;
        font-size: 1.1em;
        font-weight: 700;
        margin-bottom: 10px;
    }
    .acc-score-box {
        background: rgba(15,23,42,0.5);
        border: 1px solid rgba(74,222,128,0.15);
        border-radius: 8px;
        padding: 8px 16px;
        font-size: 0.85em;
        color: #94A3B8;
        margin-bottom: 12px;
        display: inline-block;
    }
    .acc-score-box b { color: #4ADE80; }
    .acc-correct { color: #4ADE80; font-weight: 600; }
    .acc-wrong { color: #F87171; font-weight: 600; }
    .acc-missed { color: #F97316; font-weight: 600; }
    .acc-explanation {
        background: rgba(15,23,42,0.4);
        border-left: 3px solid #22D3EE;
        padding: 8px 12px;
        margin: 4px 0;
        border-radius: 0 8px 8px 0;
        font-size: 0.85em;
        color: #94A3B8;
    }
    </style>
    """, unsafe_allow_html=True)

    if st.session_state.acc_session_rounds > 0:
        st.markdown(f"""
        <div class='acc-score-box'>
            Rodadas: <b>{st.session_state.acc_session_rounds}</b> &nbsp;|&nbsp;
            Pontuação total: <b>{st.session_state.acc_session_score}</b>
        </div>
        """, unsafe_allow_html=True)

    if not st.session_state.acc_started:
        st.info("Você verá o relato de um acidente de trabalho. Marque as NRs violadas e os EPIs que estavam faltando.")
        pool = st.session_state.acc_scenarios_pool
        if not pool:
            st.error("Não foi possível carregar os cenários de acidentes.")
            return
        if st.button("Iniciar Investigação", key="acc_start_btn", use_container_width=True):
            start_new_round()
            st.rerun()
        return

    scenario = st.session_state.acc_current_scenario
    if not scenario:
        st.error("Nenhum cenário carregado.")
        return

    st.markdown(f"""
    <div class='acc-scenario-box'>
        <div class='acc-scenario-title'>📋 {scenario['title']}</div>
        {scenario['description']}
    </div>
    """, unsafe_allow_html=True)

    if not st.session_state.acc_submitted:
        col_nr, col_epi = st.columns(2)

        with col_nr:
            st.markdown("**Quais NRs foram violadas?**")
            for nr in st.session_state.acc_nr_distractors:
                val = st.checkbox(nr, key=f"acc_nr_{nr}_{scenario['id']}", value=st.session_state.acc_nr_selections.get(nr, False))
                st.session_state.acc_nr_selections[nr] = val

        with col_epi:
            st.markdown("**Quais EPIs estavam faltando?**")
            for epi in st.session_state.acc_epi_distractors:
                val = st.checkbox(epi, key=f"acc_epi_{epi}_{scenario['id']}", value=st.session_state.acc_epi_selections.get(epi, False))
                st.session_state.acc_epi_selections[epi] = val

        if st.button("Submeter Análise", key="acc_submit_btn", use_container_width=True):
            score = calculate_round_score(scenario)
            st.session_state.acc_session_score += score
            st.session_state.acc_session_rounds += 1
            st.session_state.acc_submitted = True
            st.rerun()

    else:
        correct_nrs = set(scenario["violated_nrs"])
        correct_epis = set(scenario["missing_epis"])
        selected_nrs = {k for k, v in st.session_state.acc_nr_selections.items() if v}
        selected_epis = {k for k, v in st.session_state.acc_epi_selections.items() if v}
        round_score = calculate_round_score(scenario)

        st.markdown(f"<h3>Resultado: <span style='color:#4ADE80;'>+{round_score} pontos</span></h3>", unsafe_allow_html=True)

        col_nr_res, col_epi_res = st.columns(2)

        with col_nr_res:
            st.markdown("**NRs Violadas:**")
            for nr in correct_nrs:
                if nr in selected_nrs:
                    st.markdown(f"<div class='acc-correct'>✅ {nr} — Correto!</div>", unsafe_allow_html=True)
                else:
                    st.markdown(f"<div class='acc-missed'>⚠️ {nr} — Você não marcou!</div>", unsafe_allow_html=True)
                explanation = scenario["explanations"].get(nr, "")
                if explanation:
                    st.markdown(f"<div class='acc-explanation'>{explanation}</div>", unsafe_allow_html=True)
            for nr in selected_nrs - correct_nrs:
                st.markdown(f"<div class='acc-wrong'>❌ {nr} — Não violada neste caso</div>", unsafe_allow_html=True)

        with col_epi_res:
            st.markdown("**EPIs Faltantes:**")
            for epi in correct_epis:
                if epi in selected_epis:
                    st.markdown(f"<div class='acc-correct'>✅ {epi} — Correto!</div>", unsafe_allow_html=True)
                else:
                    st.markdown(f"<div class='acc-missed'>⚠️ {epi} — Você não marcou!</div>", unsafe_allow_html=True)
                explanation = scenario["explanations"].get(epi, "")
                if explanation:
                    st.markdown(f"<div class='acc-explanation'>{explanation}</div>", unsafe_allow_html=True)
            for epi in selected_epis - correct_epis:
                st.markdown(f"<div class='acc-wrong'>❌ {epi} — Não se aplica a este caso</div>", unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("Próximo Cenário", key="acc_next_btn", use_container_width=True):
            start_new_round()
            st.rerun()
