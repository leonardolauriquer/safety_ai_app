import os
import pickle
from pathlib import Path
import io
import time
import logging
import tempfile
import shutil
import uuid
from typing import List, Optional, Dict, Any, Tuple

from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build, HttpError
from google.oauth2 import service_account
from googleapiclient.http import MediaIoBaseDownload, MediaFileUpload, MediaIoBaseUpload
import streamlit as st
from datetime import datetime, timedelta

# Importações de módulos locais
# A importação de NRQuestionAnswering é agora feita dentro das funções para evitar dependências circulares.
from safety_ai_app.text_extractors import (
    PROCESSABLE_MIME_TYPES,
    get_mime_type_for_drive_export,
    get_extension_from_mime_type
)

logger = logging.getLogger(__name__)

# Definindo caminhos de forma mais robusta e centralizada
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(script_dir, '..', '..'))

CLIENT_SECRETS_FILE = os.path.join(project_root, 'credentials.json')
TOKEN_USER_PICKLE_FILE = os.path.join(project_root, 'token_user.pickle')
SERVICE_ACCOUNT_KEY_FILE = os.path.join(project_root, 'service_account_key.json')

# Escopos mais específicos para cada tipo de serviço
SCOPES_USER = [
    'https://www.googleapis.com/auth/drive.metadata.readonly',
    'https://www.googleapis.com/auth/drive.readonly',
    'https://www.googleapis.com/auth/drive.file'
]
SCOPES_SERVICE_ACCOUNT = [
    'https://www.googleapis.com/auth/drive.readonly'
]

# IDs de pastas do Google Drive (preenchidas pelas variáveis de ambiente)
OUR_DRIVE_FOLDER_ID = os.getenv("GOOGLE_DRIVE_CENTRAL_LIBRARY_FOLDER_ID") 
OUR_DRIVE_DONATION_FOLDER_ID = os.getenv("GOOGLE_DRIVE_DONATION_FOLDER_ID") 

if not OUR_DRIVE_FOLDER_ID:
    logger.warning("OUR_DRIVE_FOLDER_ID não configurado corretamente para a Biblioteca Central do App. Verifique o arquivo .env.")
if not OUR_DRIVE_DONATION_FOLDER_ID:
    logger.warning("OUR_DRIVE_DONATION_FOLDER_ID não configurado corretamente para a Pasta de Doações do App. Verifique o arquivo .env.")


