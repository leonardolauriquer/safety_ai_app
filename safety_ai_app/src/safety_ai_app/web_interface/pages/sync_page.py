import streamlit as st
import logging
import threading
import time
from datetime import datetime
from typing import Any, Dict, List
from queue import Queue, Empty
import os

# Importa a biblioteca para auto-refresh
from streamlit_autorefresh import st_autorefresh

from safety_ai_app.google_drive_integrator import (
    synchronize_app_central_library_to_chroma,
    # REMOVIDO: get_processable_drive_files_in_folder, # Não é mais necessário importar diretamente aqui
    get_service_account_drive_integrator_instance # NOVO IMPORT
)
from safety_ai_app.theme_config import _get_material_icon_html, THEME
from safety_ai_app.nr_rag_qa import NRQuestionAnswering
# REMOVIDO: from safety_ai_app.google_drive_integrator import OUR_DRIVE_CENTRAL_LIBRARY_FOLDER_ID

logger = logging.getLogger(__name__)

# --- Funções Auxiliares para o Thread ---
def _check_pending_files_async(integrator: Any, qa_system: NRQuestionAnswering, result_queue: Queue): # Argumentos modificados
    """
    Função executada em um thread para verificar arquivos pendentes.
    Comunica o resultado via result_queue.
    """
    try:
        # Obtém o ID da pasta usando o método interno da instância do integrador
        central_library_folder_id = integrator._get_ai_chat_sync_folder_id()
        if not central_library_folder_id:
            result_queue.put({'type': 'check_complete', 'pending_count': 0, 'success': False, 'error_message': "ID da pasta 'Base de dados IA' não encontrada.", 'timestamp': datetime.now()})
            return

        # Usa o método da instância do integrador para listar arquivos
        all_processable_files = integrator.get_processable_drive_files_in_folder(central_library_folder_id)

        if not all_processable_files:
            result_queue.put({'type': 'check_complete', 'pending_count': 0, 'success': True, 'timestamp': datetime.now()})
            return

        existing_drive_file_ids = qa_system.get_drive_file_ids_in_chroma(source_type="app_central_library_sync")
        
        pending_files = [f for f in all_processable_files if f['id'] not in existing_drive_file_ids]
        pending_count = len(pending_files)

        result_queue.put({'type': 'check_complete', 'pending_count': pending_count, 'success': True, 'timestamp': datetime.now()})

    except Exception as e:
        logger.error(f"Check Thread: Erro na verificação de arquivos pendentes: {e}", exc_info=True)
        result_queue.put({'type': 'check_complete', 'pending_count': 0, 'success': False, 'error_message': str(e), 'timestamp': datetime.now()})

def _run_sync_in_thread(app_drive_service: Any, qa_system: Any, result_queue: Queue):
    """
    Função executada em um thread para realizar a sincronização completa.
    Comunica o progresso e o resultado final via result_queue.
    """
    thread_id = threading.current_thread().ident
    try:
        def queue_progress_callback(processed: int, total: int, current_doc_name: str):
            result_queue.put({
                'type': 'sync_progress',
                'processed': processed,
                'total': total,
                'current_doc': current_doc_name,
                'timestamp': time.time()
            })

        # A função synchronize_app_central_library_to_chroma em google_drive_integrator.py
        # já chama self._get_ai_chat_sync_folder_id() internamente.
        # Então, basta passar o serviço bruto do drive (que é o serviço da conta de serviço)
        # e a instância do qa_system.
        processed_count = synchronize_app_central_library_to_chroma(
            app_drive_service, 
            qa_system,
            progress_callback=queue_progress_callback
        )

        total_files_to_process = st.session_state.sync_status_data.get('total_count', processed_count)

        result_queue.put({
            'type': 'sync_complete',
            'success': True,
            'message': f"Sincronização concluída! {processed_count} documentos processados." if processed_count > 0 else "Sincronização concluída - Nenhum documento novo encontrado.",
            'processed_count': processed_count,
            'total_count': total_files_to_process,
            'timestamp': datetime.now()
        })

    except Exception as e:
        logger.error(f"Sync Thread: Erro na sincronização (ID: {thread_id}): {e}", exc_info=True)
        result_queue.put({
            'type': 'sync_complete',
            'success': False,
            'message': f"Erro na sincronização: {str(e)}",
            'processed_count': 0,
            'total_count': 0,
            'error_message': str(e),
            'timestamp': datetime.now()
        })

