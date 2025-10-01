import os
import logging
import uuid
import tempfile
import shutil
import importlib.metadata
import sys # Adicionado: Importação de sys
from typing import List, Dict, Any, Optional
from datetime import datetime
from operator import itemgetter
from urllib.parse import quote_plus # Adicionado para garantir URLs seguras
import re # Importado para a função _get_clean_document_name

import streamlit as st
from dotenv import load_dotenv

from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import SentenceTransformerEmbeddings

from langchain_community.retrievers import BM25Retriever
from langchain_core.documents import Document
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate, PromptTemplate, SystemMessagePromptTemplate, HumanMessagePromptTemplate, MessagesPlaceholder
from langchain_core.runnables import RunnablePassthrough, RunnableParallel, RunnableLambda
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI # Adicionado para integração com OpenRouter
from langchain.retrievers import EnsembleRetriever
from langchain_community.document_loaders import PyPDFLoader, TextLoader, Docx2txtLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.messages import HumanMessage, AIMessage # Importado para o histórico do chat

# Carregar variáveis de ambiente
load_dotenv()

# Configuração de logging
# Correção: Ajustado o f-string do format e o stream para sys.stderr
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s', stream=sys.stderr)
logger = logging.getLogger(__name__)

# Exibir informações da versão do Streamlit e LangChain
logger.info(f"Streamlit Version: {st.version}")
try:
    logger.info(f"LangChain Version: {importlib.metadata.version('langchain')}")
    logger.info(f"LangChain-Google-Genai Version: {importlib.metadata.version('langchain-google-genai')}")
    logger.info(f"LangChain-Core Version: {importlib.metadata.version('langchain-core')}")
    logger.info(f"LangChain-Community Version: {importlib.metadata.version('langchain-community')}")
    logger.info(f"LangChain-OpenAI Version: {importlib.metadata.version('langchain-openai')}") # Adicionado para OpenRouter
except importlib.metadata.PackageNotFoundError as e:
    logger.warning(f"Não foi possível obter a versão de algum pacote LangChain: {e}")

# Importar PROCESSABLE_MIME_TYPES do novo módulo text_extractors
from safety_ai_app.text_extractors import PROCESSABLE_MIME_TYPES

# Importar THEME para acessar os nomes dos ícones
from safety_ai_app.theme_config import THEME

script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(script_dir, '..', '..'))
CHROMADB_PERSIST_DIRECTORY = os.path.join(project_root, "data", "chroma_db")

COLLECTION_NAME = "nrs_collection"
EMBEDDING_MODEL_NAME = 'sentence-transformers/all-MiniLM-L6-v2'

# Modelos para LLM (prioridade de uso)
# Se OPENROUTER_API_KEY estiver definida, o OpenRouter será usado com OPENROUTER_MODEL_NAME.
# Caso contrário, o GOOGLE_API_KEY será usado com GEMINI_MODEL.
GEMINI_MODEL = 'gemini-pro' # Modelo padrão para Google Generative AI

# --- FUNÇÕES AUXILIARES PARA ICONS E MENSAGENS ---
def _get_material_icon_html(icon_name):
    """Retorna a tag HTML para um ícone Material Symbols."""
    return f"""<span class='material-symbols-outlined' style='font-family: "Material Symbols Outlined" !important;'>{icon_name}</span>"""

def _render_info_like_message_for_rag(message_type, message, icon_name):
    """
    Renderiza uma mensagem com estilo Streamlit (info, warning, success, error)
    permitindo a inclusão de um ícone Material Symbols.
    """
    icon_html = _get_material_icon_html(icon_name)
    if message_type == "info":
        st.markdown(f"<div class='st-info-like'>{icon_html} {message}</div>", unsafe_allow_html=True)
    elif message_type == "warning":
        st.markdown(f"<div class='st-warning-like'>{icon_html} {message}</div>", unsafe_allow_html=True)
    elif message_type == "success":
        st.markdown(f"<div class='st-success-like'>{icon_html} {message}</div>", unsafe_allow_html=True)
    elif message_type == "error":
        st.markdown(f"<div class='st-error-like'>{icon_html} {message}</div>", unsafe_allow_html=True)
    else:
        st.markdown(f"<div>{icon_html} {message}</div>", unsafe_allow_html=True)


# --- FIM FUNÇÕES AUXILIARES PARA ICONS E MENSAGENS ---

# --- FUNÇÕES AUXILIARES ---

def _get_clean_document_name(doc_name: str) -> str:
    """
    Remove extensões de arquivo e números de versão de um nome de documento.
    Ex: "Protocolo Fictício de Segurança Interna - TechSafety Soluções - Versão 3.1.2.pdf"
    -> "Protocolo Fictício de Segurança Interna - TechSafety Soluções"
    """
    # Remover extensão de arquivo (e.g., .pdf, .docx, .txt)
    cleaned_name = re.sub(r'\.(pdf|docx|txt)$', '', doc_name, flags=re.IGNORECASE).strip()
    # Remover " - Versão X.Y.Z"
    cleaned_name = re.sub(r' - Versão \d+\.\d+\.\d+$', '', cleaned_name, flags=re.IGNORECASE).strip()
    # Remover " vX.Y.Z"
    cleaned_name = re.sub(r' v\d+\.\d+\.\d+$', '', cleaned_name, flags=re.IGNORECASE).strip()
    return cleaned_name

# --- TEMPLATES ---

