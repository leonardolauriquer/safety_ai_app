import os
import logging
from typing import Optional, Dict, Any, List
import firebase_admin
from firebase_admin import credentials, firestore
from google.cloud.firestore_v1.client import Client
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
)
from google.api_core.exceptions import ServiceUnavailable, ResourceExhausted

logger = logging.getLogger("safety_ai.firestore")

class FirestoreService:
    _instance: Optional['FirestoreService'] = None
    _db: Optional[Client] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(FirestoreService, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        """Inicializa a conexão com o Firestore usando credenciais de ambiente ou conta de serviço."""
        try:
            if not firebase_admin._apps:
                # Tenta carregar do path da conta de serviço se fornecido, senão usa Default Credentials
                cred_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
                if cred_path and os.path.exists(cred_path):
                    cred = credentials.Certificate(cred_path)
                    firebase_admin.initialize_app(cred)
                    logger.info(f"Firestore inicializado com Service Account: {cred_path}")
                else:
                    firebase_admin.initialize_app()
                    logger.info("Firestore inicializado com Google Application Default Credentials")
            
            self._db = firestore.client()
        except Exception as e:
            logger.error(f"Erro ao inicializar Firestore: {e}")
            self._db = None

    @property
    def db(self) -> Client:
        if self._db is None:
            self._initialize()
        return self._db

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type((ServiceUnavailable, ResourceExhausted)),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )
    def get_document(self, collection: str, doc_id: str) -> Optional[Dict[str, Any]]:
        """Busca um documento específico pelo ID."""
        try:
            doc_ref = self.db.collection(collection).document(doc_id)
            doc = doc_ref.get()
            if doc.exists:
                return doc.to_dict()
            return None
        except Exception as e:
            logger.error(f"Erro ao buscar documento {doc_id} em {collection}: {e}")
            return None

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type((ServiceUnavailable, ResourceExhausted)),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )
    def list_documents(self, collection: str, filters: List[tuple] = None) -> List[Dict[str, Any]]:
        """Lista documentos de uma coleção com filtros opcionais."""
        try:
            query = self.db.collection(collection)
            if filters:
                for field, op, value in filters:
                    query = query.where(field, op, value)
            
            docs = query.stream()
            return [{**doc.to_dict(), "id": doc.id} for doc in docs]
        except Exception as e:
            logger.error(f"Erro ao listar documentos da coleção {collection}: {e}")
            return []

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type((ServiceUnavailable, ResourceExhausted)),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )
    def save_document(self, collection: str, data: Dict[str, Any], doc_id: Optional[str] = None) -> str:
        """Salva ou atualiza um documento."""
        try:
            if doc_id:
                doc_ref = self.db.collection(collection).document(doc_id)
                doc_ref.set(data, merge=True)
                return doc_id
            else:
                _, doc_ref = self.db.collection(collection).add(data)
                return doc_ref.id
        except Exception as e:
            logger.error(f"Erro ao salvar documento em {collection}: {e}")
            raise

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type((ServiceUnavailable, ResourceExhausted)),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )
    def delete_document(self, collection: str, doc_id: str) -> bool:
        """Remove um documento."""
        try:
            self.db.collection(collection).document(doc_id).delete()
            return True
        except Exception as e:
            logger.error(f"Erro ao deletar documento {doc_id} em {collection}: {e}")
            return False

# Exporta uma instância global
firestore_service = FirestoreService()
