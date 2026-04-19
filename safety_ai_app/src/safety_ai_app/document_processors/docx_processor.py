import logging
from typing import List

from langchain_core.documents import Document
from langchain_community.document_loaders import Docx2txtLoader

logger = logging.getLogger(__name__)


def extract_text_from_docx(file_path: str) -> List[Document]:
    try:
        loader = Docx2txtLoader(file_path)
        docs = loader.load()
        documents: List[Document] = []
        for i, doc in enumerate(docs):
            doc.metadata['page'] = doc.metadata.get('page', i) + 1
            doc.metadata['extraction_method'] = 'docx'
            documents.append(doc)
        logger.info(f"DOCX: extraiu {sum(len(d.page_content) for d in documents)} chars de {len(documents)} seções")
        return documents
    except Exception as e:
        logger.error(f"Erro ao extrair texto de DOCX {file_path}: {e}", exc_info=True)
        return []
