import io
import logging
import os
from typing import Any, Callable, Dict, List, Optional

from googleapiclient.http import MediaIoBaseUpload
import streamlit as st

from safety_ai_app.auth.google_auth import (
    get_service_account_service,
    get_user_oauth_service,
    get_google_drive_user_creds_and_auth_info,
    get_google_drive_service_user,
    SCOPES_USER,
    SCOPES_SERVICE_ACCOUNT,
)
from safety_ai_app.drive_downloader import DriveDownloader, get_download_metadata
from safety_ai_app.drive_sync import (
    synchronize_app_central_library,
    synchronize_user_drive_folder,
)

logger = logging.getLogger(__name__)

_script_dir = os.path.dirname(os.path.abspath(__file__))
_project_root = os.path.abspath(os.path.join(_script_dir, '..', '..'))

SAFETY_AI_ROOT_FOLDER_NAME = "SafetyAI - Conhecimento Base"
AI_CHAT_SYNC_SUBFOLDER_NAME = "Base de dados IA"
LIBRARY_SUBFOLDER_NAME = "Biblioteca"
GAMES_SUBFOLDER_NAME = "Jogos"

OUR_DRIVE_CENTRAL_LIBRARY_FOLDER_ID = os.environ.get(
    'GOOGLE_DRIVE_CENTRAL_LIBRARY_FOLDER_ID', '1p4588bahKJl7O8ZRRfy4qKuKZwy0wzjX'
)
OUR_DRIVE_DONATION_FOLDER_ID = os.environ.get(
    'GOOGLE_DRIVE_DONATION_FOLDER_ID', '1Cw1WqGy77cVlSA5YmNBwI1bsnuW0Dhfz'
)

CID10_FILE_ID = "1NPeSzhEv0zDNoSjlB83k-x1PAhAn8bqQ"
GRAU_DE_RISCO_FILE_ID = "1y4jXa6KkFUrXND64BeqbTIbd_aW1wkva"
CBO2025_FILE_ID = "14psRfBWWN8_C5VP_cWznDx23sMGvMHQu"
NR28_MULTAS_FILE_ID = "1eAgvm-GeA6nNtusG0KWfSguSMRXFrkIf"
DIMENSIONAMENTO_SESMT_FILE_ID = "17pu8jBvKCRdZY2d3wbgAFUGm2eoZhidr"
PALAVRAS_CRUZADAS_FILE_ID = "1lNywo2vsXEocZItSCrM9kWuEZyWKNLqW"
SHOW_DO_MILHAO_PERGUNTAS_FILE_ID = "1Y-v4eX9VXu2yTtAmxyjBmKsBYbGoRjIM"


