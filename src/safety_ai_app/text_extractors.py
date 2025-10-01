# src/safety_ai_app/text_extractors.py
import mimetypes
import logging
import os # Adicionado para Path.exists() e open()
import io # Explicitamente necessário para BytesIO
from pypdf import PdfReader # Explicitamente necessário para extração de PDF
from docx import Document as DocxDocument # Explicitamente necessário para extração de DOCX
from typing import List, Dict, Any # Explicitamente necessário para type hints

logger = logging.getLogger(__name__)

# Mapping from Google native MIME types to their preferred export MIME types
GOOGLE_NATIVE_EXPORT_MIMES = {
    'application/vnd.google-apps.document': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', # -> .docx
    'application/vnd.google-apps.spreadsheet': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', # -> .xlsx
    'application/vnd.google-apps.presentation': 'application/vnd.openxmlformats-officedocument.presentationml.presentation', # -> .pptx
    'application/vnd.google-apps.drawing': 'image/png', # -> .png
    'application/vnd.google-apps.script': 'application/vnd.google.script.json', # -> .json
    # Add other Google Workspace types as needed
}

# Supported MIME types for direct processing by NRQuestionAnswering
# These are the types that Langchain's default loaders can handle reasonably well from a file path.
PROCESSABLE_MIME_TYPES = [
    'application/pdf',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document', # .docx
    'application/msword', # .doc (old Word format)
    'text/plain', # .txt
    'application/vnd.google-apps.document', # Google Docs (will be exported as docx)
    'application/vnd.google-apps.spreadsheet', # Google Sheets (will be exported as xlsx) -> CORRIGIDO
    'application/vnd.google-apps.presentation', # Google Slides (will be exported as pptx) -> CORRIGIDO
]

# Mapping for common MIME types to file extensions for local saving/processing
COMMON_MIME_TO_EXT = {
    'application/pdf': 'pdf',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document': 'docx',
    'application/msword': 'doc',
    'text/plain': 'txt',
    'application/vnd.google-apps.document': 'docx', # Will be exported as docx
    'application/vnd.google-apps.spreadsheet': 'xlsx', # Will be exported as xlsx
    'application/vnd.google-apps.presentation': 'pptx', # Will be exported as pptx
    'application/vnd.google-apps.drawing': 'png',
    'application/vnd.google-apps.script': 'json',
    'image/jpeg': 'jpg', 'image/png': 'png', 'image/gif': 'gif',
    'image/bmp': 'bmp', 'image/webp': 'webp', 'image/tiff': 'tiff', 'image/svg+xml': 'svg',
    'video/mp4': 'mp4', 'video/x-msvideo': 'avi', 'video/quicktime': 'mov',
    'video/x-flv': 'flv', 'video/webm': 'webm', 'video/mpeg': 'mpeg', 'video/3gpp': '3gpp',
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': 'xlsx',
    'application/vnd.openxmlformats-officedocument.presentationml.presentation': 'pptx',
}


def get_mime_type_for_drive_export(original_mime_type: str) -> str:
    """
    Given an original MIME type from Google Drive, returns the appropriate MIME type
    for exporting the file, especially for native Google Workspace formats.
    """
    return GOOGLE_NATIVE_EXPORT_MIMES.get(original_mime_type, original_mime_type)

def get_extension_from_mime_type(mime_type: str) -> str:
    """
    Returns a common file extension for a given MIME type.
    Falls back to mimetypes.guess_extension or 'bin'.
    """
    # Remove parameters like "; charset=utf-8" if present
    clean_mime_type = mime_type.split(';')[0].strip()
    
    ext = COMMON_MIME_TO_EXT.get(clean_mime_type)
    if ext:
        return ext
    
    guessed_ext = mimetypes.guess_extension(clean_mime_type, strict=False)
    # mimetypes.guess_extension returns '.ext', remove the dot
    return guessed_ext[1:] if guessed_ext else 'bin' # Default to 'bin' if nothing is found

# --- Funções de extração de texto ---
def extract_text_from_pdf(file_bytes: bytes) -> str:
    """
    Extrai texto de um arquivo PDF.
    Considera que PDFs podem ser complexos e tenta extrair o máximo de texto possível.
    """
    try:
        reader = PdfReader(io.BytesIO(file_bytes))
        text = ""
        for page in reader.pages:
            text += page.extract_text() or ""
        logger.debug("Texto extraído de PDF com sucesso.")
        return text
    except Exception as e:
        logger.error(f"Erro ao extrair texto de PDF: {e}", exc_info=True)
        return ""

def extract_text_from_docx(file_bytes: bytes) -> str:
    """
    Extrai texto de um arquivo DOCX.
    Itera sobre os parágrafos para garantir a captura de todo o conteúdo textual.
    """
    try:
        document = DocxDocument(io.BytesIO(file_bytes))
        text = "\n".join([paragraph.text for paragraph in document.paragraphs])
        logger.debug("Texto extraído de DOCX com sucesso.")
        return text
    except Exception as e:
        logger.error(f"Erro ao extrair texto de DOCX: {e}", exc_info=True)
        return ""

def extract_text_from_txt(file_bytes: bytes) -> str:
    """
    Extrai texto de um arquivo TXT.
    Decodifica os bytes usando UTF-8, que é um encoding comum e robusto.
    """
    try:
        text = file_bytes.decode('utf-8')
        logger.debug("Texto extraído de TXT com sucesso.")
        return text
    except UnicodeDecodeError:
        try:
            text = file_bytes.decode('latin-1')
            logger.warning("Texto extraído de TXT usando latin-1 devido a erro UTF-8.")
            return text
        except Exception as e:
            logger.error(f"Erro ao extrair texto de TXT com UTF-8 ou latin-1: {e}", exc_info=True)
            return ""
    except Exception as e:
        logger.error(f"Erro inesperado ao extrair texto de TXT: {e}", exc_info=True)
        return ""

def get_text_from_file_path(file_path: str, file_name: str, mime_type: str) -> str:
    """
    Função unificada para extrair texto de um arquivo LOCAL (dado seu path),
    baseando-se em seu tipo MIME.
    Retorna o texto extraído ou uma string vazia em caso de erro ou tipo não suportado.
    Parâmetros:
        file_path: O caminho completo do arquivo no sistema local.
        file_name: O nome original do arquivo (usado para logging/feedback).
        mime_type: O tipo MIME do arquivo.
    """
    if not os.path.exists(file_path):
        logger.error(f"Arquivo não encontrado no caminho: {file_path}")
        return f"[ERRO: Arquivo local não encontrado: {file_path}]"

    try:
        with open(file_path, 'rb') as f:
            file_bytes = f.read()
    except Exception as e:
        logger.error(f"Erro ao ler arquivo do caminho '{file_path}': {e}", exc_info=True)
        return f"[ERRO: Falha ao ler arquivo local para extração: {e}]"

    logger.info(f"Tentando extrair texto do arquivo: {file_name} (MIME: {mime_type}) do caminho local: {file_path}")
    if "pdf" in mime_type:
        return extract_text_from_pdf(file_bytes)
    elif "wordprocessingml.document" in mime_type or "msword" in mime_type:
        return extract_text_from_docx(file_bytes)
    elif "text/plain" in mime_type:
        return extract_text_from_txt(file_bytes)
    else:
        logger.warning(f"Tipo de arquivo não suportado para extração de texto: {mime_type} para '{file_name}'")
        return f"[ERRO: Tipo de arquivo '{mime_type}' não suportado para extração de texto. Arquivo: {file_name}]"