# --- Funções de Gerenciamento de Estado ---
def _initialize_sync_status_data():
    """Inicializa ou reseta o dicionário de estado da sincronização."""
    if "sync_status_data" not in st.session_state:
        st.session_state.sync_status_data = {}

    # Define valores padrão se não existirem ou se for um reset
    default_status = {
        "check_performed": False,
        "check_in_progress": False,
        "pending_files_count": 0,
        "in_progress": False,
        "finished": False,
        "success": False,
        "message": "Sincronização não iniciada.",
        "processed_count": 0,
        "total_count": 0,
        "current_doc_name": "",
        "last_check_time": None,
        "sync_thread": None,
        "sync_thread_id": None,
    }
    for key, value in default_status.items():
        if key not in st.session_state.sync_status_data:
            st.session_state.sync_status_data[key] = value

def _start_pending_files_check(qa_system: NRQuestionAnswering, result_queue: Queue): # Argumentos modificados
    """Inicia o thread para verificar arquivos pendentes."""
    logger.debug("[SYNC_PAGE_DEBUG] _start_pending_files_check called.")
    _initialize_sync_status_data() # Garante que o estado esteja inicializado
    st.session_state.sync_status_data["check_in_progress"] = True
    st.session_state.sync_status_data["check_performed"] = False
    st.session_state.sync_status_data["message"] = "Verificando arquivos pendentes..."

    integrator = get_service_account_drive_integrator_instance() # Obtém a instância do integrador aqui
    if not integrator:
        st.session_state.sync_status_data["check_in_progress"] = False
        st.session_state.sync_status_data["message"] = "Erro: Integrador do Google Drive não disponível para verificação."
        st.session_state.sync_status_data["success"] = False
        return

    check_thread = threading.Thread(
        target=_check_pending_files_async,
        args=(integrator, qa_system, result_queue), # Passa a instância do integrador e qa_system
        name="SafetyAI_Check_Thread"
    )
    check_thread.daemon = True
    st.session_state.sync_status_data["sync_thread"] = check_thread # Armazena a referência do thread
    st.session_state.sync_status_data["sync_thread_id"] = check_thread.ident
    check_thread.start()
    logger.info(f"Thread de verificação iniciado com ID: {check_thread.ident}")

def _start_sync_process(app_drive_service: Any, qa_system: NRQuestionAnswering, result_queue: Queue):
    """Inicia o thread para a sincronização completa."""
    logger.debug("[SYNC_PAGE_DEBUG] _start_sync_process called.")
    _initialize_sync_status_data() # Garante que o estado esteja inicializado
    st.session_state.sync_status_data["in_progress"] = True
    st.session_state.sync_status_data["finished"] = False
    st.session_state.sync_status_data["success"] = False
    st.session_state.sync_status_data["message"] = "Iniciando sincronização..."
    st.session_state.sync_status_data["processed_count"] = 0
    st.session_state.sync_status_data["current_doc_name"] = ""

    sync_thread = threading.Thread(
        target=_run_sync_in_thread,
        args=(app_drive_service, qa_system, result_queue),
        name="SafetyAI_Sync_Thread"
    )
    sync_thread.daemon = True
    st.session_state.sync_status_data["sync_thread"] = sync_thread # Armazena a referência do thread
    st.session_state.sync_status_data["sync_thread_id"] = sync_thread.ident
    sync_thread.start()
    logger.info(f"Thread de sincronização iniciado com ID: {sync_thread.ident}")

def _reset_sync_state_full():
    """Reseta completamente o estado da sincronização."""
    logger.info("Resetando estado de sincronização completo.")
    st.session_state.sync_status_data = {
        "check_performed": False,
        "check_in_progress": False,
        "pending_files_count": 0,
        "in_progress": False,
        "finished": False,
        "success": False,
        "message": "Sincronização não iniciada.",
        "processed_count": 0,
        "total_count": 0,
        "current_doc_name": "",
        "last_check_time": None,
        "sync_thread": None,
        "sync_thread_id": None,
    }
    if "sync_result_queue" in st.session_state:
        while not st.session_state.sync_result_queue.empty():
            try:
                st.session_state.sync_result_queue.get_nowait()
            except Empty:
                pass


