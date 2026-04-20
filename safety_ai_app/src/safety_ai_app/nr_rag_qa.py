import os
import json
import logging
import math
import threading
import uuid
import importlib.metadata
import re
from pathlib import Path
from typing import List, Dict, Any, Optional, Callable, Generator
from datetime import datetime
from operator import itemgetter
from urllib.parse import quote_plus

from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import (
    ChatPromptTemplate,
    SystemMessagePromptTemplate,
    HumanMessagePromptTemplate,
    MessagesPlaceholder,
)
from langchain_core.runnables import RunnablePassthrough, RunnableParallel, RunnableLambda
from langchain_openai import ChatOpenAI
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.messages import HumanMessage, AIMessage

from langchain_community.retrievers import BM25Retriever
from langchain_core.retrievers import BaseRetriever
from langchain_core.callbacks.manager import CallbackManagerForRetrieverRun


class EnsembleRetriever(BaseRetriever):
    """Retriever leve que combina BM25 e retriever semântico sem depender de langchain 0.3.x."""

    retrievers: List[Any]
    weights: List[float]

    def _get_relevant_documents(
        self, query: str, *, run_manager: CallbackManagerForRetrieverRun
    ) -> List[Document]:
        all_docs: Dict[str, Document] = {}
        scores: Dict[str, float] = {}

        for retriever, weight in zip(self.retrievers, self.weights):
            docs = retriever.invoke(query)
            for rank, doc in enumerate(docs):
                doc_id = doc.page_content[:200]
                if doc_id not in all_docs:
                    all_docs[doc_id] = doc
                    scores[doc_id] = 0.0
                scores[doc_id] += weight * (1.0 / (rank + 1))

        sorted_ids = sorted(scores, key=scores.__getitem__, reverse=True)
        return [all_docs[doc_id] for doc_id in sorted_ids]

try:
    from safety_ai_app.security.security_logger import log_security_event, SecurityEvent as _SecurityEvent
    _SEC_LOGGER_AVAILABLE = True
except ImportError:
    _SEC_LOGGER_AVAILABLE = False

try:
    from safety_ai_app.observability.rag_logger import get_rag_logger as _get_rag_logger
    _RAG_LOGGER_AVAILABLE = True
except ImportError:
    _RAG_LOGGER_AVAILABLE = False

from safety_ai_app.document_processors import (
    PDF_EXTRACTION_CONFIG,
    UniversalDocumentLoader,
    _lazy_import_sentence_transformer,
    log_module_availability,
)
from safety_ai_app.text_extractors import PROCESSABLE_MIME_TYPES

logger = logging.getLogger(__name__)

_script_dir = os.path.dirname(os.path.abspath(__file__))
_project_root = os.path.abspath(os.path.join(_script_dir, '..', '..'))

CHROMADB_PERSIST_DIRECTORY = os.path.join(_project_root, "data", "chroma_db")
COLLECTION_NAME = "nrs_collection"
EMBEDDING_MODEL_NAME = 'intfloat/multilingual-e5-large-instruct'
RERANKER_MODEL_NAME = 'cross-encoder/mmarco-mMiniLMv2-L12-H384-v1'
RERANKER_TOP_N = 5

_AI_CONFIG_PATH = os.path.join(_project_root, "data", "ai_config.json")

_AI_CONFIG_DEFAULTS: Dict[str, Any] = {
    "model": "openai/gpt-4o-mini",
    "temperature_factual": 0.1,
    "temperature_document": 0.5,
    "max_history_tokens": 16000,
    "max_history_turns": 10,
    "guardrail_threshold": 0.3,
    "retriever_top_k": 6,
    "bm25_weight": 0.3,
    "semantic_weight": 0.7,
}


def _load_ai_config() -> Dict[str, Any]:
    """Load AI configuration from data/ai_config.json with hardcoded fallbacks."""
    cfg = dict(_AI_CONFIG_DEFAULTS)
    try:
        if os.path.isfile(_AI_CONFIG_PATH):
            with open(_AI_CONFIG_PATH, "r", encoding="utf-8") as f:
                file_cfg = json.load(f)
            cfg.update(file_cfg)
            logger.info("AI config loaded from %s", _AI_CONFIG_PATH)
        else:
            logger.warning("AI config file not found at %s — using hardcoded defaults.", _AI_CONFIG_PATH)
    except Exception as exc:
        logger.warning("Failed to load AI config from %s: %s — using hardcoded defaults.", _AI_CONFIG_PATH, exc)
    return cfg

# Callback signature: (level: str, message: str) -> None
# where level is one of "info", "warning", "error", "success".
# Use make_streamlit_status_callback() to get a Streamlit-routing version,
# or pass any compatible two-argument callable (e.g., lambda level, msg: print(msg)).
StatusCallback = Optional[Callable[[str, str], None]]

try:
    logger.info(f"LangChain-Core: {importlib.metadata.version('langchain-core')}")
    logger.info(f"LangChain-Chroma: {importlib.metadata.version('langchain-chroma')}")
except importlib.metadata.PackageNotFoundError as e:
    logger.warning(f"Versão de pacote LangChain não encontrada: {e}")


# ---------------------------------------------------------------------------
# Helpers de módulo
# ---------------------------------------------------------------------------

def _load_system_prompt() -> str:
    prompt_path = Path(_script_dir) / "prompts" / "system_prompt.md"
    return prompt_path.read_text(encoding="utf-8")


def make_streamlit_status_callback() -> Callable[[str, str], None]:
    """
    Returns a two-argument (level, message) callback that routes to the
    appropriate Streamlit status widget.  Import streamlit lazily so that
    this module remains importable without a Streamlit context.

    Usage::

        from safety_ai_app.nr_rag_qa import NRQuestionAnswering, make_streamlit_status_callback
        qa = NRQuestionAnswering(on_status=make_streamlit_status_callback())
    """
    import streamlit as st

    def _callback(level: str, message: str) -> None:
        try:
            from streamlit.runtime.scriptrunner import get_script_run_ctx
            if get_script_run_ctx() is None:
                logger.info(f"[{level.upper()}] {message}")
                return
        except Exception:
            logger.info(f"[{level.upper()}] {message}")
            return
        if level == "error":
            st.error(message)
        elif level == "warning":
            st.warning(message)
        elif level == "success":
            st.success(message)
        else:
            st.info(message)

    return _callback


def _get_clean_document_name(doc_name: str) -> str:
    cleaned = re.sub(r' - Versão \d+\.\d+\.\d+$', '', doc_name, flags=re.IGNORECASE).strip()
    cleaned = re.sub(r' v\d+\.\d+\.\d+$', '', cleaned, flags=re.IGNORECASE).strip()
    return cleaned


def _extract_nr_from_query(query: str) -> Optional[str]:
    match = re.search(r'(?:NR|N\.R\.)\s*(\d+)', query, re.IGNORECASE)
    if match:
        return f"nr-{match.group(1)}"
    return None


def _clean_llm_output(output: str) -> str:
    if not output:
        return ""
    html_tags = ['</div>', '</p>', '<div>', '<p>', '</span>', '<span>', '</br>', '<br>', '<br/>']
    cleaned = output
    for tag in html_tags:
        cleaned = cleaned.replace(tag, '')
    return cleaned.strip()


def _log_module_availability():
    import streamlit as st
    logger.info(f"Streamlit Version: {st.__version__}")
    log_module_availability()


# ---------------------------------------------------------------------------
# Embeddings
# ---------------------------------------------------------------------------

class CustomHuggingFaceEmbeddings:
    """Wrapper de embeddings com suporte a modelos E5 (prefixos query/passage)."""

    def __init__(self, model_name: str):
        SentenceTransformer = _lazy_import_sentence_transformer()
        self.model = SentenceTransformer(model_name)
        self._is_e5 = "e5" in model_name.lower()
        logger.info(f"CustomHuggingFaceEmbeddings: Modelo '{model_name}' carregado (e5={self._is_e5}).")

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []
        if self._is_e5:
            texts = ["passage: " + t for t in texts]
        return self.model.encode(texts, convert_to_numpy=True, normalize_embeddings=True).tolist()

    def embed_query(self, text: str) -> List[float]:
        if not text:
            return []
        if self._is_e5:
            text = "query: " + text
        return self.model.encode([text], convert_to_numpy=True, normalize_embeddings=True)[0].tolist()


# ---------------------------------------------------------------------------
# NR structural chunking helpers
# ---------------------------------------------------------------------------

