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
        
        # System prompt - aprimorado para enfatizar o uso do histórico e contexto
        system_prompt_content = """
        Você é um assistente especializado em Saúde e Segurança do Trabalho (SST) chamado Leo.
        Sua missão é fornecer respostas claras, precisas e fáceis de entender, baseadas **em todo o contexto fornecido (incluindo NRs e documentos do usuário)**,
        no **histórico da conversa**, e em seu conhecimento geral de SST.
        **Instruções para a resposta:**
        - **Cruze as informações:** Analise todo o contexto e seu conhecimento para sintetizar a melhor resposta possível, priorizando as informações mais relevantes para a pergunta atual e o fluxo da conversa.
        - **Priorize a clareza e a amigabilidade:**
            - Use **negrito** para destacar termos-chave e conceitos importantes.
            - Utilize **listas com marcadores (`*` ou `-`)** ou **listas numeradas (`1.`)** para organizar informações complexas, requisitos, responsabilidades ou múltiplos itens.
            - Divida a resposta em **parágrafos curtos** e coesos para facilitar a leitura.
            - Mantenha a linguagem **direta, concisa e prática**, como em uma conversa de chat.
        - **Seja honesto:** Se o contexto fornecido (incluindo NRs e documentos do usuário) for insuficiente ou não contiver a informação de forma clara para uma resposta precisa, admita isso de forma educada e sugira uma nova pergunta ou um tópico relacionado, **sem inventar informações**.
        """
        
        messages_for_llm = [SystemMessage(content=system_prompt_content)]

        # Adiciona o histórico da conversa para o LLM.
        # 'chat_history' contém todas as mensagens anteriores MAIS a pergunta atual do usuário (como último item).
        # Precisamos processar as mensagens ANTES da pergunta atual do usuário, e também filtrar
        # a mensagem inicial de boas-vindas em HTML que não é relevante para o contexto conversacional do LLM.
        
        # Número máximo de mensagens do histórico a incluir (e.g., 6 mensagens = 3 perguntas do usuário, 3 respostas da IA).
        # Isso atua como uma janela deslizante básica para gerenciar os limites de tokens do modelo. Ajuste conforme necessário.
        MAX_HISTORY_MESSAGES = 6 
        
        # Lista temporária para coletar as mensagens históricas a serem adicionadas ao prompt do LLM
        history_to_add = []
        
        # Itera sobre 'chat_history' de trás para frente, excluindo a pergunta atual do usuário (chat_history[-1]).
        # Isso garante que pegamos as mensagens mais recentes da conversa anterior.
        for msg in reversed(chat_history[:-1]):
            # Para cada mensagem, verifica se já coletamos o número máximo de mensagens históricas desejado.
            if len(history_to_add) >= MAX_HISTORY_MESSAGES:
                break # Para se o limite de mensagens históricas for atingido
            
            if msg["role"] == "user":
                history_to_add.insert(0, HumanMessage(content=msg["content"]))
            elif msg["role"] == "ai":
                # Filtra a mensagem de boas-vindas em HTML do histórico da IA para o LLM.
                # Esta mensagem é um elemento de UI e não faz parte do fluxo conversacional natural para o modelo.
                if not msg.get("is_raw_html", False):
                    history_to_add.insert(0, AIMessage(content=msg["content"]))
        
        # Adiciona as mensagens históricas coletadas ao prompt do LLM, mantendo a ordem cronológica
        messages_for_llm.extend(history_to_add)

        # Adiciona o contexto RAG combinado (NRs + documentos do usuário)
        # e a pergunta atual do usuário como um HumanMessage final.
        context_str = "\n\n--- Contexto de Referência ---\n" + "\n\n".join(all_context_chunks) + "\n--- Fim do Contexto de Referência ---\n\n"
        
        messages_for_llm.append(HumanMessage(
            content=f"{context_str}Pergunta do usuário: {query}"
        ))
        
        # 3. Geração (Generation) - Usar Gemini para responder
        try:
            response = self.llm.invoke(messages_for_llm)
            return response.content.strip()
        except Exception as e:
            print(f"[!] ERRO ao gerar resposta com Gemini API: {e}")
            # Em caso de erro, fornece uma mensagem útil ao usuário.
            return f"Desculpe, ocorreu um erro ao gerar a resposta. Poderia tentar novamente ou fazer uma pergunta diferente? Detalhes: {e}"
