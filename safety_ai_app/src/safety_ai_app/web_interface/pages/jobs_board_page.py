from __future__ import annotations

import streamlit as st
import logging
import os
import sys
from typing import List, Dict, Any, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from safety_ai_app.job_api_integrator import AdzunaJobIntegrator as AdzunaJobIntegratorType
from urllib.parse import urlparse
from datetime import datetime
import time
import json

logger = logging.getLogger(__name__)

script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(script_dir, '..', '..', '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

JOBS_PAGE_IMPORT_ERROR = None
AdzunaJobIntegrator = None
THEME = {"phrases": {}, "icons": {}}
_get_material_icon_html = lambda icon: f"<span>{icon}</span>"

try:
    from safety_ai_app.theme_config import THEME, _get_material_icon_html
    from safety_ai_app.web_interface.shared_styles import inject_glass_styles, glass_marker
    from safety_ai_app.security.rate_limiter import check_rate_limit, RateLimitExceeded
except ImportError as e:
    logger.warning(f"Não foi possível importar theme_config: {e}")
    inject_glass_styles = lambda: None
    glass_marker = lambda: ""
    check_rate_limit = lambda feature: None
    class RateLimitExceeded(Exception): pass
except Exception as e:
    logger.warning(f"Erro ao importar theme_config: {e}")
    inject_glass_styles = lambda: None
    glass_marker = lambda: ""
    check_rate_limit = lambda feature: None
    class RateLimitExceeded(Exception): pass

try:
    from safety_ai_app.job_api_integrator import AdzunaJobIntegrator
except ImportError as e:
    logger.warning(f"Não foi possível importar job_api_integrator: {e}")
    JOBS_PAGE_IMPORT_ERROR = str(e)
except ValueError as e:
    logger.warning(f"Credenciais da Adzuna API não configuradas: {e}")
    JOBS_PAGE_IMPORT_ERROR = str(e)
except Exception as e:
    logger.warning(f"Erro ao importar job_api_integrator: {e}")
    JOBS_PAGE_IMPORT_ERROR = str(e)

JOB_CATEGORIES: Dict[str, List[str]] = {
    "Segurança do Trabalho": [
        "Técnico em Segurança do Trabalho",
        "Supervisor de Segurança do Trabalho",
        "Coordenador de Segurança do Trabalho",
        "Engenheiro de Segurança do Trabalho",
        "Consultor de Segurança do Trabalho",
        "Auditor de Segurança do Trabalho"
    ],
    "Enfermagem": [
        "Técnico em Enfermagem",
        "Enfermeiro",
        "Enfermeiro do Trabalho",
        "Coordenador de Enfermagem"
    ],
    "Medicina": [
        "Médico do Trabalho"
    ]
}

BRAZILIAN_STATES_ABBR: List[str] = [
    "AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA", "MT", "MS",
    "MG", "PA", "PB", "PR", "PE", "PI", "RJ", "RN", "RS", "RO", "RR", "SC",
    "SP", "SE", "TO"
]

BRAZILIAN_STATES_FULL: Dict[str, str] = {
    "AC": "Acre", "AL": "Alagoas", "AP": "Amapá", "AM": "Amazonas", "BA": "Bahia",
    "CE": "Ceará", "DF": "Distrito Federal", "ES": "Espírito Santo", "GO": "Goiás",
    "MA": "Maranhão", "MT": "Mato Grosso", "MS": "Mato Grosso do Sul", "MG": "Minas Gerais",
    "PA": "Pará", "PB": "Paraíba", "PR": "Paraná", "PE": "Pernambuco", "PI": "Piauí",
    "RJ": "Rio de Janeiro", "RN": "Rio Grande do Norte", "RS": "Rio Grande do Sul",
    "RO": "Rondônia", "RR": "Roraima", "SC": "Santa Catarina", "SP": "São Paulo",
    "SE": "Sergipe", "TO": "Tocantins"
}

@st.cache_data
def load_brazilian_cities() -> Dict[str, List[str]]:
    cities_file_path = os.path.join(project_root, "data", "brazilian_cities.json")
    logger.info(f"Tentando carregar arquivo de cidades de: {cities_file_path}")
    if not os.path.exists(cities_file_path):
        logger.error(f"Arquivo de cidades NÃO encontrado em: {cities_file_path}. Por favor, execute 'python scripts/generate_cities_data.py'.")
        st.error("Erro: Arquivo de dados de cidades brasileiras não encontrado. Por favor, execute o script 'scripts/generate_cities_data.py' na pasta 'scripts/' do projeto para gerá-lo.")
        return {}
    
    try:
        with open(cities_file_path, "r", encoding="utf-8") as f:
            cities_data = json.load(f)
        logger.info(f"Arquivo de cidades carregado com sucesso. Total de estados no JSON: {len(cities_data)}")
        return cities_data
    except json.JSONDecodeError as e:
        logger.error(f"Erro ao decodificar JSON do arquivo de cidades {cities_file_path}: {e}")
        st.error(f"Erro ao ler o arquivo de cidades. Verifique se 'brazilian_cities.json' está formatado corretamente.")
        return {}
    except Exception as e:
        logger.error(f"Erro inesperado ao carregar o arquivo de cidades {cities_file_path}: {e}", exc_info=True)
        st.error(f"Erro inesperado ao carregar dados de cidades: {e}")
        return {}

BRAZILIAN_CITIES_BY_STATE: Dict[str, List[str]] = load_brazilian_cities()
logger.info(f"BRAZILIAN_CITIES_BY_STATE carregado. Contém {len(BRAZILIAN_CITIES_BY_STATE)} estados.")


@st.cache_resource
def get_adzuna_integrator_cached() -> Any:
    if AdzunaJobIntegrator is None:
        logger.warning("AdzunaJobIntegrator não disponível - módulo não importado")
        return None
    try:
        integrator = AdzunaJobIntegrator(require_credentials=False)
        if not integrator.is_configured:
            logger.info("Integrador Adzuna inicializado sem credenciais - funcionalidade limitada")
        return integrator
    except Exception as e:
        logger.error(f"Erro inesperado ao inicializar o integrador Adzuna: {e}", exc_info=True)
        return None

# --- Callbacks para gerenciar o estado da sessão ---
def _on_category_change_callback():
    """Callback para resetar a seleção de cargo quando a categoria muda."""
    logger.info(f"Callback: Categoria mudou para {st.session_state.job_category_select}. Resetando cargo.")
    st.session_state.selected_category_job_board = st.session_state.job_category_select
    st.session_state.selected_role_job_board = None # Reseta o cargo selecionado persistente
    st.session_state.job_role_select = None # Reseta o valor do widget de cargo

def _on_role_change_callback():
    """Callback para atualizar o cargo selecionado na session_state."""
    st.session_state.selected_role_job_board = st.session_state.job_role_select
    logger.info(f"Callback: Cargo atualizado para {st.session_state.selected_role_job_board}.")

def _on_state_change_callback():
    """Callback para quando o estado muda."""
    logger.info(f"Callback: Estado mudou para {st.session_state.job_state_single_select}. Resetando cidades.")
    st.session_state.selected_state_job_board = st.session_state.job_state_single_select if st.session_state.job_state_single_select != "" else None
    st.session_state.job_cities_multiselect = [] # Reseta o valor do widget de cidades diretamente

def render_page() -> None:
    page_title = THEME["phrases"]["jobs_board"]
    page_icon_html = _get_material_icon_html(THEME["icons"]["jobs_board"])

    inject_glass_styles()

    with st.container():
        st.markdown(glass_marker(), unsafe_allow_html=True)
        st.markdown(f'''
        <div class="page-header">
            {page_icon_html}
            <h1>{page_title}</h1>
        </div>
        <div class="page-subtitle">Encontre as últimas oportunidades na área de Saúde e Segurança do Trabalho!</div>
        ''', unsafe_allow_html=True)
    
    adzuna_integrator = get_adzuna_integrator_cached()
    if not adzuna_integrator or not adzuna_integrator.is_configured:
        st.markdown("""
        <div style="background: linear-gradient(135deg, rgba(34, 211, 238, 0.1), rgba(74, 222, 128, 0.1)); 
                    border: 1px solid rgba(74, 222, 128, 0.3); 
                    border-radius: 12px; 
                    padding: 24px; 
                    text-align: center;
                    margin: 20px 0;">
            <h3 style="color: #4ADE80; margin-bottom: 16px;">Busca de Vagas em Breve!</h3>
            <p style="color: #94a3b8; margin-bottom: 16px;">
                A funcionalidade de busca de vagas de emprego está temporariamente indisponível.
            </p>
            <p style="color: #64748b; font-size: 0.9em;">
                Para ativar esta funcionalidade, configure as credenciais da API Adzuna 
                (ADZUNA_APP_ID e ADZUNA_API_KEY) nas variáveis de ambiente do projeto.
            </p>
        </div>
        """, unsafe_allow_html=True)
        return

    # Inicializa session_state para os widgets se não existirem
    # Usamos selected_..._job_board para o estado persistente e job_..._select para o valor do widget
    if "selected_category_job_board" not in st.session_state:
        st.session_state.selected_category_job_board = list(JOB_CATEGORIES.keys())[0] if JOB_CATEGORIES else None
    if "selected_role_job_board" not in st.session_state:
        st.session_state.selected_role_job_board = None
    if "selected_state_job_board" not in st.session_state:
        st.session_state.selected_state_job_board = None
    if "job_cities_multiselect" not in st.session_state: # Usamos a key do widget diretamente para o multiselect
        st.session_state.job_cities_multiselect = []

    st.markdown(f'<div class="section-title">{_get_material_icon_html("search")} Busca de Vagas</div>', unsafe_allow_html=True)
    
    # --- Seletores de Categoria e Cargo (FORA DO FORM para reatividade imediata) ---
    col1, col2 = st.columns(2)
    with col1:
        current_category = st.session_state.selected_category_job_board or ""
        selected_category_index = list(JOB_CATEGORIES.keys()).index(current_category) if current_category in JOB_CATEGORIES else 0
        st.selectbox(
            "Selecione a Categoria:",
            list(JOB_CATEGORIES.keys()),
            key="job_category_select",
            on_change=_on_category_change_callback,
            index=selected_category_index
        )

    with col2:
        available_roles = JOB_CATEGORIES.get(current_category, []) if current_category else []
        
        default_role_index = None
        current_role = st.session_state.selected_role_job_board
        if current_role and current_role in available_roles:
            default_role_index = available_roles.index(current_role)
        elif available_roles:
            default_role_index = 0
        
        st.selectbox(
            "Selecione o Cargo:",
            available_roles,
            index=default_role_index,
            disabled=not bool(available_roles),
            key="job_role_select",
            on_change=_on_role_change_callback
        )
        
        # Sincroniza selected_role_job_board com o valor padrão do selectbox se ainda for None
        # ou se o valor atual do selectbox (via key) for diferente do persistente
        if st.session_state.selected_role_job_board is None and st.session_state.job_role_select is not None:
            st.session_state.selected_role_job_board = st.session_state.job_role_select
            logger.info(f"DEBUG: Cargo padrão sincronizado para: {st.session_state.selected_role_job_board}")
        elif st.session_state.job_role_select != st.session_state.selected_role_job_board:
            # Isso pode acontecer se o usuário mudar a categoria, o cargo é resetado para None,
            # mas o selectbox já tem um valor padrão. Sincronizamos.
            st.session_state.selected_role_job_board = st.session_state.job_role_select
            logger.info(f"DEBUG: Cargo sincronizado após rerun para: {st.session_state.selected_role_job_board}")


    logger.info(f"DEBUG: Categoria selecionada (session_state): {st.session_state.selected_category_job_board}")
    logger.info(f"DEBUG: Cargo selecionado (session_state): {st.session_state.selected_role_job_board}")

    st.markdown(f'<div class="section-title">{_get_material_icon_html("location")} Localização</div>', unsafe_allow_html=True)
    col_state, col_cities = st.columns(2)
    with col_state:
        current_state = st.session_state.selected_state_job_board or ""
        selected_state_index = ([""] + BRAZILIAN_STATES_ABBR).index(current_state) if current_state in ([""] + BRAZILIAN_STATES_ABBR) else 0
        st.selectbox(
            "Selecione o Estado (Opcional):",
            [""] + BRAZILIAN_STATES_ABBR,
            key="job_state_single_select",
            on_change=_on_state_change_callback,
            index=selected_state_index
        )

    with col_cities:
        available_cities_for_selection = []
        if st.session_state.selected_state_job_board:
            available_cities_for_selection.extend(BRAZILIAN_CITIES_BY_STATE.get(st.session_state.selected_state_job_board, []))
            available_cities_for_selection = sorted(list(set(available_cities_for_selection)))
        
        st.multiselect(
            "Selecione a(s) Cidade(s) (Até 5):",
            available_cities_for_selection,
            # REMOVIDO: default=st.session_state.job_cities_multiselect para evitar a warning
            disabled=not bool(st.session_state.selected_state_job_board),
            max_selections=5,
            key="job_cities_multiselect" # O valor é gerenciado por esta key
        )

    logger.info(f"DEBUG: Estado selecionado (session_state): {st.session_state.selected_state_job_board}")
    logger.info(f"DEBUG: Cidades selecionadas (session_state): {st.session_state.job_cities_multiselect}") # Usa a key diretamente

    # --- Formulário de Busca (APENAS o botão de submissão) ---
    with st.form("job_search_submit_form"):
        search_button = st.form_submit_button("Buscar Vagas", type="primary")

    if search_button:
        search_term = st.session_state.selected_role_job_board # Usa o cargo persistente
        
        if not search_term:
            st.warning("Por favor, selecione um cargo para buscar.")
            return

        locations_to_search = []
        display_location_texts = []

        if st.session_state.job_cities_multiselect: # Usa o valor da key diretamente
            locations_to_search.extend(st.session_state.job_cities_multiselect)
            display_location_texts.extend(st.session_state.job_cities_multiselect)
        elif st.session_state.selected_state_job_board:
            full_state_name = BRAZILIAN_STATES_FULL.get(st.session_state.selected_state_job_board, st.session_state.selected_state_job_board)
            locations_to_search.append(full_state_name)
            display_location_texts.append(full_state_name)
        else:
            locations_to_search.append(None)
            display_location_texts.append("todo o Brasil")

        unique_locations_to_search = []
        unique_display_location_texts = []
        seen_locations = set()

        for loc_item in locations_to_search:
            if loc_item is None:
                loc_key = "todo o brasil"
            else:
                loc_key = str(loc_item).lower()
            
            if loc_key not in seen_locations:
                unique_locations_to_search.append(loc_item)
                if loc_item is None:
                    unique_display_location_texts.append("todo o Brasil")
                else:
                    unique_display_location_texts.append(str(loc_item))
                seen_locations.add(loc_key)

        final_display_location_text = ", ".join(sorted(list(set(unique_display_location_texts))))
        if not final_display_location_text:
            final_display_location_text = "todo o Brasil"

        is_full_time = False
        is_part_time = False
        is_contract = False
        is_permanent = False

        try:
            check_rate_limit("adzuna_api")
        except RateLimitExceeded:
            try:
                from safety_ai_app.security.security_logger import log_security_event, SecurityEvent
                log_security_event(
                    SecurityEvent.RATE_LIMIT_EXCEEDED,
                    feature="adzuna_api",
                    extra={"search_term": str(search_term)[:50]},
                )
            except Exception as log_err:
                logger.warning(f"Falha ao registrar rate-limit (Adzuna): {log_err}")
            st.markdown('''
            <div class="info-hint" style="background:rgba(245,158,11,0.1);border-color:rgba(245,158,11,0.3);color:#F59E0B;">
                <b>Limite atingido:</b> Muitas buscas em pouco tempo. Aguarde alguns segundos e tente novamente.
            </div>
            ''', unsafe_allow_html=True)
            return

        all_jobs: List[Dict[str, Any]] = []
        job_ids: set[str] = set()

        progress_bar = st.progress(0)
        status_text = st.empty()

        for i, location_param in enumerate(unique_locations_to_search):
            current_location_display = unique_display_location_texts[i] if i < len(unique_locations_to_search) else "localização desconhecida"
            status_text.text(f"Buscando vagas para '{search_term}' em '{current_location_display}' ({i+1}/{len(unique_locations_to_search)})...")
            
            jobs_from_api = adzuna_integrator.search_jobs(
                what=search_term,
                where=location_param,
                max_days_old=30,
                results_per_page=50,
                salary_min=None,
                salary_max=None,
                is_full_time=is_full_time,
                is_part_time=is_part_time,
                is_contract=is_contract,
                is_permanent=is_permanent
            )
            
            for job in jobs_from_api:
                job_id = job.get("id")
                if job_id and job_id not in job_ids:
                    all_jobs.append(job)
                    job_ids.add(job_id)
            
            progress_bar.progress((i + 1) / len(unique_locations_to_search))
            time.sleep(0.1)

        status_text.empty()
        progress_bar.empty()

        if all_jobs:
            st.markdown(f'<div class="section-title">{_get_material_icon_html("search")} Vagas encontradas para "{search_term}" em "{final_display_location_text}"</div>', unsafe_allow_html=True)
            for job in all_jobs:
                title = job.get("title", "Título não disponível")
                company = job.get("company", {}).get("display_name", "Empresa não disponível")
                location = job.get("location", {}).get("display_name", "Localização não disponível")
                description = job.get("description", "Descrição não disponível")
                redirect_url = job.get("redirect_url", "#")
                created_date_str = job.get("created")
                salary_min_job = job.get("salary_min")
                salary_max_job = job.get("salary_max")
                contract_type_job = job.get("contract_type", "Não especificado")
                category_label = job.get("category", {}).get("label", "Não especificada")

                source_website = "Não disponível"
                if redirect_url and redirect_url != "#":
                    try:
                        parsed_url = urlparse(redirect_url)
                        source_website = parsed_url.netloc.replace("www.", "")
                    except Exception:
                        pass

                formatted_date = "Não disponível"
                if created_date_str:
                    try:
                        dt_object = datetime.fromisoformat(created_date_str.replace('Z', '+00:00'))
                        formatted_date = dt_object.strftime("%d/%m/%Y %H:%M")
                    except ValueError:
                        pass

                salary_info = "Não especificado"
                # CORRIGIDO: Removido o escape '\' do '$' em todas as instâncias
                if salary_min_job and salary_max_job:
                    salary_info = f"R$ {salary_min_job:,.2f} - R$ {salary_max_job:,.2f}"
                elif salary_min_job:
                    salary_info = f"A partir de R$ {salary_min_job:,.2f}"
                elif salary_max_job:
                    salary_info = f"Até R$ {salary_max_job:,.2f}"

                short_description = description[:200] + "..." if len(description) > 200 else description

                st.markdown(f"""
                <div class="job-card">
                    <h3>{title}</h3>
                    <p><strong>Empresa:</strong> {company}</p>
                    <p><strong>Local:</strong> {location}</p>
                    <p><strong>Salário:</strong> {salary_info}</p>
                    <p><strong>Tipo de Contrato:</strong> {contract_type_job.replace('_', ' ').title()}</p>
                    <p><strong>Categoria:</strong> {category_label}</p>
                    <p><strong>Publicado em:</strong> {formatted_date}</p>
                    <p><strong>Fonte:</strong> {source_website}</p>
                    <p>{short_description}</p>
                    <a href="{redirect_url}"  class="job-link-button">Ver Vaga {_get_material_icon_html(THEME['icons']['external_link'])}</a>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info(f"Nenhuma vaga encontrada para '{search_term}' em '{final_display_location_text}' nos últimos 30 dias com os filtros selecionados.")

    st.markdown("""
    <style>
    .job-card {
        background-color: #161b22;
        border-radius: 8px;
        padding: 20px;
        margin-bottom: 15px;
        box-shadow: 0 4px 8px rgba(0, 0, 0, 0.2);
        border: 1px solid #27ae60;
    }
    .job-card h3 {
        color: #27ae60;
        margin-top: 0;
        margin-bottom: 10px;
    }
    .job-card p {
        color: #c9d1d9;
        margin-bottom: 5px;
    }
    .job-link-button {
        display: inline-flex;
        align-items: center;
        background-color: #27ae60;
        color: white !important;
        padding: 8px 15px;
        border-radius: 5px;
        text-decoration: none;
        font-weight: bold;
        transition: background-color 0.3s ease;
    }
    .job-link-button:hover {
        background-color: #39d353;
        color: white !important;
    }
    .job-link-button .material-symbols-outlined {
        margin-left: 8px;
        font-size: 1em;
    }
    </style>
    """, unsafe_allow_html=True)
