import os
import logging
from typing import List

from langchain_core.documents import Document
from langchain_community.document_loaders import PyPDFLoader

from .lazy_loaders import (
    _lazy_import_fitz,
    _lazy_import_ocr,
    PDF_EXTRACTION_CONFIG,
)

logger = logging.getLogger(__name__)


def extract_text_with_pymupdf(pdf_path: str) -> List[Document]:
    fitz = _lazy_import_fitz()
    if fitz is None:
        logger.warning("PyMuPDF não disponível - pulando extração PyMuPDF")
        return []

    documents: List[Document] = []
    try:
        with fitz.open(pdf_path) as doc:
            for page_num in range(len(doc)):
                try:
                    page = doc[page_num]
                    text = page.get_text()
                    if text.strip():
                        documents.append(Document(
                            page_content=text.strip(),
                            metadata={"page": page_num + 1, "source": pdf_path, "extraction_method": "pymupdf"}
                        ))
                except Exception as page_error:
                    logger.warning(f"Erro na página {page_num + 1} com PyMuPDF para {pdf_path}: {page_error}")
        logger.info(f"PyMuPDF extraiu {sum(len(d.page_content) for d in documents)} caracteres de {len(documents)} páginas")
        return documents
    except Exception as e:
        logger.error(f"Erro geral no PyMuPDF para {pdf_path}: {e}", exc_info=True)
        return []


def extract_text_with_ocr(pdf_path: str, max_pages: int = None) -> List[Document]:
    ocr_modules = _lazy_import_ocr()
    if ocr_modules is None:
        logger.warning("OCR não disponível - pulando extração OCR")
        return []

    pytesseract = ocr_modules['pytesseract']
    convert_from_path = ocr_modules['convert_from_path']

    documents: List[Document] = []
    try:
        logger.info(f"Iniciando OCR para {pdf_path}")
        pages_images = convert_from_path(
            pdf_path, dpi=200, first_page=1,
            last_page=max_pages if max_pages else None,
            thread_count=os.cpu_count() or 1,
        )
        for i, page_image in enumerate(pages_images):
            try:
                logger.info(f"Processando OCR página {i + 1}/{len(pages_images)}")
                text = pytesseract.image_to_string(
                    page_image,
                    lang=PDF_EXTRACTION_CONFIG["tesseract_lang"],
                    timeout=PDF_EXTRACTION_CONFIG["ocr_timeout"],
                )
                if text.strip():
                    documents.append(Document(
                        page_content=text.strip(),
                        metadata={"page": i + 1, "source": pdf_path, "extraction_method": "ocr"}
                    ))
            except Exception as page_error:
                logger.warning(f"Erro OCR na página {i + 1} de {pdf_path}: {page_error}")
        logger.info(f"OCR extraiu {sum(len(d.page_content) for d in documents)} caracteres de {len(documents)} páginas")
        return documents
    except Exception as e:
        logger.error(f"Erro geral no OCR para {pdf_path}: {e}", exc_info=True)
        return []


