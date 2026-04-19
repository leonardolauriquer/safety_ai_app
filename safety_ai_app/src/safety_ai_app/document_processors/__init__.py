from .lazy_loaders import (
    PYMUPDF_AVAILABLE,
    OCR_AVAILABLE,
    PPTX_AVAILABLE,
    EXCEL_AVAILABLE,
    PDF_EXTRACTION_CONFIG,
    _lazy_import_sentence_transformer,
    log_module_availability,
)
from .pdf_processor import extract_text_hybrid_pdf, extract_text_with_pymupdf, extract_text_with_ocr
from .docx_processor import extract_text_from_docx
from .excel_processor import extract_text_from_excel
from .pptx_processor import extract_text_from_pptx
from .image_processor import extract_text_from_image
from .universal_loader import UniversalDocumentLoader

__all__ = [
    "PYMUPDF_AVAILABLE",
    "OCR_AVAILABLE",
    "PPTX_AVAILABLE",
    "EXCEL_AVAILABLE",
    "PDF_EXTRACTION_CONFIG",
    "_lazy_import_sentence_transformer",
    "log_module_availability",
    "extract_text_hybrid_pdf",
    "extract_text_with_pymupdf",
    "extract_text_with_ocr",
    "extract_text_from_docx",
    "extract_text_from_excel",
    "extract_text_from_pptx",
    "extract_text_from_image",
    "UniversalDocumentLoader",
]