def get_google_drive_user_creds_and_auth_info() -> Tuple[Optional[Any], Optional[str], Optional[str]]:
    """
    Tenta carregar ou obter as credenciais do usuário do Google Drive.
    Retorna uma tupla: (credenciais, URL de autorização, mensagem de erro).
    - credenciais: Objeto de credenciais se autenticado, caso contrário None.
    - auth_url: URL para o usuário autorizar se a autenticação for necessária, caso contrário None.
    - error_message: Mensagem de erro se algo deu errado, caso contrário None.
    """
    creds = None
    
    # 1. Tentar carregar credenciais existentes
    if os.path.exists(TOKEN_USER_PICKLE_FILE):
        try:
            with open(TOKEN_USER_PICKLE_FILE, 'rb') as token:
                creds = pickle.load(token)
            logger.debug("Credenciais de usuário do Google Drive carregadas do arquivo pickle.")
        except (pickle.UnpicklingError, EOFError, AttributeError) as e:
            logger.warning(f"Erro ao carregar {TOKEN_USER_PICKLE_FILE}: {e}. O arquivo pode estar corrompido ou vazio. Removendo para re-autenticar.")
            if os.path.exists(TOKEN_USER_PICKLE_FILE):
                os.remove(TOKEN_USER_PICKLE_FILE)
            creds = None

    # 2. Se credenciais existentes são válidas, usá-las
    if creds and creds.valid:
        logger.info("Credenciais de usuário do Google Drive são válidas.")
        return creds, None, None 

    # 3. Se credenciais expiraram mas há refresh token, tentar renovar
    if creds and creds.expired and creds.refresh_token:
        try:
            logger.info("Credenciais de usuário do Google Drive expiradas. Tentando renovar.")
            creds.refresh(Request())
            with open(TOKEN_USER_PICKLE_FILE, 'wb') as token_file_refreshed:
                pickle.dump(creds, token_file_refreshed)
            logger.info("Token de usuário do Google Drive renovado com sucesso.")
            return creds, None, None
        except Exception as e:
            logger.error(f"Erro ao renovar o token do usuário: {e}. Será necessária uma nova autenticação.", exc_info=True)
            if os.path.exists(TOKEN_USER_PICKLE_FILE):
                os.remove(TOKEN_USER_PICKLE_FILE)
            creds = None # Forçar nova autenticação se a renovação falhar

    # 4. Se credenciais não existem ou são inválidas (após tentativas), iniciar novo fluxo OAuth
    if not creds or not creds.valid:
        try:
            flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRETS_FILE, SCOPES_USER)
        except FileNotFoundError:
            return None, None, f"Erro: Arquivo 'credentials.json' não encontrado em '{CLIENT_SECRETS_FILE}'. Por favor, verifique sua configuração de credenciais OAuth 2.0."
        except Exception as e:
            return None, None, f"Erro ao carregar credenciais do cliente: {e}. Verifique o formato do 'credentials.json'."

        flow.redirect_uri = 'http://localhost:8501' # URL de redirecionamento para Streamlit local

        query_params = st.query_params.to_dict()
        
        if 'code' not in query_params:
            auth_url, _ = flow.authorization_url(access_type='offline', prompt='consent') 
            logger.info("URL de autorização do Google Drive gerada.")
            return None, auth_url, None # Retorna a URL para a UI do Streamlit exibir
        else:
            authorization_code = query_params['code']
            try:
                flow.fetch_token(code=authorization_code)
                creds = flow.credentials
                with open(TOKEN_USER_PICKLE_FILE, 'wb') as token_file_new:
                    pickle.dump(creds, token_file_new)
                
                st.query_params.clear() # Limpa query params para evitar re-execução indesejada com 'code'
                st.success("✅ Autenticação de usuário bem-sucedida! Recarregando aplicação...")
                st.balloons()
                st.rerun() # Recarrega a aplicação. Nesta nova execução, get_google_drive_user_creds_and_auth_info()
                            # será chamada novamente e deverá encontrar as credenciais salvas.
                return None, None, "REDIRECTING" # Indica que a aplicação está redirecionando/recarregando
            except Exception as e:
                logger.error(f"Erro ao autenticar usuário com o código: {e}. Por favor, tente novamente.", exc_info=True)
                if os.path.exists(TOKEN_USER_PICKLE_FILE):
                    os.remove(TOKEN_USER_PICKLE_FILE)
                return None, None, f"Erro ao autenticar: {e}. Por favor, exclua '{TOKEN_USER_PICKLE_FILE}' e tente novamente."

    return None, None, "Estado inesperado na função de credenciais do Google Drive."


def get_google_drive_service_user(creds: Any) -> Optional[Any]:
    """
    Cria e retorna o objeto de serviço do Google Drive usando credenciais válidas.
    Retorna None se as credenciais não forem válidas.
    """
    if creds and creds.valid:
        try:
            service = build('drive', 'v3', credentials=creds)
            return service
        except Exception as e:
            logger.error(f"Erro ao construir serviço do Google Drive com credenciais válidas: {e}", exc_info=True)
            return None
    return None

def get_service_account_drive_service():
    try:
        if not os.path.exists(SERVICE_ACCOUNT_KEY_FILE):
            logger.error(f"Arquivo da chave da conta de serviço não encontrado em: {SERVICE_ACCOUNT_KEY_FILE}. Verifique o caminho.", exc_info=True)
            st.error(f"Erro: Arquivo 'service_account_key.json' não encontrado em '{SERVICE_ACCOUNT_KEY_FILE}'. Por favor, verifique sua configuração da conta de serviço.")
            return None 
        
        creds = service_account.Credentials.from_service_account_file(
            SERVICE_ACCOUNT_KEY_FILE, scopes=SCOPES_SERVICE_ACCOUNT)
        service = build('drive', 'v3', credentials=creds)
        logger.info("Serviço do Google Drive da conta de serviço inicializado com sucesso.")
        return service
    except Exception as e:
        logger.error(f"Erro ao autenticar com a conta de serviço: {e}. Verifique o arquivo 'service_account_key.json' e suas permissões.", exc_info=True)
        st.error(f"Erro ao autenticar conta de serviço: {e}. Verifique o arquivo 'service_account_key.json' e se a API do Drive está habilitada para o projeto associado.")
        return None


