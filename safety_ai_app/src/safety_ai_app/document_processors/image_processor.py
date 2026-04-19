import logging
from typing import List

from langchain_core.documents import Document

from .lazy_loaders import _lazy_import_ocr, PDF_EXTRACTION_CONFIG

logger = logging.getLogger(__name__)


def extract_text_from_image(file_path: str) -> List[Document]:
    ocr_modules = _lazy_import_ocr()
    if ocr_modules is None:
        logger.warning("OCR não disponível - pulando extração de imagem")
        return []

    pytesseract = ocr_modules['pytesseract']
    Image = ocr_modules['Image']

    try:
        logger.info(f"Iniciando OCR para imagem: {file_path}")
        image = Image.open(file_path)
        text = pytesseract.image_to_string(
            image,
            lang=PDF_EXTRACTION_CONFIG["tesseract_lang"],
            timeout=PDF_EXTRACTION_CONFIG["ocr_timeout"],
        )
        if text.strip():
            logger.info(f"OCR extraiu {len(text)} chars da imagem")
            return [Document(
                page_content=text.strip(),
                metadata={"page": 1, "source": file_path, "extraction_method": "ocr_image"}
            )]
        return []
    except Exception as e:
        logger.error(f"Erro no OCR da imagem {file_path}: {e}", exc_info=True)
        return []