_NR_ITEM_PATTERN = re.compile(
    r'(?m)^(\d{1,2}(?:\.\d+){1,5})\s+',
)
_NR_CHAPTER_PATTERN = re.compile(
    r'(?mi)^(CAP[IÍ]TULO\s+[IVXLCDM\d]+|ANEXO\s+[IVXLCDM\d]+|SEÇÃO\s+[IVXLCDM\d]+)',
)
_NR_NUMBER_FROM_NAME = re.compile(r'NR[\s\-_]?(\d{1,2})', re.IGNORECASE)
_NR_ITEM_META = re.compile(r'^(\d{1,2})(?:\.(\d+))?(?:\.\d+)*\s+')


def _extract_nr_metadata_from_content(text: str, doc_name: str = "") -> Dict[str, str]:
    """Extract nr_number, article, and item from chunk text and document name."""
    nr_number = ""
    article = ""
    item = ""

    m = _NR_NUMBER_FROM_NAME.search(doc_name)
    if m:
        nr_number = m.group(1)

    if not nr_number:
        m = re.search(r'NR[\s\-]?(\d{1,2})', text[:500], re.IGNORECASE)
        if m:
            nr_number = m.group(1)

    m = re.search(r'art(?:igo)?\.?\s*(\d+)', text[:300], re.IGNORECASE)
    if m:
        article = m.group(1)

    m = _NR_ITEM_META.search(text.lstrip())
    if m:
        item = m.group(0).strip()

    section = f"NR-{nr_number} {item}".strip() if nr_number else item
    return {"nr_number": nr_number, "article": article, "item": item, "section": section}


def _split_nr_document_structurally(
    documents: List[Document],
    chunk_size: int = 1000,
    chunk_overlap: int = 200,
) -> List[Document]:
    """
    Structural splitter for NR regulatory documents.

    Strategy:
    1. For each raw page document, detect item/chapter boundaries.
    2. Split text at those boundaries to form logical sections.
    3. Apply RecursiveCharacterTextSplitter within each section.
    4. Enrich metadata with nr_number, article, item.
    """
    base_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        add_start_index=True,
        length_function=len,
        separators=["\n\n", "\n", " ", ""],
    )

    result_chunks: List[Document] = []

    for doc in documents:
        text = doc.page_content
        doc_name = doc.metadata.get("document_name", "")

        boundary_positions = set()
        boundary_positions.add(0)
        for m in _NR_ITEM_PATTERN.finditer(text):
            boundary_positions.add(m.start())
        for m in _NR_CHAPTER_PATTERN.finditer(text):
            boundary_positions.add(m.start())

        sorted_positions = sorted(boundary_positions)

        sections = []
        for i, start in enumerate(sorted_positions):
            end = sorted_positions[i + 1] if i + 1 < len(sorted_positions) else len(text)
            section_text = text[start:end].strip()
            if section_text:
                sections.append(section_text)

        if not sections:
            sections = [text]

        for section in sections:
            section_doc = Document(page_content=section, metadata=dict(doc.metadata))
            sub_chunks = base_splitter.split_documents([section_doc])
            for chunk in sub_chunks:
                if not chunk.page_content.strip():
                    continue
                nr_meta = _extract_nr_metadata_from_content(chunk.page_content, doc_name)
                chunk.metadata.update(nr_meta)
                result_chunks.append(chunk)

    return result_chunks


# ---------------------------------------------------------------------------
# Cross-encoder reranker (lazy loaded)
# ---------------------------------------------------------------------------

_reranker_instance = None
_reranker_lock = threading.Lock()


def _get_reranker():
    global _reranker_instance
    if _reranker_instance is not None:
        return _reranker_instance if _reranker_instance is not False else None
    with _reranker_lock:
        if _reranker_instance is None:
            try:
                from sentence_transformers import CrossEncoder
                _reranker_instance = CrossEncoder(RERANKER_MODEL_NAME)
                logger.info(f"Cross-encoder reranker '{RERANKER_MODEL_NAME}' carregado.")
            except Exception as e:
                logger.warning(f"Falha ao carregar cross-encoder reranker: {e}. Reranking desativado.")
                _reranker_instance = False
    return _reranker_instance if _reranker_instance is not False else None


def _rerank_documents(query: str, docs: List[Document], top_n: int = RERANKER_TOP_N) -> List[Document]:
    """Apply cross-encoder reranking to a list of documents."""
    if not docs:
        return docs
    reranker = _get_reranker()
    if reranker is None:
        return docs[:top_n]
    try:
        pairs = [(query, doc.page_content) for doc in docs]
        scores = reranker.predict(pairs)
        ranked = sorted(zip(scores, docs), key=lambda x: x[0], reverse=True)
        logger.info(f"Reranker: {len(docs)} → top {top_n} documentos selecionados.")
        return [doc for _, doc in ranked[:top_n]]
    except Exception as e:
        logger.warning(f"Erro no reranker: {e}. Retornando docs sem reranking.")
        return docs[:top_n]


# ---------------------------------------------------------------------------
# Background model pre-warming
# ---------------------------------------------------------------------------

_warmup_done = threading.Event()
_warmup_thread: Optional[threading.Thread] = None


def _warmup_worker() -> None:
    """Pre-load the cross-encoder reranker in the background.

    The embedding model is already loaded eagerly by NRQuestionAnswering.__init__
    (via get_qa_instance_cached). Loading it again here would cause a duplicate
    1.1 GB model load. Only the reranker is truly lazy-loaded on the first query.
    """
    _reranker_ok = False
    try:
        logger.info("[WARMUP] Pre-loading cross-encoder reranker '%s'…", RERANKER_MODEL_NAME)
        result = _get_reranker()
        if result is not None:
            _reranker_ok = True
            logger.info("[WARMUP] Reranker loaded successfully.")
        else:
            logger.warning("[WARMUP] Reranker unavailable after pre-load attempt.")
    except Exception as exc:
        logger.warning("[WARMUP] Could not pre-load reranker: %s", exc)

    _warmup_done.set()
    status = "complete" if _reranker_ok else "finished (reranker unavailable)"
    logger.info("[WARMUP] Model warmup %s.", status)


def start_model_warmup() -> None:
    """Start background model pre-loading. Safe to call multiple times."""
    global _warmup_thread
    if _warmup_done.is_set():
        return
    if _warmup_thread is not None and _warmup_thread.is_alive():
        return
    _warmup_thread = threading.Thread(
        target=_warmup_worker, daemon=True, name="model-warmup"
    )
    _warmup_thread.start()
    logger.info("[WARMUP] Background model warmup thread started.")


def is_warmup_complete() -> bool:
    """Return True if the reranker background warmup has finished.

    The embedding model is loaded eagerly by NRQuestionAnswering.__init__
    (via get_qa_instance_cached), so it is not tracked here.
    """
    return _warmup_done.is_set()


# ---------------------------------------------------------------------------
# NR PDF background indexing (admin feature)
# ---------------------------------------------------------------------------

_nr_indexing_thread: Optional[threading.Thread] = None
_nr_indexing_status: Dict[str, Any] = {}
_nr_indexing_lock = threading.Lock()

NR_INDEXING_STATUS_FILE = os.path.join(
    os.path.dirname(CHROMADB_PERSIST_DIRECTORY), "nr_indexing_status.json"
)


def get_indexed_nr_numbers_from_mte(collection) -> list:
    """Return list of NR numbers (int) already indexed from MTE-oficial source."""
    try:
        result = collection.get(include=["metadatas"])
        indexed = set()
        for meta in result.get("metadatas", []):
            if meta.get("source") == "MTE-oficial":
                nr = meta.get("nr_number")
                if isinstance(nr, int):
                    indexed.add(nr)
                elif isinstance(nr, str):
                    try:
                        clean = nr.replace("NR-", "").lstrip("0") or "0"
                        indexed.add(int(clean))
                    except ValueError:
                        pass
        return sorted(indexed)
    except Exception as e:
        logger.warning(f"[NR-INDEX] Erro ao checar NRs indexadas: {e}")
        return []