def get_download_metadata(file_name: str, original_mime_type: str) -> tuple[str, str]:
    """
    Determina o nome do arquivo para download (com extensão correta) e o MIME type de exportação.
    Usa a lógica de text_extractors para padronizar.
    """
    export_mime_type = get_mime_type_for_drive_export(original_mime_type)
    extension = get_extension_from_mime_type(export_mime_type)
    
    final_file_name_for_storage = f"{Path(file_name).stem}.{extension}" if extension else file_name
    return final_file_name_for_storage, export_mime_type

def get_file_bytes_for_download(_drive_service_object, file_id: str, original_mime_type: str, export_mime_type: str) -> bytes:
    """
    Baixa o conteúdo de um arquivo do Google Drive.
    Lida com arquivos nativos do Google Workspace (exportando-os) e outros tipos de arquivo.
    """
    if not _drive_service_object:
        logger.warning(f"Objeto de serviço do Google Drive não fornecido para download do arquivo {file_id}. Retornando bytes vazios.")
        return b''

    is_google_native_file = original_mime_type.startswith('application/vnd.google-apps')
    
    try:
        if is_google_native_file and export_mime_type != original_mime_type:
            # Para documentos nativos do Google, precisamos usar export_media com o mimeType de exportação.
            request = _drive_service_object.files().export_media(fileId=file_id, mimeType=export_mime_type)
        else:
            # Para outros tipos de arquivo (ex: PDFs reais, DOCX), usamos get_media.
            request = _drive_service_object.files().get_media(fileId=file_id)

        fh = io.BytesIO()
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while done is False:
            status, done = downloader.next_chunk()
        
        fh.seek(0)
        return fh.getvalue()
            
    except HttpError as e:
        logger.error(f"Erro HTTP ao baixar arquivo {file_id}: {e}")
        st.error(f"Erro ao baixar arquivo do Google Drive: {e}. Verifique as permissões.")
        return b''
    except Exception as e:
        logger.error(f"Erro inesperado ao baixar arquivo {file_id}: {e}", exc_info=True)
        st.error(f"Erro inesperado ao baixar arquivo. Detalhes: {e}")
        return b''

def upload_file_to_drive(drive_service, uploaded_file_obj, parent_folder_id: Optional[str] = None) -> Optional[str]:
    """
    Faz upload de um arquivo para o Google Drive diretamente de um objeto Streamlit UploadedFile.
    """
    if not drive_service:
        st.error("Serviço do Google Drive não disponível para upload.")
        return None

    try:
        file_metadata = {'name': uploaded_file_obj.name}
        if parent_folder_id:
            file_metadata['parents'] = [parent_folder_id]

        # Lê o conteúdo do arquivo carregado diretamente para um buffer em memória
        file_content = uploaded_file_obj.getvalue()
        media = MediaIoBaseUpload(io.BytesIO(file_content), mimetype=uploaded_file_obj.type, resumable=True)
        
        file = drive_service.files().create(body=file_metadata,
                                            media_body=media,
                                            fields='id, name, mimeType, parents').execute()
        
        logger.info(f"Arquivo '{uploaded_file_obj.name}' (ID: {file.get('id')}) enviado com sucesso para o Drive.")
        return file.get('id')
    except Exception as e:
        logger.error(f"Erro ao enviar o arquivo '{uploaded_file_obj.name}' para o Drive: {e}", exc_info=True)
        st.error(f"Erro ao enviar o arquivo '{uploaded_file_obj.name}' para o Drive: {e}")
        return None

@st.cache_data(ttl=300, show_spinner="Listando pastas do Google Drive...")
def list_drive_folders(_drive_service, parent_id: str = 'root') -> List[Dict[str, str]]:
    """
    Lista as pastas (diretórios) no Google Drive a partir de um ID pai.
    Retorna uma lista de dicionários com 'id' e 'name'.
    """
    folders = []
    if not _drive_service:
        logger.warning("Serviço do Drive não disponível para listar pastas.")
        return folders
    page_token = None
    while True:
        try:
            response = _drive_service.files().list(
                q=f"'{parent_id}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false",
                spaces='drive',
                fields='nextPageToken, files(id, name)',
                pageToken=page_token
            ).execute()
            for folder in response.get('files', []):
                folders.append({'id': folder['id'], 'name': folder['name']})
            page_token = response.get('nextPageToken', None)
            if not page_token:
                break
        except HttpError as e:
            logger.error(f"Erro HTTP ao listar pastas do Drive: {e}")
            st.error(f"Erro ao listar pastas do Google Drive: {e}. Verifique as permissões ou autenticação.")
            break
        except Exception as e:
            logger.error(f"Erro inesperado ao listar pastas do Drive: {e}", exc_info=True)
            st.error(f"Erro inesperado ao listar pastas do Google Drive. Detalhes: {e}")
            break
    return folders


