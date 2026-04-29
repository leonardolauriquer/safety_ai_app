import os
import logging
from typing import Optional, List, BinaryIO
from google.cloud import storage
from datetime import datetime, timedelta

logger = logging.getLogger("safety_ai.storage")

class StorageService:
    _instance: Optional['StorageService'] = None
    _client: Optional[storage.Client] = None
    _bucket_name: str = os.environ.get("GCS_BUCKET_NAME", "safety-ai-knowledge-base")

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(StorageService, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        """Inicializa o cliente do Google Cloud Storage."""
        try:
            self._client = storage.Client()
            logger.info("Cliente GCS inicializado com sucesso.")
        except Exception as e:
            logger.error(f"Erro ao inicializar GCS: {e}")
            self._client = None

    @property
    def client(self) -> storage.Client:
        if self._client is None:
            self._initialize()
        return self._client

    def upload_file(self, file_obj: BinaryIO, destination_blob_name: str, content_type: Optional[str] = None) -> bool:
        """Faz upload de um arquivo para o bucket."""
        try:
            bucket = self.client.bucket(self._bucket_name)
            blob = bucket.blob(destination_blob_name)
            
            # Reposiciona o ponteiro se for um buffer
            if hasattr(file_obj, 'seek'):
                file_obj.seek(0)
                
            blob.upload_from_file(file_obj, content_type=content_type)
            logger.info(f"Arquivo {destination_blob_name} enviado para o bucket {self._bucket_name}.")
            return True
        except Exception as e:
            logger.error(f"Erro ao fazer upload para GCS ({destination_blob_name}): {e}")
            return False

    def download_file(self, blob_name: str) -> Optional[bytes]:
        """Baixa o conteúdo de um arquivo do bucket."""
        try:
            bucket = self.client.bucket(self._bucket_name)
            blob = bucket.blob(blob_name)
            return blob.download_as_bytes()
        except Exception as e:
            logger.error(f"Erro ao baixar arquivo {blob_name} do GCS: {e}")
            return None

    def get_signed_url(self, blob_name: str, expiration_minutes: int = 60) -> Optional[str]:
        """Gera uma URL assinada temporária para visualização do arquivo."""
        try:
            bucket = self.client.bucket(self._bucket_name)
            blob = bucket.blob(blob_name)
            
            url = blob.generate_signed_url(
                version="v4",
                expiration=timedelta(minutes=expiration_minutes),
                method="GET",
            )
            return url
        except Exception as e:
            logger.error(f"Erro ao gerar URL assinada para {blob_name}: {e}")
            return None

    def list_files(self, prefix: Optional[str] = None) -> List[str]:
        """Lista arquivos no bucket com um prefixo opcional."""
        try:
            blobs = self.client.list_blobs(self._bucket_name, prefix=prefix)
            return [blob.name for blob in blobs]
        except Exception as e:
            logger.error(f"Erro ao listar arquivos no bucket {self._bucket_name}: {e}")
            return []

    def delete_file(self, blob_name: str) -> bool:
        """Remove um arquivo do bucket."""
        try:
            bucket = self.client.bucket(self._bucket_name)
            blob = bucket.blob(blob_name)
            blob.delete()
            return True
        except Exception as e:
            logger.error(f"Erro ao deletar arquivo {blob_name} do GCS: {e}")
            return False

# Exporta uma instância global
storage_service = StorageService()
