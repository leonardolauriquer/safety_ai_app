# src/safety_ai_app/nr_rag_qa.py

import os
import chromadb
from chromadb.utils import embedding_functions
import google.generativeai as genai
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from typing import List, Dict, Any, Optional
import logging # Importe o módulo logging para registrar informações

logger = logging.getLogger(__name__)

# Configurações do ChromaDB
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(script_dir, '..', '..'))
CHROMADB_PERSIST_DIRECTORY = os.path.join(project_root, "data", "chroma_db") 

COLLECTION_NAME = "nrs_collection"
EMBEDDING_MODEL_NAME = 'sentence-transformers/all-MiniLM-L6-v2'

# Configurações do Google Gemini API
GEMINI_MODEL_NAME = 'gemini-1.5-flash'

class NRQuestionAnswering:
    def __init__(self):
        # 1. Configurar ChromaDB
        try:
            os.makedirs(CHROMADB_PERSIST_DIRECTORY, exist_ok=True)
            self.chroma_client = chromadb.PersistentClient(path=CHROMADB_PERSIST_DIRECTORY)
            self.embedding_function = embedding_functions.SentenceTransformerEmbeddingFunction(
                model_name=EMBEDDING_MODEL_NAME
            )
            self.collection = self.chroma_client.get_or_create_collection(
                name=COLLECTION_NAME,
                embedding_function=self.embedding_function
            )
            logger.info(f"[*] ChromaDB: Coleção '{COLLECTION_NAME}' carregada ou criada. Documentos: {self.collection.count()}")
        except Exception as e:
            logger.error(f"ERRO ao inicializar ChromaDB: {e}. Certifique-se de que vectorize_nrs.py foi executado e que o diretório '{CHROMADB_PERSIST_DIRECTORY}' existe.")
            raise type(e)(f"ERRO ao inicializar ChromaDB: {e}. Certifique-se de que vectorize_nrs.py foi executado e que o diretório '{CHROMADB_PERSIST_DIRECTORY}' existe.")

        # 2. Configurar Google Gemini API
        api_key = os.getenv("GOOGLE_API_KEY") 
        
        # --- LINHA DE DIAGNÓSTICO ADICIONADA ---
        logger.info(f"[*] Diagnóstico API Key: Valor lido do ambiente: '{api_key}'")
        # --- FIM DA LINHA DE DIAGNÓSTICO ---

        if not api_key:
            raise ValueError("A variável de ambiente GOOGLE_API_KEY não está configurada.")
        
        self.llm = ChatGoogleGenerativeAI(
            model=GEMINI_MODEL_NAME,
            google_api_key=api_key,
            temperature=0.4 # Um pouco mais de flexibilidade para formatação e síntese
        )
        logger.info(f"[*] Google Gemini: Modelo '{GEMINI_MODEL_NAME}' (via Langchain) configurado.")

    def add_document_to_collection(self, content: str, document_id: str, metadata: Optional[Dict[str, Any]] = None):
        """
        Adiciona um documento à coleção ChromaDB.
        Este método é uma adição para facilitar a ingestão de documentos com metadados,
        incluindo o 'source_url'.
        """
        # Implementação simplificada para adicionar o documento
        # Você pode adaptar isso para usar seu text_splitter se necessário
        
        # Gera embeddings para o conteúdo
        embedding = self.embedding_function.embed_documents([content])[0] # Apenas um documento por vez aqui
        
        # Adiciona à coleção
        self.collection.add(
            documents=[content],
            metadatas=[metadata if metadata is not None else {}],
            ids=[document_id],
            embeddings=[embedding]
        )
        logger.info(f"Documento '{document_id}' adicionado à coleção ChromaDB com metadados: {metadata}")


    def answer_question(self, query: str, chat_history: list[dict], dynamic_context_texts: list[str] = None, n_results: int = 7) -> str:
        logger.info(f"\n[*] Processando pergunta: '{query}'")

        # Inicializa a lista de chunks de contexto, incluindo os dinâmicos primeiro
        all_context_chunks = []
        # Conjunto para armazenar URLs de origem únicas
        source_urls = set()

        if dynamic_context_texts:
            for i, text_data in enumerate(dynamic_context_texts):
                # Se dynamic_context_texts for uma lista de dicionários com 'content' e 'source_url'
                if isinstance(text_data, dict) and 'content' in text_data:
                    all_context_chunks.append(f"### Documento do Usuário {i+1}\n{text_data['content']}")
                    if 'source_url' in text_data and text_data['source_url']:
                        source_urls.add(text_data['source_url'])
                else: # Se for apenas texto
                    all_context_chunks.append(f"### Documento do Usuário {i+1}\n{text_data}")
            logger.info(f"[*] Adicionados {len(dynamic_context_texts)} chunks de contexto dinâmico.")

        # 1. Recuperação (Retrieval) - Busca no ChromaDB
        # Usa apenas a última pergunta para buscar no RAG, evitando poluir a busca com histórico irrelevante
        results = self.collection.query(
            query_texts=[query],
            n_results=n_results,
            include=['documents', 'metadatas']
        )

        if results and results['documents'] and results['documents'][0]:
            logger.info(f"[*] Recuperados {len(results['documents'][0])} chunks relevantes do ChromaDB.")
            for i, doc_content in enumerate(results['documents'][0]):
                metadata = results['metadatas'][0][i]
                
                # Coleta source_url dos metadados do ChromaDB
                if 'source_url' in metadata and metadata['source_url']:
                    source_urls.add(metadata['source_url'])

                chunk_info = ""
                if metadata.get('nr_number'):
                    chunk_info += f"NR-{metadata['nr_number']}"
                if metadata.get('item_id'):
                    if chunk_info: chunk_info += " - "
                    chunk_info += f"Item: {metadata['item_id']}"
                
                if not chunk_info: # Fallback se não tiver nr_number ou item_id
                    chunk_info = f"Documento (ID: {metadata.get('document_id', 'N/A')})"

                all_context_chunks.append(f"### {chunk_info}\n{doc_content}")
        else:
            logger.warning("[!] Nenhum chunk relevante encontrado no ChromaDB para a pergunta.")
            if not all_context_chunks: # Se não encontrou no ChromaDB e não tem contexto dinâmico
                return "Não encontrei informações específicas sobre isso nas Normas Regulamentadoras disponíveis. Posso tentar responder de forma geral ou buscar algo diferente?"

        # Constrói a string de informações de fonte
        source_info_str = ""
        if source_urls:
            source_info_str = "\n\nFontes de informação para esta resposta (consulte para mais detalhes):\n" + \
                              "\n".join([f"- {url}" for url in sorted(list(source_urls))]) # Ordena para consistência

        # 2. Prepara as mensagens para o LLM com o histórico e o contexto RAG combinado
        messages = [SystemMessage(
            content="Você é um assistente amigável e direto, especialista em Normas Regulamentadoras (NRs) do Brasil, com foco em Saúde e Segurança do Trabalho (SST). "
                    "Sua missão é fornecer respostas claras, precisas e fáceis de entender, baseadas **em todo o contexto fornecido (incluindo NRs e documentos do usuário)** e em seu conhecimento geral de SST. "
                    "**Cruze as informações:** Analise todo o contexto e seu conhecimento para sintetizar a melhor resposta possível. "
                    "**Priorize a clareza e a amigabilidade:**"
                    "\n- Use **negrito** para destacar termos-chave e conceitos importantes."
                    "\n- Utilize **listas com marcadores (`*` ou `-`)** ou **listas numeradas (`1.`)** para organizar informações complexas, requisitos, responsabilidades ou múltiplos itens."
                    "\n- Divida a resposta em **parágrafos curtos** e coesos para facilitar a leitura."
                    "\n- Mantenha a linguagem **direta, concisa e prática**, como em uma conversa de chat."
                    "\n- Se o contexto for insuficiente ou não contiver a informação de forma clara para uma resposta precisa, admita isso de forma educada e sugira uma nova pergunta ou um tópico relacionado, sem inventar informações."
                    "\n\n**Instrução para fontes:** Se houver 'Fontes de informação' listadas no contexto, adicione um parágrafo final na sua resposta dizendo 'Para mais detalhes, consulte as fontes abaixo:' e liste as URLs. Não reproduza o URL diretamente na sua frase, a menos que seja especificamente solicitado pelo usuário."
        )]
        
        # Adiciona o histórico de chat
        # O histórico é adicionado em ordem cronológica para manter o fluxo
        for msg in chat_history:
            if msg["role"] == "user":
                messages.append(HumanMessage(content=msg["content"]))
            elif msg["role"] == "ai":
                messages.append(AIMessage(content=msg["content"]))

        # Adiciona a pergunta atual com o contexto RAG combinado e as fontes
        context_str = "\n---\n".join(all_context_chunks)
        messages.append(HumanMessage(
            content=f"Contexto relevante fornecido:\n---\n{context_str}\n{source_info_str}\n---\n\nMinha pergunta: {query}"
        ))
        
        # 3. Geração (Generation) - Usar Gemini para responder
        try:
            response = self.llm.invoke(messages)
            logger.info(f"[*] Resposta do Gemini gerada para a pergunta: '{query}'")
            return response.content.strip()
        except Exception as e:
            logger.error(f"[!] ERRO ao gerar resposta com Gemini API para '{query}': {e}")
            return f"Desculpe, ocorreu um erro ao gerar a resposta. Poderia tentar novamente ou fazer uma pergunta diferente? Detalhes: {e}"
