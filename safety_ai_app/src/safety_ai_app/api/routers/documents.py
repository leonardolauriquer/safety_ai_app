from fastapi import APIRouter, Depends, HTTPException, Body
from fastapi.responses import StreamingResponse
from typing import Dict, Any, Optional, List
from io import BytesIO
from safety_ai_app.document_generators.apr_document_generator import create_apr_document
from safety_ai_app.api.middleware.auth import get_current_user
from safety_ai_app.database.firestore_service import firestore_service
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/knowledge", response_model=List[Dict[str, Any]])
async def list_curated_knowledge(user: dict = Depends(get_current_user)):
    """Lista documentos ativos na base de conhecimento curada para o usuário."""
    return firestore_service.list_documents("knowledge_base", filters=[("active", "==", True)])

@router.post("/generate/apr")
async def generate_apr(
    data: Dict[str, Any] = Body(...),
    user_logo_base64: Optional[str] = Body(None),
    current_user: Dict = Depends(get_current_user)
):
    """
    Gera um documento APR (DOCX) com base nos dados fornecidos.
    """
    try:
        logger.info(f"Gerando APR para usuário {current_user.get('uid')}")
        doc_buffer = create_apr_document(data, user_logo_base64)
        
        filename = f"APR_{data.get('apr_number', 'document')}.docx"
        
        return StreamingResponse(
            doc_buffer,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    except Exception as e:
        logger.error(f"Erro ao gerar APR: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Erro interno ao gerar documento: {str(e)}")

from safety_ai_app.document_generators.ata_document_generator import create_ata_document

@router.post("/generate/ata")
async def generate_ata(
    data: Dict[str, Any] = Body(...),
    user_logo_base64: Optional[str] = Body(None),
    current_user: Dict = Depends(get_current_user)
):
    """
    Gera uma Ata de Reunião (DOCX) com base nos dados fornecidos.
    """
    try:
        logger.info(f"Gerando Ata para usuário {current_user.get('uid')}")
        doc_buffer = create_ata_document(data, user_logo_base64)
        
        event_title = data.get('title', 'Ata')
        filename = f"ATA_{event_title.replace(' ', '_')}.docx"
        
        return StreamingResponse(
            doc_buffer,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    except Exception as e:
        logger.error(f"Erro ao gerar Ata: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Erro interno ao gerar documento: {str(e)}")
