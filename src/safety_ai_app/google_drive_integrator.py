import os
import pickle
from pathlib import Path
import io
import time
import logging

from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from google.oauth2 import service_account
from googleapiclient.http import MediaIoBaseDownload, MediaFileUpload
import streamlit as st

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

CLIENT_SECRETS_FILE = os.path.join(Path(__file__).resolve().parents[2], 'credentials.json')
TOKEN_FILE = os.path.join(Path(__file__).resolve().parents[2], 'token.pickle')
SERVICE_ACCOUNT_KEY_FILE = os.path.join(Path(__file__).resolve().parents[2], 'service_account_key.json')

SCOPES = [
    'https://www.googleapis.com/auth/drive.readonly',
    'https://www.googleapis.com/auth/drive.file', # Permite gerenciar arquivos criados/abertos pelo app.
    'https://www.googleapis.com/auth/drive.metadata.readonly',
]

OUR_DRIVE_FOLDER_ID = "1CyjzomEqd2-acm9EkEAAbS2NxXNCIzKY"
OUR_DRIVE_DONATION_FOLDER_ID = "YOUR_DONATION_FOLDER_ID_HERE" # <<-- DEFINA O ID DA PASTA DE DOAÇÃO AQUI

DOWNLOAD_FOLDER = os.path.join(Path(__file__).resolve().parents[2], 'downloads_temp')
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

def get_google_drive_service_user():
    creds = None
    if os.path.exists(TOKEN_FILE):
        try:
            with open(TOKEN_FILE, 'rb') as token:
                creds = pickle.load(token)
        except (pickle.UnpicklingError, EOFError) as e:
            logging.warning(f"Erro ao carregar token.pickle: {e}. O arquivo pode estar corrompido.")
            if os.path.exists(TOKEN_FILE):
                os.remove(TOKEN_FILE)
            creds = None

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
                with open(TOKEN_FILE, 'wb') as token_file_refreshed:
                    pickle.dump(creds, token_file_refreshed)
                logging.info("Token de usuário do Google Drive renovado com sucesso.")
            except Exception as e:
                logging.error(f"Erro ao renovar o token do usuário: {e}. Será necessária uma nova autenticação.")
                if os.path.exists(TOKEN_FILE):
                    os.remove(TOKEN_FILE)
                return None
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRETS_FILE, SCOPES)
            flow.redirect_uri = 'http://localhost:8501'
            auth_url, _ = flow.authorization_url(prompt='consent')

            st.write("---")
            st.warning("⚠️ **Autenticação de Usuário do Google Drive Necessária**")
            st.markdown(f"Olá, Leo! Por favor, clique no link abaixo para autorizar o SafetyAI a acessar **seu** Google Drive:")
            st.markdown(f"[Autorizar Meu Google Drive]({auth_url})")
            st.write("Após a autorização, você será redirecionado de volta para esta página.")
            st.write("---")

            query_params = st.query_params
            if 'code' in query_params:
                authorization_code = query_params['code']
                try:
                    flow.fetch_token(code=authorization_code)
                    creds = flow.credentials
                    with open(TOKEN_FILE, 'wb') as token_file_new:
                        pickle.dump(creds, token_file_new)
                    st.query_params.clear()
                    st.success("✅ Autenticação de usuário bem-sucedida! Carregando Google Drive...")
                    st.balloons()
                    st.rerun()
                except Exception as e:
                    logging.error(f"Erro ao autenticar usuário: {e}. Por favor, tente novamente.")
                    if os.path.exists(TOKEN_FILE):
                        os.remove(TOKEN_FILE)
                    return None
            else:
                return None
    
    if creds:
        service = build('drive', 'v3', credentials=creds)
        return service
    else:
        return None

def get_service_account_drive_service():
    try:
        creds = service_account.Credentials.from_service_account_file(
            SERVICE_ACCOUNT_KEY_FILE, scopes=SCOPES)
        service = build('drive', 'v3', credentials=creds)
        logging.info("Serviço do Google Drive da conta de serviço inicializado com sucesso.")
        return service
    except FileNotFoundError:
        logging.error(f"Arquivo da chave da conta de serviço não encontrado em: {SERVICE_ACCOUNT_KEY_FILE}. Verifique o caminho.")
        return None
    except Exception as e:
        logging.error(f"Erro ao autenticar com a conta de serviço: {e}.")
        return None