@st.cache_data(ttl=300) # Cache por 5 minutos
def get_processable_drive_files_in_folder(_drive_service, folder_id: str) -> List[Dict[str, str]]:
    """
    Lista arquivos processáveis (PDF, DOCX, TXT, Google Docs/Sheets/Slides) em uma pasta do Drive,
    incluindo subpastas recursivamente. Retorna uma lista de dicionários com id, name e mimeType para cada arquivo.
    """
    if _drive_service is None:
        logger.warning("Serviço do Drive não disponível para listar arquivos processáveis.")
        return []
    
    processable_files = []
    try:
        page_size = 1000
        
        # Filtra apenas os tipos MIME que podem ser processados OU são pastas para recursão
        mime_type_queries = [f"mimeType='{mt}'" for mt in PROCESSABLE_MIME_TYPES]
        mime_type_queries.append("mimeType='application/vnd.google-apps.folder'")

        query = f"'{folder_id}' in parents and trashed=false and ({' or '.join(mime_type_queries)})"
        
        page_token = None
        while True:
            results = _drive_service.files().list(
                pageSize=page_size,
                q=query,
                fields="nextPageToken, files(id, name, mimeType, size)", # Adicionado 'size' para consistência
                pageToken=page_token
            ).execute()
            
            files_and_folders_found = results.get('files', [])
            
            for item in files_and_folders_found:
                if item['mimeType'] == 'application/vnd.google-apps.folder':
                    # Se for uma pasta, faz uma chamada recursiva para buscar arquivos dentro dela
                    subfolder_files = get_processable_drive_files_in_folder(_drive_service, item['id'])
                    processable_files.extend(subfolder_files)
                elif item['mimeType'] in PROCESSABLE_MIME_TYPES:
                    processable_files.append({
                        'id': item['id'],
                        'name': item['name'],
                        'mimeType': item['mimeType'],
                        'size': item.get('size') # Inclui o tamanho
                    })
            
            page_token = results.get('nextPageToken', None)
            if not page_token:
                break
            
        logger.info(f"Encontrados {len(processable_files)} arquivos processáveis na pasta do Drive '{folder_id}' (incluindo subpastas).")
        
    except HttpError as e:
        logger.error(f"Erro HTTP ao listar arquivos processáveis do Drive na pasta {folder_id}: {e}")
        st.error(f"Erro ao listar arquivos processáveis do Google Drive: {e}. Verifique as permissões ou autenticação.")
    except Exception as e:
        logger.error(f"Erro inesperado ao listar arquivos processáveis do Drive na pasta {folder_id}: {e}", exc_info=True)
        st.error(f"Erro inesperado ao listar arquivos processáveis do Google Drive. Detalhes: {e}")
    
    return processable_files

