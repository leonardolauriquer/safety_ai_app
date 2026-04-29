import os
import time
import logging
from typing import Optional, Dict, Any
from langchain_openai import ChatOpenAI

logger = logging.getLogger(__name__)

def create_llm(
    model_name: str,
    temperature: float = 0.1,
    max_tokens: int = 8192,
    streaming: bool = False,
    extra_model_kwargs: Optional[Dict[str, Any]] = None
) -> Optional[ChatOpenAI]:
    """
    Factory function to create a ChatOpenAI instance using OpenRouter.
    """
    t0 = time.time()
    ai_key = os.getenv("AI_INTEGRATIONS_OPENROUTER_API_KEY")
    ai_base = os.getenv("AI_INTEGRATIONS_OPENROUTER_BASE_URL")
    openrouter_key = os.getenv("OPENROUTER_API_KEY")

    if ai_key and ai_base:
        try:
            llm = ChatOpenAI(
                openai_api_base=ai_base,
                openai_api_key=ai_key,
                model_name=model_name,
                temperature=temperature,
                max_tokens=max_tokens,
                streaming=streaming,
            )
            logger.info(f"LLM via Replit AI Integrations ({model_name}) inicializado.")
            return llm
        except Exception as e:
            logger.warning(f"Falha na integração Replit OpenRouter: {e}. Tentando fallback...")

    if openrouter_key:
        try:
            model_kwargs = {
                "extra_headers": {
                    "HTTP-Referer": "https://safetyai.streamlit.app/",
                    "X-Title": "SafetyAI - SST",
                }
            }
            if extra_model_kwargs:
                model_kwargs.update(extra_model_kwargs)

            llm = ChatOpenAI(
                openai_api_base="https://openrouter.ai/api/v1",
                openai_api_key=openrouter_key,
                model_name=model_name,
                temperature=temperature,
                max_tokens=max_tokens,
                streaming=streaming,
                model_kwargs=model_kwargs,
            )
            logger.info(f"LLM via OpenRouter direto ({model_name}) inicializado em {time.time() - t0:.3f}s.")
            return llm
        except Exception as e:
            logger.error(f"Erro ao inicializar LLM OpenRouter: {e}", exc_info=True)
            return None

    logger.error("Configuração de IA não encontrada! Configure OpenRouter via Replit AI Integrations ou OPENROUTER_API_KEY.")
    return None
