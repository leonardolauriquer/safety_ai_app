import json
import os
from sentence_transformers import SentenceTransformer
import chromadb
from chromadb.utils import embedding_functions

# Caminho para o arquivo JSON com os chunks da NR-35
NR_CHUNKS_FILE = os.path.join("data", "nrs", "nr_35_chunks.json")

# Caminho para o diretório de persistência do ChromaDB
# Isso criará ou usará uma pasta 'chroma_db' dentro de 'data'
CHROMADB_PERSIST_DIRECTORY = os.path.join("data", "chroma_db") 

# Nome da coleção no ChromaDB onde os embeddings serão armazenados
COLLECTION_NAME = "nrs_collection"

def load_nr_chunks(file_path):
    """Carrega os chunks da NR a partir de um arquivo JSON."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            chunks = json.load(f)
        print(f"Chunks carregados com sucesso de {file_path}. Total: {len(chunks)}")
        return chunks
    except FileNotFoundError:
        print(f"ERRO: Arquivo {file_path} não encontrado. Certifique-se de ter executado nr_scraper.py primeiro.")
        return []
    except json.JSONDecodeError:
        print(f"ERRO: Não foi possível decodificar o JSON de {file_path}. Verifique o conteúdo do arquivo.")
        return []
    except Exception as e:
        print(f"ERRO ao carregar chunks: {e}")
        return []

def main():
    print("Iniciando processo de vetorização e indexação das NRs...")

    # 1. Carregar os chunks da NR-35
    nr_chunks = load_nr_chunks(NR_CHUNKS_FILE)
    if not nr_chunks:
        print("Nenhum chunk carregado. Encerrando.")
        return

    # Preparar os dados para o ChromaDB
    documents = [chunk["text_content"] for chunk in nr_chunks]
    metadatas = [
        {
            "nr_number": chunk["nr_number"],
            "nr_title": chunk["nr_title"],
            "item_id": chunk["item_id"],
            # AQUI ESTÁ A ALTERAÇÃO: Garante que item_title seja uma string vazia se for None
            "item_title": chunk["item_title"] if chunk["item_title"] is not None else "" 
        } for chunk in nr_chunks
    ]
    # IDs únicos para cada documento no ChromaDB
    ids = [f"nr_{chunk['nr_number']}_item_{i}" for i, chunk in enumerate(nr_chunks)]

    # 2. Inicializar o cliente ChromaDB (persistente em disco)
    # Garante que o diretório de persistência exista
    os.makedirs(CHROMADB_PERSIST_DIRECTORY, exist_ok=True)
    client = chromadb.PersistentClient(path=CHROMADB_PERSIST_DIRECTORY)

    # 3. Inicializar o modelo de Embeddings (Sentence Transformers)
    # O modelo será baixado automaticamente na primeira vez
    print(f"\nCarregando modelo de embeddings: {'sentence-transformers/all-MiniLM-L6-v2'}")
    model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')
    # A função de embedding abaixo não é estritamente necessária se você usar SentenceTransformerEmbeddingFunction diretamente
    # mas é mantida aqui para clareza sobre como os embeddings são gerados.
    embedding_function_lambda = lambda texts: model.encode(texts).tolist() 

    # Tenta obter a coleção; se não existir, cria uma nova
    try:
        collection = client.get_or_create_collection(
            name=COLLECTION_NAME,
            # Passando o model_name para a função de embedding do ChromaDB
            embedding_function=embedding_functions.SentenceTransformerEmbeddingFunction(
                model_name='sentence-transformers/all-MiniLM-L6-v2'
            )
        )
        print(f"Coleção '{COLLECTION_NAME}' carregada ou criada com sucesso.")
    except Exception as e:
        print(f"ERRO ao carregar/criar coleção ChromaDB: {e}")
        print("Isso pode ocorrer se a coleção foi criada com um modelo de embedding diferente anteriormente.")
        print("Tente deletar a pasta data/chroma_db e rodar novamente se tiver problemas.")
        return

    # Verifica se a coleção já possui dados. Se sim, não adiciona novamente.
    # Em um cenário real, você pode querer uma lógica de atualização.
    if collection.count() == 0:
        print(f"\nAdicionando {len(documents)} chunks à coleção '{COLLECTION_NAME}'...")
        # Use o embedding_function nativo do ChromaDB para simplificar
        collection.add(
            documents=documents,
            metadatas=metadatas,
            ids=ids
        )
        print(f"Chunks adicionados. Total de documentos na coleção: {collection.count()}")
    else:
        print(f"\nColeção '{COLLECTION_NAME}' já contém {collection.count()} documentos. Pulando adição de chunks.")
        print("Se desejar re-indexar, apague a pasta 'data/chroma_db' e execute novamente.")

    # 4. Demonstração de Busca (Query)
    print("\n--- Demonstração de Busca ---")
    query_text = "Quais são as responsabilidades da empresa em relação ao trabalho em altura?"
    print(f"Buscando por: '{query_text}'")

    # A função query do ChromaDB automaticamente gera o embedding para a query_text
    # e busca os documentos mais similares.
    results = collection.query(
        query_texts=[query_text],
        n_results=2,  # Retornar os 2 chunks mais relevantes
        include=['documents', 'metadatas', 'distances']
    )

    if results and results['documents']:
        for i, doc_content in enumerate(results['documents'][0]):
            metadata = results['metadatas'][0][i]
            distance = results['distances'][0][i]
            print(f"\nResultado {i+1} (Distância: {distance:.4f}):")
            print(f"  NR: {metadata.get('nr_number')}, Item ID: {metadata.get('item_id')}")
            print(f"  Conteúdo: {doc_content[:300]}...") # Mostra o início do conteúdo
    else:
        print("Nenhum resultado encontrado para a busca.")

    print("\nProcesso de vetorização e indexação concluído!")

if __name__ == "__main__":
    main()