def get_download_metadata(file_name, original_mime_type):
    export_mime_type = original_mime_type
    final_file_name = file_name
    
    if Path(file_name).suffix == '' and original_mime_type.startswith('application/vnd.google-apps'):
        if original_mime_type == 'application/vnd.google-apps.document':
            final_file_name = f"{file_name}.docx"
            export_mime_type = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        elif original_mime_type == 'application/vnd.google-apps.spreadsheet':
            final_file_name = f"{file_name}.xlsx"
            export_mime_type = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        elif original_mime_type == 'application/vnd.google-apps.presentation':
            final_file_name = f"{file_name}.pptx"
            export_mime_type = 'application/vnd.openxmlformats-officedocument.presentationml.presentation'
        elif original_mime_type == 'application/vnd.google-apps.drawing':
            final_file_name = f"{file_name}.png"
            export_mime_type = 'image/png'
        elif original_mime_type == 'application/vnd.google-apps.script':
            final_file_name = f"{file_name}.json"
            export_mime_type = 'application/vnd.google-apps.script+json'
        
    elif original_mime_type.startswith('application/vnd.google-apps'):
        if original_mime_type == 'application/vnd.google-apps.document':
            export_mime_type = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        elif original_mime_type == 'application/vnd.google-apps.spreadsheet':
            export_mime_type = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        elif original_mime_type == 'application/vnd.google-apps.presentation':
            export_mime_type = 'application/vnd.openxmlformats-officedocument.presentationml.presentation'
        elif original_mime_type == 'application/vnd.google-apps.drawing':
            export_mime_type = 'image/png'
        elif original_mime_type == 'application/vnd.google-apps.script':
            export_mime_type = 'application/vnd.google-apps.script+json'

    return final_file_name, export_mime_type


def get_file_bytes_for_download(_drive_service_object, file_id, export_mime_type):
    if not _drive_service_object:
        logging.warning(f"Objeto de serviço do Google Drive não fornecido para download do arquivo {file_id}. Retornando bytes vazios.")
        return b''

    request_method = None

    if export_mime_type in [
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        'application/vnd.openxmlformats-officedocument.presentationml.presentation',
        'image/png',
        'application/vnd.google-apps.script+json'
    ] and not export_mime_type.startswith('application/vnd.google-apps'):
        request_method = _drive_service_object.files().export_media
    elif export_mime_type.startswith('application/vnd.google-apps'):
        request_method = _drive_service_object.files().export_media
    else:
        request_method = _drive_service_object.files().get_media

    try:
        if request_method == _drive_service_object.files().export_media:
            request = request_method(fileId=file_id, mimeType=export_mime_type)
        else:
            request = request_method(fileId=file_id)

        fh = io.BytesIO()
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while done is False:
            status, done = downloader.next_chunk()
        
        fh.seek(0)
        return fh.getvalue()
            
    except Exception as e:
        logging.error(f"Erro ao baixar o conteúdo do arquivo (ID: {file_id}) com export_mime_type={export_mime_type}: {e}. Retornando bytes vazios.")
        return b''

def upload_file_to_drive(drive_service, uploaded_file_obj, parent_folder_id=None):
    if not drive_service:
        raise Exception("Serviço do Google Drive não disponível para upload.")

    temp_file_path = None
    try:
        file_metadata = {'name': uploaded_file_obj.name}
        if parent_folder_id:
            file_metadata['parents'] = [parent_folder_id]

        temp_file_path = os.path.join(DOWNLOAD_FOLDER, uploaded_file_obj.name)
        with open(temp_file_path, "wb") as f:
            f.write(uploaded_file_obj.getbuffer())
        
        media_body = MediaFileUpload(temp_file_path, mimetype=uploaded_file_obj.type)
        
        file = drive_service.files().create(body=file_metadata,
                                            media_body=media_body,
                                            fields='id, name, mimeType, parents').execute()
        
        logging.info(f"Arquivo '{uploaded_file_obj.name}' (ID: {file.get('id')}) enviado com sucesso para o Drive.")
        return file.get('id')
    except Exception as e:
        raise Exception(f"Erro ao enviar o arquivo '{uploaded_file_obj.name}' para o Drive: {e}")
    finally:
        if temp_file_path and os.path.exists(temp_file_path):
            os.remove(temp_file_path)

@st.cache_data(ttl=300, show_spinner="Listando pastas do Google Drive...")
def list_drive_folders(_drive_service):
    folders = [{'id': 'root', 'name': 'Meu Drive (Raiz)'}]
    if not _drive_service:
        logging.warning("Serviço do Drive não disponível para listar pastas.")
        return folders
    try:
        results = _drive_service.files().list(
            q="mimeType='application/vnd.google-apps.folder' and trashed=false",
            fields="files(id, name)",
            pageSize=1000
        ).execute()
        folders.extend(results.get('files', []))
        logging.info(f"Listadas {len(folders) - 1} pastas do Google Drive (incluindo Raiz).")
    except Exception as e:
        raise Exception(f"Erro ao listar pastas do Drive: {e}")
    return folders

@st.cache_data(ttl=300, show_spinner="Buscando arquivos no Google Drive...")
def _fetch_drive_files_cached(_drive_service, folder_id):
    if _drive_service is None:
        logging.warning(f"_fetch_drive_files_cached chamado com _drive_service=None para folder_id: {folder_id}")
        return []
    try:
        results = _drive_service.files().list(
            pageSize=100,
            q=f"'{folder_id}' in parents and trashed=false",
            fields="files(id, name, mimeType, size)").execute()
        return results.get('files', [])
    except Exception as e:
        st.error(f"❌ Erro ao buscar arquivos do Google Drive (pasta: {folder_id}). Detalhes: {e}")
        logging.error(f"Erro em _fetch_drive_files_cached (pasta: {folder_id}): Tipo: {type(e)}, Mensagem: {repr(e)}")
        return []