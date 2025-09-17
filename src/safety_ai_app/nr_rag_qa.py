import os
import chromadb
from chromadb.utils import embedding_functions
import google.generativeai as genai
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

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
            print(f"[*] ChromaDB: Coleção '{COLLECTION_NAME}' carregada ou criada. Documentos: {self.collection.count()}")
        except Exception as e:
            raise type(e)(f"ERRO ao inicializar ChromaDB: {e}. Certifique-se de que vectorize_nrs.py foi executado e que o diretório '{CHROMADB_PERSIST_DIRECTORY}' existe.")

        # 2. Configurar Google Gemini API
        api_key = os.getenv("GOOGLE_API_KEY") 
        
        # --- LINHA DE DIAGNÓSTICO ADICIONADA ---
        print(f"[*] Diagnóstico API Key: Valor lido do ambiente: '{api_key}'")
        # --- FIM DA LINHA DE DIAGNÓSTICO ---

        if not api_key:
            raise ValueError("A variável de ambiente GOOGLE_API_KEY não está configurada.")
        
        self.llm = ChatGoogleGenerativeAI(
            model=GEMINI_MODEL_NAME,
            google_api_key=api_key,
            temperature=0.4 # Um pouco mais de flexibilidade para formatação e síntese
        )
        print(f"[*] Google Gemini: Modelo '{GEMINI_MODEL_NAME}' (via Langchain) configurado.")

    def answer_question(self, query: str, chat_history: list[dict], dynamic_context_texts: list[str] = None, n_results: int = 7) -> str:
        print(f"\n[*] Processando pergunta: '{query}'")

        # Inicializa a lista de chunks de contexto, incluindo os dinâmicos primeiro
        all_context_chunks = []
        if dynamic_context_texts:
            for i, text in enumerate(dynamic_context_texts):
                all_context_chunks.append(f"### Documento do Usuário {i+1}\n{text}")
            print(f"[*] Adicionados {len(dynamic_context_texts)} chunks de contexto dinâmico.")

        # 1. Recuperação (Retrieval) - Busca no ChromaDB
        # Usa apenas a última pergunta para buscar no RAG, evitando poluir a busca com histórico irrelevante
        results = self.collection.query(
            query_texts=[query],
            n_results=n_results,
            include=['documents', 'metadatas']
        )

        if results and results['documents'] and results['documents'][0]:
            print(f"[*] Recuperados {len(results['documents'][0])} chunks relevantes do ChromaDB.")
            for i, doc_content in enumerate(results['documents'][0]):
                metadata = results['metadatas'][0][i]
                chunk_info = f"NR-{metadata.get('nr_number')} - Item: {metadata.get('item_id')}"
                all_context_chunks.append(f"### {chunk_info}\n{doc_content}")
        else:
            print("[!] Nenhum chunk relevante encontrado no ChromaDB para a pergunta.")
            if not all_context_chunks: # Se não encontrou no ChromaDB e não tem contexto dinâmico
                return "Não encontrei informações específicas sobre isso nas Normas Regulamentadoras disponíveis. Posso tentar responder de forma geral ou buscar algo diferente?"

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
        )]
        
        # Adiciona o histórico de chat (ignorando a última pergunta, que será adicionada com o contexto)
        # O histórico é adicionado em ordem cronológica inversa para que as mensagens mais recentes fiquem mais perto do final
        # e, portanto, recebam mais atenção do modelo (se o modelo considerar isso).
        for msg in chat_history:
            if msg["role"] == "user":
                messages.append(HumanMessage(content=msg["content"]))
            elif msg["role"] == "ai":
                messages.append(AIMessage(content=msg["content"]))

        # Adiciona a pergunta atual com o contexto RAG combinado
        context_str = "\n---\n".join(all_context_chunks)
        messages.append(HumanMessage(
            content=f"Contexto relevante fornecido:\n---\n{context_str}\n---\n\nMinha pergunta: {query}"
        ))
        
        # 3. Geração (Generation) - Usar Gemini para responder
        try:
            response = self.llm.invoke(messages)
            return response.content.strip()
        except Exception as e:
            print(f"[!] ERRO ao gerar resposta com Gemini API: {e}")
            return f"Desculpe, ocorreu um erro ao gerar a resposta. Poderia tentar novamente ou fazer uma pergunta diferente? Detalhes: {e}"