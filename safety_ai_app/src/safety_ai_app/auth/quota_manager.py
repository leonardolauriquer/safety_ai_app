"""
quota_manager.py — Gestão de quota de mensagens de chat no Firestore.

A quota é persistida na coleção:
  users/{user_id}/quota/{YYYY-MM-DD}

Isso garante que a quota seja real e não possa ser burlada simplesmente
recarregando a página ou abrindo outra aba.

Fallback: se o Firestore não estiver disponível, usa session_state como
backup para não quebrar o app completamente.
"""

import logging
from datetime import date, timezone, datetime
from typing import Optional

logger = logging.getLogger(__name__)

_QUOTA_COLLECTION = "users"
_QUOTA_SUBCOLLECTION = "quota"


def _get_today() -> str:
    """Retorna a data de hoje no formato YYYY-MM-DD (UTC)."""
    return date.today().isoformat()


def _get_quota_ref(user_id: str, day: Optional[str] = None):
    """Retorna a referência do documento de quota do usuário para o dia especificado."""
    try:
        from safety_ai_app.auth.google_auth import get_firestore_client
        db = get_firestore_client()
        day = day or _get_today()
        return db.collection(_QUOTA_COLLECTION).document(user_id).collection(_QUOTA_SUBCOLLECTION).document(day)
    except Exception as e:
        logger.warning(f"[quota_manager] Não foi possível obter ref do Firestore: {e}")
        return None


def get_messages_sent_today(user_id: str) -> int:
    """
    Retorna o número de mensagens enviadas pelo usuário hoje.
    Tenta o Firestore primeiro; cai para session_state em caso de falha.
    """
    import streamlit as st

    # Fallback rápido: se não há user_id, usa session_state
    if not user_id:
        return int(st.session_state.get("_chat_quota_count", 0))

    today = _get_today()

    # Cache na sessão para reduzir leituras ao Firestore (TTL de 1 minuto)
    cache_key = f"_quota_cache_{today}"
    cache_ts_key = f"_quota_cache_ts_{today}"

    import time
    cached_ts = st.session_state.get(cache_ts_key, 0)
    if time.time() - cached_ts < 60 and cache_key in st.session_state:
        return int(st.session_state[cache_key])

    ref = _get_quota_ref(user_id, today)
    if ref is None:
        return int(st.session_state.get("_chat_quota_count", 0))

    try:
        doc = ref.get()
        count = doc.to_dict().get("count", 0) if doc.exists else 0
        # Atualiza o cache de sessão
        st.session_state[cache_key] = count
        st.session_state[cache_ts_key] = time.time()
        return int(count)
    except Exception as e:
        logger.warning(f"[quota_manager] Erro ao ler quota do Firestore: {e}")
        return int(st.session_state.get("_chat_quota_count", 0))


def increment_messages_today(user_id: str) -> int:
    """
    Incrementa o contador de mensagens do usuário no Firestore.
    Retorna o novo total após o incremento.
    Usa transação atômica para evitar race conditions.
    """
    import streamlit as st
    import time

    today = _get_today()
    cache_key = f"_quota_cache_{today}"
    cache_ts_key = f"_quota_cache_ts_{today}"

    # Incremento local (sempre, para resposta imediata)
    current = int(st.session_state.get("_chat_quota_count", 0)) + 1
    st.session_state["_chat_quota_count"] = current
    st.session_state["_chat_quota_date"] = today

    if not user_id:
        return current

    ref = _get_quota_ref(user_id, today)
    if ref is None:
        return current

    try:
        from google.cloud.firestore import SERVER_TIMESTAMP
        # Incremento atômico no Firestore usando transação
        from firebase_admin import firestore as fb_firestore
        db = ref._client
        transaction = db.transaction()

        @fb_firestore.transactional
        def _update_in_transaction(transaction, ref):
            snapshot = ref.get(transaction=transaction)
            new_count = (snapshot.to_dict().get("count", 0) if snapshot.exists else 0) + 1
            transaction.set(ref, {
                "count": new_count,
                "last_updated": SERVER_TIMESTAMP,
                "user_id": user_id,
                "date": today,
            }, merge=True)
            return new_count

        new_count = _update_in_transaction(transaction, ref)
        # Sincroniza o cache de sessão com o valor real do Firestore
        st.session_state["_chat_quota_count"] = new_count
        st.session_state[cache_key] = new_count
        st.session_state[cache_ts_key] = time.time()
        return new_count
    except Exception as e:
        logger.warning(f"[quota_manager] Erro ao incrementar quota no Firestore: {e}. Usando session_state como fallback.")
        return current


def check_quota(user_id: str, daily_limit: int) -> bool:
    """
    Retorna True se o usuário ainda pode enviar mensagens hoje.
    Retorna False se a quota diária foi atingida.
    -1 como limit = ilimitado.
    """
    if daily_limit < 0:
        return True
    sent = get_messages_sent_today(user_id)
    return sent < daily_limit