def _on_start_sync_click():
    """Callback para o botão 'Sincronizar Agora'."""
    from safety_ai_app.web_app import _trigger_model_warmup_once, _trigger_nr_autoindex_once, _start_auto_sync_scheduler
    app_drive_service = st.session_state.get('app_drive_service')
    qa_system = st.session_state.get('nr_qa')
    
    # Executa sincronização com GCS primeiro se disponível (restaura estado anterior)
    if qa_system:
        try:
            logger.info("[SYNC_PAGE] Sincronizando com GCS (restauração local)...")
            qa_system.storage_manager.sync_from_gcs()
        except Exception as e:
            logger.warning(f"Erro ao sincronizar com GCS: {e}")

    if app_drive_service and qa_system:
        # Inicia processos em background
        _trigger_model_warmup_once()
        _trigger_nr_autoindex_once()
        _start_auto_sync_scheduler()
        
        # Inicia sincronização do Drive
        _start_sync_process(app_drive_service, qa_system, st.session_state.sync_result_queue)


def _on_skip_sync_click():
    """Callback para o botão 'Continuar sem sincronizar'."""
    from safety_ai_app.web_app import _trigger_model_warmup_once, _trigger_nr_autoindex_once, _start_auto_sync_scheduler
    
    # Mesmo pulando a sincronização do Drive, iniciamos as tarefas de background para o app ficar pronto
    _trigger_model_warmup_once()
    _trigger_nr_autoindex_once()
    _start_auto_sync_scheduler()
    
    _reset_sync_state_full()
    st.session_state._skip_sync_triggered = True


def _on_stop_sync_click():
    """Callback para o botão 'Parar Sincronização'."""
    st.session_state.sync_status_data["finished"] = True
    st.session_state.sync_status_data["success"] = False
    st.session_state.sync_status_data["message"] = "Sincronização interrompida pelo usuário."


def _on_refresh_status_click():
    """Callback para o botão 'Verificar Status Novamente'."""
    _reset_sync_state_full()


