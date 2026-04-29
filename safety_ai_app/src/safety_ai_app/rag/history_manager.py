"""
History Manager — SafetyAI RAG Pipeline

Responsabilidade única: compressão e sumarização do histórico de chat LangChain.
Extraído de NRQuestionAnswering._compress_history_if_needed.
"""

import logging
from typing import Any, List

logger = logging.getLogger(__name__)


def compress_history(
    messages: List[Any],
    llm: Any,
    max_turns: int = 10,
    max_chars: int = 16000,
) -> List[Any]:
    """Compress chat history when it exceeds the configured limits.

    Summarizes older messages into a single AIMessage so the context
    window does not overflow while keeping recent conversational context.

    Args:
        messages: LangChain message objects (HumanMessage / AIMessage).
        llm: The language model instance used to generate the summary.
        max_turns: Maximum number of recent turns to keep verbatim.
        max_chars: Maximum total character count before triggering compression.

    Returns:
        A new list where old messages are replaced by one summary AIMessage,
        or the original list unchanged if limits are not exceeded or llm is None.
    """
    from langchain_core.messages import AIMessage, HumanMessage

    # Fast path: no compression needed
    if len(messages) <= max_turns * 2:
        total_chars = sum(len(m.content) for m in messages if hasattr(m, "content"))
        if total_chars <= max_chars:
            return messages

    keep_recent = max_turns
    to_compress = messages[:-keep_recent] if len(messages) > keep_recent else []
    recent = messages[-keep_recent:] if len(messages) > keep_recent else messages

    if not to_compress or not llm:
        return messages

    try:
        history_text = "\n".join(
            f"{'Usuário' if isinstance(m, HumanMessage) else 'SafetyAI'}: {m.content}"
            for m in to_compress
        )
        summary_prompt = (
            "Você é um assistente que resume conversas sobre SST (Saúde e Segurança do Trabalho). "
            "Resuma o seguinte histórico de conversa em português, preservando os pontos técnicos "
            "mais importantes (NRs citadas, perguntas principais, conclusões):\n\n"
            f"{history_text}\n\n"
            "Resuma em até 400 palavras, mantendo os fatos técnicos essenciais."
        )
        summary_response = llm.invoke(summary_prompt)
        summary_content = (
            summary_response.content if hasattr(summary_response, "content") else str(summary_response)
        )
        summary_message = AIMessage(content=f"[Resumo do histórico anterior]\n{summary_content}")
        logger.info("Histórico comprimido: %d mensagens → 1 resumo.", len(to_compress))
        return [summary_message] + list(recent)
    except Exception as exc:
        logger.warning("Falha na compressão de histórico: %s. Usando histórico completo.", exc)
        return messages