GENERAL_SST_SYSTEM_MESSAGE = """
Você é um assistente de IA especializado em Saúde e Segurança do Trabalho (SST) no Brasil,
com foco em Normas Regulamentadoras (NRs).
Responda às perguntas do usuário de forma abrangente, detalhada e precisa.

Priorize o contexto fornecido abaixo.
Se o contexto contiver informações relevantes (identificadas por METADATA_FONTE_INTERNA): utilize-as para formular sua resposta e cite-as rigorosamente.
Se o contexto for insuficiente, irrelevante ou se sua resposta se basear em conhecimento generalizado sobre uma Norma Regulamentadora:

NÃO invente um documento interno.
Em vez disso, forneça uma citação para a versão oficial da NR no site do Ministério do Trabalho e Emprego (MTE).

Não invente informações.

Formate sua resposta usando Markdown, incluindo:

Títulos e subtítulos (usando # ou ##) quando apropriado.
Listas (usando * ou - para bullet points, ou 1. para numeradas).
Negrito para termos importantes.
Itálico para ênfase.

Sempre liste suas fontes (se houver) no final da sua resposta, sob o cabeçalho "Fontes:", seguindo estas regras rigorosas:

O cabeçalho "Fontes:" DEVE aparecer apenas UMA VEZ, no início da lista de referências.


Para cada fonte, use o formato apropriado (documento interno ou NR do MTE) em uma nova linha, sem repetir a palavra "Fontes:" ou "Fonte:".


Todas as URLs DEVEM SER ABSOLUTAS (começando com "https://") e válidas. NUNCA gere URLs relativas, com placeholders ou incompletas na saída final.


O atributo para abrir links em nova aba DEVE ser `target="_blank"` e incluído IMEDIATAMENTE após o fechamento do parêntese do link.
Exemplo de link em markdown: `[texto do link](URL_COMPLETA)`


PARA DOCUMENTOS INTERNOS (baseados no METADATA_FONTE_INTERNA do contexto):

METADATA_FONTE_INTERNA inclui document_name_clean, page_number e url_viewer.
Você DEVE sempre usar o url_viewer para criar um link, A MENOS QUE url_viewer seja EXATAMENTE 'N/A'.
Se url_viewer for 'N/A' (sem link): {{document_name_clean}}{{ ' - Página ' + page_number if page_number != 'N/A' else '' }} (Documento Interno)
Exemplo: Protocolo Fictício - Página 0 (Documento Interno)


Se url_viewer for uma URL VÁLIDA (que NÃO seja 'N/A') (com link): [{{document_name_clean}}{{ ' - Página ' + page_number if page_number != 'N/A' else '' }} (ver documento)]({{url_viewer}})
Exemplo: [Protocolo Fictício - Página 0 (ver documento)](https://drive.google.com/file/d/abcdefg/view?usp=drivesdk)
O {{url_viewer}} fornecido aqui é sempre uma URL ABSOLUTA.


PARA FONTES EXTERNAS (como NRs do MTE):

Se sua resposta se refere a uma NR específica, use os links oficiais abaixo, se aplicável, e explique o status da NR se ela foi revogada.
Links Oficiais MTE (USE SOMENTE ESTES E OS MANTENHA ATUALIZADOS):
Base Geral NRs: https://www.gov.br/trabalho-e-emprego/pt-br/assuntos/inspecao-do-trabalho/seguranca-e-saude-no-trabalho/ctpp-nrs/normas-regulamentadoras-nrs
NR 1: https://www.gov.br/trabalho-e-emprego/pt-br/seguranca-e-saude-no-trabalho/normatizacao/normas-regulamentadoras/nr-1 (Disposições Gerais e Gerenciamento de Riscos Ocupacionais)
NR 2 (REVOGADA): A Norma Regulamentadora nº 2 (NR-2), que tratava da Inspeção Prévia, foi REVOGADA pela Portaria MTP nº 672, de 8 de novembro de 2021. Suas disposições sobre inspeções foram incorporadas e atualizadas principalmente na NR 1 (Disposições Gerais e Gerenciamento de Riscos Ocupacionais) e na NR 12 (Segurança no Trabalho em Máquinas e Equipamentos). NÃO FORNEÇA UM LINK PARA A NR 2 REVOGADA. Se a pergunta for sobre NR 2, sua resposta DEVE obrigatoriamente esclarecer seu status de revogada e citar a NR 1 ou NR 12 como as normas atualmente relevantes para o tema.
NR 3: https://www.gov.br/trabalho-e-emprego/pt-br/seguranca-e-saude-no-trabalho/normatizacao/normas-regulamentadoras/nr-3 (Embargo ou Interdição)
NR 4: https://www.gov.br/trabalho-e-emprego/pt-br/seguranca-e-saude-no-trabalho/normatizacao/normas-regulamentadoras/nr-4 (Serviços Especializados em Engenharia de Segurança e em Medicina do Trabalho - SESMT)
NR 5: https://www.gov.br/trabalho-e-emprego/pt-br/seguranca-e-saude-no-trabalho/normatizacao/normas-regulamentadoras/nr-5 (Comissão Interna de Prevenção de Acidentes - CIPA)
NR 6: https://www.gov.br/trabalho-e-emprego/pt-br/seguranca-e-saude-no-trabalho/normatizacao/normas-regulamentadoras/nr-6 (Equipamento de Proteção Individual - EPI)
NR 7: https://www.gov.br/trabalho-e-emprego/pt-br/seguranca-e-saude-no-trabalho/normatizacao/normas-regulamentadoras/nr-7 (Programa de Controle Médico de Saúde Ocupacional - PCMSO)
NR 8: https://www.gov.br/trabalho-e-emprego/pt-br/seguranca-e-saude-no-trabalho/normatizacao/normas-regulamentadoras/nr-8 (Edificações)
NR 9: https://www.gov.br/trabalho-e-emprego/pt-br/seguranca-e-saude-no-trabalho/normatizacao/normas-regulamentadoras/nr-9 (Avaliação e Controle das Exposições Ocupacionais a Agentes Físicos, Químicos e Biológicos)
NR 10: https://www.gov.br/trabalho-e-emprego/pt-br/seguranca-e-saude-no-trabalho/normatizacao/normas-regulamentadoras/nr-10 (Segurança em Instalações e Serviços em Eletricidade)
NR 11: https://www.gov.br/trabalho-e-emprego/pt-br/seguranca-e-saude-no-trabalho/normatizacao/normas-regulamentadoras/nr-11 (Transporte, Movimentação, Armazenagem e Manuseio de Materiais)
NR 12: https://www.gov.br/trabalho-e-emprego/pt-br/seguranca-e-saude-no-trabalho/normatizacao/normas-regulamentadoras/nr-12 (Segurança no Trabalho em Máquinas e Equipamentos)
NR 13: https://www.gov.br/trabalho-e-emprego/pt-br/seguranca-e-saude-no-trabalho/normatizacao/normas-regulamentadoras/nr-13 (Caldeiras, Vasos de Pressão, Tubulações e Tanques Metálicos de Armazenamento)
NR 14: https://www.gov.br/trabalho-e-emprego/pt-br/seguranca-e-saude-no-trabalho/normatizacao/normas-regulamentadoras/nr-14 (Fornos Industriais)
NR 15: https://www.gov.br/trabalho-e-emprego/pt-br/seguranca-e-saude-no-trabalho/normatizacao/normas-regulamentadoras/nr-15 (Atividades e Operações Insalubres)
NR 16: https://www.gov.br/trabalho-e-emprego/pt-br/seguranca-e-saude-no-trabalho/normatizacao/normas-regulamentadoras/nr-16 (Atividades e Operações Perigosas)
NR 17: https://www.gov.br/trabalho-e-emprego/pt-br/seguranca-e-saude-no-trabalho/normatizacao/normas-regulamentadoras/nr-17 (Ergonomia)
NR 18: https://www.gov.br/trabalho-e-emprego/pt-br/seguranca-e-saude-no-trabalho/normatizacao/normas-regulamentadoras/nr-18 (Condições e Meio Ambiente de Trabalho na Indústria da Construção)
NR 19: https://www.gov.br/trabalho-e-emprego/pt-br/seguranca-e-saude-no-trabalho/normatizacao/normas-regulamentadoras/nr-19 (Explosivos)
NR 20: https://www.gov.br/trabalho-e-emprego/pt-br/seguranca-e-saude-no-trabalho/normatizacao/normas-regulamentadoras/nr-20 (Segurança e Saúde no Trabalho com Inflamáveis e Combustíveis)
NR 21: https://www.gov.br/trabalho-e-emprego/pt-br/seguranca-e-saude-no-trabalho/normatizacao/normas-regulamentadoras/nr-21 (Trabalho a Céu Aberto)
NR 22: https://www.gov.br/trabalho-e-emprego/pt-br/seguranca-e-saude-no-trabalho/normatizacao/normas-regulamentadoras/nr-22 (Segurança e Saúde Ocupacional na Mineração)
NR 23: https://www.gov.br/trabalho-e-emprego/pt-br/seguranca-e-saude-no-trabalho/normatizacao/normas-regulamentadoras/nr-23 (Proteção Contra Incêndios)
NR 24: https://www.gov.br/trabalho-e-emprego/pt-br/seguranca-e-saude-no-trabalho/normatizacao/normas-regulamentadoras/nr-24 (Condições Sanitárias e de Conforto nos Locais de Trabalho)
NR 25: https://www.gov.br/trabalho-e-emprego/pt-br/seguranca-e-saude-no-trabalho/normatizacao/normas-regulamentadoras/nr-25 (Resíduos Industriais)
NR 26: https://www.gov.br/trabalho-e-emprego/pt-br/seguranca-e-saude-no-trabalho/normatizacao/normas-regulamentadoras/nr-26 (Sinalização de Segurança)
NR 27 (REVOGADA/Não-Regulamentada): A NR 27, que trataria do Registro Profissional do Técnico de Segurança do Trabalho, foi revogada pela Portaria GM n.º 262, de 29 de maio de 2008, e suas disposições foram incorporadas em outras legislações. NÃO FORNEÇA UM LINK PARA A NR 27.
NR 28: https://www.gov.br/trabalho-e-emprego/pt-br/seguranca-e-saude-no-trabalho/normatizacao/normas-regulamentadoras/nr-28 (Fiscalização e Penalidades)
NR 29: https://www.gov.br/trabalho-e-emprego/pt-br/seguranca-e-saude-no-trabalho/normatizacao/normas-regulamentadoras/nr-29 (Segurança e Saúde no Trabalho Portuário)
NR 30: https://www.gov.br/trabalho-e-emprego/pt-br/seguranca-e-saude-no-trabalho/normatizacao/normas-regulamentadoras/nr-30 (Segurança e Saúde no Trabalho Aquaviário)
NR 31: https://www.gov.br/trabalho-e-emprego/pt-br/seguranca-e-saude-no-trabalho/normatizacao/normas-regulamentadoras/nr-31 (Segurança e Saúde no Trabalho na Agricultura, Pecuária Silvicultura, Exploração Florestal e Aquicultura)
NR 32: https://www.gov.br/trabalho-e-emprego/pt-br/seguranca-e-saude-no-trabalho/normatizacao/normas-regulamentadoras/nr-32 (Segurança e Saúde no Trabalho em Serviços de Saúde)
NR 33: https://www.gov.br/trabalho-e-emprego/pt-br/seguranca-e-saude-no-trabalho/normatizacao/normas-regulamentadoras/nr-33 (Espaços Confinados)
NR 34: https://www.gov.br/trabalho-e-emprego/pt-br/seguranca-e-saude-no-trabalho/normatizacao/normas-regulamentadoras/nr-34 (Condições e Meio Ambiente de Trabalho na Indústria da Construção e Reparação Naval)
NR 35: https://www.gov.br/trabalho-e-emprego/pt-br/seguranca-e-saude-no-trabalho/normatizacao/normas-regulamentadoras/nr-35 (Trabalho em Altura)
NR 36: https://www.gov.br/trabalho-e-emprego/pt-br/seguranca-e-saude-no-trabalho/normatizacao/normas-regulamentadoras/nr-36 (Segurança e Saúde no Trabalho em Empresas de Abate e Processamento de Carnes e Derivados)
NR 37: https://www.gov.br/trabalho-e-emprego/pt-br/seguranca-e-saude-no-trabalho/normatizacao/normas-regulamentadoras/nr-37 (Segurança e Saúde em Plataformas de Petróleo)
NR 38: https://www.gov.br/trabalho-e-emprego/pt-br/seguranca-e-saude-no-trabalho/normatizacao/normas-regulamentadoras/nr-38 (Segurança e Saúde no Trabalho nas Atividades de Limpeza Urbana e Manejo de Resíduos Sólidos Urbanos)


Formato EXATO da citação DEVE ser (para NRs ativas): [Norma Regulamentadora nº X (MTE) (ver documento)](URL_ABSOLUTA_E_REAL_DA_NR_NO_MTE)
Exemplo para NR 1: [Norma Regulamentadora nº 1 (MTE) (ver documento)](https://www.gov.br/trabalho-e-emprego/pt-br/seguranca-e-saude-no-trabalho/normatizacao/normas-regulamentadoras/nr-1)
NUNCA invente links ou diga que não tem acesso à internet. Utilize os links fornecidos aqui e o formato especificado.

Contexto da Base de Conhecimento Interna (detalhes estruturados para citação):

{retrieved_context}

{dynamic_context_str}
"""

