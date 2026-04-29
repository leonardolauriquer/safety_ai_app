"""
Feature access helper for SafetyAI.

Reads plan definitions from data/plans/plans.json and global feature flags
from data/feature_flags.json to determine what the current user can access.

User plan is stored in st.session_state["user_plan"] (default: "free").
Admins always bypass plan restrictions.

Failure policy: if config files cannot be loaded, the system defaults to
*deny* for restricted capabilities (fail-closed) to avoid silent privilege
escalation.

Quota de chat: persistida no Firestore via quota_manager para evitar
burla por reload ou múltiplas abas.
"""

import json
import logging
import os
from datetime import date
from typing import Any, Dict, Optional

import streamlit as st

logger = logging.getLogger(__name__)

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_DATA_DIR = os.path.abspath(os.path.join(_THIS_DIR, "..", "..", "data"))
_PLANS_PATH = os.path.join(_DATA_DIR, "plans", "plans.json")
_FLAGS_PATH = os.path.join(_DATA_DIR, "feature_flags.json")

_PLANS_LOAD_FAILED: bool = False
_FLAGS_LOAD_FAILED: bool = False
_plans_cache: Optional[Dict[str, Any]] = None
_flags_cache: Optional[Dict[str, bool]] = None

_PLAN_FEATURE_TO_FLAGS: Dict[str, list] = {
    "document_generation": ["apr_generator", "ata_generator"],
    "job_board":           ["job_board"],
    "news_feed":           ["news_feed"],
    "games":               ["games"],
    "quick_queries":       ["quick_queries"],
    "dimensioning":        ["dimensioning"],
    "knowledge_base_sync": ["knowledge_base"],
    "chat_messages_per_day": ["chat"],
}