def _nr_indexing_worker(qa_instance, nr_list: list) -> None:
    """Background thread: indexes NR PDFs using the app's existing QA instance."""
    import json as _json

    nrs_dir = os.path.join(os.path.dirname(CHROMADB_PERSIST_DIRECTORY), "nrs")
    status: Dict[str, Any] = {
        "running": True, "started_at": datetime.now().isoformat(),
        "total": len(nr_list), "done": 0, "errors": 0,
        "current": None, "results": {}
    }

    def _save_status():
        try:
            with open(NR_INDEXING_STATUS_FILE, "w") as f:
                _json.dump(status, f)
        except Exception:
            pass

    _save_status()

    for nr in nr_list:
        pdf_path = os.path.join(nrs_dir, f"NR-{nr:02d}.pdf")
        status["current"] = f"NR-{nr:02d}"
        _save_status()

        if not os.path.exists(pdf_path):
            logger.warning(f"[NR-INDEX] NR-{nr:02d}: PDF não encontrado")
            status["results"][str(nr)] = {"status": "not_found"}
            status["done"] += 1
            _save_status()
            continue

        try:
            meta = {
                "nr_number": nr,
                "doc_type": "norma_regulamentadora",
                "source": "MTE-oficial",
                "source_file": f"NR-{nr:02d}.pdf",
                "document_name": f"NR-{nr:02d}",
                "source_type": "local_pdf",
                "extraction_method": "pypdf",
                "file_type": "application/pdf",
            }
            before = qa_instance.vector_db._collection.count()
            qa_instance.process_document_to_chroma(
                file_path=pdf_path,
                document_name=f"NR-{nr:02d}.pdf",
                source="MTE-oficial",
                file_type="application/pdf",
                additional_metadata=meta,
            )
            after = qa_instance.vector_db._collection.count()
            added = after - before
            logger.info(f"[NR-INDEX] NR-{nr:02d}: OK, +{added} chunks (total: {after})")
            status["results"][str(nr)] = {"status": "ok", "chunks_added": added}
        except Exception as e:
            logger.error(f"[NR-INDEX] NR-{nr:02d}: ERRO — {e}", exc_info=True)
            status["results"][str(nr)] = {"status": "error", "error": str(e)}
            status["errors"] += 1

        status["done"] += 1
        _save_status()

    status["running"] = False
    status["current"] = None
    status["finished_at"] = datetime.now().isoformat()
    _save_status()
    logger.info(f"[NR-INDEX] Indexamento concluído. {status['done']}/{status['total']} NRs processadas.")


def start_nr_indexing_background(qa_instance, nr_list: list) -> bool:
    """Start background NR indexing. Returns False if already running."""
    global _nr_indexing_thread
    with _nr_indexing_lock:
        if _nr_indexing_thread is not None and _nr_indexing_thread.is_alive():
            return False
        _nr_indexing_thread = threading.Thread(
            target=_nr_indexing_worker,
            args=(qa_instance, nr_list),
            daemon=True,
            name="nr-indexing",
        )
        _nr_indexing_thread.start()
        logger.info(f"[NR-INDEX] Background indexing started for {len(nr_list)} NRs.")
        return True


def get_nr_indexing_status() -> Dict[str, Any]:
    """Return current indexing status from file."""
    import json as _json
    try:
        if os.path.exists(NR_INDEXING_STATUS_FILE):
            with open(NR_INDEXING_STATUS_FILE) as f:
                return _json.load(f)
    except Exception:
        pass
    return {}


def is_nr_indexing_running() -> bool:
    """True if the background indexing thread is still alive."""
    global _nr_indexing_thread
    return _nr_indexing_thread is not None and _nr_indexing_thread.is_alive()


# ---------------------------------------------------------------------------
# NRQuestionAnswering
# ---------------------------------------------------------------------------

