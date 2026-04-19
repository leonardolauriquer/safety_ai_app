import logging
from typing import List

from langchain_core.documents import Document

from .lazy_loaders import _lazy_import_pptx

logger = logging.getLogger(__name__)


def extract_text_from_pptx(file_path: str) -> List[Document]:
    Presentation = _lazy_import_pptx()
    if Presentation is None:
        logger.warning("python-pptx não disponível - pulando extração PPTX")
        return []

    documents: List[Document] = []
    try:
        prs = Presentation(file_path)
        for slide_num, slide in enumerate(prs.slides, 1):
            slide_content = []
            for shape in slide.shapes:
                if hasattr(shape, "text") and shape.text.strip():
                    slide_content.append(shape.text.strip())
                if hasattr(shape, "table"):
                    for row in shape.table.rows:
                        row_text = [str(cell).strip() for cell in row.cells if cell is not None and str(cell).strip()]
                        if row_text:
                            slide_content.append(" | ".join(row_text))
            if slide_content:
                documents.append(Document(
                    page_content="\n".join(slide_content),
                    metadata={"page": slide_num, "source": file_path, "extraction_method": "pptx"}
                ))
        logger.info(f"PowerPoint: extraiu {sum(len(d.page_content) for d in documents)} chars de {len(documents)} slides")
        return documents
    except Exception as e:
        logger.error(f"Erro ao extrair texto do PowerPoint {file_path}: {e}", exc_info=True)
        return []