def _load_plans() -> Optional[Dict[str, Any]]:
    """Return the plans dict, or None if loading failed."""
    global _plans_cache, _PLANS_LOAD_FAILED
    if _plans_cache is not None:
        return _plans_cache
    if _PLANS_LOAD_FAILED:
        return None
    try:
        with open(_PLANS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        _plans_cache = {p["id"]: p for p in data.get("plans", [])}
        return _plans_cache
    except Exception as e:
        logger.error(f"[feature_access] Falha ao carregar plans.json: {e}")
        _PLANS_LOAD_FAILED = True
        return None


def _load_flags() -> Optional[Dict[str, bool]]:
    """Return the feature flags dict, or None if loading failed."""
    global _flags_cache, _FLAGS_LOAD_FAILED
    if _flags_cache is not None:
        return _flags_cache
    if _FLAGS_LOAD_FAILED:
        return None
    try:
        with open(_FLAGS_PATH, "r", encoding="utf-8") as f:
            _flags_cache = json.load(f)
        return _flags_cache
    except Exception as e:
        logger.error(f"[feature_access] Falha ao carregar feature_flags.json: {e}")
        _FLAGS_LOAD_FAILED = True
        return None


def get_user_plan_id() -> str:
    """Return the active plan id for the current session user (default: 'free')."""
    return st.session_state.get("user_plan", "free")


def get_plan(plan_id: str) -> Optional[Dict[str, Any]]:
    """Return the plan dict for a given plan id, or None if not found / load failed."""
    plans = _load_plans()
    if plans is None:
        return None
    return plans.get(plan_id)


def get_user_plan() -> Optional[Dict[str, Any]]:
    """Return the full plan dict for the current user, or None if config is unavailable."""
    plan_id = get_user_plan_id()
    plan = get_plan(plan_id)
    if plan is None:
        plan = get_plan("free")
    return plan


def is_feature_globally_enabled(feature: str) -> bool:
    """
    Return True if the feature is switched on in feature_flags.json.

    Defaults to *False* (deny) when the flags file cannot be loaded,
    so a broken config does not inadvertently open access.
    """
    flags = _load_flags()
    if flags is None:
        logger.warning(
            f"[feature_access] feature_flags.json indisponível; negando '{feature}' por precaução."
        )
        return False
    return bool(flags.get(feature, True))


def user_has_feature(feature: str) -> bool:
    """
    Return True if the current user's plan grants access to *feature* AND
    all corresponding global feature flags are enabled.

    The mapping _PLAN_FEATURE_TO_FLAGS translates plan-level feature keys
    (e.g. "document_generation") to their counterparts in feature_flags.json
    (e.g. ["apr_generator", "ata_generator"]).  When no mapping exists the
    plan feature key itself is checked against the global flags file.

    Fail-closed rules:
    - If feature_flags.json cannot be loaded     → deny.
    - If plans.json cannot be loaded             → deny.
    - If the feature key is not in the plan def  → deny (warn + deny unknown features).
    - Admins bypass plan restrictions but global flags still apply.
    """
    flag_keys = _PLAN_FEATURE_TO_FLAGS.get(feature, [feature])
    for flag_key in flag_keys:
        if not is_feature_globally_enabled(flag_key):
            return False

    if st.session_state.get("is_admin", False):
        return True

    plan = get_user_plan()
    if plan is None:
        logger.warning(
            f"[feature_access] Plano do usuário indisponível; negando '{feature}' por precaução."
        )
        return False

    features = plan.get("features", {})
    if feature not in features:
        logger.warning(
            f"[feature_access] Feature '{feature}' não definida no plano '{plan.get('id', '?')}'; "
            "negando por precaução (fail-closed)."
        )
        return False

    value = features[feature]
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    return bool(value)


def get_daily_chat_limit() -> int:
    """
    Return how many chat messages the user can send per day.
    -1 means unlimited.
    Admins always get unlimited.
    Returns a conservative default (10) when config is unavailable.
    """
    if st.session_state.get("is_admin", False):
        return -1

    plan = get_user_plan()
    if plan is None:
        logger.warning(
            "[feature_access] Plano indisponível; aplicando limite conservador de 10 mensagens/dia."
        )
        return 10

    return int(plan.get("features", {}).get("chat_messages_per_day", 10))


def get_chat_messages_sent_today() -> int:
    """Return the number of chat messages sent by this user today.

    Tenta o Firestore (via quota_manager) primeiro para garantir consistência
    entre sessões e abas. Cai para session_state se o Firestore falhar.
    """
    user_id = st.session_state.get("session_id")
    if user_id:
        try:
            from safety_ai_app.auth.quota_manager import get_messages_sent_today
            return get_messages_sent_today(user_id)
        except Exception as e:
            logger.warning(f"[feature_access] Falha ao ler quota do Firestore: {e}. Usando session_state.")

    # Fallback para session_state
    today = date.today().isoformat()
    if st.session_state.get("_chat_quota_date") != today:
        st.session_state["_chat_quota_date"] = today
        st.session_state["_chat_quota_count"] = 0
    return int(st.session_state.get("_chat_quota_count", 0))


def increment_chat_messages_today() -> None:
    """Increment the daily chat message counter for the current user.

    Persiste no Firestore via quota_manager para evitar burla por reload.
    """
    user_id = st.session_state.get("session_id")
    if user_id:
        try:
            from safety_ai_app.auth.quota_manager import increment_messages_today
            increment_messages_today(user_id)
            return
        except Exception as e:
            logger.warning(f"[feature_access] Falha ao incrementar quota no Firestore: {e}. Usando session_state.")

    # Fallback para session_state
    today = date.today().isoformat()
    if st.session_state.get("_chat_quota_date") != today:
        st.session_state["_chat_quota_date"] = today
        st.session_state["_chat_quota_count"] = 0
    st.session_state["_chat_quota_count"] = st.session_state.get("_chat_quota_count", 0) + 1


def check_chat_quota() -> bool:
    """
    Return True if the user can still send messages today.
    Return False if the daily quota is exhausted.
    """
    limit = get_daily_chat_limit()
    if limit < 0:
        return True
    user_id = st.session_state.get("session_id")
    if user_id:
        try:
            from safety_ai_app.auth.quota_manager import check_quota
            return check_quota(user_id, limit)
        except Exception as e:
            logger.warning(f"[feature_access] Falha ao verificar quota no Firestore: {e}. Usando session_state.")
    sent = get_chat_messages_sent_today()
    return sent < limit


def render_upgrade_prompt(feature_label: str = "este recurso") -> None:
    """
    Render a tasteful upgrade call-to-action informing the user that
    *feature_label* is not available on their current plan.
    """
    plan = get_user_plan()
    plan_name = plan.get("name", "Gratuito") if plan else "Gratuito"

    st.markdown(
        f"""
        <div style="
            background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
            border: 1px solid rgba(74,222,128,0.25);
            border-radius: 16px;
            padding: 32px 28px;
            text-align: center;
            max-width: 540px;
            margin: 40px auto;
        ">
            <div style="font-size: 2.5rem; margin-bottom: 12px;">🔒</div>
            <h3 style="color: #f8fafc; margin: 0 0 8px 0; font-size: 1.3rem;">
                Recurso não disponível no seu plano
            </h3>
            <p style="color: #94a3b8; margin: 0 0 16px 0; font-size: 0.95rem;">
                <strong style="color:#f8fafc;">{feature_label}</strong> não está
                incluído no plano <strong style="color:#4ade80;">{plan_name}</strong>.
                Faça o upgrade para desbloquear este e outros recursos avançados.
            </p>
            <p style="color: #64748b; font-size: 0.82rem; margin: 0;">
                Entre em contato com o administrador para alterar seu plano.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_chat_quota_exceeded() -> None:
    """Render a friendly message when the user has reached their daily chat quota."""
    limit = get_daily_chat_limit()
    plan = get_user_plan()
    plan_name = plan.get("name", "Gratuito") if plan else "Gratuito"

    st.markdown(
        f"""
        <div style="
            background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
            border: 1px solid rgba(251,191,36,0.3);
            border-radius: 16px;
            padding: 24px 22px;
            text-align: center;
            margin: 16px 0;
        ">
            <div style="font-size: 2rem; margin-bottom: 10px;">⏳</div>
            <h4 style="color: #f8fafc; margin: 0 0 6px 0; font-size: 1.1rem;">
                Limite diário atingido
            </h4>
            <p style="color: #94a3b8; margin: 0 0 10px 0; font-size: 0.9rem;">
                Você utilizou suas <strong style="color:#fbbf24;">{limit} mensagens</strong>
                de hoje no plano <strong style="color:#4ade80;">{plan_name}</strong>.
                O contador é reiniciado à meia-noite.
            </p>
            <p style="color: #64748b; font-size: 0.82rem; margin: 0;">
                Para acesso ilimitado, peça ao administrador para atualizar seu plano.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )
