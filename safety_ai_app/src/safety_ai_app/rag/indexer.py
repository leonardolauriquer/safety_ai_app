import logging
import re
import os
from datetime import datetime
from typing import List, Dict, Any, Optional
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# NR structural chunking helpers
# ---------------------------------------------------------------------------

_NR_ITEM_PATTERN = re.compile(
    r'(?m)^(\d{1,2}(?:\.\d+){1,5})\s+',
)
_NR_CHAPTER_PATTERN = re.compile(
    r'(?mi)^(CAP[IÍ]TULO\s+[IVXLCDM\d]+|ANEXO\s+[IVXLCDM\d]+|SEÇÃO\s+[IVXLCDM\d]+)',
)
_NR_NUMBER_FROM_NAME = re.compile(r'NR[\s\-_]?(\d{1,2})', re.IGNORECASE)
_NR_ITEM_META = re.compile(r'^(\d{1,2})(?:\.(\d+))?(?:\.\d+)*\s+')

def extract_nr_metadata_from_content(text: str, doc_name: str = "") -> Dict[str, str]:
    """Extract nr_number, article, and item from chunk text and document name."""
    nr_number = ""
    article = ""
    item = ""

    m = _NR_NUMBER_FROM_NAME.search(doc_name)
    if m:
        nr_number = m.group(1)

    if not nr_number:
        m = re.search(r'NR[\s\-]?(\d{1,2})', text[:500], re.IGNORECASE)
        if m:
            nr_number = m.group(1)

    m = re.search(r'art(?:igo)?\.?\s*(\d+)', text[:300], re.IGNORECASE)
    if m:
        article = m.group(1)

    m = _NR_ITEM_META.search(text.lstrip())
    if m:
        item = m.group(0).strip()

    section = f"NR-{nr_number} {item}".strip() if nr_number else item
    return {"nr_number": nr_number, "article": article, "item": item, "section": section}


def split_nr_document_structurally(
    documents: List[Document],
    chunk_size: int = 1000,
    chunk_overlap: int = 200,
) -> List[Document]:
    """
    Structural splitter for NR regulatory documents.
    """
    base_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        add_start_index=True,
        length_function=len,
        separators=["\n\n", "\n", " ", ""],
    )

    result_chunks: List[Document] = []

    for doc in documents:
        text = doc.page_content
        doc_name = doc.metadata.get("document_name", "")

        boundary_positions = set()
        boundary_positions.add(0)
        for m in _NR_ITEM_PATTERN.finditer(text):
            boundary_positions.add(m.start())
        for m in _NR_CHAPTER_PATTERN.finditer(text):
            boundary_positions.add(m.start())

        sorted_positions = sorted(boundary_positions)

        sections = []
        for i, start in enumerate(sorted_positions):
            end = sorted_positions[i + 1] if i + 1 < len(sorted_positions) else len(text)
            section_text = text[start:end].strip()
            if section_text:
                sections.append(section_text)

        if not sections:
            sections = [text]

        for section in sections:
            section_doc = Document(page_content=section, metadata=dict(doc.metadata))
            sub_chunks = base_splitter.split_documents([section_doc])
            for chunk in sub_chunks:
                if not chunk.page_content.strip():
                    continue
                nr_meta = extract_nr_metadata_from_content(chunk.page_content, doc_name)
                chunk.metadata.update(nr_meta)
                result_chunks.append(chunk)

    return result_chunks

def get_indexed_nr_numbers_from_mte(collection) -> list:
    """Return list of NR numbers (int) already indexed from MTE-oficial source."""
    try:
        result = collection.get(include=["metadatas"])
        indexed = set()
        for meta in result.get("metadatas", []):
            if meta.get("source") == "MTE-oficial":
                nr = meta.get("nr_number")
                if isinstance(nr, int):
                    indexed.add(nr)
                elif isinstance(nr, str):
                    try:
                        clean = nr.replace("NR-", "").lstrip("0") or "0"
                        indexed.add(int(clean))
                    except ValueError:
                        pass
        return sorted(indexed)
    except Exception as e:
        logger.warning(f"[NR-INDEX] Erro ao checar NRs indexadas: {e}")
        return []
