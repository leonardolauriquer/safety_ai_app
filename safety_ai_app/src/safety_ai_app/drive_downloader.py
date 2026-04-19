import io
import json
import logging
import os
import tempfile
import shutil
from datetime import datetime
from typing import Any, Dict, List, Optional

from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseDownload
import streamlit as st

from pathlib import Path

from safety_ai_app.text_extractors import (
    PROCESSABLE_MIME_TYPES,
    get_mime_type_for_drive_export,
    get_extension_from_mime_type,
)

logger = logging.getLogger(__name__)

_METADATA_FILENAME = '.download_metadata.json'


def get_download_metadata(file_name: str, original_mime_type: str) -> tuple:
    """Return (local_file_name, export_mime_type) for a Drive file."""
    export_mime_type = get_mime_type_for_drive_export(original_mime_type)
    extension = get_extension_from_mime_type(export_mime_type)
    local_name = f"{Path(file_name).stem}.{extension}" if extension else file_name
    return local_name, export_mime_type


class DriveDownloader:
    """Download/listing helpers that operate on a Google Drive service object.

    All cache-heavy operations use Streamlit's ``@st.cache_data`` with the
    ``_self`` convention so that the instance itself is excluded from hashing
    (safe because ``GoogleDriveIntegrator`` is itself a ``@st.cache_resource``
    singleton).
    """

    def __init__(self, service: Any, data_dir: str) -> None:
        self.service = service
        self.data_dir = data_dir

    # ------------------------------------------------------------------
    # Remote metadata (cached)
    # ------------------------------------------------------------------

    @st.cache_data(ttl=300)
    def get_file_metadata(_self, file_id: str) -> Dict[str, Any]:
        if not _self.service:
            return {"file_id": file_id, "modified_time": None, "md5_checksum": None}
        try:
            meta = _self.service.files().get(
                fileId=file_id, fields='id, modifiedTime, md5Checksum'
            ).execute()
            return {
                "file_id": file_id,
                "modified_time": meta.get('modifiedTime'),
                "md5_checksum": meta.get('md5Checksum'),
            }
        except Exception as e:
            logger.error(f"Erro ao obter metadados do arquivo {file_id}: {e}")
            return {"file_id": file_id, "modified_time": None, "md5_checksum": None}

    # ------------------------------------------------------------------
    # Local download-metadata management
    # ------------------------------------------------------------------

    def _metadata_path(self) -> str:
        return os.path.join(self.data_dir, _METADATA_FILENAME)

    def _load_metadata(self) -> Dict[str, Any]:
        path = self._metadata_path()
        if os.path.exists(path):
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                logger.warning(f"Erro ao carregar metadados de download: {e}")
        return {}

    def _save_metadata(self, metadata: Dict[str, Any]) -> None:
        path = self._metadata_path()
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2, ensure_ascii=False)
        except IOError as e:
            logger.error(f"Erro ao salvar metadados de download: {e}")

    def _update_metadata(self, file_id: str, local_path: str, remote_meta: Dict[str, Any]) -> None:
        all_meta = self._load_metadata()
        all_meta[file_id] = {
            "local_path": local_path,
            "modified_time": remote_meta.get("modified_time"),
            "md5_checksum": remote_meta.get("md5_checksum"),
            "downloaded_at": datetime.now().isoformat(),
        }
        self._save_metadata(all_meta)

    def should_download(self, file_id: str, local_path: str) -> bool:
        if not os.path.exists(local_path):
            return True
        local = self._load_metadata().get(file_id)
        if not local:
            return True
        remote = self.get_file_metadata(file_id)
        if not remote.get("modified_time") and not remote.get("md5_checksum"):
            return True
        if remote.get("md5_checksum") and local.get("md5_checksum"):
            return remote["md5_checksum"] != local["md5_checksum"]
        if remote.get("modified_time") and local.get("modified_time"):
            return remote["modified_time"] != local["modified_time"]
        return True

    # ------------------------------------------------------------------
    # File/folder lookup
    # ------------------------------------------------------------------

    def get_file_id_in_folder(self, parent_folder_id: str, file_name: str, is_folder: bool = False) -> Optional[str]:
        if not self.service:
            return None
        try:
            query = f"'{parent_folder_id}' in parents and name = '{file_name}' and trashed = false"
            if is_folder:
                query += " and mimeType = 'application/vnd.google-apps.folder'"
            results = self.service.files().list(
                q=query, spaces='drive', fields='files(id, name, mimeType)'
            ).execute()
            for item in results.get('files', []):
                if is_folder and item.get('mimeType') == 'application/vnd.google-apps.folder':
                    return item['id']
                elif not is_folder and item.get('mimeType') != 'application/vnd.google-apps.folder':
                    return item['id']
        except Exception as e:
            logger.error(f"Erro ao buscar '{file_name}' em '{parent_folder_id}': {e}", exc_info=True)
        return None

    def get_folder_id_by_name(self, parent_folder_id: str, folder_name: str) -> Optional[str]:
        if not self.service:
            return None
        try:
            query = (
                f"name = '{folder_name}' and mimeType = 'application/vnd.google-apps.folder' "
                f"and '{parent_folder_id}' in parents and trashed = false"
            )
            results = self.service.files().list(
                q=query, spaces='drive', fields='files(id, name)'
            ).execute()
            items = results.get('files', [])
            if items:
                return items[0]['id']
            if parent_folder_id == 'root':
                query_all = (
                    f"name = '{folder_name}' and mimeType = 'application/vnd.google-apps.folder' "
                    "and trashed = false"
                )
                results_all = self.service.files().list(
                    q=query_all, corpora='allDrives',
                    includeItemsFromAllDrives=True, supportsAllDrives=True,
                    fields='files(id, name, parents)'
                ).execute()
                for item in results_all.get('files', []):
                    return item['id']
        except Exception as e:
            logger.error(f"Erro ao buscar ID da pasta '{folder_name}': {e}", exc_info=True)
        return None

    # ------------------------------------------------------------------
    # Bytes download
    # ------------------------------------------------------------------

    def download_bytes(self, file_id: str, original_mime_type: str, export_mime_type: str) -> bytes:
        if not self.service:
            return b''
        try:
            is_native = original_mime_type.startswith('application/vnd.google-apps')
            if is_native and export_mime_type != original_mime_type:
                request = self.service.files().export_media(fileId=file_id, mimeType=export_mime_type)
            else:
                request = self.service.files().get_media(fileId=file_id)
            fh = io.BytesIO()
            downloader = MediaIoBaseDownload(fh, request)
            done = False
            while not done:
                _, done = downloader.next_chunk()
            fh.seek(0)
            return fh.getvalue()
        except HttpError as e:
            logger.error(f"Erro HTTP ao baixar arquivo {file_id}: {e}")
        except Exception as e:
            logger.error(f"Erro inesperado ao baixar arquivo {file_id}: {e}", exc_info=True)
        return b''

    # ------------------------------------------------------------------
    # File download to local path
    # ------------------------------------------------------------------

    def download_to_path(self, file_id: str, local_path: str, force: bool = False) -> None:
        if not self.service:
            raise ConnectionError("Serviço do Google Drive não disponível.")
        if not force and not self.should_download(file_id, local_path):
            logger.info(f"Arquivo '{file_id}' não modificado. Usando cache local.")
            return
        file_meta = self.service.files().get(fileId=file_id, fields='mimeType, name').execute()
        original_mime = file_meta['mimeType']
        _, export_mime = get_download_metadata(file_meta['name'], original_mime)
        data = self.download_bytes(file_id, original_mime, export_mime)
        if not data:
            raise Exception(f"Falha ao baixar '{file_meta['name']}'.")
        os.makedirs(os.path.dirname(local_path), exist_ok=True)
        with open(local_path, 'wb') as fh:
            fh.write(data)
        self._update_metadata(file_id, local_path, self.get_file_metadata(file_id))

    def download_from_folder(self, folder_id: str, file_name: str, local_path: str) -> Optional[str]:
        file_id = self.get_file_id_in_folder(folder_id, file_name, is_folder=False)
        if not file_id:
            logger.error(f"Arquivo '{file_name}' não encontrado na pasta '{folder_id}'.")
            return None
        try:
            self.download_to_path(file_id, local_path)
            return local_path
        except Exception as e:
            logger.error(f"Falha ao baixar '{file_name}' da pasta '{folder_id}': {e}", exc_info=True)
            return None

    def download_by_path(self, drive_file_path: str, local_save_path: str) -> bool:
        if not self.service:
            return False
        path_parts = drive_file_path.split('/')
        current_parent = 'root'
        for part in path_parts[:-1]:
            folder_id = self.get_folder_id_by_name(current_parent, part)
            if not folder_id:
                logger.error(f"Pasta '{part}' não encontrada.")
                return False
            current_parent = folder_id
        file_name = path_parts[-1]
        file_id = self.get_file_id_in_folder(current_parent, file_name, is_folder=False)
        if not file_id:
            return False
        try:
            file_meta = self.service.files().get(fileId=file_id, fields='mimeType, name').execute()
            _, export_mime = get_download_metadata(file_name, file_meta['mimeType'])
            data = self.download_bytes(file_id, file_meta['mimeType'], export_mime)
            if data:
                os.makedirs(os.path.dirname(local_save_path), exist_ok=True)
                with open(local_save_path, 'wb') as fh:
                    fh.write(data)
                return True
        except Exception as e:
            logger.error(f"Erro ao baixar '{file_name}' por caminho: {e}", exc_info=True)
        return False

    # ------------------------------------------------------------------
    # Folder/file listing (cached)
    # ------------------------------------------------------------------

    @st.cache_data(ttl=300)
    def list_folders(_self, parent_id: str = 'root') -> List[Dict[str, str]]:
        folders: List[Dict[str, str]] = []
        if not _self.service:
            return folders
        page_token = None
        while True:
            try:
                resp = _self.service.files().list(
                    q=(f"'{parent_id}' in parents and "
                       "mimeType='application/vnd.google-apps.folder' and trashed=false"),
                    spaces='drive', fields='nextPageToken, files(id, name)', pageToken=page_token
                ).execute()
                for f in resp.get('files', []):
                    folders.append({'id': f['id'], 'name': f['name']})
                page_token = resp.get('nextPageToken')
                if not page_token:
                    break
            except Exception as e:
                logger.error(f"Erro ao listar pastas: {e}")
                return []
        return folders

    @st.cache_data(ttl=300)
    def get_processable_files(_self, folder_id: str) -> List[Dict[str, str]]:
        if not _self.service:
            return []
        files: List[Dict[str, str]] = []
        try:
            mime_queries = [f"mimeType='{mt}'" for mt in PROCESSABLE_MIME_TYPES]
            mime_queries.append("mimeType='application/vnd.google-apps.folder'")
            query = f"'{folder_id}' in parents and trashed=false and ({' or '.join(mime_queries)})"
            page_token = None
            while True:
                results = _self.service.files().list(
                    pageSize=1000, q=query,
                    fields="nextPageToken, files(id, name, mimeType, size)",
                    pageToken=page_token
                ).execute()
                for item in results.get('files', []):
                    if item['mimeType'] == 'application/vnd.google-apps.folder':
                        files.extend(_self.get_processable_files(item['id']))
                    elif item['mimeType'] in PROCESSABLE_MIME_TYPES:
                        files.append({
                            'id': item['id'], 'name': item['name'],
                            'mimeType': item['mimeType'], 'size': item.get('size')
                        })
                page_token = results.get('nextPageToken')
                if not page_token:
                    break
        except Exception as e:
            logger.error(f"Erro ao listar arquivos processáveis em '{folder_id}': {e}", exc_info=True)
        return files
