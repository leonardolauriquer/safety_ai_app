import os
import shutil
import logging
from typing import Optional
from google.cloud import storage
from google.api_core import exceptions

logger = logging.getLogger(__name__)

class GCSStorageManager:
    """
    Gerencia a sincronização do diretório do ChromaDB com o Google Cloud Storage.
    """
    def __init__(self, local_path: str, bucket_name: Optional[str] = None):
        self.local_path = local_path
        self._client: Optional[storage.Client] = None
        
        # Tenta obter o bucket das variáveis de ambiente
        self.bucket_name = bucket_name or os.getenv("GCS_BUCKET_NAME")
        
        if not self.bucket_name:
            # Tenta inferir um nome de bucket se estiver no GCP
            project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
            if project_id:
                self.bucket_name = f"safety-ai-storage-{project_id}"
                logger.info(f"Usando bucket default inferido: {self.bucket_name}")
            else:
                logger.warning("GCS_BUCKET_NAME e GOOGLE_CLOUD_PROJECT não definidos. Persistência desativada.")

    @property
    def client(self):
        if self._client is None:
            try:
                self._client = storage.Client()
            except Exception as e:
                logger.error(f"Falha ao inicializar cliente GCS: {e}")
        return self._client

    def _ensure_bucket(self):
        if not self.bucket_name or not self.client:
            return None
        
        try:
            bucket = self.client.get_bucket(self.bucket_name)
            return bucket
        except exceptions.NotFound:
            try:
                logger.info(f"Criando bucket {self.bucket_name}...")
                bucket = self.client.create_bucket(self.bucket_name)
                return bucket
            except Exception as e:
                logger.error(f"Erro ao criar bucket {self.bucket_name}: {e}")
                return None
        except Exception as e:
            logger.error(f"Erro ao acessar bucket {self.bucket_name}: {e}")
            return None

    def sync_from_gcs(self):
        """Baixa os arquivos do GCS para o diretório local."""
        bucket = self._ensure_bucket()
        if not bucket:
            return False

        try:
            blobs = bucket.list_blobs(prefix="chroma_db/")
            count = 0
            for blob in blobs:
                # Remove o prefixo chroma_db/ para o caminho local
                relative_path = blob.name.replace("chroma_db/", "", 1)
                full_local_path = os.path.join(self.local_path, relative_path)
                
                os.makedirs(os.path.dirname(full_local_path), exist_ok=True)
                blob.download_to_filename(full_local_path)
                count += 1
            
            if count > 0:
                logger.info(f"Sincronização GCS -> Local concluída: {count} arquivos baixados.")
            else:
                logger.info("Nenhum arquivo encontrado no GCS para baixar.")
            return True
        except Exception as e:
            logger.error(f"Erro na sincronização GCS -> Local: {e}")
            return False

    def sync_to_gcs(self):
        """Faz o upload dos arquivos locais para o GCS."""
        bucket = self._ensure_bucket()
        if not bucket:
            return False

        if not os.path.exists(self.local_path):
            logger.warning(f"Diretório local {self.local_path} não existe. Nada para sincronizar.")
            return False

        try:
            count = 0
            for root, _, files in os.walk(self.local_path):
                for file in files:
                    local_file = os.path.join(root, file)
                    # Cria o caminho no GCS preservando a estrutura
                    relative_path = os.path.relpath(local_file, self.local_path)
                    blob_path = f"chroma_db/{relative_path.replace(os.sep, '/')}"
                    
                    blob = bucket.blob(blob_path)
                    blob.upload_from_filename(local_file)
                    count += 1
            
            logger.info(f"Sincronização Local -> GCS concluída: {count} arquivos enviados.")
            return True
        except Exception as e:
            logger.error(f"Erro na sincronização Local -> GCS: {e}")
            return False
