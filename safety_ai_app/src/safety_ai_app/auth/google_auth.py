import os
import secrets
import json
import logging
from typing import Optional, Any, Tuple, Dict

import streamlit as st

# Mover importações pesadas para dentro das funções (Lazy Loading)
# from google.oauth2.credentials import Credentials  # Mantida no topo pois é rápida
# from google_auth_oauthlib.flow import InstalledAppFlow # MOVIDA
# from googleapiclient.discovery import build # MOVIDA
import firebase_admin
from firebase_admin import credentials, firestore

logger = logging.getLogger(__name__)

# Inicializar Firebase se ainda não foi inicializado
if not firebase_admin._apps:
    try:
        # Tenta usar credenciais padrão do ambiente (Cloud Run / Google Cloud)
        firebase_admin.initialize_app()
        logger.info("Firebase Admin SDK inicializado com sucesso.")
    except Exception as e:
        logger.error(f"Erro ao inicializar Firebase: {e}")

def get_firestore_client():
    """Retorna o cliente do Firestore."""
    return firestore.client()

def _token_key_for_user(user_id: Optional[str]) -> str:
    """Return the database token_key for the given user_id (or the shared legacy key when None)."""
    if user_id is not None:
        return f"{_DB_TOKEN_KEY}:{user_id}"
    return _DB_TOKEN_KEY

script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(script_dir, '..', '..', '..'))

TOKEN_USER_JSON_FILE = os.path.join(project_root, 'token_user.json')
_LEGACY_PICKLE_FILE = os.path.join(project_root, 'token_user.pickle')
_DB_TOKEN_KEY = 'user_oauth_token'

if os.path.exists(_LEGACY_PICKLE_FILE):
    try:
        os.remove(_LEGACY_PICKLE_FILE)
        logger.info("Arquivo legado token_user.pickle removido.")
    except OSError as _e:
        logger.warning(f"Não foi possível remover token_user.pickle legado: {_e}")

SCOPES_USER = [
    'https://www.googleapis.com/auth/drive.metadata.readonly',
    'https://www.googleapis.com/auth/drive.readonly',
    'https://www.googleapis.com/auth/drive.file'
]
SCOPES_SERVICE_ACCOUNT = [
    'https://www.googleapis.com/auth/drive.readonly'
]


def _load_creds_from_db(user_id: Optional[str] = None) -> Optional[Credentials]:
    """Load OAuth credentials from Firebase Firestore."""
    try:
        db = get_firestore_client()
        token_key = _token_key_for_user(user_id)
        doc_ref = db.collection('google_oauth_tokens').document(token_key)
        doc = doc_ref.get()
        
        if not doc.exists:
            return None
            
        data_str = doc.to_dict().get('token_data')
        if not data_str:
            return None
            
        data = json.loads(data_str)
        return Credentials.from_authorized_user_info(data, SCOPES_USER)
    except Exception as e:
        logger.warning(f"Erro ao carregar token do Firestore: {e}")
        return None

def _save_creds_to_db(creds: Credentials, user_id: Optional[str] = None) -> None:
    """Persist OAuth credentials to Firebase Firestore."""
    try:
        db = get_firestore_client()
        token_key = _token_key_for_user(user_id)
        doc_ref = db.collection('google_oauth_tokens').document(token_key)
        
        doc_ref.set({
            'token_key': token_key,
            'token_data': creds.to_json(),
            'updated_at': firestore.SERVER_TIMESTAMP,
            'user_id': user_id
        })
        logger.info("Token OAuth guardado no Firestore com sucesso.")
    except Exception as e:
        raise OSError(f"Falha ao guardar token no Firestore: {e}") from e

def _delete_creds_from_db(user_id: Optional[str] = None) -> None:
    """Remove OAuth credentials from Firebase Firestore."""
    try:
        db = get_firestore_client()
        token_key = _token_key_for_user(user_id)
        db.collection('google_oauth_tokens').document(token_key).delete()
    except Exception as e:
        logger.warning(f"Erro ao remover token do Firestore: {e}")


@st.cache_data
def _get_service_account_credentials_from_env() -> Optional[Dict]:
    env_creds = os.environ.get('GOOGLE_SERVICE_ACCOUNT_KEY')
    if env_creds:
        try:
            return json.loads(env_creds)
        except json.JSONDecodeError as e:
            logger.warning(f"Erro ao decodificar GOOGLE_SERVICE_ACCOUNT_KEY: {e}")
    return None


@st.cache_data
def _get_client_credentials_from_env() -> Optional[Dict]:
    env_creds = os.environ.get('GOOGLE_CLIENT_CREDENTIALS')
    if env_creds:
        try:
            return json.loads(env_creds)
        except json.JSONDecodeError as e:
            logger.warning(f"Erro ao decodificar GOOGLE_CLIENT_CREDENTIALS: {e}")
    return None


