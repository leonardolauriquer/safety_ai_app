import logging
import re
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from safety_ai_app.api.middleware.auth import require_admin
from safety_ai_app.database.firestore_service import firestore_service
from safety_ai_app.storage.storage_service import storage_service
import uuid
from datetime import datetime

import tempfile
import os
from safety_ai_app.api.deps import get_qa_engine

router = APIRouter()
logger = logging.getLogger("safety_ai_api.admin")

COLLECTION_KNOWLEDGE = "knowledge_base"

# Limites e whitelist de tipos permitidos
MAX_FILE_SIZE_BYTES = 50 * 1024 * 1024  # 50MB
ALLOWED_CONTENT_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/msword",
    "text/plain",
    "text/csv",
    "application/vnd.ms-excel",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
}
ALLOWED_EXTENSIONS = {"pdf", "docx", "doc", "txt", "csv", "xls", "xlsx"}


def _sanitize_filename(filename: str) -> str:
    """Remove caracteres perigosos do nome do arquivo (path traversal, etc.)."""
    # Remove ../ e caracteres não-alfanuméricos exceto . - _
    safe = re.sub(r'[^a-zA-Z0-9._\-]', '_', os.path.basename(filename))
    return safe[:200]  # limita o tamanho


@router.get("/knowledge", response_model=List[Dict[str, Any]])
async def list_knowledge_base(user: dict = Depends(require_admin)):
    """Lista todos os documentos na base de conhecimento curada."""
    return firestore_service.list_documents(COLLECTION_KNOWLEDGE)

@router.post("/knowledge/upload")
async def upload_document(
    file: UploadFile = File(...),
    title: str = Form(...),
    category: str = Form("Geral"),
    description: Optional[str] = Form(None),
    user: dict = Depends(require_admin),
    qa_engine = Depends(get_qa_engine)
):
    """
    Upload de um novo documento para a base de conhecimento (Admin only).
    Salva o arquivo no GCS e os metadados no Firestore + Indexação RAG.
    """
    tmp_path = None
    try:
        # === VALIDAÇÃO DE SEGURANÇA ===
        # 1. Verificar tipo MIME contra whitelist
        if file.content_type not in ALLOWED_CONTENT_TYPES:
            raise HTTPException(
                status_code=415,
                detail=f"Tipo de arquivo não permitido: '{file.content_type}'. "
                       f"Permitidos: {', '.join(sorted(ALLOWED_CONTENT_TYPES))}"
            )

        # 2. Verificar extensão do arquivo
        file_ext = ""
        if "." in file.filename:
            file_ext = file.filename.rsplit(".", 1)[-1].lower()
        if file_ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=415,
                detail=f"Extensão '.{file_ext}' não permitida."
            )

        # 3. Ler conteúdo e verificar tamanho
        content = await file.read()
        if len(content) > MAX_FILE_SIZE_BYTES:
            raise HTTPException(
                status_code=413,
                detail=f"Arquivo muito grande. Máximo: {MAX_FILE_SIZE_BYTES // (1024*1024)}MB. "
                       f"Recebido: {len(content) // (1024*1024)}MB"
            )
        if len(content) == 0:
            raise HTTPException(status_code=400, detail="Arquivo vazio.")

        # 4. Sanitizar nome do arquivo
        safe_filename = _sanitize_filename(file.filename)

        file_id = str(uuid.uuid4())
        blob_name = f"knowledge_base/{file_id}.{file_ext}"

        # Salvar temporariamente para processamento RAG
        with tempfile.NamedTemporaryFile(delete=False, suffix=f".{file_ext}") as tmp:
            tmp.write(content)
            tmp_path = tmp.name

        logger.info(
            f"Upload admin: arquivo='{safe_filename}' tipo='{file.content_type}' "
            f"tamanho={len(content)} bytes uid={user.get('uid')}"
        )


        # Upload para o GCS (usa o conteúdo já lido em memória)
        import io
        success = storage_service.upload_file(
            io.BytesIO(content),
            blob_name,
            content_type=file.content_type
        )
        
        if not success:
            raise HTTPException(status_code=500, detail="Falha no upload para o Cloud Storage")
            
        # Salvar metadados no Firestore
        doc_data = {
            "title": title,
            "filename": safe_filename,
            "blob_name": blob_name,
            "category": category,
            "description": description,
            "uploaded_by": user.get("email"),
            "uploaded_at": datetime.utcnow().isoformat(),
            "file_size_bytes": len(content),
            "content_type": file.content_type,
            "active": True
        }
        
        doc_id = firestore_service.save_document(COLLECTION_KNOWLEDGE, doc_data)
        
        # Indexar no RAG (ChromaDB)
        try:
            qa_engine.process_document_to_chroma(
                file_path=tmp_path,
                document_name=title,
                source="Curadoria Centralizada",
                file_type=file.content_type,
                additional_metadata={
                    "firestore_id": doc_id,
                    "blob_name": blob_name,
                    "source_type": "app_central_library_sync" # Tipo para documentos oficiais
                }
            )
            logger.info(f"Documento '{title}' indexado no RAG com sucesso.")
        except Exception as rag_err:
            logger.error(f"Erro na indexação RAG: {rag_err}")
            # Não falha o upload se apenas a indexação falhar, mas logamos o erro
        
        return {"status": "success", "id": doc_id, "blob_name": blob_name}
    except Exception as e:
        logger.error(f"Erro no upload administrativo: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.remove(tmp_path)

@router.delete("/knowledge/{doc_id}")
async def delete_document(
    doc_id: str, 
    user: dict = Depends(require_admin),
    qa_engine = Depends(get_qa_engine)
):
    """Remove um documento da base de conhecimento (Admin only)."""
    doc = firestore_service.get_document(COLLECTION_KNOWLEDGE, doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Documento não encontrado")
        
    # Remove do GCS
    storage_service.delete_file(doc["blob_name"])
    
    # Remove do RAG (ChromaDB)
    try:
        qa_engine.remove_document_by_id(doc["title"])
    except Exception as e:
        logger.warning(f"Erro ao tentar remover do RAG: {e}")
    
    # Remove do Firestore
    firestore_service.delete_document(COLLECTION_KNOWLEDGE, doc_id)
    
    return {"status": "success", "message": "Documento removido"}

@router.patch("/knowledge/{doc_id}/toggle")
async def toggle_document_status(doc_id: str, user: dict = Depends(require_admin)):
    """Ativa/Desativa um documento na base (sem deletar)."""
    doc = firestore_service.get_document(COLLECTION_KNOWLEDGE, doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Documento não encontrado")
        
    new_status = not doc.get("active", True)
    firestore_service.save_document(COLLECTION_KNOWLEDGE, {"active": new_status}, doc_id=doc_id)
    
    return {"status": "success", "active": new_status}

