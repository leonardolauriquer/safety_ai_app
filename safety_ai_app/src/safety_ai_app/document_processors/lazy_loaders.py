import os
import logging

logger = logging.getLogger(__name__)

PYMUPDF_AVAILABLE = False
OCR_AVAILABLE = False
PPTX_AVAILABLE = False
EXCEL_AVAILABLE = False
_lazy_modules: dict = {}

PDF_EXTRACTION_CONFIG = {
    "max_ocr_pages": 10,
    "ocr_timeout": 30,
    "min_text_length": 20,
    "tesseract_lang": "por+eng",
}


def _lazy_import_fitz():
    global PYMUPDF_AVAILABLE
    if 'fitz' not in _lazy_modules:
        try:
            import fitz
            _lazy_modules['fitz'] = fitz
            PYMUPDF_AVAILABLE = True
        except ImportError:
            _lazy_modules['fitz'] = None
            PYMUPDF_AVAILABLE = False
    return _lazy_modules['fitz']


def _lazy_import_ocr():
    global OCR_AVAILABLE
    if 'ocr' not in _lazy_modules:
        try:
            import pytesseract
            from pdf2image import convert_from_path
            from PIL import Image
            import subprocess

            poppler_available = False
            tesseract_available = False

            try:
                subprocess.run(['pdftoppm', '-h'], capture_output=True, text=True, timeout=10)
                poppler_available = True
            except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
                pass

            try:
                result = subprocess.run(['tesseract', '--version'], capture_output=True, text=True, timeout=10)
                if result.returncode == 0:
                    tesseract_available = True
            except Exception:
                pass

            if poppler_available and tesseract_available:
                OCR_AVAILABLE = True
                _lazy_modules['ocr'] = {
                    'pytesseract': pytesseract,
                    'convert_from_path': convert_from_path,
                    'Image': Image,
                }
            else:
                _lazy_modules['ocr'] = None
        except ImportError:
            _lazy_modules['ocr'] = None
            OCR_AVAILABLE = False
    return _lazy_modules['ocr']


def _lazy_import_pptx():
    global PPTX_AVAILABLE
    if 'pptx' not in _lazy_modules:
        try:
            from pptx import Presentation
            _lazy_modules['pptx'] = Presentation
            PPTX_AVAILABLE = True
        except ImportError:
            _lazy_modules['pptx'] = None
            PPTX_AVAILABLE = False
    return _lazy_modules['pptx']


def _lazy_import_excel():
    global EXCEL_AVAILABLE
    if 'excel' not in _lazy_modules:
        try:
            import openpyxl
            import pandas as pd
            _lazy_modules['excel'] = {'openpyxl': openpyxl, 'pd': pd}
            EXCEL_AVAILABLE = True
        except ImportError:
            _lazy_modules['excel'] = None
            EXCEL_AVAILABLE = False
    return _lazy_modules['excel']


def _lazy_import_sentence_transformer():
    if 'SentenceTransformer' not in _lazy_modules:
        from sentence_transformers import SentenceTransformer
        _lazy_modules['SentenceTransformer'] = SentenceTransformer
    return _lazy_modules['SentenceTransformer']


def log_module_availability():
    _lazy_import_fitz()
    logger.info(f"PyMuPDF: {'Disponível' if PYMUPDF_AVAILABLE else 'Não disponível'}")
    _lazy_import_ocr()
    logger.info(f"OCR (Tesseract + Poppler): {'Disponível' if OCR_AVAILABLE else 'Não disponível'}")
    _lazy_import_pptx()
    logger.info(f"PowerPoint: {'Disponível' if PPTX_AVAILABLE else 'Não disponível'}")
    _lazy_import_excel()
    logger.info(f"Excel: {'Disponível' if EXCEL_AVAILABLE else 'Não disponível'}")
