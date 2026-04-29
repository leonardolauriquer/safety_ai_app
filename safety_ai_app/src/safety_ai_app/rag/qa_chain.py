import logging
import re
from typing import List, Dict, Any, Optional
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.prompts import (
    ChatPromptTemplate,
    SystemMessagePromptTemplate,
    HumanMessagePromptTemplate,
    MessagesPlaceholder,
)
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough, RunnableParallel, RunnableLambda
from operator import itemgetter
from urllib.parse import quote_plus
from .indexer import extract_nr_metadata_from_content

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# LLM Output Cleaning
# ---------------------------------------------------------------------------

def clean_llm_output(output: str) -> str:
    if not output:
        return ""
    html_tags = ['</div>', '</p>', '<div>', '<p>', '</span>', '<span>', '</br>', '<br>', '<br/>']
    cleaned = output
    for tag in html_tags:
        cleaned = cleaned.replace(tag, '')
    return cleaned.strip()

# ---------------------------------------------------------------------------
# Document Name Cleaning
# ---------------------------------------------------------------------------

def get_clean_document_name(doc_name: str) -> str:
    cleaned = re.sub(r' - Versão \d+\.\d+\.\d+$', '', doc_name, flags=re.IGNORECASE).strip()
    cleaned = re.sub(r' v\d+\.\d+\.\d+$', '', cleaned, flags=re.IGNORECASE).strip()
    return cleaned

# ---------------------------------------------------------------------------
# Query Processing
# ---------------------------------------------------------------------------

def extract_nr_from_query(query: str) -> Optional[str]:
    match = re.search(r'(?:NR|N\.R\.)\s*(\d+)', query, re.IGNORECASE)
    if match:
        return f"nr-{match.group(1)}"
    return None

# ---------------------------------------------------------------------------
# Temperature Detection
# ---------------------------------------------------------------------------

_DOC_GENERATION_PATTERNS = re.compile(
    r'(cri[ae]\s|elabor[ae]\s|redij[ae]\s|escreva\s|gere?\s|mont[ae]\s|formul[ae]\s|'
    r'\bapr\b|\bata\b|relat[oó]rio\s+de\s|laudo\s+t[eé]cnico|'
    r'\bpcmso\b|\bpgr\b|\bltcat\b|\bppp\b|\bppra\b|\bpcmat\b|'
    r'modelo\s+de|template\s+de|exemplo\s+de\s+documento)',
    re.IGNORECASE,
)

def detect_temperature(query: str, temp_doc: float, temp_factual: float) -> float:
    """Return document or factual temperature based on query type."""
    return temp_doc if _DOC_GENERATION_PATTERNS.search(query) else temp_factual

# ---------------------------------------------------------------------------
# Retrieval Processing
# ---------------------------------------------------------------------------

def process_retrieved_docs(docs: List[Any], query: str) -> Dict[str, Any]:
    """Process retrieved docs into formatted context string and download list."""
    nr_filter = extract_nr_from_query(query)
    filtered_docs = []

    if nr_filter:
        nr_number = nr_filter.replace('nr-', '')
        search_patterns = [
            rf"nr-{nr_number}[\-\.]", rf"nr{nr_number}[\-\.]",
            rf"NR{nr_number}[\-\.]", rf"NR-{nr_number}[\-\.]",
            rf"nr[\-\s]*{nr_number}[\-\s]", rf"NR[\-\s]*{nr_number}[\-\s]",
        ]
        content_patterns = [
            rf"NR[\-\s]*{nr_number}[\.\-\s]",
            rf"Norma[\s]+Regulamentadora[\s]+n?º?[\s]*{nr_number}",
            rf"NR[\s]*{nr_number}[\s]*[\-\:]",
        ]
        for doc in docs:
            name_raw = doc.metadata.get('document_name', '')
            content = doc.page_content or ''
            in_name = any(re.search(p, name_raw, re.IGNORECASE) for p in search_patterns)
            in_content = any(re.search(p, content[:500], re.IGNORECASE) for p in content_patterns)
            if in_name or in_content:
                filtered_docs.append(doc)

        if not filtered_docs:
            logger.warning(f"Post-filtering para '{nr_filter}' resultou em 0 docs.")
            fallback_terms = (
                ["instalações elétricas", "segurança elétrica", "eletricidade"]
                if nr_number == '10'
                else [f"nr {nr_number}", f"norma {nr_number}"]
            )
            for doc in docs[:10]:
                if any(t.lower() in doc.page_content.lower() for t in fallback_terms):
                    filtered_docs.append(doc)
            if not filtered_docs:
                filtered_docs = docs[:5]
    else:
        filtered_docs = docs

    formatted_context = []
    unique_docs_for_download: Dict[str, Dict] = {}

    for doc in filtered_docs:
        doc_name_raw = doc.metadata.get('document_name', 'Documento Desconhecido')
        clean_doc_name = get_clean_document_name(doc_name_raw)
        page_number = doc.metadata.get('page_number', doc.metadata.get('page', 'N/A'))
        drive_file_id = doc.metadata.get('drive_file_id', None)
        file_type = doc.metadata.get('file_type', 'application/octet-stream')

        url_viewer = "N/A"
        if drive_file_id:
            url_viewer = f"https://drive.google.com/file/d/{quote_plus(drive_file_id)}/view?usp=drivesdk"

        source_metadata_str = (
            f"document_name_clean: '{clean_doc_name}', "
            f"page_number: '{page_number}', "
            f"url_viewer: '{url_viewer}'"
        )
        formatted_context.append(
            f"--- Início do Conteúdo do Documento ---\n{doc.page_content}\n"
            f"--- Fim do Conteúdo do Documento ---\nMETADATA_FONTE_INTERNA: {source_metadata_str}"
        )

        if drive_file_id and drive_file_id not in unique_docs_for_download:
            unique_docs_for_download[drive_file_id] = {
                "document_name": clean_doc_name,
                "drive_file_id": drive_file_id,
                "file_type": file_type,
            }

    if not filtered_docs:
        logger.warning("Nenhum documento recuperado. LLM responderá sem contexto específico.")

    return {
        "context": "\n\n".join(formatted_context),
        "suggested_downloads": list(unique_docs_for_download.values()),
    }

