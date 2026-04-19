import os
import sys

# Adiciona o diretório 'src' ao sys.path para que 'safety_ai_app' seja importável
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(script_dir, '..'))
src_path = os.path.join(project_root, 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)

import logging
import argparse

from safety_ai_app.google_drive_integrator import (
    get_service_account_drive_integrator_instance,
    AI_CHAT_SYNC_SUBFOLDER_NAME,
    SAFETY_AI_ROOT_FOLDER_NAME,
)
from safety_ai_app.nr_rag_qa import NRQuestionAnswering

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

CHROMADB_PERSIST_DIRECTORY = os.path.join(project_root, "data", "chroma_db")
COLLECTION_NAME = "nrs_collection"

# Modelo de embeddings multilíngue — 1024 dimensões, SOTA para português (E5-large-instruct)
EMBEDDING_MODEL_NAME = 'intfloat/multilingual-e5-large-instruct'

# Arquivo sentinela que registra o modelo de embeddings usado na última indexação.
# Se o modelo mudar, uma re-indexação completa é disparada automaticamente.
_EMBEDDING_SENTINEL_FILE = os.path.join(CHROMADB_PERSIST_DIRECTORY, ".embedding_model")


def _read_indexed_model() -> str:
    """Return the embedding model name recorded in the sentinel file, or empty string."""
    try:
        with open(_EMBEDDING_SENTINEL_FILE, "r", encoding="utf-8") as f:
            return f.read().strip()
    except FileNotFoundError:
        return ""


def _write_indexed_model(model_name: str) -> None:
    """Persist the current embedding model name to the sentinel file."""
    os.makedirs(CHROMADB_PERSIST_DIRECTORY, exist_ok=True)
    with open(_EMBEDDING_SENTINEL_FILE, "w", encoding="utf-8") as f:
        f.write(model_name)


def _needs_reindex() -> bool:
    """
    Return True if a full collection reindex is required.

    A reindex is needed when:
    - The sentinel file is missing (unknown state — may be a post-upgrade first run).
    - The sentinel records a different embedding model than the current one (dimension mismatch).

    Treating a missing sentinel as "unknown → reindex" is safe: recreating an empty
    or legacy collection is cheap, while a dimension mismatch causes runtime failures.
    """
    indexed = _read_indexed_model()
    if not indexed:
        logger.warning(
            "MIGRATION GUARD: Arquivo sentinela de modelo não encontrado. "
            "Estado do modelo de embeddings é desconhecido — pode ser uma primeira "
            "execução pós-upgrade. Forçando re-indexação completa para garantir "
            f"compatibilidade com o modelo atual '{EMBEDDING_MODEL_NAME}'."
        )
        return True
    if indexed != EMBEDDING_MODEL_NAME:
        logger.warning(
            f"MIGRATION GUARD: A coleção ChromaDB foi indexada com '{indexed}', "
            f"mas o modelo atual é '{EMBEDDING_MODEL_NAME}'. "
            "Forçando re-indexação completa para evitar incompatibilidade de dimensão."
        )
        return True
    return False


