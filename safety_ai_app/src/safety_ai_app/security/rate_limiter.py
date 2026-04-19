"""
Rate limiting por sessão para o SafetyAI App.

Usa st.session_state para rastrear chamadas por feature dentro de uma janela
de tempo deslizante, sem depender de serviços externos.

Features disponíveis e seus limites padrão:
  - chat_llm:     10 chamadas / 60 segundos
  - icd_api:      20 chamadas / 60 segundos
  - adzuna_api:    5 chamadas / 60 segundos
  - drive_sync:    3 chamadas / 300 segundos
  - file_upload:  20 chamadas / 300 segundos
"""

import time
import logging
from typing import Dict, Tuple

import streamlit as st

logger = logging.getLogger(__name__)

RATE_LIMITS: Dict[str, Tuple[int, int]] = {
    "chat_llm":    (10,  60),
    "icd_api":     (20,  60),
    "adzuna_api":  (5,   60),
    "drive_sync":  (3,  300),
    "file_upload": (20, 300),
}


class RateLimitExceeded(Exception):
    """Raised quando o rate limit de uma feature é excedido na sessão."""

    def __init__(self, feature: str, limit: int, window: int, retry_after: float):
        self.feature = feature
        self.limit = limit
        self.window = window
        self.retry_after = retry_after
        super().__init__(
            f"Rate limit atingido para '{feature}': {limit} chamadas / {window}s. "
            f"Tente novamente em {retry_after:.0f}s."
        )


def _get_rate_key(feature: str) -> str:
    return f"_rate_limit_{feature}"


def check_rate_limit(feature: str) -> None:
    """
    Verifica e registra uma chamada para a feature dada.

    Levanta RateLimitExceeded se o limite for excedido.
    Caso a feature não esteja configurada em RATE_LIMITS, permite sem restrição.

    Args:
        feature: Nome da feature (ex: 'chat_llm', 'icd_api').

    Raises:
        RateLimitExceeded: Quando o limite de chamadas é atingido na janela de tempo.
    """
    if feature not in RATE_LIMITS:
        return

    limit, window = RATE_LIMITS[feature]
    now = time.time()
    key = _get_rate_key(feature)

    if key not in st.session_state:
        st.session_state[key] = []

    timestamps: list = st.session_state[key]
    cutoff = now - window
    timestamps = [t for t in timestamps if t > cutoff]

    if len(timestamps) >= limit:
        oldest = timestamps[0]
        retry_after = window - (now - oldest)
        logger.warning(
            f"[RATE_LIMIT] Feature='{feature}' limit={limit}/{window}s excedido. "
            f"Retry in {retry_after:.0f}s."
        )
        raise RateLimitExceeded(feature, limit, window, max(retry_after, 1.0))

    timestamps.append(now)
    st.session_state[key] = timestamps


def get_rate_limit_status(feature: str) -> Dict[str, object]:
    """
    Retorna o status atual do rate limit para uma feature.

    Returns:
        Dict com 'calls_made', 'calls_remaining', 'window_seconds', 'limit'.
    """
    if feature not in RATE_LIMITS:
        return {"calls_made": 0, "calls_remaining": -1, "window_seconds": 0, "limit": -1}

    limit, window = RATE_LIMITS[feature]
    now = time.time()
    key = _get_rate_key(feature)
    timestamps = st.session_state.get(key, [])
    cutoff = now - window
    active = [t for t in timestamps if t > cutoff]

    return {
        "calls_made": len(active),
        "calls_remaining": max(0, limit - len(active)),
        "window_seconds": window,
        "limit": limit,
    }
