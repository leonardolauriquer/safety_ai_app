import logging
import threading
from typing import List, Dict, Any, Optional
from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever
from langchain_core.callbacks.manager import CallbackManagerForRetrieverRun
from langchain_community.retrievers import BM25Retriever

logger = logging.getLogger(__name__)

def initialize_bm25_retriever(vector_db, doc_count: int, top_k: int) -> Optional[BM25Retriever]:
    """
    Initialize a BM25 retriever using documents from ChromaDB.
    """
    if doc_count > 0:
        results = vector_db._collection.get(
            ids=vector_db._collection.get()['ids'],
            include=['documents', 'metadatas'],
        )
        all_docs = [
            Document(page_content=content, metadata=meta)
            for content, meta in zip(results['documents'], results['metadatas'])
        ]
        logger.info(f"BM25Retriever: {len(all_docs)} documentos indexados (k={top_k}).")
        return BM25Retriever.from_documents(all_docs, k=top_k)
    return None

def create_ensemble_retriever(
    vector_db,
    bm25_retriever: Optional[BM25Retriever],
    top_k: int,
    semantic_weight: float,
    bm25_weight: float
) -> BaseRetriever:
    """
    Create an ensemble retriever combining vector search and BM25.
    """
    vr = vector_db.as_retriever(search_type="similarity", search_kwargs={"k": top_k})
    
    if bm25_retriever:
        logger.info(f"EnsembleRetriever configurado (Vector + BM25, pesos sem={semantic_weight:.2f}/bm25={bm25_weight:.2f}).")
        return EnsembleRetriever(retrievers=[vr, bm25_retriever], weights=[semantic_weight, bm25_weight])
    
    logger.warning("Usando apenas Vector Retriever (ChromaDB vazio ou sem documentos).")
    return vr

RERANKER_MODEL_NAME = 'cross-encoder/mmarco-mMiniLMv2-L12-H384-v1'
RERANKER_TOP_N = 5

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

def rerank_documents(query: str, docs: List[Document], top_n: int = RERANKER_TOP_N) -> List[Document]:
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