def _synchronize_drive_files_to_chroma_incremental(drive_service, folder_id: str, qa_system, source_description: str, source_type_metadata: str) -> int:
    """
    Função interna para sincronizar documentos de uma pasta do Google Drive para a base de conhecimento ChromaDB
    de forma incremental, adicionando apenas arquivos novos.
    """
    from safety_ai_app.nr_rag_qa import NRQuestionAnswering # Importar para type hinting
    if not drive_service or not isinstance(qa_system, NRQuestionAnswering):
        # Mensagens de erro já são exibidas pelos chamadores se o serviço ou QA não estiverem disponíveis
        return 0

    processed_count = 0
    # Cria um diretório temporário único para cada sincronização
    temp_download_dir = tempfile.mkdtemp(prefix=f"drive_chroma_sync_{source_type_metadata}_")
    
    try:
        st.info(f"Buscando arquivos processáveis na pasta do Drive '{folder_id}' para sincronização (Source Type: {source_type_metadata})...")
        # Usar get_processable_drive_files_in_folder que já lida com recursão
        all_processable_files_in_drive = get_processable_drive_files_in_folder(drive_service, folder_id)
        
        if not all_processable_files_in_drive:
            st.warning(f"⚠️ Nenhum arquivo processável (PDF, DOCX, TXT, Google Docs/Sheets/Slides) encontrado na pasta selecionada.")
            return 0
        
        # Obter IDs dos arquivos já processados na ChromaDB para este source_type
        existing_drive_file_ids_in_chroma = qa_system.get_drive_file_ids_in_chroma(source_type=source_type_metadata)
        
        files_to_process = []
        for file_item in all_processable_files_in_drive:
            if file_item['id'] not in existing_drive_file_ids_in_chroma:
                files_to_process.append(file_item)
            else:
                logger.info(f"Arquivo '{file_item['name']}' (ID: {file_item['id']}) já está na ChromaDB com '{source_type_metadata}'. Ignorando.")

        if not files_to_process:
            st.info("Todos os arquivos processáveis já estão sincronizados ou não houve novos arquivos a adicionar.")
            return 0

        st.info(f"Preparando para sincronizar {len(files_to_process)} novo(s) documento(s).")
        progress_bar = st.progress(0) # Inicializa a barra de progresso
        
        for i, item in enumerate(files_to_process):
            file_id = item['id']
            file_name = item['name']
            original_mime_type = item['mimeType']

            # final_file_name_for_storage é o nome que o arquivo teria se fosse baixado com sua extensão correta
            final_file_name_for_storage, export_mime_type = get_download_metadata(file_name, original_mime_type)
            
            # --- CORREÇÃO DO PROBLEMA DE NOME DE ARQUIVO LONGO ---
            # Gerar um nome de arquivo temporário curto e único usando UUID
            # Isso garante que o caminho total do arquivo não exceda o limite MAX_PATH do Windows (260 caracteres)
            # A extensão é mantida para que o Langchain Loader possa inferir o tipo.
            unique_temp_filename = f"{uuid.uuid4().hex}.{get_extension_from_mime_type(export_mime_type)}"
            temp_file_path = os.path.join(temp_download_dir, unique_temp_filename)
            # --- FIM DA CORREÇÃO ---

            try:
                file_bytes = get_file_bytes_for_download(drive_service, file_id, original_mime_type, export_mime_type)
                
                if file_bytes:
                    with open(temp_file_path, 'wb') as f:
                        f.write(file_bytes)
                    logger.info(f"Download de '{file_name}' concluído para {temp_file_path}.")

                    processed_file_type = export_mime_type # O tipo MIME final do arquivo baixado para processamento

                    qa_system.process_document_to_chroma(
                        file_path=temp_file_path,
                        document_name=file_name,
                        source=source_description,
                        file_type=processed_file_type,
                        additional_metadata={"source_type": source_type_metadata, "drive_file_id": file_id}
                    )
                    processed_count += 1
                else:
                    st.warning(f"⚠️ Não foi possível baixar ou o arquivo '{file_name}' estava vazio. Ignorando.")

            except Exception as e:
                logger.error(f"Erro ao processar '{file_name}' do Google Drive para ChromaDB: {e}", exc_info=True)
                st.error(f"❌ Erro ao sincronizar '{file_name}': {e}")
            finally:
                if os.path.exists(temp_file_path):
                    try:
                        os.remove(temp_file_path)
                    except OSError as e:
                        logger.warning(f"Não foi possível remover arquivo temporário '{temp_file_path}': {e}")
            
            progress_text = f"Processando: {file_name} ({i + 1}/{len(files_to_process)})..."
            progress_bar.progress((i + 1) / len(files_to_process), text=progress_text) # Atualiza a barra de progresso com texto

        st.success(f"🎉 Sincronização concluída! {processed_count} novo(s) documento(s) adicionado(s) à base de conhecimento.")
    except Exception as e:
        logger.error(f"Erro geral durante a sincronização de pasta do Drive para ChromaDB: {e}", exc_info=True)
        st.error(f"❌ Ocorreu um erro inesperado durante a sincronização: {e}")
    finally:
        if os.path.exists(temp_download_dir):
            try:
                shutil.rmtree(temp_download_dir)
                logger.info(f"Diretório temporário '{temp_download_dir}' removido com sucesso.")
            except OSError as e:
                logger.error(f"Erro ao remover diretório temporário '{temp_download_dir}': {e}")
                
    return processed_count

