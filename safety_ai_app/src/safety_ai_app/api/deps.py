import logging
from typing import Optional
from safety_ai_app.nr_rag_qa import NRQuestionAnswering

logger = logging.getLogger("safety_ai_api.deps")

# Global instance of the QA engine
_qa_engine: Optional[NRQuestionAnswering] = None

def get_qa_engine() -> NRQuestionAnswering:
    """
    Dependency to get the singleton instance of the QA engine.
    Lazy initializes if necessary.
    """
    global _qa_engine
    if _qa_engine is None:
        logger.info("Initializing NRQuestionAnswering engine for API...")
        _qa_engine = NRQuestionAnswering()
    return _qa_engine