def _token_json_file_for_user(user_id: Optional[str]) -> str:
    """Return the local fallback JSON file path for the given user.

    When user_id is provided a user-scoped file name is used so that multiple
    users do not overwrite each other's tokens if the database is unavailable.
    When user_id is None the legacy shared file is used for backward compatibility.
    """
    if user_id is not None:
        safe_id = user_id.replace(os.sep, "_").replace("/", "_")
        return os.path.join(project_root, f"token_user_{safe_id}.json")
    return TOKEN_USER_JSON_FILE


def _load_creds_from_json(user_id: Optional[str] = None) -> Optional[Credentials]:
    """Load OAuth credentials — database first, local file as fallback.

    Args:
        user_id: Optional identifier for the user whose credentials to load.
                 When None, the legacy shared token is used for backward compatibility.
    """
    db_creds = _load_creds_from_db(user_id=user_id)
    if db_creds is not None:
        return db_creds

    token_file = _token_json_file_for_user(user_id)
    if not os.path.exists(token_file):
        return None
    try:
        with open(token_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        creds = Credentials.from_authorized_user_info(data, SCOPES_USER)
        try:
            _save_creds_to_db(creds, user_id=user_id)
            os.remove(token_file)
            logger.info("Token migrado do ficheiro local para o banco de dados.")
        except OSError as migrate_err:
            logger.warning(f"Não foi possível migrar token para o banco de dados: {migrate_err}")
        return creds
    except (json.JSONDecodeError, KeyError, ValueError) as e:
        logger.warning(f"Erro ao carregar {token_file}: {e}. Removendo para re-autenticar.")
        os.remove(token_file)
        return None


def _save_creds_to_json(creds: Credentials, user_id: Optional[str] = None) -> None:
    """Persist OAuth credentials — database primary, local file as fallback.

    Raises OSError / IOError on write failure so callers can handle the
    situation explicitly instead of silently continuing with unsaved tokens.

    Args:
        creds: The OAuth credentials to persist.
        user_id: Optional identifier for the user. When None, the legacy shared
                 token slot is used for backward compatibility.
    """
    token_file = _token_json_file_for_user(user_id)
    try:
        _save_creds_to_db(creds, user_id=user_id)
        if os.path.exists(token_file):
            try:
                os.remove(token_file)
            except OSError:
                pass
    except OSError:
        logger.warning("Falha ao guardar no banco de dados; a tentar ficheiro local como fallback.")
        with open(token_file, 'w', encoding='utf-8') as f:
            f.write(creds.to_json())


def _delete_creds(user_id: Optional[str] = None) -> None:
    """Remove stored OAuth credentials from all storage locations.

    Args:
        user_id: Optional identifier for the user whose credentials to remove.
                 When None, the legacy shared token is removed for backward compatibility.
    """
    _delete_creds_from_db(user_id=user_id)
    token_file = _token_json_file_for_user(user_id)
    if os.path.exists(token_file):
        try:
            os.remove(token_file)
        except OSError:
            pass


def get_google_drive_user_creds_and_auth_info(
    user_id: Optional[str] = None,
) -> Tuple[Optional[Any], Optional[str], Optional[str]]:
    """Return (creds, auth_url, error_message) for the given user.

    Args:
        user_id: Optional identifier for the user whose Drive session to manage.
                 When provided each user's token is stored and retrieved in
                 isolation.  When None the legacy single-token behaviour is
                 preserved for backward compatibility.
    """
    creds = _load_creds_from_json(user_id=user_id)

    if creds and creds.valid:
        return creds, None, None

    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
        except Exception as e:
            logger.error(f"Erro ao renovar o token do usuário: {e}. Será necessária uma nova autenticação.", exc_info=True)
            _delete_creds(user_id=user_id)
            creds = None
        if creds:
            try:
                _save_creds_to_json(creds, user_id=user_id)
            except OSError as e:
                logger.warning(f"Token renovado mas não foi possível salvar: {e}. Re-autenticação necessária na próxima sessão.")
            return creds, None, None

    flow = None
    try:
        env_client_creds = _get_client_credentials_from_env()
        if env_client_creds:
            from google_auth_oauthlib.flow import InstalledAppFlow
            flow = InstalledAppFlow.from_client_config(env_client_creds, SCOPES_USER)
            logger.info("Credenciais OAuth carregadas da variável de ambiente.")
        else:
            logger.error("GOOGLE_CLIENT_CREDENTIALS não configurado.")
            return None, None, "Erro: Configure GOOGLE_CLIENT_CREDENTIALS no painel de Secrets do Replit."
    except Exception as e:
        logger.error(f"Erro ao inicializar o fluxo de autenticação: {e}", exc_info=True)
        return None, None, f"Erro ao carregar credenciais do cliente: {e}."

    if flow is None:
        return None, None, "Erro interno: Não foi possível inicializar o fluxo de autenticação."

    # Detecção dinâmica de URI de Redirecionamento
    explicit_redirect = os.environ.get('OAUTH_REDIRECT_URI')
    replit_domain = os.environ.get('REPLIT_DEV_DOMAIN')
    
    if explicit_redirect:
        flow.redirect_uri = explicit_redirect
        logger.info(f"Usando URI de redirecionamento explícita: {explicit_redirect}")
    elif replit_domain:
        flow.redirect_uri = f'https://{replit_domain}'
        logger.info(f"Usando domínio do Replit: {flow.redirect_uri}")
    else:
        # Fallback padrão, mas tenta detectar se estamos em HTTPS se possível via streamlit headers
        # (Nota: st.context.headers só disponível em versões mais recentes do Streamlit)
        flow.redirect_uri = 'http://localhost:8501'
        logger.info(f"Usando URI de fallback: {flow.redirect_uri}. Configure OAUTH_REDIRECT_URI para produção.")

    query_params = st.query_params.to_dict()
    oauth_state = secrets.token_urlsafe(32)

    if 'code' not in query_params:
        auth_url, _ = flow.authorization_url(
            access_type='offline',
            prompt='consent',
            state=oauth_state
        )
        st.session_state['oauth_state'] = oauth_state
        return None, auth_url, None

    returned_state = query_params.get('state', '')
    stored_state = st.session_state.get('oauth_state', '')

    if stored_state and returned_state != stored_state:
        logger.warning("Possível ataque CSRF detectado: state não corresponde.")
        try:
            from safety_ai_app.security.security_logger import log_security_event, SecurityEvent
            log_security_event(SecurityEvent.CSRF_ERROR, detail="OAuth state mismatch — possível ataque CSRF.")
        except Exception as log_err:
            logger.warning(f"Falha ao registrar evento CSRF no security_logger: {log_err}")
        st.query_params.clear()
        if 'oauth_state' in st.session_state:
            del st.session_state['oauth_state']
        return None, None, "Erro de segurança: state inválido. Por favor, tente novamente."

    authorization_code = query_params['code']
    try:
        flow.fetch_token(code=authorization_code)
        creds = flow.credentials
        try:
            _save_creds_to_json(creds, user_id=user_id)
        except OSError as save_err:
            logger.warning(f"Autenticação bem-sucedida mas não foi possível salvar token: {save_err}. Re-autenticação necessária na próxima sessão.")
        st.query_params.clear()
        if 'oauth_state' in st.session_state:
            del st.session_state['oauth_state']
        try:
            from safety_ai_app.security.security_logger import log_security_event, SecurityEvent
            log_security_event(SecurityEvent.LOGIN_SUCCESS, detail="OAuth login bem-sucedido.")
        except Exception as log_err:
            logger.warning(f"Falha ao registrar evento LOGIN_SUCCESS no security_logger: {log_err}")
        st.success("✅ Autenticação de usuário bem-sucedida! Recarregando aplicação...")
        st.balloons()
        st.rerun()
        return None, None, "REDIRECTING_SUCCESS"
    except Exception as e:
        logger.error(f"Erro ao autenticar usuário com o código: {e}.", exc_info=True)
        _delete_creds(user_id=user_id)
        if 'oauth_state' in st.session_state:
            del st.session_state['oauth_state']
        try:
            from safety_ai_app.security.security_logger import log_security_event, SecurityEvent
            log_security_event(SecurityEvent.LOGIN_FAILURE, detail=f"Erro ao trocar código OAuth: {type(e).__name__}")
        except Exception as log_err:
            logger.warning(f"Falha ao registrar evento LOGIN_FAILURE no security_logger: {log_err}")
        return None, None, f"Erro ao autenticar: {e}. Por favor, tente novamente."


def get_service_account_service() -> Optional[Any]:
    """Build and return a Google Drive API service using service-account credentials."""
    creds_dict = _get_service_account_credentials_from_env()
    if not creds_dict:
        logger.error("GOOGLE_SERVICE_ACCOUNT_KEY não configurado.")
        return None
    try:
        from google.oauth2.service_account import Credentials as SACredentials
        from googleapiclient.discovery import build
        creds = SACredentials.from_service_account_info(creds_dict, scopes=SCOPES_SERVICE_ACCOUNT)
        service = build('drive', 'v3', credentials=creds)
        logger.info("Serviço do Google Drive (conta de serviço) inicializado.")
        return service
    except Exception as e:
        logger.error(f"Erro ao criar serviço de conta de serviço: {e}", exc_info=True)
        return None


def get_user_oauth_service(creds: Any) -> Optional[Any]:
    """Build and return a Google Drive API service using user OAuth credentials."""
    if creds and creds.valid:
        try:
            from googleapiclient.discovery import build
            return build('drive', 'v3', credentials=creds)
        except Exception as e:
            logger.error(f"Erro ao construir serviço do Google Drive (usuário): {e}", exc_info=True)
    return None


def get_google_drive_service_user(creds: Any) -> Optional[Any]:
    """Alias for get_user_oauth_service (backward compatibility)."""
    return get_user_oauth_service(creds)
