import logging
import os
from fastapi import Request, HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
import firebase_admin
from firebase_admin import auth

logger = logging.getLogger("safety_ai_api.auth")

# Security scheme for FastAPI docs
security = HTTPBearer()

async def get_current_user(credentials: HTTPAuthorizationCredentials = Security(security)):
    """
    Middleware para verificar o token ID do Firebase.
    Extrai o user_id (uid) do token.
    """
    token = credentials.credentials
    try:
        # Verifica o token com o Firebase Admin SDK
        # Check_revoked=True garante que tokens revogados sejam rejeitados
        decoded_token = auth.verify_id_token(token, check_revoked=True)
        return decoded_token
    except auth.ExpiredIdTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expirado",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except auth.InvalidIdTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception as e:
        logger.error(f"Erro na autenticação Firebase: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Falha na autenticação",
            headers={"WWW-Authenticate": "Bearer"},
        )

async def require_admin(user: dict = Depends(get_current_user)):
    """
    Verifica se o usuário autenticado possui privilégios de administrador.
    A verificação é feita exclusivamente via Firebase Custom Claims.
    Para conceder acesso admin, use: auth.set_custom_user_claims(uid, {'is_admin': True})
    """
    is_admin = user.get("is_admin", False) or user.get("admin", False)
    if not is_admin:
        logger.warning(
            f"Acesso admin negado para uid={user.get('uid', 'unknown')} "
            f"email={user.get('email', 'unknown')}"
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso negado: Requer privilégios de administrador"
        )
    return user