def render_page() -> None:
    _initialize_sync_status_data()

    # Hide sidebar on sync page (like login page)
    st.markdown("""
        <style>
            [data-testid="stSidebar"] { display: none !important; }
            [data-testid="stSidebarCollapsedControl"] { display: none !important; }
            .stApp > header { display: none !important; }
            section[data-testid="stSidebar"] { display: none !important; }
            button[kind="header"] { display: none !important; }
            .css-1544g2n { display: none !important; }
            div[data-testid="collapsedControl"] { display: none !important; }
        </style>
    """, unsafe_allow_html=True)

    # Get theme colors - ALL GREEN palette (no orange)
    accent_green = THEME['colors']['accent_green']  # #4ADE80 - bright green
    accent_green_dark = '#166534'  # Dark green for secondary button
    accent_green_medium = '#15803D'  # Medium green
    accent_cyan = THEME['colors'].get('accent_cyan', '#22D3EE')
    text_secondary = THEME['colors'].get('text_secondary', '#94A3B8')
    
    # Inject custom CSS for the sync page with Cyber-Neon design
    st.markdown(f"""
        <style>
            /* Full page background */
            .stApp {{
                background: linear-gradient(135deg, #020617 0%, #0B1220 50%, #0F172A 100%) !important;
            }}
            
            /* Main content card styling */
            div[data-testid="stVerticalBlock-sync_main_card"] {{
                background: linear-gradient(145deg, rgba(15, 23, 42, 0.95) 0%, rgba(11, 18, 32, 0.98) 100%);
                border-radius: 20px;
                padding: 2rem;
                margin-top: 1rem;
                box-shadow: 
                    0 0 0 1px rgba(74, 222, 128, 0.2),
                    0 0 40px rgba(74, 222, 128, 0.15),
                    0 20px 60px rgba(0, 0, 0, 0.5);
                text-align: center;
                max-width: 800px;
                margin-left: auto;
                margin-right: auto;
            }}
            
            /* Neon title styling */
            .neon-title {{
                font-family: 'Orbitron', sans-serif;
                font-size: 2rem;
                font-weight: 800;
                text-align: center;
                background: linear-gradient(135deg, {accent_green} 0%, {accent_cyan} 50%, {accent_green} 100%);
                background-size: 200% auto;
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                background-clip: text;
                animation: gradient-shift 3s ease-in-out infinite;
                margin-bottom: 0.5rem;
                letter-spacing: 1px;
            }}
            
            @keyframes gradient-shift {{
                0%, 100% {{ background-position: 0% center; }}
                50% {{ background-position: 100% center; }}
            }}
            
            .sync-message {{
                font-size: 1.1em;
                margin-bottom: 1.5rem;
                color: {text_secondary};
                text-align: center;
            }}
            
            /* Button base styling with readable text */
            .stButton > button {{
                border-radius: 12px !important;
                padding: 14px 28px !important;
                font-size: 1rem !important;
                font-weight: 700 !important;
                transition: all 0.3s ease !important;
                letter-spacing: 0.5px !important;
                border: 2px solid transparent !important;
            }}
            
            /* Primary button - green gradient with BLACK text (high contrast) */
            .stButton > button[kind="primary"],
            .stButton > button:not([kind="secondary"]) {{
                background: linear-gradient(135deg, {accent_green} 0%, #22C55E 100%) !important;
                border-color: {accent_green} !important;
                color: #000000 !important;
                box-shadow: 0 0 20px rgba(74, 222, 128, 0.4) !important;
            }}
            
            /* Force BLACK text on primary buttons with all selectors */
            .stButton > button[kind="primary"] p,
            .stButton > button[kind="primary"] span,
            .stButton > button:not([kind="secondary"]) p,
            .stButton > button:not([kind="secondary"]) span {{
                color: #000000 !important;
            }}
            
            .stButton > button[kind="primary"]:hover,
            .stButton > button:not([kind="secondary"]):hover {{
                transform: translateY(-3px) !important;
                box-shadow: 0 0 30px rgba(74, 222, 128, 0.6), 0 8px 25px rgba(0, 0, 0, 0.3) !important;
                color: #000000 !important;
            }}
            
            /* Secondary button - DARK GREEN gradient with WHITE text */
            .stButton > button[kind="secondary"] {{
                background: linear-gradient(135deg, {accent_green_dark} 0%, {accent_green_medium} 100%) !important;
                border-color: {accent_green_dark} !important;
                color: #FFFFFF !important;
                box-shadow: 0 0 20px rgba(22, 101, 52, 0.5) !important;
            }}
            
            /* Force WHITE text on secondary buttons */
            .stButton > button[kind="secondary"] p,
            .stButton > button[kind="secondary"] span {{
                color: #FFFFFF !important;
            }}
            
            .stButton > button[kind="secondary"]:hover {{
                transform: translateY(-3px) !important;
                box-shadow: 0 0 30px rgba(22, 101, 52, 0.7), 0 8px 25px rgba(0, 0, 0, 0.3) !important;
                color: #FFFFFF !important;
            }}
            
            /* Status container styling */
            .stStatus {{
                margin-top: 1.5rem;
                margin-bottom: 1.5rem;
            }}
            
            .stStatus > div {{
                border-radius: 12px !important;
                background: rgba(74, 222, 128, 0.1) !important;
                border: 1px solid rgba(74, 222, 128, 0.3) !important;
            }}
            
            /* Warning/Info/Success/Error boxes */
            .stWarning, .stInfo, .stSuccess, .stError {{
                border-radius: 12px !important;
            }}
            
            /* Progress bar styling */
            .stProgress > div > div {{
                background: linear-gradient(90deg, {accent_green}, {accent_cyan}) !important;
                border-radius: 10px !important;
            }}
            
            /* Divider styling */
            hr {{
                border: none !important;
                height: 1px !important;
                background: linear-gradient(90deg, transparent, rgba(74, 222, 128, 0.5), transparent) !important;
                margin: 1.5rem 0 !important;
            }}
        </style>
    """, unsafe_allow_html=True)

    st.markdown(f"<h1 class='neon-title'>{_get_material_icon_html('sync')} Sincronização da Biblioteca Central</h1>", unsafe_allow_html=True)
    st.markdown("<p class='sync-message'>Mantenha sua base de conhecimento atualizada com os documentos mais recentes do Google Drive.</p>", unsafe_allow_html=True)
    # app_drive_service é o serviço bruto, qa_system é a instância NRQuestionAnswering
    app_drive_service = st.session_state.get('app_drive_service')
    qa_system: NRQuestionAnswering = st.session_state.get('nr_qa')

    if not app_drive_service or not qa_system:
        st.error("Serviços essenciais (Google Drive ou QA System) não disponíveis. Por favor, faça login novamente.")
        st.query_params["page"] = "login"
        st.stop()
        return

    # Process queue messages (rerun logic)
    while not st.session_state.sync_result_queue.empty():
        try:
            message = st.session_state.sync_result_queue.get(block=False)
            if message['type'] == 'check_complete':
                st.session_state.sync_status_data["check_performed"] = True
                st.session_state.sync_status_data["check_in_progress"] = False
                st.session_state.sync_status_data["pending_files_count"] = message['pending_count']
                st.session_state.sync_status_data["last_check_time"] = message['timestamp']
                st.session_state.sync_status_data["success"] = message['success']
                if not message['success']:
                    st.session_state.sync_status_data["message"] = f"Erro na verificação: {message['error_message']}"
                st.session_state.sync_status_data["sync_thread"] = None
                st.session_state.sync_status_data["sync_thread_id"] = None
                st.rerun()
                return
            elif message['type'] == 'sync_progress':
                st.session_state.sync_status_data["processed_count"] = message['processed']
                st.session_state.sync_status_data["total_count"] = message['total']
                st.session_state.sync_status_data["current_doc_name"] = message['current_doc']
            elif message['type'] == 'sync_complete':
                st.session_state.sync_status_data["finished"] = True
                st.session_state.sync_status_data["in_progress"] = False
                st.session_state.sync_status_data["success"] = message['success']
                st.session_state.sync_status_data["message"] = message['message']
                st.session_state.sync_status_data["processed_count"] = message['processed_count']
                st.session_state.sync_status_data["total_count"] = message['total_count']
                st.session_state.sync_status_data["sync_thread"] = None
                st.session_state.sync_status_data["sync_thread_id"] = None
                st.rerun()
                return
        except Empty:
            pass
        except Exception as e:
            logger.error(f"SyncPage Render: Erro ao processar mensagem da fila: {e}", exc_info=True)

    # Conditional autorefresh
    if st.session_state.sync_status_data["check_in_progress"] or st.session_state.sync_status_data["in_progress"]:
        st_autorefresh(interval=500, key="sync_page_autorefresh_active")

    # --- Main Content Area wrapped in a custom styled container ---
    with st.container(key="sync_main_card"):

        # Redirect after finished sync
        if st.session_state.sync_status_data["finished"]:
            if st.session_state.sync_status_data["success"]:
                st.markdown(f"<p style='text-align: center; color: {THEME['colors']['accent_green']}; font-size: 1.5em;'>{_get_material_icon_html(THEME['icons']['check_circle'])}</p>", unsafe_allow_html=True)
                st.success(st.session_state.sync_status_data['message'])
            else:
                st.markdown(f"<p style='text-align: center; color: #dc3545; font-size: 1.5em;'>{_get_material_icon_html(THEME['icons']['error_icon'])}</p>", unsafe_allow_html=True)
                st.error(st.session_state.sync_status_data['message'])

            st.info("Redirecionando para a página inicial...")
            _reset_sync_state_full()
            st.query_params["page"] = "home"
            st.query_params["sync_done"] = "true"
            st.stop()
            return

        # Initial check logic
        if not st.session_state.sync_status_data["check_performed"] and \
           not st.session_state.sync_status_data["check_in_progress"]:
            st.markdown(f"<p style='text-align: center; font-size: 1.5em;'>{_get_material_icon_html('info')}</p>", unsafe_allow_html=True)
            st.info("Iniciando verificação de arquivos pendentes. Aguarde...")
            _start_pending_files_check(qa_system, st.session_state.sync_result_queue) # Chamada ajustada
            st.rerun()
            return

        # Check in progress state
        if st.session_state.sync_status_data["check_in_progress"]:
            # AQUI: Label do st.status é apenas texto. Ícone e mensagem detalhada dentro do bloco.
            with st.status("Verificando arquivos pendentes...", expanded=True, state="running"):
                st.markdown(f"{_get_material_icon_html('search')} Isso pode levar alguns instantes, dependendo do número de arquivos na sua biblioteca.", unsafe_allow_html=True)
            if st.session_state.sync_status_data["last_check_time"]:
                st.caption(f"Última verificação: {st.session_state.sync_status_data['last_check_time'].strftime('%d/%m/%Y %H:%M:%S')}")
            return

        # Sync in progress state
        if st.session_state.sync_status_data["in_progress"]:
            # AQUI: Label do st.status é apenas texto. Ícone e mensagem detalhada dentro do bloco.
            with st.status("Sincronizando biblioteca central...", expanded=True, state="running") as status_sync:
                progress_value = 0.0
                total_count = st.session_state.sync_status_data.get('total_count', 0)
                processed_count = st.session_state.sync_status_data.get('processed_count', 0)
                if total_count > 0:
                    progress_value = processed_count / total_count

                st.markdown(f"{_get_material_icon_html('sync_alt')} Processando: **{st.session_state.sync_status_data.get('current_doc_name', 'N/A')}** ({processed_count}/{total_count})", unsafe_allow_html=True)
                status_sync.progress(progress_value) # O texto do progress já está no markdown acima

            st.markdown("<br>", unsafe_allow_html=True)
            col_stop_button, _ = st.columns([1, 3])
            with col_stop_button:
                st.button("Parar Sincronização", key="stop_sync_button", use_container_width=True, on_click=_on_stop_sync_click)
            return

        # After check, not in progress
        if st.session_state.sync_status_data["check_performed"] and \
           not st.session_state.sync_status_data["in_progress"]:

            pending_count = st.session_state.sync_status_data["pending_files_count"]

            if pending_count > 0:
                st.markdown(f"<p style='text-align: center; font-size: 1.5em; color: #ffc107;'>{_get_material_icon_html('warning')}</p>", unsafe_allow_html=True)
                st.warning(f"Encontrados **{pending_count}** arquivo(s) pendente(s) para sincronização.")
                st.write("Para garantir que sua base de conhecimento esteja sempre atualizada, recomendamos sincronizar agora.")

                st.markdown("<br>", unsafe_allow_html=True)
                col1, col2 = st.columns(2)
                with col1:
                    st.button("Sincronizar Agora", key="start_sync_button", use_container_width=True, on_click=_on_start_sync_click)
                with col2:
                    st.button("Continuar sem sincronizar", key="skip_sync_button", use_container_width=True, type="secondary", on_click=_on_skip_sync_click)
                
                if st.session_state.get('_skip_sync_triggered'):
                    st.session_state._skip_sync_triggered = False
                    st.query_params["page"] = "home"
                    st.query_params["sync_done"] = "true"
                    st.stop()
                    return
            else:
                st.markdown(f"<p style='text-align: center; font-size: 1.5em; color: {THEME['colors']['accent_green']};'>{_get_material_icon_html('check_circle')}</p>", unsafe_allow_html=True)
                st.success("Sua biblioteca central está totalmente sincronizada!")
                st.write("Todos os documentos estão atualizados. Redirecionando para o aplicativo principal...")
                _reset_sync_state_full()
                st.query_params["page"] = "home"
                st.query_params["sync_done"] = "true"
                st.stop()
                return

        # Refresh status button (only if no active operations)
        if not st.session_state.sync_status_data["in_progress"] and \
           not st.session_state.sync_status_data["check_in_progress"] and \
           not st.session_state.sync_status_data["finished"]:
            st.markdown(f"<p style='text-align: center; font-size: 1.5em;'>{_get_material_icon_html('refresh')}</p>", unsafe_allow_html=True)
            st.info("Se o status não estiver atualizando, você pode tentar verificar novamente.")
            st.button("Verificar Status Novamente", key="refresh_sync_status_button", use_container_width=True, on_click=_on_refresh_status_click)