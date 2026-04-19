import logging
from typing import List

from langchain_core.documents import Document
from langchain_community.document_loaders import TextLoader

from .pdf_processor import extract_text_hybrid_pdf
from .docx_processor import extract_text_from_docx
from .pptx_processor import extract_text_from_pptx
from .excel_processor import extract_text_from_excel
from .image_processor import extract_text_from_image

logger = logging.getLogger(__name__)


class UniversalDocumentLoader:
    def __init__(self, file_path: str, file_type: str):
        self.file_path = file_path
        self.file_type = file_type

    def load(self) -> List[Document]:
        try:
            documents: List[Document] = []
            extraction_method = "unknown"

            if self.file_type == 'application/pdf':
                documents = extract_text_hybrid_pdf(self.file_path)
                extraction_method = "hybrid_pdf"

            elif self.file_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
                documents = extract_text_from_docx(self.file_path)
                extraction_method = "docx"

            elif self.file_type in [
                'application/vnd.ms-powerpoint',
                'application/vnd.openxmlformats-officedocument.presentationml.presentation',
            ]:
                documents = extract_text_from_pptx(self.file_path)
                extraction_method = "pptx"

            elif self.file_type in [
                'application/vnd.ms-excel',
                'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                'text/csv',
            ]:
                documents = extract_text_from_excel(self.file_path)
                extraction_method = "excel"

            elif self.file_type in ['image/jpeg', 'image/png', 'image/tiff', 'image/bmp']:
                documents = extract_text_from_image(self.file_path)
                extraction_method = "ocr_image"

            elif self.file_type in ['text/plain', 'text/markdown', 'text/html']:
                loader = TextLoader(self.file_path, encoding='utf-8')
                docs = loader.load()
                for i, doc in enumerate(docs):
                    doc.metadata['page'] = doc.metadata.get('page', i) + 1
                    documents.append(doc)
                extraction_method = "text"

            if not documents:
                with open(self.file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    fallback_text = f.read()
                if fallback_text.strip():
                    documents.append(Document(
                        page_content=fallback_text.strip(),
                        metadata={
                            "page": 1,
                            "source": self.file_path,
                            "extraction_method": f"{extraction_method}_single_fallback",
                            "file_type": self.file_type,
                        }
                    ))

            for doc in documents:
                doc.metadata.setdefault("extraction_method", extraction_method)
                doc.metadata.setdefault("file_type", self.file_type)
                doc.metadata.setdefault("source", self.file_path)

            logger.info(f"UniversalDocumentLoader: {len(documents)} docs com método {extraction_method}")
            return documents

        except Exception as e:
            logger.error(f"Erro no UniversalDocumentLoader para {self.file_path}: {e}", exc_info=True)
            return []
