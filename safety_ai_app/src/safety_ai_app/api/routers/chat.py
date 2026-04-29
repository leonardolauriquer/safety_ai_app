import logging
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from typing import List, Dict, Any

from safety_ai_app.api.schemas.chat import ChatRequest, ChatResponse, ChatMessage
from safety_ai_app.api.deps import get_qa_engine
from safety_ai_app.api.middleware.auth import get_current_user
from safety_ai_app.nr_rag_qa import NRQuestionAnswering

router = APIRouter()
logger = logging.getLogger("safety_ai_api.chat")

@router.post("/ask", response_model=ChatResponse)
async def ask_question(
    request: ChatRequest,
    qa: NRQuestionAnswering = Depends(get_qa_engine),
    user: dict = Depends(get_current_user)
):
    """
    Endpoint para perguntas e respostas (SST).
    Retorna a resposta completa de uma vez.
    """
    try:
        # Converter histórico para o formato esperado pelo NRQuestionAnswering
        # O NRQuestionAnswering usa uma lista de dicionários {"role": "user", "content": "..."}
        history = [msg.model_dump() for msg in request.history]
        
        result = qa.ask(
            query=request.query,
            history=history,
            dynamic_context_texts=request.attached_docs
        )
        
        return ChatResponse(
            answer=result.get("answer", ""),
            suggested_downloads=result.get("suggested_downloads", []),
            sources=result.get("sources", []),
            call_id=result.get("call_id")
        )
    except Exception as e:
        logger.error(f"Erro no endpoint /ask: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/stream")
async def stream_question(
    request: ChatRequest,
    qa: NRQuestionAnswering = Depends(get_qa_engine),
    user: dict = Depends(get_current_user)
):
    """
    Endpoint para perguntas e respostas com streaming (Server-Sent Events).
    """
    history = [msg.model_dump() for msg in request.history]
    
    def event_generator():
        try:
            for token in qa.stream_answer_question(
                query=request.query,
                history=history,
                dynamic_context_texts=request.attached_docs
            ):
                yield f"data: {token}\n\n"
            
            # Enviar metadados finais (downloads sugeridos) no final do stream
            # Em uma implementação real de SSE, poderíamos usar um tipo de evento específico
            # ou anexar no último frame.
            suggested = qa.get_last_suggested_downloads()
            if suggested:
                import json
                yield f"event: metadata\ndata: {json.dumps({'suggested_downloads': suggested})}\n\n"
                
            yield "event: close\ndata: [DONE]\n\n"
        except Exception as e:
            logger.error(f"Erro no streaming SSE: {e}")
            yield f"event: error\ndata: {str(e)}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
