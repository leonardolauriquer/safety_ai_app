"""
Módulo de configuração de logging estruturado em JSON com IDs de correlação.
"""

import logging
import logging.handlers
import json
import os
import uuid
import time
from datetime import datetime, timezone
from contextlib import contextmanager
from typing import Optional, Generator

_correlation_id_store = {}

def get_correlation_id() -> str:
    """Obtém o correlation_id atual ou gera um novo."""
    try:
        import streamlit as st
        if hasattr(st, 'session_state') and 'correlation_id' in st.session_state:
            return st.session_state.correlation_id
    except Exception:
        pass
    
    thread_id = id(os.getpid())
    if thread_id in _correlation_id_store:
        return _correlation_id_store[thread_id]
    
    new_id = str(uuid.uuid4())[:8]
    _correlation_id_store[thread_id] = new_id
    return new_id


def set_correlation_id(correlation_id: str) -> None:
    """Define o correlation_id no session_state do Streamlit."""
    try:
        import streamlit as st
        if hasattr(st, 'session_state'):
            st.session_state.correlation_id = correlation_id
    except Exception:
        pass
    
    thread_id = id(os.getpid())
    _correlation_id_store[thread_id] = correlation_id


class CorrelationIdFilter(logging.Filter):
    """Filtro que adiciona correlation_id ao registro de log."""
    
    def filter(self, record: logging.LogRecord) -> bool:
        record.correlation_id = get_correlation_id()
        return True


class _SuppressScriptRunContextFilter(logging.Filter):
    """Suprime avisos ruidosos 'missing ScriptRunContext' de threads em background do Streamlit."""

    def filter(self, record: logging.LogRecord) -> bool:
        return "missing ScriptRunContext" not in record.getMessage()


class JSONFormatter(logging.Formatter):
    """Formatador que produz logs em formato JSON estruturado."""
    
    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "correlation_id": getattr(record, 'correlation_id', 'unknown')
        }
        
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)
        
        return json.dumps(log_entry, ensure_ascii=False)


def setup_logging() -> None:
    """
    Configura o sistema de logging com:
    - Formato JSON estruturado
    - Handler para console (INFO)
    - Handler para arquivo rotativo (logs/app.log, 5MB, 3 backups)
    - Filtro de correlation_id
    """
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.abspath(os.path.join(script_dir, '..', '..'))
    logs_dir = os.path.join(project_root, 'logs')
    
    os.makedirs(logs_dir, exist_ok=True)
    
    root_logger = logging.getLogger()
    
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    root_logger.setLevel(logging.DEBUG)
    
    json_formatter = JSONFormatter()
    correlation_filter = CorrelationIdFilter()
    suppress_filter = _SuppressScriptRunContextFilter()

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(json_formatter)
    console_handler.addFilter(correlation_filter)
    console_handler.addFilter(suppress_filter)
    root_logger.addHandler(console_handler)

    log_file_path = os.path.join(logs_dir, 'app.log')
    file_handler = logging.handlers.RotatingFileHandler(
        log_file_path,
        maxBytes=5 * 1024 * 1024,
        backupCount=3,
        encoding='utf-8'
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(json_formatter)
    file_handler.addFilter(correlation_filter)
    file_handler.addFilter(suppress_filter)
    root_logger.addHandler(file_handler)

    # Suprime os avisos "missing ScriptRunContext" nos loggers internos do Streamlit.
    # O logger correto em versões recentes do Streamlit é scriptrunner_utils (não scriptrunner).
    for _sc_name in (
        "streamlit.runtime.scriptrunner_utils.script_run_context",
        "streamlit.runtime.scriptrunner_utils",
        "streamlit.runtime.scriptrunner.script_run_context",
        "streamlit.runtime.scriptrunner",
        "streamlit.runtime",
        "streamlit",
        "streamlit.runtime.caching",
        "streamlit.runtime.caching.cache_data_api",
    ):
        _sc_l = logging.getLogger(_sc_name)
        _sc_l.addFilter(suppress_filter)
        for _h in _sc_l.handlers:
            _h.addFilter(suppress_filter)

    logging.getLogger(__name__).info("Logging configurado com sucesso")


@contextmanager
def log_context(operation: str) -> Generator[str, None, None]:
    """
    Context manager que define correlation_id e loga início/fim da operação com timing.
    
    Args:
        operation: Nome da operação sendo executada
        
    Yields:
        correlation_id: O ID de correlação gerado para esta operação
        
    Example:
        with log_context("processar_documento") as correlation_id:
            # código da operação
            pass
    """
    correlation_id = str(uuid.uuid4())[:8]
    set_correlation_id(correlation_id)
    
    logger = logging.getLogger(__name__)
    start_time = time.perf_counter()
    
    logger.info(f"Iniciando operação: {operation}")
    
    try:
        yield correlation_id
    except Exception as e:
        elapsed_time = (time.perf_counter() - start_time) * 1000
        logger.error(f"Erro na operação '{operation}' após {elapsed_time:.2f}ms: {e}")
        raise
    finally:
        elapsed_time = (time.perf_counter() - start_time) * 1000
        logger.info(f"Finalizando operação: {operation} - Tempo: {elapsed_time:.2f}ms")
