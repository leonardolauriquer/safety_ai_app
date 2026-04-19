import logging
from typing import List

from langchain_core.documents import Document

from .lazy_loaders import _lazy_import_excel

logger = logging.getLogger(__name__)


def extract_text_from_excel(file_path: str) -> List[Document]:
    excel_modules = _lazy_import_excel()
    if excel_modules is None:
        logger.warning("openpyxl/pandas não disponível - pulando extração Excel")
        return []

    openpyxl = excel_modules['openpyxl']
    documents: List[Document] = []
    try:
        workbook = openpyxl.load_workbook(file_path, data_only=True)
        for sheet_name in workbook.sheetnames:
            sheet = workbook[sheet_name]
            sheet_content = []
            for row in sheet.iter_rows(values_only=True):
                row_text = [str(cell).strip() for cell in row if cell is not None and str(cell).strip()]
                if row_text:
                    sheet_content.append(" | ".join(row_text))
            if sheet_content:
                documents.append(Document(
                    page_content="\n".join(sheet_content),
                    metadata={"page": 1, "source": file_path, "extraction_method": "excel", "sheet_name": sheet_name}
                ))
        logger.info(f"Excel: extraiu {sum(len(d.page_content) for d in documents)} chars de {len(documents)} planilhas")
        return documents
    except Exception as e:
        logger.error(f"Erro ao extrair texto do Excel {file_path}: {e}", exc_info=True)
        return []