def extract_text_hybrid_pdf(pdf_path: str) -> List[Document]:
    logger.info(f"Iniciando extração híbrida para {pdf_path}")
    min_len = PDF_EXTRACTION_CONFIG["min_text_length"]
    extracted: List[Document] = []

    # Estratégia 1: PyPDFLoader
    try:
        logger.info("Tentativa 1: PyPDFLoader")
        loader = PyPDFLoader(pdf_path)
        docs = loader.load()
        if docs and sum(len(d.page_content.strip()) for d in docs) >= min_len:
            logger.info(f"PyPDFLoader: Sucesso - {sum(len(d.page_content) for d in docs)} chars em {len(docs)} páginas")
            for i, doc in enumerate(docs):
                doc.metadata['page'] = doc.metadata.get('page', i) + 1
                extracted.append(doc)
            return extracted
        else:
            logger.warning(f"PyPDFLoader: Texto insuficiente ou vazio para {pdf_path}")
    except Exception as e:
        logger.warning(f"PyPDFLoader falhou para {pdf_path}: {e}")

    # Estratégia 2: PyMuPDF
    fitz = _lazy_import_fitz()
    if fitz is not None:
        logger.info("Tentativa 2: PyMuPDF")
        try:
            with fitz.open(pdf_path) as doc:
                for page_num in range(len(doc)):
                    try:
                        page = doc[page_num]
                        text = page.get_text()
                        if text.strip():
                            extracted.append(Document(
                                page_content=text.strip(),
                                metadata={"page": page_num + 1, "source": pdf_path, "extraction_method": "pymupdf"}
                            ))
                    except Exception as page_error:
                        logger.warning(f"Erro na página {page_num + 1} com PyMuPDF: {page_error}")
            if extracted and sum(len(d.page_content.strip()) for d in extracted) >= min_len:
                logger.info(f"PyMuPDF: Sucesso - {sum(len(d.page_content) for d in extracted)} chars")
                return extracted
            else:
                logger.warning(f"PyMuPDF: Texto insuficiente ou vazio para {pdf_path}")
                extracted = []
        except Exception as e:
            logger.error(f"Erro geral no PyMuPDF para {pdf_path}: {e}", exc_info=True)
    else:
        logger.info("Tentativa 2: PyMuPDF - PULADA (não disponível)")

    # Estratégia 3: OCR
    ocr_modules = _lazy_import_ocr()
    if ocr_modules is not None:
        pytesseract = ocr_modules['pytesseract']
        convert_from_path = ocr_modules['convert_from_path']
        logger.info("Tentativa 3: OCR (limitado a primeiras páginas)")
        try:
            pages_images = convert_from_path(
                pdf_path, dpi=200, first_page=1,
                last_page=PDF_EXTRACTION_CONFIG["max_ocr_pages"],
                thread_count=os.cpu_count() or 1,
            )
            for i, page_image in enumerate(pages_images):
                try:
                    text = pytesseract.image_to_string(
                        page_image,
                        lang=PDF_EXTRACTION_CONFIG["tesseract_lang"],
                        timeout=PDF_EXTRACTION_CONFIG["ocr_timeout"],
                    )
                    if text.strip():
                        extracted.append(Document(
                            page_content=text.strip(),
                            metadata={"page": i + 1, "source": pdf_path, "extraction_method": "ocr"}
                        ))
                except Exception as page_error:
                    logger.warning(f"Erro OCR na página {i + 1} de {pdf_path}: {page_error}")
            if extracted and sum(len(d.page_content.strip()) for d in extracted) >= min_len:
                logger.info(f"OCR: Sucesso - {sum(len(d.page_content) for d in extracted)} chars")
                return extracted
            else:
                logger.warning(f"OCR: Texto insuficiente ou vazio para {pdf_path}")
                extracted = []
        except Exception as e:
            logger.error(f"Erro geral no OCR para {pdf_path}: {e}", exc_info=True)
    else:
        logger.info("Tentativa 3: OCR - PULADA (não disponível)")

    # Estratégia 4: Metadados como último recurso
    if fitz is not None:
        try:
            logger.info("Tentativa 4: Extrair metadados")
            with fitz.open(pdf_path) as doc:
                metadata = doc.metadata
                meta_text = ""
                if metadata.get('title'):
                    meta_text += f"Título: {metadata['title']}\n"
                if metadata.get('subject'):
                    meta_text += f"Assunto: {metadata['subject']}\n"
                if metadata.get('author'):
                    meta_text += f"Autor: {metadata['author']}\n"
                if meta_text.strip():
                    logger.info(f"Metadados extraídos: {len(meta_text)} chars")
                    return [Document(
                        page_content=meta_text.strip(),
                        metadata={"page": 1, "source": pdf_path, "extraction_method": "metadata"}
                    )]
        except Exception as meta_error:
            logger.warning(f"Extração de metadados falhou para {pdf_path}: {meta_error}")

    logger.error(f"TODAS as estratégias de extração falharam para {pdf_path}. Retornando lista vazia.")
    return []
