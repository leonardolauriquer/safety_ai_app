"""
Logger de eventos de segurança para o SafetyAI App.

Garante que PII (email, nome) nunca apareça em texto claro nos logs.
Todos os eventos de segurança são gravados com correlation_id e
identificadores mascarados/hasheados.

Eventos registrados:
  - login_success / login_failure / logout
  - rate_limit_exceeded
  - file_rejected (tamanho, tipo, etc.)
  - auth_error / csrf_error
  - session_timeout
  - temp_cleanup
"""

import hashlib
import logging
from enum import Enum
from typing import Optional

logger = logging.getLogger("safety_ai.security")


class SecurityEvent(str, Enum):
    LOGIN_SUCCESS = "login_success"
    LOGIN_FAILURE = "login_failure"
    LOGOUT = "logout"
    SESSION_TIMEOUT = "session_timeout"
    CSRF_ERROR = "csrf_error"
    AUTH_ERROR = "auth_error"
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"
    FILE_REJECTED = "file_rejected"
    FILE_UPLOADED = "file_uploaded"
    TEMP_CLEANUP = "temp_cleanup"
    SUSPICIOUS_INPUT = "suspicious_input"
    PROMPT_INJECTION_ATTEMPT = "prompt_injection_attempt"


_MAX_DETAIL_LENGTH = 200
_MAX_EXTRA_VALUE_LENGTH = 120


def _mask_identifier(value: Optional[str]) -> str:
    """
    Mascara um identificador sensível retornando um hash SHA-256 truncado (12 chars).
    Retorna 'unknown' se o valor for vazio.
    """
    if not value:
        return "unknown"
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:12]


def _safe_truncate(value: str, max_len: int) -> str:
    """Trunca strings longas para evitar logging acidental de dados sensíveis."""
    if len(value) > max_len:
        return value[:max_len] + "…[truncated]"
    return value


def _get_correlation_id() -> str:
    try:
        import streamlit as st
        return st.session_state.get("correlation_id", "no-session")
    except Exception:
        return "no-session"


def log_security_event(
    event: SecurityEvent,
    *,
    user_email: Optional[str] = None,
    detail: Optional[str] = None,
    feature: Optional[str] = None,
    file_name: Optional[str] = None,
    file_size_mb: Optional[float] = None,
    extra: Optional[dict] = None,
) -> None:
    """
    Registra um evento de segurança sem expor PII em texto claro.

    Args:
        event:        Tipo do evento (SecurityEvent).
        user_email:   Email do usuário — será hasheado antes de logar.
        detail:       Descrição adicional do evento.
        feature:      Feature relacionada (ex: 'chat_llm', 'file_upload').
        file_name:    Nome do arquivo (ex: ao rejeitar upload).
        file_size_mb: Tamanho do arquivo em MB.
        extra:        Dicionário de dados adicionais (não-PII).
    """
    payload: dict = {
        "security_event": event.value,
        "correlation_id": _get_correlation_id(),
    }

    if user_email:
        payload["user_hash"] = _mask_identifier(user_email)

    if detail:
        payload["detail"] = _safe_truncate(str(detail), _MAX_DETAIL_LENGTH)

    if feature:
        payload["feature"] = feature

    if file_name:
        payload["file_name"] = _safe_truncate(str(file_name), 128)

    if file_size_mb is not None:
        payload["file_size_mb"] = round(file_size_mb, 2)

    if extra:
        for k, v in extra.items():
            if k not in payload:
                payload[k] = _safe_truncate(str(v), _MAX_EXTRA_VALUE_LENGTH) if isinstance(v, str) else v

    level = logging.WARNING if event in {
        SecurityEvent.RATE_LIMIT_EXCEEDED,
        SecurityEvent.FILE_REJECTED,
        SecurityEvent.SESSION_TIMEOUT,
        SecurityEvent.SUSPICIOUS_INPUT,
    } else (
        logging.ERROR if event in {
            SecurityEvent.CSRF_ERROR,
            SecurityEvent.AUTH_ERROR,
            SecurityEvent.LOGIN_FAILURE,
        } else logging.INFO
    )

    logger.log(level, str(payload))
