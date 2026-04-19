import streamlit as st
import logging
import os
import tempfile
import shutil
from typing import List, Dict, Any, Optional
import time

# Importa as configurações de tema e a nova função para injetar CSS de ícones nos botões
from safety_ai_app.theme_config import THEME, _get_material_icon_html_for_button_css, _get_material_icon_html
from safety_ai_app.web_interface.shared_styles import inject_glass_styles, glass_marker
from safety_ai_app.security.security_logger import log_security_event, SecurityEvent
from safety_ai_app.security.rate_limiter import check_rate_limit, RateLimitExceeded
from safety_ai_app.google_drive_integrator import (
    list_drive_folders,
    synchronize_user_drive_folder_to_chroma,
    synchronize_app_central_library_to_chroma,
    get_app_central_library_info
)
from safety_ai_app.nr_rag_qa import NRQuestionAnswering
from safety_ai_app.text_extractors import PROCESSABLE_MIME_TYPES

logger = logging.getLogger(__name__)

# --- Helper functions para renderização consistente de ícones e mensagens ---
def _render_info_like_message(message_type, message, icon_name=None):
    """
    Renderiza uma mensagem com estilo Streamlit (info, warning, success, error)
    permitindo a inclusão de um ícone SVG inline.
    """
    icon_html = _get_material_icon_html(icon_name) if icon_name else ""
    st.markdown(f"<div class='st-{message_type}-like'>{icon_html} {message}</div>", unsafe_allow_html=True)

# REMOVIDA A FUNÇÃO _get_st_button_label, pois os ícones serão injetados via CSS

# --- Helper function ---
def _refresh_rag_qa_instance():
    """
    Recarrega a instância de NRQuestionAnswering para refletir as últimas
    alterações na ChromaDB. Isso é crucial após adicionar/remover documentos.
    """
    if 'nr_qa' in st.session_state and isinstance(st.session_state.nr_qa, NRQuestionAnswering):
        st.cache_resource.clear()
        st.session_state.nr_qa = NRQuestionAnswering()
        logger.info("Instância NRQuestionAnswering recarregada no session_state após sincronização/limpeza.")
    else:
        logger.warning("Não foi possível recarregar a instância de NRQuestionAnswering, ela não está no session_state ou não é do tipo esperado.")