# ---------------------------------------------------------------------------
# Guardrails and SST Domain Validation
# ---------------------------------------------------------------------------

# Padrões que indicam que o LLM pode ter sido manipulado para sair do domínio SST.
JAILBREAK_RESPONSE_PATTERNS = re.compile(
    r'(ignor(?:e|ando|ei)\s+(minhas?\s+)?instru[çc][oõ]es|'
    r'modo?\s+desenvolvedor|'
    r'sem\s+(restri[çc][oõ]es|filtros|limites)|'
    r'estou\s+livre\s+para|'
    r'posso\s+agora\s+(?:fazer|dizer|responder)|'
    r'dan\s+mode|jailbreak|'
    r'as an ai without restrictions|'
    r'ignoring\s+(my\s+)?previous\s+(instructions?|constraints?)|'
    r'sure[,.]?\s+i\'?ll?\s+ignore|'
    r'pretend\s+(you\s+are|to\s+be)|'
    r'act\s+as\s+if\s+you\s+have\s+no|'
    r'forget\s+(your|all)\s+(previous\s+)?(instructions?|rules?|constraints?))',
    re.IGNORECASE,
)

# Palavras-chave do domínio SST: respostas legítimas deveriam conter ao menos uma.
SST_DOMAIN_KEYWORDS = re.compile(
    r'(nr[\s\-]?\d+|norma\s+regulamentadora|segura[nç]|trabalhador|'
    r'epi|epc|cipa|sesmt|ppgr|pcmso|pgr|ltcat|cbo|cnae|cid[\s\-]?\d|'
    r'acidente|risco\s+ocup|insalubre|periculoso|ergonomia|brigada\s+de|'
    r'laudo\s+t[eé]cnico|fiscali[zs]a|minist[eé]rio\s+do\s+trabalho|'
    r'\bmte\b|\bsst\b|saúde\s+ocupacional|medicina\s+do\s+trabalho|'
    r'equipamento\s+de\s+prote|certificado\s+de\s+aprova|'
    r'trabalho\s+em\s+altura|espa[çc]o\s+confinado|atividade\s+insalubre|'
    r'atividade\s+perigosa|agen?te\s+(f[ií]sico|qu[ií]mico|biol[oó]gico)|'
    r'cat\b|fat\b|nexo\s+t[eé]cnico|dose\s+di[aá]ria|limite\s+de\s+toler|'
    r'programa\s+de\s+preven|gest[aã]o\s+de\s+riscos|apr\b|ata\s+de|'
    r'investigar\s+acidente|[aá]rvore\s+de\s+causas|laudo\s+pericial|'
    r'quadro\s+i\s+da\s+nr|adi[çc]ional\s+de\s+insalubridade|'
    r'ppp\b|e\s*social\b|rat\b|\bsat\b|ntep\b)',
    re.IGNORECASE,
)

# Indicadores de recusa legítima pelo próprio modelo (não deve ser bloqueada).
REFUSAL_PATTERNS = re.compile(
    r'(fora\s+da\s+minha\s+[aá]rea|especializa[çc][aã]o|'
    r'n[aã]o\s+posso\s+(?:ajudar|responder)|'
    r'n[aã]o\s+est[oá]\s+(?:dentro|relacionado)|'
    r'limite\s+de\s+(?:minha|meu)|'
    r'safetyai|sst\s+no\s+brasil|'
    r'al[eé]m\s+da\s+minha\s+especializa|'
    r'reformul[ae]\s+(sua\s+)?pergunta|'
    r'restrij[ao]\s+a\s+temas)',
    re.IGNORECASE,
)

SAFE_REFUSAL = (
    "Essa solicitação está além da minha área de especialização em Saúde e Segurança do Trabalho (SST). "
    "Não consigo ajudar com esse tema, mas posso ajudá-lo se a pergunta for reformulada para um contexto de SST — por exemplo:\n"
    "- 'Quais riscos de segurança estão associados a [atividade]?'\n"
    "- 'Qual NR regula [processo/equipamento]?'\n"
    "- 'Como elaborar o PGR para [setor]?'\n\n"
    "Como posso ajudá-lo dentro do universo SST?"
)

def is_jailbreak_response(answer: str) -> bool:
    """Verifica se a resposta do LLM apresenta marcadores de jailbreak/evasão de domínio."""
    return bool(JAILBREAK_RESPONSE_PATTERNS.search(answer))

def is_off_domain_response(answer: str, threshold: float) -> bool:
    """
    Detecta respostas substantivas sem termos suficientes do domínio SST.
    """
    if threshold <= 0.0:
        return False
    if len(answer) < 250:
        return False
    if REFUSAL_PATTERNS.search(answer):
        return False
    import math
    required = max(1, math.ceil(threshold * 3))
    matches = SST_DOMAIN_KEYWORDS.findall(answer)
    return len(matches) < required