def main(force_reindex: bool = False):
    """
    Inicia o processo de vetorização e indexação das NRs e outros documentos
    da pasta do Google Drive 'SafetyAI - Conhecimento Base/Base de dados IA' no ChromaDB.

    Pipeline:
    - Modelo de embeddings multilíngue (multilingual-e5-large-instruct, 1024 dims)
    - Chunking estrutural para NRs (chunk_size=1000, overlap=200)
    - Metadados enriquecidos: nr_number, article, item extraídos por parsing estrutural

    Args:
        force_reindex: Se True, deleta e recria a coleção nrs_collection no ChromaDB
                       e re-indexa todos os documentos do Drive.
                       OBRIGATÓRIO ao trocar o modelo de embeddings.
    """
    logger.info("Iniciando processo de vetorização e indexação dos documentos do Google Drive...")
    logger.info(f"Modelo de embeddings: {EMBEDDING_MODEL_NAME}")

    # Auto-detect model change and force reindex when needed
    if not force_reindex and _needs_reindex():
        force_reindex = True
        logger.warning("Re-indexação forçada automaticamente por mudança de modelo de embeddings.")

    qa_system = NRQuestionAnswering(chroma_persist_directory=CHROMADB_PERSIST_DIRECTORY)
    if not qa_system:
        logger.critical("Falha ao inicializar NRQuestionAnswering. Encerrando o processo de vetorização.")
        return

    drive_integrator = get_service_account_drive_integrator_instance()
    if not drive_integrator:
        logger.critical("Falha ao inicializar GoogleDriveIntegrator. Verifique as credenciais da conta de serviço.")
        return

    ai_chat_sync_folder_id = drive_integrator._get_ai_chat_sync_folder_id()
    if not ai_chat_sync_folder_id:
        logger.critical(
            f"Pasta '{SAFETY_AI_ROOT_FOLDER_NAME}/{AI_CHAT_SYNC_SUBFOLDER_NAME}' não encontrada no Google Drive."
        )
        logger.critical("Certifique-se de que a estrutura de pastas está correta e que a conta de serviço tem acesso.")
        return

    if force_reindex:
        logger.info(
            "Opção --force-reindex ativada. Deletando e recriando a coleção "
            f"'{COLLECTION_NAME}' no ChromaDB para garantir compatibilidade de dimensão..."
        )
        try:
            # Full collection delete + recreate: required when embedding dimension changes.
            # clear_docs_by_source_type() only removes by filter and does not reset dimension.
            qa_system.clear_chroma_collection()
            logger.info(f"Coleção '{COLLECTION_NAME}' deletada e recriada com sucesso.")
        except Exception as e:
            logger.error(f"ERRO ao recriar a coleção ChromaDB: {e}", exc_info=True)
            logger.warning(
                "Tentando continuar, mas pode haver inconsistências se a coleção não foi recriada corretamente."
            )

    logger.info(
        f"Iniciando sincronização incremental da pasta '{AI_CHAT_SYNC_SUBFOLDER_NAME}' "
        "do Google Drive para o ChromaDB."
    )

    processed_count = drive_integrator.synchronize_app_central_library_to_chroma(
        qa_system=qa_system,
        progress_callback=None,
    )

    logger.info(f"Sincronização concluída. {processed_count} novos/atualizados documentos processados.")

    # Record the current model after successful indexing
    _write_indexed_model(EMBEDDING_MODEL_NAME)
    logger.info(f"Sentinela de modelo atualizado: '{EMBEDDING_MODEL_NAME}'")

    # Demonstration query
    logger.info("\n--- Demonstração de Busca ---")
    query_text = "Quais são as responsabilidades da empresa em relação ao trabalho em altura?"
    logger.info(f"Buscando por: '{query_text}'")
    try:
        docs = qa_system.vector_db.similarity_search(query_text, k=2)
        if docs:
            for i, doc in enumerate(docs):
                meta = doc.metadata
                logger.info(f"\nResultado {i+1}:")
                logger.info(f"  NR: {meta.get('nr_number', 'N/A')}, Item: {meta.get('item', 'N/A')}, Artigo: {meta.get('article', 'N/A')}")
                logger.info(f"  Documento: {meta.get('document_name', 'N/A')}")
                logger.info(f"  Conteúdo: {doc.page_content[:300]}...")
        else:
            logger.info("Nenhum resultado encontrado para a busca de demonstração.")
    except Exception as e:
        logger.error(f"ERRO durante a demonstração de busca: {e}", exc_info=True)

    logger.info("Processo de vetorização e indexação concluído!")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description=(
            "Vetoriza e indexa NRs e outros documentos do Google Drive no ChromaDB.\n"
            f"Modelo: {EMBEDDING_MODEL_NAME} (multilíngue, 1024 dims).\n\n"
            "IMPORTANTE: Use --force-reindex ao trocar o modelo de embeddings.\n"
            "O script detecta automaticamente mudanças de modelo via arquivo sentinela "
            f"em {_EMBEDDING_SENTINEL_FILE}."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--force-reindex",
        action="store_true",
        help=(
            "Deleta e recria a coleção nrs_collection no ChromaDB, garantindo compatibilidade "
            "de dimensão, e re-indexa todos os documentos do Drive com o pipeline atualizado "
            "(modelo multilíngue 768 dims + chunking estrutural NR). "
            "Obrigatório após troca de modelo de embeddings. "
            "Também é acionado automaticamente se o script detectar mudança de modelo."
        ),
    )
    args = parser.parse_args()
    main(force_reindex=args.force_reindex)