class NRQuestionAnswering:
    """
    Sistema de QA para NRs (Normas Regulamentadoras) utilizando RAG (Retrieval Augmented Generation)
    com modelos Google Generative AI ou OpenRouter AI. Inclui recuperação híbrida (BM25 + Vector DB).
    """

    def __init__(self, collection_name: str = COLLECTION_NAME, model_name: str = EMBEDDING_MODEL_NAME):
        """
        Inicializa o sistema de QA.

        Args:
            collection_name (str): Nome da coleção no ChromaDB.
            model_name (str): Nome do modelo de embeddings da HuggingFace.
        """
        self.collection_name = collection_name
        self.embedding_function = SentenceTransformerEmbeddings(model_name=model_name)
        logger.info(f"Loaded SentenceTransformer embedding model: {EMBEDDING_MODEL_NAME}")

        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            add_start_index=True,
        )
        self.chroma_client = self._initialize_chroma()
        self.vector_db = Chroma(
            collection_name=self.collection_name,
            embedding_function=self.embedding_function,
            client=self.chroma_client,
            persist_directory=CHROMADB_PERSIST_DIRECTORY
        )
        self.chroma_doc_count = self.vector_db._collection.count()
        if self.chroma_doc_count > 0:
            logger.info(f"ChromaDB: Collection '{COLLECTION_NAME}' loaded with {self.chroma_doc_count} documents.")
        else:
            logger.warning(f"ChromaDB: Collection '{COLLECTION_NAME}' loaded but is empty. No documents found.")

        self.llm = self._initialize_llm()
        
        self.bm25_retriever: Optional[BM25Retriever] = None
        self.vector_retriever = self.vector_db.as_retriever(search_type="mmr", search_kwargs={"k": 5})
        self.ensemble_retriever: Optional[EnsembleRetriever] = None
        self.retriever: Any = self.vector_retriever # Usado para logging ou acesso direto, mas a cadeia usará current_retriever

        if self.chroma_doc_count > 0:
            self.update_retrievers()
        else:
            logger.warning("ChromaDB vazia na inicialização. EnsembleRetriever não configurado inicialmente.")

        self.rag_chain = self._setup_rag_chain()

        logger.info("Sistema NRQuestionAnswering inicializado. ChromaDB e LLM configurados.")
        logger.info("Retriever principal (EnsembleRetriever ou Vector Retriever) configurado.")

    def _initialize_chroma(self):
        """Inicializa e retorna o cliente ChromaDB."""
        try:
            from chromadb import PersistentClient
            os.makedirs(CHROMADB_PERSIST_DIRECTORY, exist_ok=True)
            client = PersistentClient(path=CHROMADB_PERSIST_DIRECTORY)
            logger.info(f"ChromaDB PersistentClient inicializado em: {CHROMADB_PERSIST_DIRECTORY}")
            return client
        except Exception as e:
            logger.critical(f"CRITICAL ERROR initializing ChromaDB PersistentClient: {e}", exc_info=True)
            error_message = f"Erro crítico ao inicializar o banco de dados ChromaDB. Detalhes: {e}"
            _render_info_like_message_for_rag("error", error_message, THEME['icons']['error_x'])
            raise

    def _initialize_llm(self):
        """Inicializa e retorna o modelo LLM, priorizando OpenRouter se configurado."""
        openrouter_api_key = os.getenv("OPENROUTER_API_KEY")
        openrouter_model_name = os.getenv("OPENROUTER_MODEL_NAME")
        google_api_key = os.getenv("GOOGLE_API_KEY")

        # --- Tenta inicializar com OpenRouter ---
        if openrouter_api_key and openrouter_model_name:
            try:
                llm = ChatOpenAI(
                    openai_api_base="https://openrouter.ai/api/v1",
                    openai_api_key=openrouter_api_key,
                    model_name=openrouter_model_name,
                    temperature=0.4,
                    # Adicionar extra_headers conforme a recomendação do OpenRouter para atribuição do app
                    model_kwargs={
                        "extra_headers": {
                            "HTTP-Referer": "https://safetyai.streamlit.app/", # URL do seu app Streamlit (substitua se tiver uma diferente)
                            "X-Title": "SafetyAI - SST"
                        }
                    }
                )
                logger.info(f"Modelo OpenRouter ({openrouter_model_name}) inicializado com sucesso.")
                return llm
            except Exception as e:
                logger.error(f"Erro ao inicializar o modelo OpenRouter ({openrouter_model_name}): {e}", exc_info=True)
                error_message = (
                    f"**Erro ao inicializar o modelo de IA do OpenRouter (`{openrouter_model_name}`)!** \n"
                    f"Por favor, verifique os seguintes pontos:\n"
                    f"1. Sua `OPENROUTER_API_KEY` está correta no arquivo `.env`?\n"
                    f"2. O `OPENROUTER_MODEL_NAME` (`{openrouter_model_name}`) está correto e disponível no OpenRouter para sua chave de API?\n"
                    f"3. Você tem créditos suficientes (se for um modelo pago) ou está dentro dos limites de uso (se for gratuito)?\n\n"
                    f"Detalhes técnicos do erro: `{e}`"
                )
                _render_info_like_message_for_rag("error", error_message, THEME['icons']['error_x'])
                # Continua para tentar o Google Gemini como fallback
        elif openrouter_api_key and not openrouter_model_name:
            warning_message = (
                f"**Aviso: OPENROUTER_API_KEY está configurada, mas OPENROUTER_MODEL_NAME não!**\n"
                f"Por favor, defina um modelo no seu `.env` para usar o OpenRouter. "
                f"Tentando inicializar com Google Gemini como fallback."
            )
            _render_info_like_message_for_rag("warning", warning_message, THEME['icons']['warning_sign'])
        elif not openrouter_api_key and openrouter_model_name:
            warning_message = (
                f"**Aviso: OPENROUTER_MODEL_NAME está configurado, mas OPENROUTER_API_KEY não!**\n"
                f"Por favor, defina sua chave de API no seu `.env` para usar o OpenRouter. "
                f"Tentando inicializar com Google Gemini como fallback."
            )
            _render_info_like_message_for_rag("warning", warning_message, THEME['icons']['warning_sign'])

        # --- Fallback para Google Gemini ---
        if google_api_key:
            try:
                llm = ChatGoogleGenerativeAI(
                    model=GEMINI_MODEL,
                    google_api_key=google_api_key,
                    temperature=0.4,
                    convert_system_message_to_human=True
                )
                logger.info(f"Modelo Google Generative AI ({GEMINI_MODEL}) inicializado com sucesso.")
                return llm
            except Exception as e:
                logger.error(f"Erro ao inicializar o modelo Google Generative AI: {e}", exc_info=True)
                error_message = (
                    f"**Erro ao inicializar o modelo de IA do Google (`{GEMINI_MODEL}`)!** \n"
                    f"Por favor, verifique os seguintes pontos no seu ambiente Google Cloud:\n"
                    f"1. Sua `GOOGLE_API_KEY` está correta no arquivo `.env`?\n"
                    f"2. A **'Generative Language API'** ou **'Vertex AI API'** está(ão) habilitada(s) no seu projeto do Google Cloud Console? (Vá em APIs & Services -> Dashboard)\n"
                    f"3. O modelo `{GEMINI_MODEL}` está disponível para sua API Key ou região? Verifique a lista de modelos disponíveis no Google AI Studio.\n\n"
                    f"Detalhes técnicos do erro: `{e}`"
                )
                _render_info_like_message_for_rag("error", error_message, THEME['icons']['error_x'])
                return None
        else:
            error_message = (
                f"**Erro Crítico: Nenhuma chave de API (OpenRouter ou Google) está configurada!**\n"
                f"Por favor, adicione `OPENROUTER_API_KEY` e `OPENROUTER_MODEL_NAME` (ou `GOOGLE_API_KEY`) ao seu arquivo `.env`."
            )
            _render_info_like_message_for_rag("error", error_message, THEME['icons']['error_x'])
            return None


    def _setup_rag_chain(self):
        """Configura a cadeia RAG com um prompt adaptado, incluindo contexto dinâmico e histórico de chat."""
        if not self.llm:
            warning_message = "LLM não está inicializado. A cadeia RAG não pode ser configurada."
            _render_info_like_message_for_rag("warning", warning_message, THEME['icons']['warning_sign'])
            return None
        
        # Cria o prompt de chat completo, incluindo o SYSTEM_MESSAGE, histórico e a pergunta do usuário
        system_message_prompt = SystemMessagePromptTemplate.from_template(GENERAL_SST_SYSTEM_MESSAGE)
        human_message_prompt = HumanMessagePromptTemplate.from_template("{question}")
        
        prompt = ChatPromptTemplate.from_messages([
            system_message_prompt,
            MessagesPlaceholder(variable_name="chat_history_messages"), # Para o histórico formatado
            human_message_prompt
        ])

        current_retriever = self.ensemble_retriever if self.ensemble_retriever else self.vector_retriever
        
        if not current_retriever:
            error_message = "Nenhum retriever configurado. Não é possível configurar a cadeia RAG."
            _render_info_like_message_for_rag("error", error_message, THEME['icons']['error_x'])
            return None

        # Função para formatar os documentos para o prompt
        # Esta função apenas prepara o contexto para o LLM. A formatação de saída da citação
        # é definida pelo LLM com base no GENERAL_SST_SYSTEM_MESSAGE.
        def format_docs_with_links(docs):
            formatted_strings = []
            for i, doc in enumerate(docs):
                doc_name_raw = doc.metadata.get('document_name', 'Documento Desconhecido')
                clean_doc_name = _get_clean_document_name(doc_name_raw) # Use a nova função auxiliar
                page_number = doc.metadata.get('page_number', 'N/A') # Use 'N/A' se não disponível
                drive_file_id = doc.metadata.get('drive_file_id', None)
                
                url_viewer = "N/A" # Default para 'N/A'
                if drive_file_id:
                    encoded_drive_file_id = quote_plus(drive_file_id)
                    url_viewer = f"https://drive.google.com/file/d/{encoded_drive_file_id}/view?usp=drivesdk"

                # Pass structured info to LLM, clearly indicating fields with quotes for clarity
                # O LLM DEVE USAR ESTAS VARIÁVEIS PARA CONSTRUIR AS CITAÇÕES.
                source_metadata_str = (
                    f"document_name_clean: '{clean_doc_name}', "
                    f"page_number: '{page_number}', "
                    f"url_viewer: '{url_viewer}'"
                )
                
                # Apresentar o conteúdo do documento e a informação da fonte ao LLM
                formatted_strings.append(f"--- Início do Conteúdo do Documento ---\n{doc.page_content}\n--- Fim do Conteúdo do Documento ---\nMETADATA_FONTE_INTERNA: {source_metadata_str}")
            return "\n\n".join(formatted_strings)


        # A cadeia RAG agora é um RunnableParallel que prepara todas as entradas para o prompt
        rag_chain = (
            RunnableParallel(
                # O retriever recebe apenas a "question" como input e formata os docs com links
                retrieved_context=itemgetter("question") | current_retriever | RunnableLambda(format_docs_with_links),
                # O contexto dinâmico é formatado se existir, usando RunnableLambda
                dynamic_context_str=itemgetter("dynamic_context_texts") | RunnableLambda(lambda x: "\n\n### Documentos Anexados pelo Usuário (ALTA PRIORIDADE):\n" + "\n---\n".join(x) + "\n---\n" if x else ""),
                # A pergunta original e o histórico de chat formatado são passados para o prompt
                question=itemgetter("question"),
                chat_history_messages=itemgetter("chat_history_messages") # Recebe o histórico já formatado
            )
            | prompt
            | self.llm
            | StrOutputParser()
        )
        logger.info(f"Cadeia RAG configurada usando: {current_retriever.__class__.__name__}.")
        return rag_chain

    def update_retrievers(self):
        """
        Atualiza o BM25Retriever e o EnsembleRetriever com base nos documentos atuais no ChromaDB.
        Deve ser chamado após adicionar/remover documentos.
        """
        try:
            # Obtém todos os documentos do ChromaDB para construir o BM25 Retriever
            all_chroma_docs_raw = self.vector_db._collection.get(ids=None, include=["documents", "metadatas"])
            
            if not all_chroma_docs_raw['documents']:
                logger.warning("Nenhum documento encontrado na ChromaDB para inicializar BM25Retriever. Revertendo para Vector Retriever.")
                self.retriever = self.vector_db.as_retriever(search_type="mmr", search_kwargs={"k": 5})
                self.bm25_retriever = None
                self.ensemble_retriever = None
                self.rag_chain = self._setup_rag_chain() # Reconfigura a cadeia com o retriever atualizado
                return

            docs_for_bm25 = [
                Document(page_content=doc_content, metadata=all_chroma_docs_raw['metadatas'][i])
                for i, doc_content in enumerate(all_chroma_docs_raw['documents'])
            ]
            
            self.bm25_retriever = BM25Retriever.from_documents(docs_for_bm25)
            self.bm25_retriever.k = 3 # Número de documentos a serem retornados pelo BM25

            self.ensemble_retriever = EnsembleRetriever(
                retrievers=[self.bm25_retriever, self.vector_retriever],
                weights=[0.5, 0.5] # Pesos para a combinação
            )
            self.retriever = self.ensemble_retriever # Define o retriever principal como EnsembleRetriever

            logger.info("BM25Retriever inicializado com documentos existentes.")
            logger.info("Configurado EnsembleRetriever (BM25 + Vector DB) para busca híbrida.")

            # Certifique-se de que self.rag_chain seja atualizado APÓS self.ensemble_retriever ser configurado
            self.rag_chain = self._setup_rag_chain() 
            logger.info("Cadeia RAG atualizada para usar o EnsembleRetriever.")
        except Exception as e:
            logger.error(f"Erro ao atualizar os retrievers (BM25/Ensemble): {e}", exc_info=True)
            error_message = f"Erro ao configurar a busca híbrida (EnsembleRetriever). Usando apenas busca vetorial. Detalhes: {e}"
            _render_info_like_message_for_rag("error", error_message, THEME['icons']['error_x'])
            self.retriever = self.vector_db.as_retriever(search_type="mmr", search_kwargs={"k": 5})
            # Mesmo em caso de erro, tente configurar a cadeia RAG com o retriever fallback
            self.rag_chain = self._setup_rag_chain()


    def _get_loader_for_file_type(self, file_path: str, file_type: str):
        """Retorna o loader apropriado da Langchain para o tipo de arquivo."""
        if file_type == 'application/pdf':
            return PyPDFLoader(file_path)
        elif file_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
            return Docx2txtLoader(file_path)
        elif file_type == 'text/plain' or file_type == "text/markdown" or file_type == "text/html":
            return TextLoader(file_path, encoding='utf-8')
        else:
            logger.error(f"No specific Langchain loader defined for processable file type '{file_type}'.")
            raise NotImplementedError(f"Loader not implemented for file type '{file_type}'.")


    def process_document_to_chroma(self, file_path: str, document_name: str, source: str = "Local", file_type: str = "application/pdf", additional_metadata: Optional[Dict[str, Any]] = None):
        """
        Processa um documento, divide em chunks e adiciona ao ChromaDB.
        """
        logger.info(f"Iniciando processamento do documento: '{document_name}' ({file_type})")
        
        try:
            if not os.path.exists(file_path):
                logger.error(f"File not found at path: {file_path}")
                error_message = f"Erro: Arquivo '{document_name}' não encontrado no caminho temporário."
                _render_info_like_message_for_rag("error", error_message, THEME['icons']['error_x'])
                return

            if file_type not in PROCESSABLE_MIME_TYPES:
                logger.error(f"File type '{file_type}' is not supported for text extraction. Processable types: {PROCESSABLE_MIME_TYPES}")
                warning_message = f"Tipo de arquivo '{file_type}' não suportado para ingestão. Documento '{document_name}' ignorado."
                _render_info_like_message_for_rag("warning", warning_message, THEME['icons']['warning_sign'])
                return

            loader = self._get_loader_for_file_type(file_path, file_type)
            documents = loader.load()
            logger.info(f"Documento '{document_name}' carregado. Total de páginas/elementos: {len(documents)}")

            document_metadata_id = additional_metadata.get("drive_file_id") if additional_metadata and additional_metadata.get("drive_file_id") else str(uuid.uuid4())

            base_metadata = {
                "document_name": document_name,
                "source": source,
                "file_type": file_type,
                "upload_timestamp": datetime.now().isoformat(),
                "document_metadata_id": document_metadata_id
            }
            if additional_metadata:
                base_metadata.update(additional_metadata)

            for doc in documents:
                doc.metadata.update(base_metadata)
                if "page" in doc.metadata:
                    doc.metadata["page_number"] = doc.metadata["page"]
                    del doc.metadata["page"]
                elif "loc" in doc.metadata and isinstance(doc.metadata["loc"], dict) and "page_number" in doc.metadata["loc"]:
                    doc.metadata["page_number"] = doc.metadata["loc"]["page_number"]
                    del doc.metadata["loc"]


            chunks = self.text_splitter.split_documents(documents)
            logger.info(f"Documento '{document_name}' dividido em {len(chunks)} chunks.")

            for chunk in chunks:
                if "chunk_id" not in chunk.metadata:
                    chunk.metadata["chunk_id"] = str(uuid.uuid4())


            self.vector_db.add_documents(chunks)
            logger.info(f"{len(chunks)} chunks de '{document_name}' adicionados ao ChromaDB com sucesso.")
            success_message = f"Documento '{document_name}' processado e adicionado à base de conhecimento."
            _render_info_like_message_for_rag("success", success_message, THEME['icons']['success_check'])
            
            self.update_retrievers()

        except Exception as e:
            logger.error(f"Erro ao processar '{document_name}': {e}", exc_info=True)
            error_message = f"Erro ao processar o documento '{document_name}'. Detalhes: {e}"
            _render_info_like_message_for_rag("error", error_message, THEME['icons']['error_x'])

    def add_simple_text_to_collection(self, content: str, document_name: str, source: str = "User Input", source_type: str = "UserUploadedText", metadata: Optional[Dict[str, Any]] = None):
        logger.info(f"Adding simple text '{document_name}' to ChromaDB collection.")
        doc_metadata = metadata if metadata is not None else {}

        document_metadata_id = doc_metadata.get("document_metadata_id") if doc_metadata and doc_metadata.get("document_metadata_id") else str(uuid.uuid4())

        doc_metadata.update({
            "document_name": document_name,
            "source": source,
            "source_type": source_type,
            "file_type": "text/plain",
            "page_number": "N/A",
            "document_metadata_id": document_metadata_id,
            "chunk_id": str(uuid.uuid4())
        })
        doc = Document(page_content=content, metadata=doc_metadata)
        self.vector_db.add_documents([doc])
        logger.info(f"Document '{document_name}' (ID: {document_metadata_id}) added to ChromaDB collection.")
        self.update_retrievers()

    def list_processed_documents(self) -> List[Dict]:
        if self.vector_db:
            documents_info = {}

            results = self.vector_db._collection.get(ids=None, include=['metadatas'])
            all_metadatas = results.get('metadatas', [])

            for metadata in all_metadatas:
                doc_name = metadata.get("document_name")
                source = metadata.get("source", "Unknown")
                source_type = metadata.get("source_type", "N/A")

                if doc_name:
                    document_metadata_id = metadata.get("document_metadata_id")
                    if not document_metadata_id:
                        document_metadata_id = (doc_name, source, source_type)

                    key = document_metadata_id

                    if key not in documents_info:
                        documents_info[key] = {
                            "name": doc_name,
                            "source": source,
                            "source_type": source_type,
                            "chunks": 0,
                            "file_type": metadata.get("file_type"),
                            "drive_file_id": metadata.get("drive_file_id"),
                            "document_metadata_id": document_metadata_id
                        }
                    documents_info[key]["chunks"] += 1

            sorted_docs = sorted(documents_info.values(), key=lambda x: x['name'])
            logger.info(f"Listed {len(sorted_docs)} unique documents in ChromaDB collection.")
            return sorted_docs
        else:
            logger.warning("ChromaDB collection not available to list documents.")
            return []

    def get_drive_file_ids_in_chroma(self, source_type: Optional[str] = None) -> List[str]:
        if not self.vector_db:
            logger.warning("ChromaDB collection not initialized to search for drive_file_ids.")
            return []

        where_clause = {}
        if source_type:
            where_clause["source_type"] = source_type

        try:
            results = self.vector_db._collection.get(
                where=where_clause,
                ids=None,
                include=['metadatas']
            )

            file_ids = set()
            for metadata in results.get('metadatas', []):
                if 'drive_file_id' in metadata and metadata['drive_file_id']:
                    file_ids.add(metadata['drive_file_id'])
            return list(file_ids)
        except Exception as e:
            logger.error(f"Error fetching drive_file_ids from ChromaDB (source_type: {source_type}): {e}", exc_info=True)
            return []

    def clear_chroma_collection(self) -> None:
        """
        Limpa completamente a coleção ChromaDB, excluindo-a e re-inicializando.
        """
        try:
            if self.vector_db and self.vector_db._client:
                self.vector_db._client.delete_collection(self.vector_db._collection.name)
                logger.info(f"ChromaDB collection '{self.collection_name}' deleted successfully.")
            else:
                logger.warning("ChromaDB client not available to delete collection or collection not found. Attempting to re-initialize anyway.")

            self.vector_db = Chroma(
                collection_name=self.collection_name,
                embedding_function=self.embedding_function,
                client=self.chroma_client,
                persist_directory=CHROMADB_PERSIST_DIRECTORY
            )
            logger.info(f"ChromaDB collection '{self.collection_name}' re-initialized as empty.")

            self.bm25_retriever = None
            self.vector_retriever = self.vector_db.as_retriever(search_type="mmr", search_kwargs={"k": 5})
            self.ensemble_retriever = None
            self.retriever = self.vector_retriever
            self.rag_chain = self._setup_rag_chain()

            logger.info("Retrievers re-inicializados após limpeza da coleção (agora vazios).")

        except Exception as e:
            logger.error(f"Error clearing and re-initializing ChromaDB collection '{self.collection_name}': {e}", exc_info=True)
            error_message = f"Erro ao limpar e reiniciar a base de conhecimento. Detalhes: {e}"
            _render_info_like_message_for_rag("error", error_message, THEME['icons']['error_x'])
            raise

    def clear_docs_by_source_type(self, source_type_to_remove: str) -> int:
        if self.vector_db:
            try:
                results_to_delete = self.vector_db._collection.get(
                    where={"source_type": source_type_to_remove},
                    ids=None,
                    include=[]
                )
                ids_to_delete = results_to_delete.get('ids', [])

                if ids_to_delete:
                    self.vector_db._collection.delete(ids=ids_to_delete)
                    logger.info(f"Removed {len(ids_to_delete)} chunks with source_type '{source_type_to_remove}' from ChromaDB collection.")
                    self.update_retrievers()
                    return len(ids_to_delete)
                else:
                    logger.info(f"No documents with source_type '{source_type_to_remove}' found to remove from ChromaDB collection.")
                    return 0
            except Exception as e:
                logger.error(f"Error removing documents with source_type '{source_type_to_remove}' from ChromaDB: {e}", exc_info=True)
                error_message = f"Erro ao remover documentos por tipo de fonte. Detalhes: {e}"
                _render_info_like_message_for_rag("error", error_message, THEME['icons']['error_x'])
                return 0
        else:
            logger.warning("ChromaDB collection not available to remove documents.")
            return 0

    def remove_document_by_id(self, document_metadata_id: str) -> int:
        """
        Remove documentos da coleção ChromaDB com base em seu document_metadata_id.
        """
        if self.vector_db:
            try:
                results_to_delete = self.vector_db._collection.get(
                    where={"document_metadata_id": document_metadata_id},
                    ids=None,
                    include=[]
                )
                ids_to_delete = results_to_delete.get('ids', [])

                if ids_to_delete:
                    self.vector_db._collection.delete(ids=ids_to_delete)
                    logger.info(f"Removed {len(ids_to_delete)} chunks associated with document_metadata_id '{document_metadata_id}' from ChromaDB collection.")
                    self.update_retrievers()
                    return len(ids_to_delete)
                else:
                    logger.info(f"No documents associated with document_metadata_id '{document_metadata_id}' found to remove.")
                    return 0
            except Exception as e:
                logger.error(f"Error removing documents for document_metadata_id '{document_metadata_id}' from ChromaDB: {e}", exc_info=True)
                error_message = f"Erro ao remover documento. Detalhes: {e}"
                _render_info_like_message_for_rag("error", error_message, THEME['icons']['error_x'])
                return 0
        else:
            logger.warning("ChromaDB collection not available to remove documents.")
            return 0


    def answer_question(self, query: str, chat_history: List[Dict[str, str]], dynamic_context_texts: List[str] = []) -> str:
        """
        Faz uma pergunta ao sistema de QA.
        """
        if not self.rag_chain:
            return "O sistema de IA não está completamente inicializado ou houve um erro na configuração da cadeia RAG. Por favor, tente novamente mais tarde."
        
        try:
            logger.info(f"Processando pergunta: '{query}' com retriever: {self.retriever.__class__.__name__ if self.retriever else 'N/A'}")
            
            # Converte o histórico do chat para o formato MessagesPlaceholder
            chat_history_messages = []
            for msg in chat_history:
                if msg["role"] == "user":
                    chat_history_messages.append(HumanMessage(content=msg["content"]))
                elif msg["role"] == "ai":
                    chat_history_messages.append(AIMessage(content=msg["content"]))

            # A cadeia RAG agora é responsável por todo o processo de recuperação e formatação do prompt.
            # Basta passar a pergunta, o contexto dinâmico e o histórico do chat como entrada para a cadeia.
            response = self.rag_chain.invoke({
                "question": query,
                "dynamic_context_texts": dynamic_context_texts,
                "chat_history_messages": chat_history_messages # Passa o histórico já formatado
            })
            
            return response
        except Exception as e:
            logger.error(f"Erro ao processar a pergunta '{query}': {e}", exc_info=True)
            return f"Desculpe, ocorreu um erro ao gerar a resposta. Por favor, tente novamente ou faça outra pergunta. Detalhes: {e}."
