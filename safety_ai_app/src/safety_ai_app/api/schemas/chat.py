from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

class ChatMessage(BaseModel):
    role: str = Field(..., description="Papel da mensagem: 'user' ou 'assistant'")
    content: str = Field(..., description="Conteúdo da mensagem")

class ChatRequest(BaseModel):
    query: str = Field(..., description="Pergunta do usuário")
    history: List[ChatMessage] = Field(default_factory=list, description="Histórico de chat")
    stream: bool = Field(default=True, description="Se deve usar streaming de resposta")
    user_id: Optional[str] = Field(None, description="ID do usuário Firebase")
    session_id: Optional[str] = Field(None, description="ID da sessão")
    attached_docs: List[str] = Field(default_factory=list, description="Textos de documentos anexados")

class ChatResponse(BaseModel):
    answer: str = Field(..., description="Resposta completa gerada")
    suggested_downloads: List[Dict[str, str]] = Field(default_factory=list, description="Downloads sugeridos")
    sources: List[Dict[str, Any]] = Field(default_factory=list, description="Fontes consultadas (metadados)")
    call_id: Optional[str] = Field(None, description="ID da chamada para logging/feedback")

class ChatError(BaseModel):
    error: str
    detail: Optional[str] = None
