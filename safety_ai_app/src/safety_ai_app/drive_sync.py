import os
import logging
import tempfile
import shutil
import uuid
from typing import Optional, Callable, Any

from safety_ai_app.text_extractors import get_extension_from_mime_type

logger = logging.getLogger(__name__)


def synchronize_drive_folder_to_chroma(
    integrator: Any,
    folder_id: str,
    qa_system: Any,
    source_description: str,
    source_type_metadata: str,
    progress_callback: Optional[Callable[[int, int, str], None]] = None,
) -> int:
    from safety_ai_app.nr_rag_qa import NRQuestionAnswering
    from safety_ai_app.drive_downloader import get_download_metadata

    if not integrator.service or not isinstance(qa_system, NRQuestionAnswering):
        logger.error("Serviço do Drive ou sistema QA não disponível para sincronização.")
        if progress_callback:
            progress_callback(0, 0, "Erro interno: Serviço indisponível")
        return 0

    all_files = integrator.get_processable_drive_files_in_folder(folder_id)

    if not all_files:
        logger.info(f"Nenhum arquivo processável encontrado na pasta '{folder_id}'.")
        if progress_callback:
            progress_callback(0, 0, "Nenhum arquivo encontrado")
        return 0

    existing_ids = qa_system.get_drive_file_ids_in_chroma(source_type=source_type_metadata)
    files_to_process = [f for f in all_files if f['id'] not in existing_ids]

    if not files_to_process:
        logger.info("Todos os arquivos já estão sincronizados.")
        if progress_callback:
            progress_callback(0, 0, "Todos os arquivos já sincronizados")
        return 0

    logger.info(f"Preparando para sincronizar {len(files_to_process)} novo(s) documento(s).")
    total = len(files_to_process)
    processed = 0
    temp_dir = tempfile.mkdtemp(prefix=f"drive_chroma_sync_{source_type_metadata}_")

    try:
        for item in files_to_process:
            file_id = item['id']
            file_name = item['name']
            original_mime_type = item['mimeType']

            if progress_callback:
                progress_callback(processed, total, file_name)

            final_file_name, export_mime_type = get_download_metadata(file_name, original_mime_type)
            unique_name = f"{uuid.uuid4().hex}.{get_extension_from_mime_type(export_mime_type)}"
            temp_path = os.path.join(temp_dir, unique_name)

            try:
                file_bytes = integrator._download_file_bytes_internal(file_id, original_mime_type, export_mime_type)
                if file_bytes:
                    with open(temp_path, 'wb') as f:
                        f.write(file_bytes)
                    qa_system.process_document_to_chroma(
                        file_path=temp_path,
                        document_name=file_name,
                        source=source_description,
                        file_type=export_mime_type,
                        additional_metadata={"source_type": source_type_metadata, "drive_file_id": file_id}
                    )
                    processed += 1
                else:
                    logger.warning(f"Arquivo '{file_name}' vazio ou falha no download. Ignorando.")
            except Exception as e:
                logger.error(f"Erro ao processar '{file_name}' para ChromaDB: {e}", exc_info=True)
            finally:
                if os.path.exists(temp_path):
                    try:
                        os.remove(temp_path)
                    except OSError as e:
                        logger.warning(f"Não foi possível remover '{temp_path}': {e}")
    except Exception as e:
        logger.error(f"Erro geral durante a sincronização Drive→Chroma: {e}", exc_info=True)
        if progress_callback:
            progress_callback(processed, total, f"Erro: {str(e)}")
    finally:
        if os.path.exists(temp_dir):
            try:
                shutil.rmtree(temp_dir)
            except OSError as e:
                logger.warning(f"Erro ao remover diretório temporário '{temp_dir}': {e}")

    if progress_callback:
        progress_callback(processed, total, "Concluído")

    return processed


def synchronize_app_central_library(
    integrator: Any,
    qa_system: Any,
    ai_chat_sync_folder_id: str,
    progress_callback: Optional[Callable[[int, int, str], None]] = None,
) -> int:
    logger.info("Iniciando sincronização incremental da Biblioteca Central (Base de dados IA).")
    return synchronize_drive_folder_to_chroma(
        integrator,
        ai_chat_sync_folder_id,
        qa_system,
        source_description="Biblioteca Central do App (Base de dados IA)",
        source_type_metadata="app_central_library_sync",
        progress_callback=progress_callback,
    )


def synchronize_user_drive_folder(
    integrator: Any,
    folder_id: str,
    qa_system: Any,
    progress_callback: Optional[Callable[[int, int, str], None]] = None,
) -> int:
    from safety_ai_app.nr_rag_qa import NRQuestionAnswering

    if not isinstance(qa_system, NRQuestionAnswering):
        logger.warning("Sistema de QA não é NRQuestionAnswering.")
        if progress_callback:
            progress_callback(0, 0, "Erro interno: QA indisponível")
        return 0

    logger.info("Iniciando sincronização da pasta do Drive do usuário. Documentos antigos serão removidos.")
    removed = qa_system.clear_docs_by_source_type(source_type_to_remove="user_uploaded_drive")
    if removed > 0:
        logger.info(f"{removed} chunks removidos para re-sincronização.")

    return synchronize_drive_folder_to_chroma(
        integrator,
        folder_id,
        qa_system,
        source_description=f"Google Drive do Usuário (ID: {folder_id})",
        source_type_metadata="user_uploaded_drive",
        progress_callback=progress_callback,
    )