def _render_auto_sync_status_panel() -> None:
    """Render the auto-sync scheduler status card in the knowledge-base admin panel."""
    try:
        from safety_ai_app.auto_sync_scheduler import get_scheduler
        scheduler = get_scheduler()
        status = scheduler.get_status()
    except Exception as exc:
        logger.warning("Auto-sync scheduler not available: %s", exc)
        return

    if status["last_run_success"] is False:
        failed_message = status.get("last_run_message", "Erro desconhecido.")
        last_run_time = status.get("last_run_time")
        last_run_str = last_run_time.strftime("%d/%m/%Y %H:%M:%S") if last_run_time else "hora desconhecida"
        st.error(
            f"**Alerta: A sincronização automática da Base de Conhecimento falhou!**\n\n"
            f"Última tentativa em {last_run_str}: {failed_message}\n\n"
            "Verifique as credenciais do Google Drive e a conectividade de rede. "
            "Use o botão abaixo para tentar uma nova sincronização.",
            icon="🚨",
        )

    accent_green = THEME["colors"].get("accent_green", "#4ADE80")
    accent_cyan = THEME["colors"].get("accent_cyan", "#22D3EE")
    text_secondary = THEME["colors"].get("text_secondary", "#94A3B8")

    st.markdown(
        f'<div class="section-title">{_get_material_icon_html("schedule")} Sincronização Automática</div>',
        unsafe_allow_html=True,
    )

    is_syncing: bool = status["is_syncing"]
    last_success: Optional[bool] = status["last_run_success"]
    last_time = status["last_run_time"]
    next_time = status["next_run_time"]
    interval: int = status["interval_minutes"]
    message: str = status["last_run_message"]
    processed: int = status["last_processed_count"]

    last_time_str = last_time.strftime("%d/%m/%Y %H:%M:%S") if last_time else "Nunca"
    next_time_str = next_time.strftime("%d/%m/%Y %H:%M:%S") if next_time else "Aguardando inicialização..."

    if is_syncing:
        sync_status_icon = _get_material_icon_html("sync")
        sync_status_label = "Sincronizando agora..."
        status_color = accent_cyan
    elif last_success is True:
        sync_status_icon = _get_material_icon_html("check_circle")
        sync_status_label = "Última sincronização concluída com sucesso"
        status_color = accent_green
    elif last_success is False:
        sync_status_icon = _get_material_icon_html("error")
        sync_status_label = "Última sincronização falhou"
        status_color = "#F87171"
    else:
        sync_status_icon = _get_material_icon_html("hourglass_empty")
        sync_status_label = "Aguardando primeira execução automática"
        status_color = text_secondary

    st.markdown(
        f"""
        <div style="
            background: rgba(255,255,255,0.04);
            border: 1px solid rgba(74,222,128,0.25);
            border-radius: 12px;
            padding: 1rem 1.25rem;
            margin-bottom: 1rem;
        ">
            <div style="display:flex; align-items:center; gap:0.5rem; margin-bottom:0.75rem;">
                <span style="color:{status_color}; font-size:1.3em;">{sync_status_icon}</span>
                <span style="color:{status_color}; font-weight:600;">{sync_status_label}</span>
            </div>
            <div style="display:grid; grid-template-columns:1fr 1fr; gap:0.5rem 1.5rem; font-size:0.9em; color:{text_secondary};">
                <div><b>Intervalo automático:</b> a cada {interval} minutos</div>
                <div><b>Documentos na última execução:</b> {processed}</div>
                <div><b>Última execução:</b> {last_time_str}</div>
                <div><b>Próxima execução:</b> {next_time_str}</div>
                <div style="grid-column:1/-1;"><b>Resultado:</b> {message}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    sync_now_key = "auto_sync_trigger_now_kb"
    st.markdown(
        _get_material_icon_html_for_button_css(sync_now_key, "sync"),
        unsafe_allow_html=True,
    )
    if st.button(
        label="Sincronizar Agora (Auto-sync)",
        key=sync_now_key,
        help="Dispara uma sincronização incremental imediata em segundo plano.",
        disabled=is_syncing,
    ):
        triggered = scheduler.trigger_now()
        if triggered:
            _render_info_like_message(
                "success",
                "Sincronização automática disparada em segundo plano. "
                "Recarregue esta página em alguns momentos para ver o resultado.",
                THEME["icons"]["success_check"],
            )
        else:
            _render_info_like_message(
                "warning",
                "Uma sincronização já está em andamento. Aguarde a conclusão.",
                THEME["icons"]["warning_sign"],
            )



def render_page():
    inject_glass_styles()

    with st.container():
        st.markdown(glass_marker(), unsafe_allow_html=True)
        st.markdown(f'''
        <div class="page-header">
            {_get_material_icon_html(THEME["icons"]["brain_gear"])}
            <h1>{THEME.get("phrases", {}).get("knowledge_base_page_title", "Base de Conhecimento AI")}</h1>
        </div>
        <div class="page-subtitle">{THEME.get("phrases", {}).get("knowledge_base_description", "Gerencie os documentos que alimentam a inteligência do seu Safety AI Navigator.")}</div>
        ''', unsafe_allow_html=True)

    qa_system: NRQuestionAnswering = st.session_state.nr_qa
    if qa_system is None:
        _render_info_like_message("error", "O sistema de QA (RAG) não foi inicializado. Por favor, verifique as configurações da API Key e ChromaDB.", THEME["icons"]["error_x"])
        return

    # --- Auto-sync Status Panel ---
    _render_auto_sync_status_panel()

    # --- Abas para organização ---
    tab1, tab2, tab3 = st.tabs(["Sincronização da Biblioteca Central", "Sincronização do Meu Drive", "Upload Local"])

    # --- Aba 1: Sincronização da Biblioteca Central do App ---
    with tab1:
        st.markdown(f'<div class="section-title">{_get_material_icon_html(THEME["icons"]["library_books"])} Sincronizar com Biblioteca Central</div>', unsafe_allow_html=True)
        _render_info_like_message("info", "Sincroniza e baixa os arquivos da biblioteca central do aplicativo para a sua base de conhecimento interna. Apenas arquivos novos ou atualizados serão adicionados.", THEME["icons"]["info_circular_outline"])

        app_drive_service = st.session_state.get("app_drive_service")
        if app_drive_service is None:
            _render_info_like_message("warning", "O serviço da conta de aplicativo do Google Drive não está disponível. Verifique as credenciais da conta de serviço.", THEME["icons"]["warning_sign"])
        else:
            central_library_info = None
            try:
                central_library_info = get_app_central_library_info(app_drive_service)
            except Exception as e:
                logger.error(f"Erro ao obter informações da Biblioteca Central do App: {e}", exc_info=True)

            if central_library_info:
                st.markdown(f"**Biblioteca Central:** `{central_library_info.get('name', 'N/A')}`")
                st.markdown(f"Última modificação da pasta: `{central_library_info.get('modified_time', 'N/A')}`")
            else:
                _render_info_like_message("warning", "Não foi possível obter informações da Biblioteca Central do App. Verifique o Google Drive ou as permissões.", THEME["icons"]["warning_sign"])

            sync_button_key = "full_width_action_sync_central_library_kb"
            st.markdown(_get_material_icon_html_for_button_css(sync_button_key, THEME['icons']['sync']), unsafe_allow_html=True)
            if st.button(
                label="Sincronizar com Biblioteca Central", # Apenas texto
                key=sync_button_key,
                help="Sincroniza a biblioteca central do aplicativo",
                use_container_width=True
            ):
                try:
                    check_rate_limit("drive_sync")
                except RateLimitExceeded as rle:
                    log_security_event(SecurityEvent.RATE_LIMIT_EXCEEDED, feature="drive_sync", detail="Sincronização Biblioteca Central bloqueada por rate limit")
                    _render_info_like_message("warning", str(rle), THEME["icons"]["warning_sign"])
                    st.stop()
                with st.spinner(f"{_get_material_icon_html(THEME['icons']['loading_hourglass'])} Sincronizando Biblioteca Central... Isso pode levar alguns minutos para a primeira sincronização ou para muitas atualizações."):
                    try:
                        processed_count = synchronize_app_central_library_to_chroma(app_drive_service, qa_system)
                        if processed_count > 0:
                            _render_info_like_message("success", f"{processed_count} novo(s) documento(s) da Biblioteca Central adicionado(s) à base de conhecimento!", THEME["icons"]["success_check"])
                        else:
                            _render_info_like_message("info", "Biblioteca Central já está atualizada. Nenhum novo documento para adicionar/atualizar.", THEME["icons"]["generic_info"])
                        _refresh_rag_qa_instance()
                        st.rerun()
                    except Exception as e:
                        _render_info_like_message("error", f"Falha na sincronização com a Biblioteca Central: {e}", THEME["icons"]["error_x"])
                        logger.error(f"Erro durante a sincronização da Biblioteca Central para Chroma: {e}", exc_info=True)

    # --- Aba 2: Sincronização do Meu Google Drive ---
    with tab2:
        st.markdown(f'<div class="section-title">{_get_material_icon_html(THEME["icons"]["sync"])} Sincronizar com Pasta do Meu Drive</div>', unsafe_allow_html=True)
        _render_info_like_message("info", "Selecione uma pasta do seu Google Drive para sincronizar seus próprios documentos com a base de conhecimento. A sincronização é incremental: apenas novos documentos ou versões atualizadas serão adicionados, sem remover documentos já existentes de outras fontes.", THEME["icons"]["info_circular_outline"])

        user_drive_service = st.session_state.get("user_drive_service")
        if user_drive_service is None:
            _render_info_like_message("warning", "Por favor, autentique seu Google Drive para usar esta funcionalidade. Se você já autenticou, aguarde o carregamento ou reinicie o aplicativo.", THEME["icons"]["warning_sign"])
            
            re_auth_button_key = "small_action_re_auth_drive_kb_sync"
            st.markdown(_get_material_icon_html_for_button_css(re_auth_button_key, THEME['icons']['login_key']), unsafe_allow_html=True)
            if st.button(
                label="Tentar Autenticar Google Drive Agora", # Apenas texto
                key=re_auth_button_key
            ):
                st.session_state["user_drive_service"] = None # Reseta para forçar nova tentativa de auth no web_app.py
                st.rerun()
        else:
            user_folders = [{'id': 'root', 'name': 'Meu Drive (Raiz)'}]
            try:
                folders_from_drive = list_drive_folders(user_drive_service)
                user_folders.extend([f for f in folders_from_drive if f['id'] != 'root'])
            except Exception as e:
                logger.error(f"Erro ao listar pastas do Drive do usuário para sincronização: {e}", exc_info=True)
                _render_info_like_message("error", f"Erro ao listar suas pastas do Drive: {e}. Verifique sua conexão ou permissões.", THEME["icons"]["error_x"])
            
            folder_options = {f['name']: f['id'] for f in user_folders}
            sorted_folder_names = sorted(folder_options.keys(), key=lambda x: (x != 'Meu Drive (Raiz)', x))

            selected_folder_name = st.selectbox(
                "Selecione uma pasta do seu Drive para sincronizar:",
                options=sorted_folder_names,
                key="user_drive_sync_folder_selector_kb",
                help="Escolha uma pasta para adicionar seus documentos à base de conhecimento."
            )
            selected_folder_id = folder_options.get(selected_folder_name, 'root')

            sync_folder_button_key = "full_width_action_sync_user_drive_folder_kb"
            st.markdown(_get_material_icon_html_for_button_css(sync_folder_button_key, THEME['icons']['sync']), unsafe_allow_html=True)
            if st.button(
                label="Sincronizar Pasta Selecionada", # Apenas texto
                key=sync_folder_button_key,
                help="Sincroniza documentos da pasta selecionada do seu Google Drive.",
                use_container_width=True
            ):
                if selected_folder_id:
                    try:
                        check_rate_limit("drive_sync")
                    except RateLimitExceeded as rle:
                        log_security_event(SecurityEvent.RATE_LIMIT_EXCEEDED, feature="drive_sync", detail="Sincronização pasta do usuário bloqueada por rate limit")
                        _render_info_like_message("warning", str(rle), THEME["icons"]["warning_sign"])
                        st.stop()
                    with st.spinner(f"{_get_material_icon_html(THEME['icons']['loading_hourglass'])} Sincronizando documentos da pasta '{selected_folder_name}' do seu Drive..."):
                        try:
                            processed_count = synchronize_user_drive_folder_to_chroma(
                                user_drive_service,
                                selected_folder_id,
                                qa_system
                            )
                            if processed_count >= 0:
                                _render_info_like_message("success", f"Sincronização concluída! {processed_count} novo(s) documento(s) adicionado(s) da pasta '{selected_folder_name}' à base de conhecimento.", THEME["icons"]["success_check"])
                            _refresh_rag_qa_instance()
                            st.rerun()
                        except Exception as e:
                            _render_info_like_message("error", f"Falha na sincronização: {e}", THEME["icons"]["error_x"])
                            logger.error(f"Erro durante a sincronização do Drive do usuário para Chroma: {e}", exc_info=True)
                else:
                    _render_info_like_message("warning", "Por favor, selecione uma pasta do Google Drive para sincronizar.", THEME["icons"]["warning_sign"])
        
    # --- Aba 3: Upload de Documentos Locais ---
    with tab3:
        st.markdown(f'<div class="section-title">{_get_material_icon_html(THEME["icons"]["upload_arrow"])} Upload de Documentos Locais para a Base de Conhecimento</div>', unsafe_allow_html=True)
        _render_info_like_message("info", "Faça upload de documentos (PDF, DOCX, TXT) diretamente do seu computador. Eles serão processados e adicionados à sua base de conhecimento.", THEME["icons"]["info_circular_outline"])

        uploaded_files = st.file_uploader(
            "Selecione um ou mais documentos (PDF, DOCX, TXT)",
            type=["pdf", "docx", "txt"],
            accept_multiple_files=True,
            key="local_upload_knowledge"
        )

        if uploaded_files:
            process_docs_button_key = "full_width_action_process_local_docs_button_kb"
            st.markdown(_get_material_icon_html_for_button_css(process_docs_button_key, THEME['icons']['upload_arrow']), unsafe_allow_html=True)
            if st.button(
                label="Processar e Adicionar Documentos Selecionados (Local)", # Apenas texto
                key=process_docs_button_key,
                use_container_width=True
            ):
                try:
                    check_rate_limit("file_upload")
                except RateLimitExceeded as rle:
                    log_security_event(SecurityEvent.RATE_LIMIT_EXCEEDED, feature="file_upload", detail="Upload local para base de conhecimento bloqueado por rate limit")
                    _render_info_like_message("warning", str(rle), THEME["icons"]["warning_sign"])
                    st.stop()
                MAX_FILE_SIZE_MB = 15
                successful_uploads = 0
                temp_dir = tempfile.mkdtemp()
                try:
                    for up_file in uploaded_files:
                        file_name = up_file.name
                        file_bytes = up_file.getvalue()
                        file_type = up_file.type
                        size_mb = len(file_bytes) / (1024 * 1024)

                        if size_mb > MAX_FILE_SIZE_MB:
                            log_security_event(
                                SecurityEvent.FILE_REJECTED,
                                file_name=file_name,
                                file_size_mb=size_mb,
                                detail=f"Arquivo excede {MAX_FILE_SIZE_MB} MB",
                                feature="kb_upload",
                            )
                            _render_info_like_message("error", f"Arquivo '{file_name}' rejeitado: tamanho máximo é {MAX_FILE_SIZE_MB} MB (enviado: {size_mb:.1f} MB).", THEME["icons"]["error_x"])
                            continue

                        if file_type not in PROCESSABLE_MIME_TYPES:
                            _render_info_like_message("error", f"Tipo de arquivo '{file_type}' para '{file_name}' não suportado. Tipos suportados: {', '.join(PROCESSABLE_MIME_TYPES)}", THEME["icons"]["error_x"])
                            continue

                        temp_file_path = os.path.join(temp_dir, file_name)
                        with open(temp_file_path, "wb") as f:
                            f.write(file_bytes)

                        try:
                            qa_system.process_document_to_chroma(
                                file_path=temp_file_path,
                                document_name=file_name,
                                source="Upload Local",
                                file_type=file_type,
                                additional_metadata={"source_type": "local_upload"}
                            )
                            successful_uploads += 1
                            log_security_event(
                                SecurityEvent.FILE_UPLOADED,
                                file_name=file_name,
                                file_size_mb=size_mb,
                                feature="kb_upload",
                            )
                            _render_info_like_message("success", f"Documento '{file_name}' processado e adicionado à base de conhecimento.", THEME["icons"]["success_check"])
                        except Exception as e:
                            _render_info_like_message("error", f"Erro ao processar '{file_name}': {e}", THEME["icons"]["error_x"])
                            logger.error(f"Erro ao processar '{file_name}': {e}", exc_info=True)
                finally:
                    if os.path.exists(temp_dir):
                        shutil.rmtree(temp_dir)
                        logger.info(f"Diretório temporário '{temp_dir}' removido.")

                if successful_uploads > 0:
                    _render_info_like_message("success", f"{successful_uploads} documento(s) adicionado(s) com sucesso à base de conhecimento!", THEME["icons"]["success_check"])
                    _refresh_rag_qa_instance()
                    st.rerun()
        else:
            _render_info_like_message("info", "Selecione um ou mais arquivos para fazer upload para a base de conhecimento.", THEME["icons"]["generic_info"])

        clear_local_uploads_button_key = "full_width_action_clear_local_uploads_kb"
        st.markdown(_get_material_icon_html_for_button_css(clear_local_uploads_button_key, THEME['icons']['delete_trash']), unsafe_allow_html=True)
        if st.button(
            label="Limpar Documentos de Upload Local", # Apenas texto
            key=clear_local_uploads_button_key,
            use_container_width=True
        ):
            with st.spinner(f"{_get_material_icon_html(THEME['icons']['loading_hourglass'])} Removendo documentos de upload local..."):
                removed_count = qa_system.clear_docs_by_source_type("local_upload")
                if removed_count > 0:
                    _render_info_like_message("success", f"{removed_count} chunks de documentos de upload local removidos da base de conhecimento!", THEME["icons"]["success_check"])
                else:
                    _render_info_like_message("info", "Nenhum documento de upload local encontrado para remover.", THEME["icons"]["generic_info"])
                _refresh_rag_qa_instance()
                st.rerun()

    # --- Documentos Atualmente na Base de Conhecimento ---
    st.markdown(f'<div class="section-title">{_get_material_icon_html(THEME["icons"]["document_stack"])} Documentos Atualmente na Base de Conhecimento</div>', unsafe_allow_html=True)
    _render_info_like_message("info", "Visualize os documentos que o SafetyAI tem acesso para responder às suas perguntas.", THEME["icons"]["info_circular_outline"])

    documents_in_chroma = qa_system.list_processed_documents()

    if documents_in_chroma:
        search_term = st.text_input("Filtrar por nome do documento:", key="kb_search_docs").lower()
        if search_term:
            documents_in_chroma = [doc for doc in documents_in_chroma if search_term in doc['name'].lower()]

        documents_per_page = 50
        total_docs = len(documents_in_chroma)
        total_pages = (total_docs + documents_per_page - 1) // documents_per_page

        st.markdown(f"Total de documentos únicos exibidos: **{total_docs}**")

        if total_docs > 0:
            if 'kb_current_page' not in st.session_state:
                st.session_state.kb_current_page = 1
            st.session_state.kb_current_page = min(st.session_state.kb_current_page, total_pages)
            if st.session_state.kb_current_page < 1: st.session_state.kb_current_page = 1


            col_prev, col_page_info, col_next = st.columns([1, 2, 1])

            with col_prev:
                prev_page_button_key = "icon_only_kb_prev_page_button"
                st.markdown(_get_material_icon_html_for_button_css(prev_page_button_key, THEME['icons']['arrow_left']), unsafe_allow_html=True)
                if st.button(
                    label="", # Rótulo vazio, o ícone é injetado via CSS
                    key=prev_page_button_key,
                    help="Página anterior",
                    disabled=st.session_state.kb_current_page == 1
                ):
                    st.session_state.kb_current_page -= 1
                    st.rerun()
            with col_page_info:
                st.markdown(f"<div style='text-align: center; margin-top: 10px;'>Página {st.session_state.kb_current_page} de {total_pages} (Total: {total_docs} arquivos)</div>", unsafe_allow_html=True)
            with col_next:
                next_page_button_key = "icon_only_kb_next_page_button"
                st.markdown(_get_material_icon_html_for_button_css(next_page_button_key, THEME['icons']['arrow_right']), unsafe_allow_html=True)
                if st.button(
                    label="", # Rótulo vazio, o ícone é injetado via CSS
                    key=next_page_button_key,
                    help="Próxima página",
                    disabled=st.session_state.kb_current_page == total_pages
                ):
                    st.session_state.kb_current_page += 1
                    st.rerun()

            start_idx = (st.session_state.kb_current_page - 1) * documents_per_page
            end_idx = start_idx + documents_per_page
            paginated_files = documents_in_chroma[start_idx:end_idx] # <-- Aqui paginated_files é definido

            for doc in paginated_files: # <-- CORREÇÃO: Usar paginated_files aqui
                source_type_display = doc['source_type']
                if source_type_display == 'nr_vectorization':
                    source_type_display = 'Norma Regulamentadora (Padrão)'
                elif source_type_display == 'local_upload':
                    source_type_display = 'Upload Local'
                elif source_type_display == 'user_uploaded_drive':
                    source_type_display = 'Google Drive (Usuário)'
                elif source_type_display == 'app_central_library_sync':
                    source_type_display = 'Biblioteca Central do App'

                remove_button_key = f"small_action_remove_doc_{doc['document_metadata_id']}"

                st.markdown(f"""
                <div style="
                    border: 1px solid #444;
                    border-radius: 8px;
                    padding: 10px;
                    margin-bottom: 10px;
                    background-color: #222;
                ">
                    <p style="font-size: 1.1em; font-weight: bold; color: {THEME.get('colors', {}).get('primary', 'white')}; margin-bottom: 5px;">
                        {_get_material_icon_html(THEME['icons']['document'])} {doc['name']}
                    </p>
                    <p style="font-size: 0.9em; color: #bbb; margin-bottom: 5px;">
                        Origem: {doc['source']} | Tipo: {source_type_display}
                    </p>
                    <p style="font-size: 0.9em; color: #bbb;">
                        Chunks Processados: {doc['chunks']} | Extensão: {doc['file_type'].split('/')[-1] if doc['file_type'] else 'Desconhecida'}
                    </p>
                    <div style="text-align: right; margin-top: 10px;">
                """, unsafe_allow_html=True)
                
                st.markdown(_get_material_icon_html_for_button_css(remove_button_key, THEME['icons']['delete_trash']), unsafe_allow_html=True)
                if st.button(
                    label="Remover", # Apenas texto
                    key=remove_button_key,
                    help=f"Remover o documento '{doc['name']}' da base de conhecimento."
                ):
                    try:
                        qa_system.remove_document_by_id(doc['document_metadata_id'])
                        st.session_state.last_removed_doc_id = doc['document_metadata_id']
                    except Exception as e:
                        logger.error(f"Erro ao remover documento {doc['document_metadata_id']}: {e}", exc_info=True)
                        _render_info_like_message("error", f"Erro ao remover documento: {e}", THEME["icons"]["error_x"])
                    _refresh_rag_qa_instance() # Refresh after removal
                    st.rerun()

                st.markdown("</div></div>", unsafe_allow_html=True)

            if st.session_state.get('last_removed_doc_id'):
                _render_info_like_message("success", f"Documento com ID {st.session_state.last_removed_doc_id} removido com sucesso!", THEME["icons"]["success_check"])
                st.session_state.pop('last_removed_doc_id')
                _refresh_rag_qa_instance()
                st.rerun()

        else:
            _render_info_like_message("info", "Nenhum documento encontrado com o termo de busca.", THEME["icons"]["generic_info"])

        col_clear_all, col_clear_user_drive = st.columns(2)
        with col_clear_all:
            if 'confirm_clear_chromadb' not in st.session_state:
                st.session_state.confirm_clear_chromadb = False

            clear_all_button_key = "full_width_action_clear_chroma_full_kb"
            st.markdown(_get_material_icon_html_for_button_css(clear_all_button_key, THEME['icons']['delete_trash']), unsafe_allow_html=True)
            if st.button(
                label="Limpar TODA a Base de Conhecimento", # Apenas texto
                key=clear_all_button_key,
                use_container_width=True
            ):
                if st.session_state.confirm_clear_chromadb:
                    with st.spinner(f"{_get_material_icon_html(THEME['icons']['loading_hourglass'])} Limpando base de conhecimento..."):
                        try:
                            qa_system.clear_chroma_collection()
                            st.session_state.confirm_clear_chromadb = False
                            _render_info_like_message("success", "Base de conhecimento limpa com sucesso!", THEME["icons"]["success_check"])
                            _refresh_rag_qa_instance()
                            st.rerun()
                        except Exception as e:
                            _render_info_like_message("error", f"Erro ao limpar a base de conhecimento: {e}", THEME["icons"]["error_x"])
                            logger.error(f"Erro ao limpar ChromaDB: {e}", exc_info=True)
                else:
                    st.session_state.confirm_clear_chromadb = True
                    _render_info_like_message("warning", "Tem certeza? Isso apagará TODOS os documentos! Clique novamente no botão acima para confirmar.", THEME["icons"]["warning_sign"])

            if st.session_state.confirm_clear_chromadb:
                st.markdown(f'<p style="text-align: center; color: {THEME["colors"]["text_secondary"]}; font-size: 0.9em;">Clique novamente no botão acima para confirmar a limpeza total.</p>', unsafe_allow_html=True)
                cancel_button_key = "back_button_cancel_clear_chroma_full_kb_confirm"
                # Não precisa de ícone no botão de cancelar, mas se quisesse, seria assim:
                # st.markdown(_get_material_icon_html_for_button_css(cancel_button_key, THEME['icons']['cancel']), unsafe_allow_html=True)
                if st.button(
                    label="Cancelar Limpeza Total", # Apenas texto
                    key=cancel_button_key
                ):
                    st.session_state.confirm_clear_chromadb = False
                    st.rerun()

        with col_clear_user_drive:
            clear_user_drive_button_key = "full_width_action_clear_user_drive_kb"
            st.markdown(_get_material_icon_html_for_button_css(clear_user_drive_button_key, THEME['icons']['delete_trash']), unsafe_allow_html=True)
            if st.button(
                label="Limpar Documentos Sincronizados do Meu Drive", # Apenas texto
                key=clear_user_drive_button_key,
                use_container_width=True
            ):
                with st.spinner(f"{_get_material_icon_html(THEME['icons']['loading_hourglass'])} Removendo documentos do seu Google Drive..."):
                    removed_count = qa_system.clear_docs_by_source_type("user_uploaded_drive")
                    if removed_count > 0:
                        _render_info_like_message("success", f"{removed_count} chunks de documentos do seu Google Drive removidos da base de conhecimento!", THEME["icons"]["success_check"])
                    else:
                        _render_info_like_message("info", "Nenhum documento do seu Google Drive encontrado para remover.", THEME["icons"]["generic_info"])
                    _refresh_rag_qa_instance()
                    st.rerun()

    else:
        _render_info_like_message("info", "Nenhum documento na base de conhecimento ainda. Sincronize ou faça upload para começar!", THEME["icons"]["generic_info"])