class GoogleDriveIntegrator:
    """Thin facade over DriveDownloader providing Drive access via service-account credentials."""

    def __init__(self) -> None:
        self.service = get_service_account_service()
        if not self.service:
            raise ConnectionError("Não foi possível inicializar o serviço do Google Drive.")
        self._dl = DriveDownloader(self.service, os.path.join(_project_root, 'data'))

    # ------------------------------------------------------------------
    # Download / listing — delegate to DriveDownloader
    # ------------------------------------------------------------------

    def _download_file_bytes_internal(self, file_id: str, original_mime: str, export_mime: str) -> bytes:
        return self._dl.download_bytes(file_id, original_mime, export_mime)

    def download_file_from_drive(self, file_id: str, local_path: str, force_download: bool = False) -> None:
        self._dl.download_to_path(file_id, local_path, force=force_download)

    def download_file_from_folder(self, folder_id: str, file_name: str, local_path: str) -> Optional[str]:
        return self._dl.download_from_folder(folder_id, file_name, local_path)

    def _get_file_id_in_folder(self, parent_folder_id: str, file_name: str, is_folder: bool = False) -> Optional[str]:
        return self._dl.get_file_id_in_folder(parent_folder_id, file_name, is_folder)

    def get_folder_id_by_name(self, parent_folder_id: str, folder_name: str) -> Optional[str]:
        return self._dl.get_folder_id_by_name(parent_folder_id, folder_name)

    def download_file_by_path(self, drive_file_path: str, local_save_path: str) -> bool:
        return self._dl.download_by_path(drive_file_path, local_save_path)

    def list_drive_folders(self, parent_id: str = 'root') -> List[Dict[str, str]]:
        return self._dl.list_folders(parent_id)

    def get_processable_drive_files_in_folder(self, folder_id: str) -> List[Dict[str, str]]:
        return self._dl.get_processable_files(folder_id)

    # ------------------------------------------------------------------
    # Upload
    # ------------------------------------------------------------------

    def upload_file_to_drive(self, uploaded_file_obj: Any, parent_folder_id: Optional[str] = None) -> Optional[str]:
        if not self.service:
            return None
        try:
            meta: Dict[str, Any] = {'name': uploaded_file_obj.name}
            if parent_folder_id:
                meta['parents'] = [parent_folder_id]
            mime_type = getattr(uploaded_file_obj, 'type', None) or 'application/octet-stream'
            media = MediaIoBaseUpload(io.BytesIO(uploaded_file_obj.getvalue()), mimetype=mime_type, resumable=True)
            file = self.service.files().create(body=meta, media_body=media, fields='id').execute()
            logger.info(f"Arquivo '{uploaded_file_obj.name}' enviado (ID: {file.get('id')}).")
            return file.get('id')
        except Exception as e:
            logger.error(f"Erro ao enviar '{uploaded_file_obj.name}': {e}", exc_info=True)
            return None

    # ------------------------------------------------------------------
    # Games — delegate to data_parsers.games_parser
    # ------------------------------------------------------------------

    def _download_and_parse_crossword_excel_internal(self, file_name: str) -> Optional[List[Dict[str, Any]]]:
        from safety_ai_app.data_parsers.games_parser import download_and_parse_crossword
        return download_and_parse_crossword(self._dl, PALAVRAS_CRUZADAS_FILE_ID, file_name)

    def _download_and_parse_show_do_milhao_excel_internal(self, file_name: str) -> Optional[List[Dict[str, Any]]]:
        from safety_ai_app.data_parsers.games_parser import download_and_parse_show_do_milhao
        return download_and_parse_show_do_milhao(self._dl, SHOW_DO_MILHAO_PERGUNTAS_FILE_ID, file_name)

    def _download_game_json_internal(self, file_name: str) -> Optional[List[Dict[str, Any]]]:
        """Downloads a JSON game data file from the Games Drive folder. Returns None on failure."""
        import json, tempfile
        try:
            folder_id = self._get_games_folder_id()
            if not folder_id:
                logger.warning(f"Games folder not found in Drive for file '{file_name}'")
                return None
            with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as tmp:
                tmp_path = tmp.name
            result = self.download_file_from_folder(folder_id, file_name, tmp_path)
            if not result:
                logger.warning(f"File '{file_name}' not found in Drive games folder.")
                return None
            with open(tmp_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            import os; os.unlink(tmp_path)
            logger.info(f"Loaded {len(data)} entries from Drive: {file_name}")
            return data
        except Exception as e:
            logger.warning(f"Could not load '{file_name}' from Drive: {e}")
            return None

    # ------------------------------------------------------------------
    # Cached folder IDs
    # ------------------------------------------------------------------

    @st.cache_resource(ttl=3600)
    def _get_safety_ai_root_folder_id(_self) -> Optional[str]:
        return _self.get_folder_id_by_name('root', SAFETY_AI_ROOT_FOLDER_NAME)

    @st.cache_resource(ttl=3600)
    def _get_ai_chat_sync_folder_id(_self) -> Optional[str]:
        root_id = _self._get_safety_ai_root_folder_id()
        return _self.get_folder_id_by_name(root_id, AI_CHAT_SYNC_SUBFOLDER_NAME) if root_id else None

    @st.cache_resource(ttl=3600)
    def _get_library_folder_id(_self) -> Optional[str]:
        root_id = _self._get_safety_ai_root_folder_id()
        return _self.get_folder_id_by_name(root_id, LIBRARY_SUBFOLDER_NAME) if root_id else None

    @st.cache_resource(ttl=3600)
    def _get_games_folder_id(_self) -> Optional[str]:
        root_id = _self._get_safety_ai_root_folder_id()
        return _self.get_folder_id_by_name(root_id, GAMES_SUBFOLDER_NAME) if root_id else None

    # ------------------------------------------------------------------
    # Sync — delegate to drive_sync
    # ------------------------------------------------------------------

    def synchronize_app_central_library_to_chroma(
        self, qa_system: Any, progress_callback: Optional[Callable[[int, int, str], None]] = None
    ) -> int:
        folder_id = self._get_ai_chat_sync_folder_id()
        if not folder_id:
            logger.error("ID da pasta de sincronização não configurada.")
            if progress_callback:
                progress_callback(0, 0, "Erro: Pasta não configurada")
            return 0
        return synchronize_app_central_library(self, qa_system, folder_id, progress_callback)

    def synchronize_user_drive_folder_to_chroma(
        self, folder_id: str, qa_system: Any, progress_callback: Optional[Callable[[int, int, str], None]] = None
    ) -> int:
        return synchronize_user_drive_folder(self, folder_id, qa_system, progress_callback)

    # ------------------------------------------------------------------
    # Misc
    # ------------------------------------------------------------------

    def get_app_central_library_info(self) -> Optional[Dict[str, Any]]:
        folder_id = self._get_ai_chat_sync_folder_id()
        if not folder_id or not self.service:
            return None
        try:
            folder = self.service.files().get(
                fileId=folder_id, fields='name, modifiedTime'
            ).execute()
            return {"name": folder.get('name'), "modified_time": folder.get('modifiedTime')}
        except Exception as e:
            logger.error(f"Erro ao obter info da pasta de sync: {e}", exc_info=True)
            return None


# ==========================================================================
# Module-level singleton + helpers
# ==========================================================================

@st.cache_resource
def get_service_account_drive_integrator_instance() -> Optional[GoogleDriveIntegrator]:
    try:
        return GoogleDriveIntegrator()
    except Exception as e:
        logger.error(f"Erro ao criar GoogleDriveIntegrator: {e}", exc_info=True)
        return None


def _is_app_service(drive_service: Any) -> bool:
    """True when *drive_service* is the singleton service-account service."""
    integrator = get_service_account_drive_integrator_instance()
    return integrator is not None and integrator.service is drive_service


class _ExternalDriveContext:
    """Minimal adapter for non-integrator services (e.g. user OAuth).

    Provides the same interface that ``drive_sync`` functions expect.
    """

    def __init__(self, service: Any) -> None:
        self.service = service

    def get_processable_drive_files_in_folder(self, folder_id: str) -> List[Dict[str, str]]:
        dl = DriveDownloader(self.service, '')
        return dl.get_processable_files(folder_id)

    def _download_file_bytes_internal(self, file_id: str, original_mime: str, export_mime: str) -> bytes:
        dl = DriveDownloader(self.service, '')
        return dl.download_bytes(file_id, original_mime, export_mime)


# ==========================================================================
# Public API wrappers — the callers (pages) use these
# ==========================================================================

def get_service_account_drive_service() -> Optional[Any]:
    integrator = get_service_account_drive_integrator_instance()
    return integrator.service if integrator else None


def get_file_id_in_folder(service: Any, parent_folder_id: str, file_name: str, is_folder: bool = False) -> Optional[str]:
    if _is_app_service(service):
        integrator = get_service_account_drive_integrator_instance()
        return integrator._get_file_id_in_folder(parent_folder_id, file_name, is_folder) if integrator else None
    if not service:
        return None
    return DriveDownloader(service, '').get_file_id_in_folder(parent_folder_id, file_name, is_folder)


def download_file_from_drive(service: Any, file_id: str, local_path: str) -> None:
    integrator = get_service_account_drive_integrator_instance()
    if _is_app_service(service):
        if integrator:
            integrator.download_file_from_drive(file_id, local_path)
        else:
            raise ConnectionError("Serviço do Google Drive não disponível.")
        return
    if not service:
        raise ConnectionError("Serviço do Google Drive não disponível.")
    DriveDownloader(service, os.path.join(_project_root, 'data')).download_to_path(file_id, local_path)


def get_folder_id_by_name(drive_service: Any, parent_folder_id: str, folder_name: str) -> Optional[str]:
    if _is_app_service(drive_service):
        integrator = get_service_account_drive_integrator_instance()
        return integrator.get_folder_id_by_name(parent_folder_id, folder_name) if integrator else None
    if not drive_service:
        return None
    return DriveDownloader(drive_service, '').get_folder_id_by_name(parent_folder_id, folder_name)


def download_file_by_path(drive_file_path: str, local_save_path: str) -> bool:
    integrator = get_service_account_drive_integrator_instance()
    return integrator.download_file_by_path(drive_file_path, local_save_path) if integrator else False


def download_file_by_name_from_folder(drive_service: Any, file_name: str, parent_folder_id: str, local_save_path: str) -> Optional[str]:
    if _is_app_service(drive_service):
        integrator = get_service_account_drive_integrator_instance()
        return integrator.download_file_from_folder(parent_folder_id, file_name, local_save_path) if integrator else None
    if not drive_service:
        return None
    return DriveDownloader(drive_service, os.path.join(_project_root, 'data')).download_from_folder(
        parent_folder_id, file_name, local_save_path
    )


@st.cache_data(ttl=3600)
def download_and_parse_crossword_excel(file_name: str) -> Optional[List[Dict[str, Any]]]:
    integrator = get_service_account_drive_integrator_instance()
    return integrator._download_and_parse_crossword_excel_internal(file_name) if integrator else None


@st.cache_data(ttl=3600)
def download_and_parse_show_do_milhao_excel(file_name: str) -> Optional[List[Dict[str, Any]]]:
    integrator = get_service_account_drive_integrator_instance()
    return integrator._download_and_parse_show_do_milhao_excel_internal(file_name) if integrator else None


@st.cache_data(ttl=3600)
def download_game_json_from_drive(file_name: str) -> Optional[List[Dict[str, Any]]]:
    """Downloads a JSON game data file from the Drive Jogos folder. Returns None if Drive unavailable."""
    integrator = get_service_account_drive_integrator_instance()
    return integrator._download_game_json_internal(file_name) if integrator else None


def upload_file_to_drive(drive_service: Any, uploaded_file_obj: Any, parent_folder_id: Optional[str] = None) -> Optional[str]:
    """Upload using the provided service (app service-account or user OAuth)."""
    if not drive_service:
        return None
    if _is_app_service(drive_service):
        integrator = get_service_account_drive_integrator_instance()
        return integrator.upload_file_to_drive(uploaded_file_obj, parent_folder_id) if integrator else None
    try:
        meta: Dict[str, Any] = {'name': uploaded_file_obj.name}
        if parent_folder_id:
            meta['parents'] = [parent_folder_id]
        mime_type = getattr(uploaded_file_obj, 'type', None) or 'application/octet-stream'
        media = MediaIoBaseUpload(io.BytesIO(uploaded_file_obj.getvalue()), mimetype=mime_type, resumable=True)
        file = drive_service.files().create(body=meta, media_body=media, fields='id').execute()
        logger.info(f"Arquivo '{uploaded_file_obj.name}' enviado (ID: {file.get('id')}).")
        return file.get('id')
    except Exception as e:
        logger.error(f"Erro ao enviar '{uploaded_file_obj.name}': {e}", exc_info=True)
        return None


def list_drive_folders(drive_service: Any, parent_id: str = 'root') -> List[Dict[str, str]]:
    if _is_app_service(drive_service):
        return get_service_account_drive_integrator_instance().list_drive_folders(parent_id)  # type: ignore[union-attr]
    if not drive_service:
        return []
    return DriveDownloader(drive_service, '').list_folders(parent_id)


def get_processable_drive_files_in_folder(drive_service: Any, folder_id: str) -> List[Dict[str, str]]:
    if _is_app_service(drive_service):
        return get_service_account_drive_integrator_instance().get_processable_drive_files_in_folder(folder_id)  # type: ignore[union-attr]
    if not drive_service:
        return []
    return DriveDownloader(drive_service, '').get_processable_files(folder_id)


def get_file_bytes_by_id(drive_service_object: Any, file_id: str, original_mime_type: str) -> bytes:
    _, export_mime = get_download_metadata("dummy", original_mime_type)
    if _is_app_service(drive_service_object):
        integrator = get_service_account_drive_integrator_instance()
        return integrator._download_file_bytes_internal(file_id, original_mime_type, export_mime) if integrator else b''
    if not drive_service_object:
        return b''
    return DriveDownloader(drive_service_object, '').download_bytes(file_id, original_mime_type, export_mime)


def get_file_bytes_for_download(drive_service_object: Any, file_id: str, original_mime_type: str, export_mime_type: str) -> bytes:
    if _is_app_service(drive_service_object):
        integrator = get_service_account_drive_integrator_instance()
        return integrator._download_file_bytes_internal(file_id, original_mime_type, export_mime_type) if integrator else b''
    if not drive_service_object:
        return b''
    return DriveDownloader(drive_service_object, '').download_bytes(file_id, original_mime_type, export_mime_type)


def synchronize_app_central_library_to_chroma(
    drive_service: Any, qa_system: Any,
    progress_callback: Optional[Callable[[int, int, str], None]] = None
) -> int:
    """Always uses the app service-account — `drive_service` is ignored (app-only operation)."""
    integrator = get_service_account_drive_integrator_instance()
    return integrator.synchronize_app_central_library_to_chroma(qa_system, progress_callback) if integrator else 0


def synchronize_user_drive_folder_to_chroma(
    drive_service: Any, folder_id: str, qa_system: Any,
    progress_callback: Optional[Callable[[int, int, str], None]] = None
) -> int:
    integrator = get_service_account_drive_integrator_instance()
    if integrator and integrator.service is drive_service:
        return integrator.synchronize_user_drive_folder_to_chroma(folder_id, qa_system, progress_callback)
    if not drive_service:
        return 0
    return synchronize_user_drive_folder(_ExternalDriveContext(drive_service), folder_id, qa_system, progress_callback)


def get_app_central_library_info(drive_service: Any) -> Optional[Dict[str, Any]]:
    """Always uses the app service-account — `drive_service` is ignored (app-only operation)."""
    integrator = get_service_account_drive_integrator_instance()
    return integrator.get_app_central_library_info() if integrator else None
