import logging
from typing import List
from ..document_processors import _lazy_import_sentence_transformer

logger = logging.getLogger(__name__)

# Cache model instance globally within the module scope
_SENTENCE_TRANSFORMER_INSTANCE = None

class CustomHuggingFaceEmbeddings:
    """Wrapper de embeddings com suporte a modelos E5 (prefixos query/passage)."""

    def __init__(self, model_name: str):
        self.model_name = model_name
        self._model = None
        self._is_e5 = "e5" in model_name.lower()

    @property
    def model(self):
        global _SENTENCE_TRANSFORMER_INSTANCE
        if _SENTENCE_TRANSFORMER_INSTANCE is None:
            logger.info(f"[LAZY] Carregando modelo de embeddings '{self.model_name}' (pela primeira vez)...")
            SentenceTransformer = _lazy_import_sentence_transformer()
            _SENTENCE_TRANSFORMER_INSTANCE = SentenceTransformer(self.model_name)
            logger.info(f"CustomHuggingFaceEmbeddings: Modelo '{self.model_name}' carregado.")
        return _SENTENCE_TRANSFORMER_INSTANCE

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