class NRQuestionAnswering:
    def __init__(
        self,
        collection_name: str = COLLECTION_NAME,
        model_name: str = EMBEDDING_MODEL_NAME,
        chroma_persist_directory: str = CHROMADB_PERSIST_DIRECTORY,
        on_status: StatusCallback = None,
    ):
        self._on_status: Callable[[str, str], None] = on_status or (
            lambda level, msg: logger.info(f"[{level.upper()}] {msg}")
        )

        self.collection_name = collection_name
        self.chroma_persist_directory = chroma_persist_directory

        self.embedding_function = CustomHuggingFaceEmbeddings(model_name=model_name)
        logger.info(f"Loaded embeddings model: {EMBEDDING_MODEL_NAME}")

        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000, chunk_overlap=200,
            add_start_index=True, length_function=len, is_separator_regex=False,
        )
        self.backup_splitter = RecursiveCharacterTextSplitter(
            chunk_size=200, chunk_overlap=40,
            add_start_index=True, length_function=len, is_separator_regex=False,
        )

        self._ai_cfg = _load_ai_config()
        self._apply_ai_config(self._ai_cfg)

        self.chroma_client = self._initialize_chroma()
        self.vector_db = Chroma(
            collection_name=self.collection_name,
            embedding_function=self.embedding_function,
            client=self.chroma_client,
            persist_directory=self.chroma_persist_directory,
        )
        self.chroma_doc_count = self.vector_db._collection.count()
        if self.chroma_doc_count > 0:
            logger.info(f"ChromaDB: Collection '{COLLECTION_NAME}' loaded with {self.chroma_doc_count} documents.")
        else:
            logger.warning(f"ChromaDB: Collection '{COLLECTION_NAME}' is empty.")

        self.llm = self._initialize_llm()
        self.vector_retriever = self.vector_db.as_retriever(
            search_type="similarity", search_kwargs={"k": self._retriever_top_k}
        )
        self.bm25_retriever = self._initialize_bm25_retriever()
        self.retriever = self._create_ensemble_retriever()
        self.retriever_type = "Ensemble Retriever" if self.bm25_retriever else "Vector Retriever (fallback)"
        self.rag_chain = self._setup_rag_chain()

        logger.info(f"NRQuestionAnswering inicializado. Retriever: {self.retriever_type}")

    # ------------------------------------------------------------------
    # Status helper
    # ------------------------------------------------------------------

    def _notify(self, level: str, message: str) -> None:
        self._on_status(level, message)

    # ------------------------------------------------------------------
    # Config helpers
    # ------------------------------------------------------------------

    def _apply_ai_config(self, cfg: Dict[str, Any]) -> None:
        """Extract typed config values from a config dict into instance attributes."""
        self._llm_model_name: str = str(cfg.get("model", _AI_CONFIG_DEFAULTS["model"]))
        self._temperature_factual: float = float(cfg.get("temperature_factual", _AI_CONFIG_DEFAULTS["temperature_factual"]))
        self._temperature_document: float = float(cfg.get("temperature_document", _AI_CONFIG_DEFAULTS["temperature_document"]))
        self._max_history_turns: int = int(cfg.get("max_history_turns", _AI_CONFIG_DEFAULTS["max_history_turns"]))
        self._max_history_tokens: int = int(cfg.get("max_history_tokens", _AI_CONFIG_DEFAULTS["max_history_tokens"]))
        self._retriever_top_k: int = int(cfg.get("retriever_top_k", _AI_CONFIG_DEFAULTS["retriever_top_k"]))
        self._bm25_weight: float = float(cfg.get("bm25_weight", _AI_CONFIG_DEFAULTS["bm25_weight"]))
        self._semantic_weight: float = float(cfg.get("semantic_weight", _AI_CONFIG_DEFAULTS["semantic_weight"]))
        self._guardrail_threshold: float = max(0.0, min(1.0, float(
            cfg.get("guardrail_threshold", _AI_CONFIG_DEFAULTS["guardrail_threshold"])
        )))
        logger.info(
            "AI config applied: model=%s, temp_factual=%.2f, temp_doc=%.2f, top_k=%d, "
            "bm25_w=%.2f, sem_w=%.2f, max_turns=%d, max_tokens=%d, guardrail_threshold=%.2f",
            self._llm_model_name, self._temperature_factual, self._temperature_document,
            self._retriever_top_k, self._bm25_weight, self._semantic_weight,
            self._max_history_turns, self._max_history_tokens, self._guardrail_threshold,
        )

    def reload_from_config(self) -> bool:
        """Re-read data/ai_config.json and apply new settings to the live pipeline.

        Re-initialises the LLM, retrievers and RAG chain without restarting the
        app or reloading the ChromaDB/embedding model (which are expensive).
        Returns True on success, False if an error occurred.
        """
        try:
            new_cfg = _load_ai_config()
            self._apply_ai_config(new_cfg)
            self._ai_cfg = new_cfg

            self.llm = self._initialize_llm()
            self.vector_retriever = self.vector_db.as_retriever(
                search_type="similarity", search_kwargs={"k": self._retriever_top_k}
            )
            self.bm25_retriever = self._initialize_bm25_retriever()
            self.retriever = self._create_ensemble_retriever()
            self.retriever_type = "Ensemble Retriever" if self.bm25_retriever else "Vector Retriever (fallback)"
            self.rag_chain = self._setup_rag_chain()

            logger.info("Pipeline reloaded from config. model=%s, top_k=%d", self._llm_model_name, self._retriever_top_k)
            self._notify("success", f"Pipeline recarregado com modelo '{self._llm_model_name}'.")
            return True
        except Exception as exc:
            logger.error("Failed to reload pipeline from config: %s", exc, exc_info=True)
            self._notify("error", f"Erro ao recarregar pipeline: {exc}")
            return False

    # ------------------------------------------------------------------
    # Initializers
    # ------------------------------------------------------------------

    def _initialize_chroma(self):
        try:
            from chromadb import PersistentClient
            os.makedirs(self.chroma_persist_directory, exist_ok=True)
            client = PersistentClient(path=self.chroma_persist_directory)
            logger.info(f"ChromaDB PersistentClient inicializado em: {self.chroma_persist_directory}")
            return client
        except Exception as e:
            logger.critical(f"CRITICAL ERROR initializing ChromaDB: {e}", exc_info=True)
            self._notify("error", f"Erro crítico ao inicializar ChromaDB. Detalhes: {e}")
            raise

    def _initialize_llm(self):
        ai_key = os.getenv("AI_INTEGRATIONS_OPENROUTER_API_KEY")
        ai_base = os.getenv("AI_INTEGRATIONS_OPENROUTER_BASE_URL")
        openrouter_key = os.getenv("OPENROUTER_API_KEY")
        model_name = getattr(self, "_llm_model_name", _AI_CONFIG_DEFAULTS["model"])
        init_temperature = getattr(self, "_temperature_factual", 0.1)

        if ai_key and ai_base:
            try:
                llm = ChatOpenAI(
                    openai_api_base=ai_base,
                    openai_api_key=ai_key,
                    model_name=model_name,
                    temperature=init_temperature,
                    max_tokens=8192,
                )
                logger.info(f"LLM via Replit AI Integrations ({model_name}) inicializado.")
                return llm
            except Exception as e:
                logger.warning(f"Falha na integração Replit OpenRouter: {e}. Tentando fallback...")

        if openrouter_key:
            try:
                llm = ChatOpenAI(
                    openai_api_base="https://openrouter.ai/api/v1",
                    openai_api_key=openrouter_key,
                    model_name=model_name,
                    temperature=init_temperature,
                    max_tokens=8192,
                    model_kwargs={
                        "extra_headers": {
                            "HTTP-Referer": "https://safetyai.streamlit.app/",
                            "X-Title": "SafetyAI - SST",
                        }
                    },
                )
                logger.info(f"LLM via OpenRouter direto ({model_name}) inicializado.")
                return llm
            except Exception as e:
                err_msg = str(e)
                logger.error(f"Erro ao inicializar LLM OpenRouter: {err_msg}", exc_info=True)
                self._notify("error", f"Erro ao inicializar modelo: {err_msg}")
                return None

        self._notify(
            "error",
            "Configuração de IA não encontrada! Configure OpenRouter via Replit AI Integrations ou OPENROUTER_API_KEY.",
        )
        return None

    def _initialize_bm25_retriever(self):
        if self.chroma_doc_count > 0:
            results = self.vector_db._collection.get(
                ids=self.vector_db._collection.get()['ids'],
                include=['documents', 'metadatas'],
            )
            all_docs = [
                Document(page_content=content, metadata=meta)
                for content, meta in zip(results['documents'], results['metadatas'])
            ]
            top_k = getattr(self, "_retriever_top_k", _AI_CONFIG_DEFAULTS["retriever_top_k"])
            logger.info(f"BM25Retriever: {len(all_docs)} documentos indexados (k={top_k}).")
            return BM25Retriever.from_documents(all_docs, k=top_k)
        return None

    def _create_ensemble_retriever(self, vector_retriever=None, bm25_retriever=None):
        top_k = getattr(self, "_retriever_top_k", _AI_CONFIG_DEFAULTS["retriever_top_k"])
        vr = vector_retriever or self.vector_db.as_retriever(search_type="similarity", search_kwargs={"k": top_k})
        br = bm25_retriever if bm25_retriever is not None else self.bm25_retriever
        if br:
            sem_w = getattr(self, "_semantic_weight", _AI_CONFIG_DEFAULTS["semantic_weight"])
            bm25_w = getattr(self, "_bm25_weight", _AI_CONFIG_DEFAULTS["bm25_weight"])
            logger.info(f"EnsembleRetriever configurado (Vector + BM25, pesos sem={sem_w:.2f}/bm25={bm25_w:.2f}).")
            return EnsembleRetriever(retrievers=[vr, br], weights=[sem_w, bm25_w])
        logger.warning("Usando apenas Vector Retriever (ChromaDB vazio ou sem documentos).")
        return vr

    # ------------------------------------------------------------------
    # RAG chain
    # ------------------------------------------------------------------

    def _setup_rag_chain(self):
        if not self.llm:
            logger.warning("LLM não inicializado. Cadeia RAG não configurada.")
            self._notify("warning", "LLM não inicializado. A cadeia RAG não pode ser configurada.")
            return None

        system_prompt_text = _load_system_prompt()
        system_message_prompt = SystemMessagePromptTemplate.from_template(system_prompt_text)
        human_message_prompt = HumanMessagePromptTemplate.from_template("{question}")
        prompt = ChatPromptTemplate.from_messages([
            system_message_prompt,
            MessagesPlaceholder(variable_name="chat_history_messages"),
            human_message_prompt,
        ])

        def process_retrieved_docs(retrieved_info: Dict[str, Any]) -> Dict[str, Any]:
            return self._process_retrieved_docs(retrieved_info["docs"], retrieved_info["query"])

        rag_chain = (
            RunnableParallel(
                retrieved_data=RunnablePassthrough.assign(
                    docs=RunnableLambda(lambda x: _rerank_documents(
                        x["question"],
                        self._get_retriever_for_query(
                            x.get("expanded_query") or x["question"]
                        ).invoke(x.get("expanded_query") or x["question"]),
                    )),
                    query=itemgetter("question"),
                ) | RunnableLambda(process_retrieved_docs),
                question=itemgetter("question"),
                chat_history_messages=itemgetter("chat_history_messages"),
                dynamic_context_str=itemgetter("dynamic_context_texts") | RunnableLambda(
                    lambda x: (
                        "\n\n### Documentos Anexados pelo Usuário (ALTA PRIORIDADE):\n"
                        + "\n---\n".join(x) + "\n---\n"
                    ) if x else ""
                ),
            )
            | RunnablePassthrough.assign(
                retrieved_context=itemgetter("retrieved_data") | RunnableLambda(lambda x: x["formatted_context"])
            )
            | {
                "answer": (
                    prompt | self.llm | StrOutputParser() | RunnableLambda(_clean_llm_output)
                ),
                "suggested_downloads": itemgetter("retrieved_data") | RunnableLambda(
                    lambda x: x["suggested_downloads"]
                ),
            }
        )
        logger.info(f"Cadeia RAG configurada usando {self.retriever_type}.")
        return rag_chain

    def _get_retriever_for_query(self, query: str):
        nr_detected = _extract_nr_from_query(query)
        if nr_detected:
            logger.info(f"NR '{nr_detected}' detectada — filtro via post-filtering.")
        return self.retriever

    def _expand_query(self, query: str) -> str:
        """
        Use the LLM to generate an expanded/reformulated version of the user query
        to maximize semantic and lexical recall during retrieval.
        Returns the expanded query string or the original if expansion fails.
        """
        if not self.llm:
            return query
        try:
            expansion_prompt = (
                "Você é um assistente especializado em Saúde e Segurança do Trabalho (SST) no Brasil.\n"
                "Reformule e expanda a pergunta abaixo para maximizar a recuperação de trechos relevantes "
                "de Normas Regulamentadoras (NRs) e documentos de SST.\n"
                "Produza UMA versão expandida: inclua sinônimos técnicos, siglas, termos correlatos em português.\n"
                "Retorne APENAS a pergunta expandida, sem explicações.\n\n"
                f"Pergunta original: {query}"
            )
            from langchain_core.messages import HumanMessage as _HumanMessage
            response = self.llm.invoke([_HumanMessage(content=expansion_prompt)])
            expanded = response.content.strip() if hasattr(response, 'content') else str(response).strip()
            if expanded and len(expanded) > 10:
                logger.info(f"Query expansion: '{query[:60]}' → '{expanded[:80]}'")
                return expanded
        except Exception as e:
            logger.warning(f"Query expansion falhou: {e}. Usando query original.")
        return query

    # ------------------------------------------------------------------
    # Retrieval helpers
    # ------------------------------------------------------------------

    def _process_retrieved_docs(self, docs: List[Document], query: str) -> Dict[str, Any]:
        """Process retrieved docs into formatted context string and download list."""
        nr_filter = _extract_nr_from_query(query)
        filtered_docs = []

        if nr_filter:
            nr_number = nr_filter.replace('nr-', '')
            search_patterns = [
                rf"nr-{nr_number}[\-\.]", rf"nr{nr_number}[\-\.]",
                rf"NR{nr_number}[\-\.]", rf"NR-{nr_number}[\-\.]",
                rf"nr[\-\s]*{nr_number}[\-\s]", rf"NR[\-\s]*{nr_number}[\-\s]",
            ]
            content_patterns = [
                rf"NR[\-\s]*{nr_number}[\.\-\s]",
                rf"Norma[\s]+Regulamentadora[\s]+n?º?[\s]*{nr_number}",
                rf"NR[\s]*{nr_number}[\s]*[\-\:]",
            ]
            for doc in docs:
                name_raw = doc.metadata.get('document_name', '')
                content = doc.page_content or ''
                in_name = any(re.search(p, name_raw, re.IGNORECASE) for p in search_patterns)
                in_content = any(re.search(p, content[:500], re.IGNORECASE) for p in content_patterns)
                if in_name or in_content:
                    filtered_docs.append(doc)

            if not filtered_docs:
                logger.warning(f"Post-filtering para '{nr_filter}' resultou em 0 docs.")
                fallback_terms = (
                    ["instalações elétricas", "segurança elétrica", "eletricidade"]
                    if nr_number == '10'
                    else [f"nr {nr_number}", f"norma {nr_number}"]
                )
                for doc in docs[:10]:
                    if any(t.lower() in doc.page_content.lower() for t in fallback_terms):
                        filtered_docs.append(doc)
                if not filtered_docs:
                    filtered_docs = docs[:5]
        else:
            filtered_docs = docs

        formatted_context = []
        unique_docs_for_download: Dict[str, Dict] = {}

        for doc in filtered_docs:
            doc_name_raw = doc.metadata.get('document_name', 'Documento Desconhecido')
            clean_doc_name = _get_clean_document_name(doc_name_raw)
            page_number = doc.metadata.get('page_number', doc.metadata.get('page', 'N/A'))
            drive_file_id = doc.metadata.get('drive_file_id', None)
            file_type = doc.metadata.get('file_type', 'application/octet-stream')

            url_viewer = "N/A"
            if drive_file_id:
                url_viewer = f"https://drive.google.com/file/d/{quote_plus(drive_file_id)}/view?usp=drivesdk"

            source_metadata_str = (
                f"document_name_clean: '{clean_doc_name}', "
                f"page_number: '{page_number}', "
                f"url_viewer: '{url_viewer}'"
            )
            formatted_context.append(
                f"--- Início do Conteúdo do Documento ---\n{doc.page_content}\n"
                f"--- Fim do Conteúdo do Documento ---\nMETADATA_FONTE_INTERNA: {source_metadata_str}"
            )

            if drive_file_id and drive_file_id not in unique_docs_for_download:
                unique_docs_for_download[drive_file_id] = {
                    "document_name": clean_doc_name,
                    "drive_file_id": drive_file_id,
                    "file_type": file_type,
                }

        if not filtered_docs:
            logger.warning("Nenhum documento recuperado. LLM responderá sem contexto específico.")

        return {
            "formatted_context": "\n\n".join(formatted_context),
            "suggested_downloads": list(unique_docs_for_download.values()),
        }

    def _retrieve_and_format(
        self,
        query: str,
        dynamic_context_texts: List[str],
    ) -> Dict[str, Any]:
        """Retrieve docs and return formatted context + downloads + dynamic context str."""
        docs = self._get_retriever_for_query(query).invoke(query)
        result = self._process_retrieved_docs(docs, query)

        dynamic_context_str = ""
        if dynamic_context_texts:
            dynamic_context_str = (
                "\n\n### Documentos Anexados pelo Usuário (ALTA PRIORIDADE):\n"
                + "\n---\n".join(dynamic_context_texts) + "\n---\n"
            )

        return {
            "retrieved_context": result["formatted_context"],
            "suggested_downloads": result["suggested_downloads"],
            "dynamic_context_str": dynamic_context_str,
        }

    # ------------------------------------------------------------------
    # History compression
    # ------------------------------------------------------------------

    def _compress_history_if_needed(
        self,
        messages: List[Any],
        max_turns: int = 10,
        max_chars: int = 16000,
    ) -> List[Any]:
        """
        Summarize old messages when history exceeds max_turns or max_chars.
        Returns a new list where old messages are replaced by a summary AIMessage.
        """
        if len(messages) <= max_turns * 2:
            total_chars = sum(len(m.content) for m in messages if hasattr(m, 'content'))
            if total_chars <= max_chars:
                return messages

        keep_recent = max_turns
        to_compress = messages[:-keep_recent] if len(messages) > keep_recent else []
        recent = messages[-keep_recent:] if len(messages) > keep_recent else messages

        if not to_compress or not self.llm:
            return messages

        try:
            history_text = "\n".join(
                f"{'Usuário' if isinstance(m, HumanMessage) else 'SafetyAI'}: {m.content}"
                for m in to_compress
            )
            summary_prompt = (
                "Você é um assistente que resume conversas sobre SST (Saúde e Segurança do Trabalho). "
                "Resuma o seguinte histórico de conversa em português, preservando os pontos técnicos "
                "mais importantes (NRs citadas, perguntas principais, conclusões):\n\n"
                f"{history_text}\n\n"
                "Resuma em até 400 palavras, mantendo os fatos técnicos essenciais."
            )
            summary_response = self.llm.invoke(summary_prompt)
            summary_content = summary_response.content if hasattr(summary_response, 'content') else str(summary_response)
            summary_message = AIMessage(content=f"[Resumo do histórico anterior]\n{summary_content}")
            logger.info(f"Histórico comprimido: {len(to_compress)} mensagens → 1 resumo.")
            return [summary_message] + list(recent)
        except Exception as e:
            logger.warning(f"Falha na compressão de histórico: {e}. Usando histórico completo.")
            return messages

    # ------------------------------------------------------------------
    # Dynamic temperature
    # ------------------------------------------------------------------

    _DOC_GENERATION_PATTERNS = re.compile(
        r'(cri[ae]\s|elabor[ae]\s|redij[ae]\s|escreva\s|gere?\s|mont[ae]\s|formul[ae]\s|'
        r'\bapr\b|\bata\b|relat[oó]rio\s+de\s|laudo\s+t[eé]cnico|'
        r'\bpcmso\b|\bpgr\b|\bltcat\b|\bppp\b|\bppra\b|\bpcmat\b|'
        r'modelo\s+de|template\s+de|exemplo\s+de\s+documento)',
        re.IGNORECASE,
    )

    def _detect_temperature(self, query: str) -> float:
        """Return document or factual temperature based on query type (values from ai_config.json)."""
        temp_doc = getattr(self, "_temperature_document", _AI_CONFIG_DEFAULTS["temperature_document"])
        temp_factual = getattr(self, "_temperature_factual", _AI_CONFIG_DEFAULTS["temperature_factual"])
        return temp_doc if self._DOC_GENERATION_PATTERNS.search(query) else temp_factual

    def _create_llm_for_streaming(self, temperature: float):
        """Create a ChatOpenAI instance configured for streaming with the given temperature."""
        ai_key = os.getenv("AI_INTEGRATIONS_OPENROUTER_API_KEY")
        ai_base = os.getenv("AI_INTEGRATIONS_OPENROUTER_BASE_URL")
        openrouter_key = os.getenv("OPENROUTER_API_KEY")
        model_name = getattr(self.llm, 'model_name', "openai/gpt-oss-120b")
        max_tokens = getattr(self.llm, 'max_tokens', 8192) or 8192

        try:
            if ai_key and ai_base:
                return ChatOpenAI(
                    openai_api_base=ai_base,
                    openai_api_key=ai_key,
                    model_name=model_name,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    streaming=True,
                )
            if openrouter_key:
                base_model_kwargs = getattr(self.llm, 'model_kwargs', {}) or {}
                return ChatOpenAI(
                    openai_api_base="https://openrouter.ai/api/v1",
                    openai_api_key=openrouter_key,
                    model_name=model_name,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    streaming=True,
                    model_kwargs=base_model_kwargs,
                )
        except Exception as e:
            logger.warning(f"Falha ao criar LLM de streaming: {e}. Usando LLM padrão.")
        return self.llm

    # ------------------------------------------------------------------
    # Streaming
    # ------------------------------------------------------------------

    def stream_answer_question(
        self,
        query: str,
        chat_history: List[Dict[str, str]],
        dynamic_context_texts: List[str] = [],
    ) -> Generator[str, None, None]:
        """
        Generator that yields validated text chunks.

        All tokens are buffered internally and safety-checked BEFORE being
        yielded to the caller, so no unsafe content ever reaches the UI.
        Call get_last_suggested_downloads() after exhausting the generator.
        """
        self._last_suggested_downloads: List[Dict] = []

        if not self.llm:
            yield "O sistema de IA não está completamente inicializado. Por favor, tente novamente mais tarde."
            return

        try:
            chat_history_messages: List[Any] = []
            for msg in chat_history:
                role = msg.get("role", "")
                if role == "user":
                    chat_history_messages.append(HumanMessage(content=msg["content"]))
                elif role in ("ai", "assistant"):
                    content = msg["content"]
                    if isinstance(content, dict) and 'answer' in content:
                        content = content["answer"]
                    if isinstance(content, str):
                        chat_history_messages.append(AIMessage(content=content))

            chat_history_messages = self._compress_history_if_needed(
                chat_history_messages,
                max_turns=getattr(self, "_max_history_turns", _AI_CONFIG_DEFAULTS["max_history_turns"]),
                max_chars=getattr(self, "_max_history_tokens", _AI_CONFIG_DEFAULTS["max_history_tokens"]),
            )

            context_data = self._retrieve_and_format(query, dynamic_context_texts)

            temperature = self._detect_temperature(query)
            streaming_llm = self._create_llm_for_streaming(temperature)

            system_prompt_text = _load_system_prompt()
            system_message_prompt = SystemMessagePromptTemplate.from_template(system_prompt_text)
            human_message_prompt = HumanMessagePromptTemplate.from_template("{question}")
            prompt = ChatPromptTemplate.from_messages([
                system_message_prompt,
                MessagesPlaceholder(variable_name="chat_history_messages"),
                human_message_prompt,
            ])

            prompt_value = prompt.format_messages(
                retrieved_context=context_data["retrieved_context"],
                dynamic_context_str=context_data["dynamic_context_str"],
                chat_history_messages=chat_history_messages,
                question=query,
            )

            # Buffer all tokens before yielding — guardrail runs on the full text
            buffered_tokens: List[str] = []
            for chunk in streaming_llm.stream(prompt_value):
                token = chunk.content if hasattr(chunk, 'content') else str(chunk)
                if token:
                    buffered_tokens.append(token)

            full_text = "".join(buffered_tokens)

            if self._is_jailbreak_response(full_text):
                logger.warning(f"Stream bloqueado por guardrail (jailbreak). Query: '{query[:80]}'")
                if _SEC_LOGGER_AVAILABLE:
                    log_security_event(
                        _SecurityEvent.PROMPT_INJECTION_ATTEMPT,
                        feature="llm_stream_guardrail",
                        extra={"guardrail": "jailbreak", "query_excerpt": query[:80]},
                    )
                yield self._SAFE_REFUSAL
                return

            if self._is_off_domain_response(full_text):
                logger.warning(f"Stream bloqueado por guardrail (fora do domínio SST). Query: '{query[:80]}'")
                if _SEC_LOGGER_AVAILABLE:
                    log_security_event(
                        _SecurityEvent.PROMPT_INJECTION_ATTEMPT,
                        feature="llm_stream_guardrail",
                        extra={"guardrail": "off_domain", "query_excerpt": query[:80]},
                    )
                yield self._SAFE_REFUSAL
                return

            # Safe — yield buffered tokens for progressive display
            self._last_suggested_downloads = context_data["suggested_downloads"]
            for token in buffered_tokens:
                yield token

        except Exception as e:
            err_msg = str(e)
            logger.error(f"Erro no streaming para '{query}': {err_msg}", exc_info=True)
            yield f"Desculpe, ocorreu um erro ao gerar a resposta. Detalhes: {err_msg}."

    def get_last_suggested_downloads(self) -> List[Dict]:
        """Return suggested_downloads populated by the last stream_answer_question call."""
        return getattr(self, '_last_suggested_downloads', [])

    # ------------------------------------------------------------------
    # Retriever update
    # ------------------------------------------------------------------

    def update_retrievers(self):
        try:
            self.chroma_doc_count = self.vector_db._collection.count()
            self.vector_retriever = self.vector_db.as_retriever(search_type="similarity", search_kwargs={"k": 10})
            self.bm25_retriever = self._initialize_bm25_retriever()
            self.retriever = self._create_ensemble_retriever()
            self.retriever_type = "Ensemble Retriever" if self.bm25_retriever else "Vector Retriever (fallback)"
            self.rag_chain = self._setup_rag_chain()
            logger.info(f"Cadeia RAG atualizada: {self.retriever_type}")
        except Exception as e:
            err_msg = str(e)
            logger.error(f"Erro ao atualizar retrievers: {err_msg}", exc_info=True)
            self._notify("error", f"Erro ao configurar busca. Usando busca vetorial. Detalhes: {err_msg}")
            self.vector_retriever = self.vector_db.as_retriever(search_type="similarity", search_kwargs={"k": 10})
            self.bm25_retriever = None
            self.retriever = self.vector_retriever
            self.retriever_type = "Vector Retriever (fallback)"
            self.rag_chain = self._setup_rag_chain()

    # ------------------------------------------------------------------
    # Document ingestion
    # ------------------------------------------------------------------

    def _get_loader_for_file_type(self, file_path: str, file_type: str) -> UniversalDocumentLoader:
        return UniversalDocumentLoader(file_path, file_type)

    def _extract_text_content_debug(self, documents: List[Document]) -> str:
        all_text = ""
        for i, doc in enumerate(documents):
            page_content = doc.page_content.strip()
            all_text += page_content + "\n"
            char_count = len(page_content)
            extraction_method = doc.metadata.get('extraction_method', 'unknown')
            page_num = doc.metadata.get('page_number', doc.metadata.get('page', 'N/A'))
            if char_count == 0:
                logger.warning(f"Página {page_num} (idx {i}): VAZIO — {extraction_method}")
            elif char_count < 50:
                logger.warning(f"Página {page_num} (idx {i}): MUITO PEQUENO ({char_count} chars) — {extraction_method}")
            else:
                logger.info(f"Página {page_num} (idx {i}): OK ({char_count} chars) — {extraction_method}")
        return all_text.strip()

    def process_document_to_chroma(
        self,
        file_path: str,
        document_name: str,
        source: str = "Local",
        file_type: str = "application/pdf",
        additional_metadata: Optional[Dict[str, Any]] = None,
    ):
        logger.info(f"Processando documento: '{document_name}' ({file_type})")
        try:
            if not os.path.exists(file_path):
                logger.error(f"Arquivo não encontrado: {file_path}")
                self._notify("error", f"Arquivo '{document_name}' não encontrado.")
                return

            if file_type not in PROCESSABLE_MIME_TYPES:
                logger.error(f"Tipo '{file_type}' não suportado.")
                self._notify("warning", f"Tipo '{file_type}' não suportado. Documento '{document_name}' ignorado.")
                return

            loader = self._get_loader_for_file_type(file_path, file_type)
            documents = loader.load()
            logger.info(f"'{document_name}' carregado: {len(documents)} páginas/elementos.")

            doc_meta_id = (
                additional_metadata.get("drive_file_id")
                if additional_metadata and additional_metadata.get("drive_file_id")
                else str(uuid.uuid4())
            )
            base_metadata = {
                "document_name": document_name,
                "source": source,
                "file_type": file_type,
                "upload_timestamp": datetime.now().isoformat(),
                "document_metadata_id": doc_meta_id,
                "extraction_success": True,
            }
            if additional_metadata:
                base_metadata.update(additional_metadata)

            for doc in documents:
                doc.metadata.update(base_metadata)
                if "page" in doc.metadata:
                    doc.metadata["page_number"] = str(doc.metadata["page"])
                    doc.metadata["page"] = doc.metadata["page_number"]
                elif "loc" in doc.metadata and isinstance(doc.metadata["loc"], dict):
                    pn = str(doc.metadata["loc"].get("page_number", "1"))
                    doc.metadata["page_number"] = pn
                    doc.metadata["page"] = pn
                    del doc.metadata["loc"]
                elif "page_number" not in doc.metadata:
                    doc.metadata["page_number"] = "1"
                    doc.metadata["page"] = "1"
                else:
                    doc.metadata["page"] = doc.metadata["page_number"]

            total_text = "\n".join(d.page_content for d in documents).strip()
            total_len = len(total_text)
            for doc in documents:
                doc.metadata["total_text_length"] = total_len

            logger.info(f"Total de caracteres extraídos: {total_len}")

            if total_len == 0:
                logger.warning(f"Nenhum texto extraído de '{document_name}'.")
                self._notify("warning", f"'{document_name}' não contém texto extraível.")
                return

            if total_len < PDF_EXTRACTION_CONFIG["min_text_length"]:
                self._notify("warning", f"'{document_name}' contém muito pouco texto ({total_len} caracteres).")

            self._extract_text_content_debug(documents)

            chunks = _split_nr_document_structurally(documents, chunk_size=1000, chunk_overlap=200)
            logger.info(f"'{document_name}': {len(chunks)} chunks (structural NR chunker, chunk_size=1000).")

            if len(chunks) == 0:
                chunks = self.text_splitter.split_documents(documents)
                logger.info(f"Fallback text_splitter: {len(chunks)} chunks.")

            if len(chunks) == 0:
                chunks = self.backup_splitter.split_documents(documents)
                logger.info(f"Fallback backup_splitter: {len(chunks)} chunks.")

            if len(chunks) == 0 and total_len > 0:
                chunks = [Document(
                    page_content=total_text,
                    metadata={**base_metadata, "page_number": "1", "chunk_id": str(uuid.uuid4()), "chunk_method": "single_fallback"},
                )]
                logger.info("Criado 1 chunk único (fallback).")
            elif len(chunks) == 0:
                self._notify("error", f"'{document_name}' não pôde ser processado — conteúdo vazio.")
                return

            for chunk in chunks:
                if "chunk_id" not in chunk.metadata:
                    chunk.metadata["chunk_id"] = str(uuid.uuid4())

            try:
                self.vector_db.add_documents(chunks)
                logger.info(f"{len(chunks)} chunks de '{document_name}' adicionados ao ChromaDB.")

                if hasattr(self.vector_db, 'persist'):
                    self.vector_db.persist()

                extraction_methods = set(d.metadata.get('extraction_method', 'standard') for d in documents)
                extraction_info = ", ".join(extraction_methods) or "standard"
                self._notify("success", f"'{document_name}' processado com sucesso ({len(chunks)} chunks, extração: {extraction_info}).")
                self.update_retrievers()

            except Exception as chroma_error:
                err_msg = str(chroma_error)
                logger.error(f"Erro ao adicionar chunks ao ChromaDB para '{document_name}': {err_msg}", exc_info=True)
                if "Expected Embeddings to be non-empty" in err_msg:
                    self._notify("error", f"Erro ao processar '{document_name}': chunks vazios ou inválidos para embeddings.")
                else:
                    self._notify("error", f"Erro ao adicionar '{document_name}' ao banco de dados: {err_msg}")
                return

        except Exception as e:
            err_msg = str(e)
            logger.error(f"Erro geral ao processar '{document_name}': {err_msg}", exc_info=True)
            self._notify("error", f"Erro ao processar '{document_name}'. Detalhes: {err_msg}")

    def add_simple_text_to_collection(
        self,
        content: str,
        document_name: str,
        source: str = "Local",
        source_type: str = "User Input",
        metadata: Optional[Dict[str, Any]] = None,
    ):
        doc_metadata = metadata if metadata is not None else {}
        doc_meta_id = doc_metadata.get("document_metadata_id") or str(uuid.uuid4())
        doc_metadata.update({
            "document_name": document_name,
            "source": source,
            "source_type": source_type,
            "file_type": "text/plain",
            "page_number": "1",
            "document_metadata_id": doc_meta_id,
            "chunk_id": str(uuid.uuid4()),
        })
        doc = Document(page_content=content, metadata=doc_metadata)
        self.vector_db.add_documents([doc])
        logger.info(f"Texto '{document_name}' (ID: {doc_meta_id}) adicionado ao ChromaDB.")
        self.update_retrievers()

    # ------------------------------------------------------------------
    # Query / management helpers
    # ------------------------------------------------------------------

    def list_processed_documents(self) -> List[Dict]:
        if not (self.vector_db and hasattr(self.vector_db, '_collection') and self.vector_db._collection):
            logger.warning("ChromaDB não disponível para listar documentos.")
            return []

        results = self.vector_db._collection.get(ids=None, include=['metadatas'])
        documents_info: Dict[str, Dict] = {}
        for metadata in results.get('metadatas', []):
            doc_name = metadata.get("document_name")
            if not doc_name:
                continue
            source = metadata.get("source", "Unknown")
            source_type = metadata.get("source_type", "N/A")
            doc_meta_id = metadata.get("document_metadata_id") or f"{doc_name}-{source}-{source_type}"
            if doc_meta_id not in documents_info:
                documents_info[doc_meta_id] = {
                    "name": doc_name, "source": source, "source_type": source_type,
                    "chunks": 0, "file_type": metadata.get("file_type"),
                    "drive_file_id": metadata.get("drive_file_id"),
                    "document_metadata_id": doc_meta_id,
                }
            documents_info[doc_meta_id]["chunks"] += 1

        sorted_docs = sorted(documents_info.values(), key=lambda x: x['name'])
        logger.info(f"Listados {len(sorted_docs)} documentos únicos no ChromaDB.")
        return sorted_docs

    def get_drive_file_ids_in_chroma(self, source_type: Optional[str] = None) -> List[str]:
        if not (hasattr(self, 'vector_db') and self.vector_db and
                hasattr(self.vector_db, '_collection') and self.vector_db._collection):
            return []
        try:
            where_clause = {"source_type": source_type} if source_type else {}
            results = self.vector_db._collection.get(where=where_clause, ids=None, include=['metadatas'])
            file_ids = {m['drive_file_id'] for m in results.get('metadatas', []) if m.get('drive_file_id')}
            return list(file_ids)
        except Exception as e:
            logger.error(f"Erro ao buscar drive_file_ids (source_type={source_type}): {e}", exc_info=True)
            return []

    def clear_chroma_collection(self) -> None:
        try:
            if self.vector_db and self.vector_db._client:
                self.vector_db._client.delete_collection(self.vector_db._collection.name)
                logger.info(f"Collection '{self.collection_name}' deletada.")

            self.vector_db = Chroma(
                collection_name=self.collection_name,
                embedding_function=self.embedding_function,
                client=self.chroma_client,
                persist_directory=self.chroma_persist_directory,
            )
            self.vector_retriever = self.vector_db.as_retriever(search_type="similarity", search_kwargs={"k": 10})
            self.bm25_retriever = None
            self.retriever = self.vector_retriever
            self.retriever_type = "Vector Retriever (fallback)"
            self.rag_chain = self._setup_rag_chain()
            logger.info("ChromaDB reinicializado como coleção vazia.")

        except Exception as e:
            err_msg = str(e)
            logger.error(f"Erro ao limpar ChromaDB: {err_msg}", exc_info=True)
            self._notify("error", f"Erro ao limpar a base de conhecimento. Detalhes: {err_msg}")
            raise

    def clear_docs_by_source_type(self, source_type_to_remove: str) -> int:
        if not (self.vector_db and hasattr(self.vector_db, '_collection') and self.vector_db._collection):
            logger.warning("ChromaDB não disponível.")
            return 0
        try:
            deleted_ids = self.vector_db.delete(where={"source_type": source_type_to_remove})
            if deleted_ids:
                logger.info(f"Removidos {len(deleted_ids)} chunks com source_type '{source_type_to_remove}'.")
                self.update_retrievers()
                return len(deleted_ids)
            return 0
        except Exception as e:
            err_msg = str(e)
            logger.error(f"Erro ao remover por source_type: {err_msg}", exc_info=True)
            self._notify("error", f"Erro ao remover documentos por tipo de fonte. Detalhes: {err_msg}")
            return 0

    def remove_document_by_id(self, document_metadata_id: str) -> int:
        if not (self.vector_db and hasattr(self.vector_db, '_collection') and self.vector_db._collection):
            logger.warning("ChromaDB não disponível.")
            return 0
        try:
            deleted_ids = self.vector_db.delete(where={"document_metadata_id": document_metadata_id})
            if deleted_ids:
                logger.info(f"Removidos {len(deleted_ids)} chunks para id '{document_metadata_id}'.")
                self.update_retrievers()
                return len(deleted_ids)
            return 0
        except Exception as e:
            err_msg = str(e)
            logger.error(f"Erro ao remover documento '{document_metadata_id}': {err_msg}", exc_info=True)
            self._notify("error", f"Erro ao remover documento. Detalhes: {err_msg}")
            return 0

    # Padrões que indicam que o LLM pode ter sido manipulado para sair do domínio SST.
    _JAILBREAK_RESPONSE_PATTERNS = re.compile(
        r'(ignor(?:e|ando|ei)\s+(minhas?\s+)?instru[çc][oõ]es|'
        r'modo?\s+desenvolvedor|'
        r'sem\s+(restri[çc][oõ]es|filtros|limites)|'
        r'estou\s+livre\s+para|'
        r'posso\s+agora\s+(?:fazer|dizer|responder)|'
        r'dan\s+mode|jailbreak|'
        r'as an ai without restrictions|'
        r'ignoring\s+(my\s+)?previous\s+(instructions?|constraints?)|'
        r'sure[,.]?\s+i\'?ll?\s+ignore|'
        r'pretend\s+(you\s+are|to\s+be)|'
        r'act\s+as\s+if\s+you\s+have\s+no|'
        r'forget\s+(your|all)\s+(previous\s+)?(instructions?|rules?|constraints?))',
        re.IGNORECASE,
    )

    # Palavras-chave do domínio SST: respostas legítimas deveriam conter ao menos uma.
    _SST_DOMAIN_KEYWORDS = re.compile(
        r'(nr[\s\-]?\d+|norma\s+regulamentadora|segura[nç]|trabalhador|'
        r'epi|epc|cipa|sesmt|ppgr|pcmso|pgr|ltcat|cbo|cnae|cid[\s\-]?\d|'
        r'acidente|risco\s+ocup|insalubre|periculoso|ergonomia|brigada\s+de|'
        r'laudo\s+t[eé]cnico|fiscali[zs]a|minist[eé]rio\s+do\s+trabalho|'
        r'\bmte\b|\bsst\b|saúde\s+ocupacional|medicina\s+do\s+trabalho|'
        r'equipamento\s+de\s+prote|certificado\s+de\s+aprova|'
        r'trabalho\s+em\s+altura|espa[çc]o\s+confinado|atividade\s+insalubre|'
        r'atividade\s+perigosa|agen?te\s+(f[ií]sico|qu[ií]mico|biol[oó]gico)|'
        r'cat\b|fat\b|nexo\s+t[eé]cnico|dose\s+di[aá]ria|limite\s+de\s+toler|'
        r'programa\s+de\s+preven|gest[aã]o\s+de\s+riscos|apr\b|ata\s+de|'
        r'investigar\s+acidente|[aá]rvore\s+de\s+causas|laudo\s+pericial|'
        r'quadro\s+i\s+da\s+nr|adi[çc]ional\s+de\s+insalubridade|'
        r'ppp\b|e\s*social\b|rat\b|\bsat\b|ntep\b)',
        re.IGNORECASE,
    )

    # Indicadores de recusa legítima pelo próprio modelo (não deve ser bloqueada).
    _REFUSAL_PATTERNS = re.compile(
        r'(fora\s+da\s+minha\s+[aá]rea|especializa[çc][aã]o|'
        r'n[aã]o\s+posso\s+(?:ajudar|responder)|'
        r'n[aã]o\s+est[oá]\s+(?:dentro|relacionado)|'
        r'limite\s+de\s+(?:minha|meu)|'
        r'safetyai|sst\s+no\s+brasil|'
        r'al[eé]m\s+da\s+minha\s+especializa|'
        r'reformul[ae]\s+(sua\s+)?pergunta|'
        r'restrij[ao]\s+a\s+temas)',
        re.IGNORECASE,
    )

    _SAFE_REFUSAL = (
        "Essa solicitação está além da minha área de especialização em Saúde e Segurança do Trabalho (SST). "
        "Não consigo ajudar com esse tema, mas posso ajudá-lo se a pergunta for reformulada para um contexto de SST — por exemplo:\n"
        "- 'Quais riscos de segurança estão associados a [atividade]?'\n"
        "- 'Qual NR regula [processo/equipamento]?'\n"
        "- 'Como elaborar o PGR para [setor]?'\n\n"
        "Como posso ajudá-lo dentro do universo SST?"
    )

    def _is_jailbreak_response(self, answer: str) -> bool:
        """Verifica se a resposta do LLM apresenta marcadores de jailbreak/evasão de domínio."""
        return bool(self._JAILBREAK_RESPONSE_PATTERNS.search(answer))

    def _is_off_domain_response(self, answer: str) -> bool:
        """
        Detecta respostas substantivas sem termos suficientes do domínio SST.

        The sensitivity is controlled by ``guardrail_threshold`` (0.0–1.0):
        - 0.0  → guardrail disabled; never block.
        - 0.3  → (default) require ≥1 SST keyword match — same behaviour as before.
        - 1.0  → require ≥3 SST keyword matches (stricter).

        Formula: required_matches = ceil(threshold * 3), minimum 1.
        Short responses and recognised refusal patterns are always exempt.
        """
        threshold = getattr(self, "_guardrail_threshold", _AI_CONFIG_DEFAULTS["guardrail_threshold"])
        if threshold <= 0.0:
            return False
        if len(answer) < 250:
            return False
        if self._REFUSAL_PATTERNS.search(answer):
            return False
        required = max(1, math.ceil(threshold * 3))
        matches = self._SST_DOMAIN_KEYWORDS.findall(answer)
        return len(matches) < required

    def answer_question(
        self,
        query: str,
        chat_history: List[Dict[str, str]],
        dynamic_context_texts: List[str] = [],
    ) -> Dict[str, Any]:
        if not self.rag_chain:
            return {
                "answer": "O sistema de IA não está completamente inicializado. Por favor, tente novamente mais tarde.",
                "suggested_downloads": [],
            }

        rag_logger = _get_rag_logger() if _RAG_LOGGER_AVAILABLE else None
        session_id = "unknown"
        try:
            import streamlit as _st_mod
            session_id = _st_mod.session_state.get("session_id", "unknown")
        except Exception:
            pass

        call_id: Optional[str] = None
        if rag_logger:
            call_id = rag_logger.start_call(query=query, session_id=session_id)
            rag_logger.start_retrieval(call_id)

        try:
            logger.info(f"Processando pergunta: '{query}' | retriever: {self.retriever_type}")
            chat_history_messages = []
            for msg in chat_history:
                role = msg.get("role", "")
                if role == "user":
                    chat_history_messages.append(HumanMessage(content=msg["content"]))
                elif role in ("ai", "assistant"):
                    content = msg["content"]
                    if isinstance(content, dict) and 'answer' in content:
                        content = content["answer"]
                    if isinstance(content, str):
                        chat_history_messages.append(AIMessage(content=content))

            chat_history_messages = self._compress_history_if_needed(
                chat_history_messages,
                max_turns=getattr(self, "_max_history_turns", _AI_CONFIG_DEFAULTS["max_history_turns"]),
                max_chars=getattr(self, "_max_history_tokens", _AI_CONFIG_DEFAULTS["max_history_tokens"]),
            )
            expanded_query = self._expand_query(query)

            if rag_logger and call_id:
                rag_logger.set_expanded_query(call_id, expanded_query)
                try:
                    docs = self.retriever.invoke(expanded_query)
                    chunks = [
                        {
                            "source": d.metadata.get("document_name", "unknown"),
                            "score": 0.0,
                            "content_preview": d.page_content[:200],
                        }
                        for d in docs
                    ]
                    rag_logger.log_retrieval(call_id, chunks)
                except Exception:
                    pass
                rag_logger.start_generation(
                    call_id,
                    model_used=getattr(self.llm, "model_name", "unknown") if self.llm else "none",
                )

            temperature = self._detect_temperature(query)
            original_temp = getattr(self.llm, 'temperature', 0.3)
            if temperature != original_temp and hasattr(self.llm, 'temperature'):
                try:
                    self.llm.temperature = temperature
                    result = self.rag_chain.invoke({
                        "question": query,
                        "expanded_query": expanded_query,
                        "dynamic_context_texts": dynamic_context_texts,
                        "chat_history_messages": chat_history_messages,
                    })
                finally:
                    self.llm.temperature = original_temp
            else:
                result = self.rag_chain.invoke({
                    "question": query,
                    "expanded_query": expanded_query,
                    "dynamic_context_texts": dynamic_context_texts,
                    "chat_history_messages": chat_history_messages,
                })

            answer_text = result.get("answer", "") if isinstance(result, dict) else str(result)

            if rag_logger and call_id:
                rag_logger.log_generation(call_id, answer=answer_text)

            if self._is_jailbreak_response(answer_text):
                logger.warning(f"Resposta do LLM bloqueada por guardrail (jailbreak). Query: '{query[:80]}'")
                if _SEC_LOGGER_AVAILABLE:
                    log_security_event(
                        _SecurityEvent.PROMPT_INJECTION_ATTEMPT,
                        feature="llm_output_guardrail",
                        extra={"guardrail": "jailbreak", "query_excerpt": query[:80]},
                    )
                if rag_logger and call_id:
                    rag_logger.finish_call(call_id, error="guardrail:jailbreak")
                return {"answer": self._SAFE_REFUSAL, "suggested_downloads": []}

            if self._is_off_domain_response(answer_text):
                logger.warning(f"Resposta do LLM bloqueada por guardrail (fora do domínio SST). Query: '{query[:80]}'")
                if _SEC_LOGGER_AVAILABLE:
                    log_security_event(
                        _SecurityEvent.PROMPT_INJECTION_ATTEMPT,
                        feature="llm_output_guardrail",
                        extra={"guardrail": "off_domain", "query_excerpt": query[:80]},
                    )
                if rag_logger and call_id:
                    rag_logger.finish_call(call_id, error="guardrail:off_domain")
                return {"answer": self._SAFE_REFUSAL, "suggested_downloads": []}

            if rag_logger and call_id:
                rag_logger.finish_call(call_id)
            return result
        except Exception as e:
            err_msg = str(e)
            logger.error(f"Erro ao processar '{query}': {err_msg}", exc_info=True)
            if rag_logger and call_id:
                rag_logger.finish_call(call_id, error=err_msg[:200])
            return {
                "answer": f"Desculpe, ocorreu um erro ao gerar a resposta. Detalhes: {err_msg}.",
                "suggested_downloads": [],
            }