def synchronize_user_drive_folder_to_chroma(drive_service, folder_id: str, qa_system: Any) -> int:
    """
    Sincroniza documentos de uma pasta ESPECÍFICA do Google Drive do USUÁRIO para a base de conhecimento.
    Realiza uma sincronização incremental. Antes de adicionar novos, remove APENAS os documentos
    que foram previamente sincronizados do Drive do USUÁRIO (identificados por source_type).
    """
    from safety_ai_app.nr_rag_qa import NRQuestionAnswering # Importar para type hinting
    if not isinstance(qa_system, NRQuestionAnswering):
        st.warning("⚠️ Sistema de QA não é uma instância de NRQuestionAnswering. Não foi possível limpar documentos antigos.")
        return 0

    st.info("🔄 Iniciando sincronização da sua pasta do Google Drive. Documentos antigos do Drive do usuário serão removidos antes de adicionar os novos.")
    
    # Clear existing user-uploaded drive docs
    removed_chunks = qa_system.clear_docs_by_source_type(source_type_to_remove="user_uploaded_drive")
    if removed_chunks > 0:
        st.success(f"✅ {removed_chunks} chunks de documentos do Drive do usuário removidos para re-sincronização.")
    else:
        st.info("ℹ️ Nenhum documento do Drive do usuário previamente sincronizado encontrado para remover.")


    return _synchronize_drive_files_to_chroma_incremental(drive_service, folder_id, qa_system, 
                                                          source_description=f"Google Drive do Usuário (ID: {folder_id})", 
                                                          source_type_metadata="user_uploaded_drive")

def synchronize_app_central_library_to_chroma(drive_service, qa_system: Any) -> int:
    """
    Sincroniza documentos da Biblioteca Central (pasta do aplicativo) para a base de conhecimento.
    Realiza uma sincronização incremental, adicionando apenas arquivos novos ou atualizados.
    Não remove documentos existentes, apenas adiciona os que faltam.
    """
    if not OUR_DRIVE_FOLDER_ID:
        st.error("❌ Erro: A ID da pasta da Biblioteca Central não está configurada. Verifique a variável GOOGLE_DRIVE_CENTRAL_LIBRARY_FOLDER_ID no arquivo .env.")
        return 0

    st.info("🔄 Iniciando sincronização incremental da Biblioteca Central do SafetyAI. Apenas novos documentos serão adicionados.")
    return _synchronize_drive_files_to_chroma_incremental(drive_service, OUR_DRIVE_FOLDER_ID, qa_system,
                                                          source_description="Biblioteca Central do App",
                                                          source_type_metadata="app_central_library_sync")

def get_app_central_library_info(drive_service) -> Optional[Dict[str, Any]]:
    """
    Retorna informações sobre a pasta da Biblioteca Central do App no Google Drive.
    """
    if not drive_service:
        logger.error("Serviço do Google Drive da conta de aplicativo não disponível.")
        return None
    if not OUR_DRIVE_FOLDER_ID or OUR_DRIVE_FOLDER_ID == "ID_DA_PASTA_BIBLIOTECA_CENTRAL": # Verifica se ainda é o placeholder
        logger.warning("OUR_DRIVE_FOLDER_ID não configurado corretamente para a Biblioteca Central do App. Verifique o arquivo .env.")
        return None

    try:
        folder = drive_service.files().get(
            fileId=OUR_DRIVE_FOLDER_ID, 
            fields='name, modifiedTime'
        ).execute()
        return {
            "name": folder.get('name'),
            "modified_time": folder.get('modifiedTime')
        }
    except HttpError as e:
        logger.error(f"Erro HTTP ao obter informações da pasta da Biblioteca Central (ID: {OUR_DRIVE_FOLDER_ID}): {e}")
        st.error(f"Erro ao obter informações da pasta da Biblioteca Central. Verifique o ID da pasta e as permissões da conta de serviço. Detalhes: {e}")
        return None
    except Exception as e:
        logger.error(f"Erro inesperado ao obter informações da pasta da Biblioteca Central (ID: {OUR_DRIVE_FOLDER_ID}): {e}", exc_info=True)
        st.error(f"Erro inesperado ao obter informações da pasta da Biblioteca Central. Detalhes: {e}")
        return None
