"""
Helpers compartilhados do Painel de Administração — SafetyAI

Contém: funções de I/O, verificação de admin, constantes de paths.
Importado por todos os módulos de tab do admin.
"""

import json
import logging
import os
from pathlib import Path
from typing import Any, List

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Paths centralizados
# ---------------------------------------------------------------------------

_PROJECT_ROOT = Path(__file__).parents[5]
_DATA_DIR = _PROJECT_ROOT / "data"

_PLANS_PATH = _DATA_DIR / "plans" / "plans.json"
_AI_CONFIG_PATH = _DATA_DIR / "ai_config.json"
_FEATURE_FLAGS_PATH = _DATA_DIR / "feature_flags.json"
_LOG_PATH = _PROJECT_ROOT / "logs" / "app.log"
_SECURITY_LOG_PATH = _PROJECT_ROOT / "logs" / "security.log"
_RAG_LOGS_DIR = _DATA_DIR / "rag_logs"
_CHROMA_DB_DIR = _DATA_DIR / "chroma_db"
_ADMIN_CONFIG_PATH = _DATA_DIR / "admin_config.json"


# ---------------------------------------------------------------------------
# Helpers de I/O JSON
# ---------------------------------------------------------------------------

def _load_json(path: Path, default: Any) -> Any:
    try:
        if path.exists():
            with path.open(encoding="utf-8") as f:
                return json.load(f)
    except Exception as exc:
        logger.warning("Falha ao carregar %s: %s", path, exc)
    return default


def _save_json(path: Path, data: Any) -> bool:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as exc:
        logger.error("Falha ao salvar %s: %s", path, exc)
        return False


def _human_size(n_bytes: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n_bytes < 1024:
            return f"{n_bytes:.1f} {unit}"
        n_bytes /= 1024
    return f"{n_bytes:.1f} TB"


# ---------------------------------------------------------------------------
# Gestão de admins
# ---------------------------------------------------------------------------

def _load_persisted_admin_emails() -> List[str]:
    """Carrega a lista de admin emails salva em disco (admin_config.json)."""
    data = _load_json(_ADMIN_CONFIG_PATH, {"admin_emails": []})
    return [e.strip().lower() for e in data.get("admin_emails", []) if e.strip()]


def _save_persisted_admin_emails(emails: List[str]) -> bool:
    """Salva a lista de admin emails em admin_config.json para persistência."""
    try:
        _ADMIN_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with _ADMIN_CONFIG_PATH.open("w", encoding="utf-8") as f:
            json.dump(
                {"admin_emails": [e.strip().lower() for e in emails if e.strip()]},
                f,
                indent=2,
            )
        return True
    except Exception as exc:
        logger.warning("Falha ao salvar admin_config.json: %s", exc)
        return False


def _is_admin() -> bool:
    """Verifica se o utilizador atual é admin via Custom Claims ou ADMIN_EMAILS."""
    import streamlit as st

    if st.session_state.get("is_admin"):
        return True
    user_email = st.session_state.get("user_email", "").strip().lower()
    if not user_email:
        return False
    raw = os.environ.get("ADMIN_EMAILS", "")
    admin_set = {e.strip().lower() for e in raw.split(",") if e.strip()}
    admin_set.update(_load_persisted_admin_emails())
    return user_email in admin_set
