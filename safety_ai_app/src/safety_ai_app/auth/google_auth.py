import os
import secrets
import json
import logging
from typing import Optional, Any, Tuple, Dict

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
import streamlit as st

logger = logging.getLogger(__name__)

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


def _get_db_connection():
    """Return a psycopg2 connection using DATABASE_URL, or None if unavailable."""
    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        return None
    try:
        import psycopg2
        conn = psycopg2.connect(database_url)
        return conn
    except Exception as e:
        logger.warning(f"Não foi possível conectar ao banco de dados: {e}")
        return None


def _ensure_token_table(conn) -> bool:
    """Create the google_oauth_tokens table if it doesn't exist. Returns True on success."""
    try:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS google_oauth_tokens (
                    id SERIAL PRIMARY KEY,
                    token_key VARCHAR(255) NOT NULL UNIQUE,
                    token_data TEXT NOT NULL,
                    updated_at TIMESTAMP DEFAULT NOW()
                )
            """)
        conn.commit()
        return True
    except Exception as e:
        logger.warning(f"Não foi possível criar tabela google_oauth_tokens: {e}")
        conn.rollback()
        return False


def _load_creds_from_db() -> Optional[Credentials]:
    """Load OAuth credentials from PostgreSQL database."""
    conn = _get_db_connection()
    if conn is None:
        return None
    try:
        _ensure_token_table(conn)
        with conn.cursor() as cur:
            cur.execute(
                "SELECT token_data FROM google_oauth_tokens WHERE token_key = %s",
                (_DB_TOKEN_KEY,)
            )
            row = cur.fetchone()
        if row is None:
            return None
        data = json.loads(row[0])
        return Credentials.from_authorized_user_info(data, SCOPES_USER)
    except (json.JSONDecodeError, KeyError, ValueError) as e:
        logger.warning(f"Erro ao deserializar token do banco de dados: {e}. Removendo para re-autenticar.")
        _delete_creds_from_db()
        return None
    except Exception as e:
        logger.warning(f"Erro ao carregar token do banco de dados: {e}")
        return None
    finally:
        conn.close()


def _save_creds_to_db(creds: Credentials) -> None:
    """Persist OAuth credentials to PostgreSQL database."""
    conn = _get_db_connection()
    if conn is None:
        raise OSError("Banco de dados indisponível — não foi possível salvar o token.")
    try:
        _ensure_token_table(conn)
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO google_oauth_tokens (token_key, token_data, updated_at)
                VALUES (%s, %s, NOW())
                ON CONFLICT (token_key) DO UPDATE
                    SET token_data = EXCLUDED.token_data,
                        updated_at = NOW()
            """, (_DB_TOKEN_KEY, creds.to_json()))
        conn.commit()
        logger.info("Token OAuth guardado no banco de dados com sucesso.")
    except Exception as e:
        conn.rollback()
        raise OSError(f"Falha ao guardar token no banco de dados: {e}") from e
    finally:
        conn.close()


def _delete_creds_from_db() -> None:
    """Remove OAuth credentials from the database."""
    conn = _get_db_connection()
    if conn is None:
        return
    try:
        _ensure_token_table(conn)
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM google_oauth_tokens WHERE token_key = %s",
                (_DB_TOKEN_KEY,)
            )
        conn.commit()
    except Exception as e:
        logger.warning(f"Erro ao remover token do banco de dados: {e}")
        conn.rollback()
    finally:
        conn.close()


def _get_service_account_credentials_from_env() -> Optional[Dict]:
    env_creds = os.environ.get('GOOGLE_SERVICE_ACCOUNT_KEY')
    if env_creds:
        try:
            return json.loads(env_creds)
        except json.JSONDecodeError as e:
            logger.warning(f"Erro ao decodificar GOOGLE_SERVICE_ACCOUNT_KEY: {e}")
    return None


def _get_client_credentials_from_env() -> Optional[Dict]:
    env_creds = os.environ.get('GOOGLE_CLIENT_CREDENTIALS')
    if env_creds:
        try:
            return json.loads(env_creds)
        except json.JSONDecodeError as e:
            logger.warning(f"Erro ao decodificar GOOGLE_CLIENT_CREDENTIALS: {e}")
    return None


def _load_creds_from_json() -> Optional[Credentials]:
    """Load OAuth credentials — database first, local file as fallback."""
    db_creds = _load_creds_from_db()
    if db_creds is not None:
        return db_creds

    if not os.path.exists(TOKEN_USER_JSON_FILE):
        return None
    try:
        with open(TOKEN_USER_JSON_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        creds = Credentials.from_authorized_user_info(data, SCOPES_USER)
        try:
            _save_creds_to_db(creds)
            os.remove(TOKEN_USER_JSON_FILE)
            logger.info("Token migrado do ficheiro local para o banco de dados.")
        except OSError as migrate_err:
            logger.warning(f"Não foi possível migrar token para o banco de dados: {migrate_err}")
        return creds
    except (json.JSONDecodeError, KeyError, ValueError) as e:
        logger.warning(f"Erro ao carregar {TOKEN_USER_JSON_FILE}: {e}. Removendo para re-autenticar.")
        os.remove(TOKEN_USER_JSON_FILE)
        return None


def _save_creds_to_json(creds: Credentials) -> None:
    """Persist OAuth credentials — database primary, local file as fallback.

    Raises OSError / IOError on write failure so callers can handle the
    situation explicitly instead of silently continuing with unsaved tokens.
    """
    try:
        _save_creds_to_db(creds)
        if os.path.exists(TOKEN_USER_JSON_FILE):
            try:
                os.remove(TOKEN_USER_JSON_FILE)
            except OSError:
                pass
    except OSError:
        logger.warning("Falha ao guardar no banco de dados; a tentar ficheiro local como fallback.")
        with open(TOKEN_USER_JSON_FILE, 'w', encoding='utf-8') as f:
            f.write(creds.to_json())


def _delete_creds() -> None:
    """Remove stored OAuth credentials from all storage locations."""
    _delete_creds_from_db()
    if os.path.exists(TOKEN_USER_JSON_FILE):
        try:
            os.remove(TOKEN_USER_JSON_FILE)
        except OSError:
            pass


def get_google_drive_user_creds_and_auth_info() -> Tuple[Optional[Any], Optional[str], Optional[str]]:
    creds = _load_creds_from_json()

    if creds and creds.valid:
        return creds, None, None

    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
        except Exception as e:
            logger.error(f"Erro ao renovar o token do usuário: {e}. Será necessária uma nova autenticação.", exc_info=True)
            _delete_creds()
            creds = None
        if creds:
            try:
                _save_creds_to_json(creds)
            except OSError as e:
                logger.warning(f"Token renovado mas não foi possível salvar: {e}. Re-autenticação necessária na próxima sessão.")
            return creds, None, None

    flow = None
    try:
        env_client_creds = _get_client_credentials_from_env()
        if env_client_creds:
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

    explicit_redirect = os.environ.get('OAUTH_REDIRECT_URI')
    replit_domain = os.environ.get('REPLIT_DEV_DOMAIN')
    if explicit_redirect:
        flow.redirect_uri = explicit_redirect
    elif replit_domain:
        flow.redirect_uri = f'https://{replit_domain}'
    else:
        flow.redirect_uri = 'http://localhost:8501'

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
            _save_creds_to_json(creds)
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
        _delete_creds()
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
            return build('drive', 'v3', credentials=creds)
        except Exception as e:
            logger.error(f"Erro ao construir serviço do Google Drive (usuário): {e}", exc_info=True)
    return None


def get_google_drive_service_user(creds: Any) -> Optional[Any]:
    """Alias for get_user_oauth_service (backward compatibility)."""
    return get_user_oauth_service(creds)
