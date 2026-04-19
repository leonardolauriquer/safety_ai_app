# Sistema de IA e RAG

## Visao Geral

O SafetyAI utiliza uma arquitetura RAG (Retrieval-Augmented Generation) para fornecer respostas precisas e fundamentadas sobre Saude e Seguranca do Trabalho.

---

## 1. Arquitetura RAG

### 1.1 Diagrama de Fluxo

```
┌────────────────┐
│   Pergunta     │
│   do Usuario   │
└───────┬────────┘
        │
        ▼
┌────────────────────────────────────┐
│       Query Expansion (LLM)        │
│  Expande/reformula a query com     │
│  sinonimos tecnicos SST            │
└───────┬────────────────────────────┘
        │ expanded_query
        ▼
┌────────────────────────────────────┐
│        Ensemble Retriever          │
│  ┌──────────────┬───────────────┐  │
│  │ BM25 (50%)   │ Vector (50%)  │  │
│  │ (keywords)   │ (semantic)    │  │
│  └──────────────┴───────────────┘  │
└───────────────┬────────────────────┘
                │ top-k docs
                ▼
┌────────────────────────────────────┐
│  Cross-Encoder Reranker            │
│  (ms-marco-MiniLM-L-6-v2)          │
│  Reordena por relevancia real      │
│  e seleciona top-5                 │
└───────────────┬────────────────────┘
                │ top-5 docs rerankeados
                ▼
┌────────────────────────────────────┐
│            LLM Prompt              │
│  ┌──────────────────────────────┐  │
│  │ System Prompt (SafetyAI)     │  │
│  │ + Contexto Recuperado        │  │
│  │ + Pergunta Original          │  │
│  └──────────────────────────────┘  │
└───────────────┬────────────────────┘
                │
                ▼
┌────────────────┐
│   OpenRouter   │
│ (gpt-oss-120b) │
└───────┬────────┘
        │
        ▼
┌────────────────┐
│   Resposta     │
│  com Citacoes  │
└────────────────┘
```

---

## 2. Modelo de Linguagem (LLM)

### 2.1 Configuracao

| Parametro | Valor |
|-----------|-------|
| Provider | OpenRouter |
| Modelo | `openai/gpt-oss-120b` |
| Temperature | 0.3 |
| Max Tokens | 8192 |

### 2.2 Inicializacao com Fallback

```python
def _initialize_llm(self):
    # 1. Tenta Replit AI Integrations
    if AI_INTEGRATIONS_OPENROUTER_API_KEY and AI_INTEGRATIONS_OPENROUTER_BASE_URL:
        llm = ChatOpenAI(
            openai_api_base=AI_INTEGRATIONS_OPENROUTER_BASE_URL,
            openai_api_key=AI_INTEGRATIONS_OPENROUTER_API_KEY,
            model_name="openai/gpt-oss-120b",
            temperature=0.3,
            max_tokens=8192
        )
        return llm
    
    # 2. Fallback para OPENROUTER_API_KEY direto
    if OPENROUTER_API_KEY:
        llm = ChatOpenAI(
            openai_api_base="https://openrouter.ai/api/v1",
            openai_api_key=OPENROUTER_API_KEY,
            model_name="openai/gpt-oss-120b",
            temperature=0.3,
            max_tokens=8192,
            model_kwargs={
                "extra_headers": {
                    "HTTP-Referer": "https://safetyai.streamlit.app/",
                    "X-Title": "SafetyAI - SST"
                }
            }
        )
        return llm
    
    return None  # Erro: nenhuma configuracao disponivel
```

---

## 3. Sistema de Embeddings

### 3.1 Modelo

| Parametro | Valor |
|-----------|-------|
| Modelo | `sentence-transformers/paraphrase-multilingual-mpnet-base-v2` |
| Dimensao | 768 |
| Idiomas | Multilíngue (inclui português) |
| Device | CPU |
| Tipo | Sentence Transformers |

> **Motivo da troca**: O modelo anterior (`all-MiniLM-L6-v2`, 384 dims) era focado em inglês
> e produzia embeddings semanticamente imprecisos para textos regulatórios em português.
> O `paraphrase-multilingual-mpnet-base-v2` oferece 768 dimensões e suporte nativo ao português,
> melhorando significativamente a recuperação de trechos de NRs.

### 3.2 Classe Customizada

```python
class CustomHuggingFaceEmbeddings:
    def __init__(self, model_name: str):
        self.model = SentenceTransformer(model_name)
    
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return self.model.encode(texts, convert_to_numpy=True).tolist()
    
    def embed_query(self, text: str) -> List[float]:
        return self.model.encode([text], convert_to_numpy=True)[0].tolist()
```

---

## 4. Vector Store (ChromaDB)

### 4.1 Configuracao

| Parametro | Valor |
|-----------|-------|
| Tipo | PersistentClient |
| Caminho | `data/chroma_db/` |
| Collection | `nrs_collection` |

### 4.2 Estrutura de Metadados (enriquecida)

```python
{
    "source": "nome_do_arquivo.pdf",
    "page": 1,
    "file_id": "google_drive_file_id",
    "chunk_index": 0,
    "timestamp": "2026-01-03T12:00:00",
    # Novos campos extraídos pelo chunker estrutural NR:
    "nr_number": "12",      # ex.: "12" para NR-12
    "article": "3",         # número do artigo, se presente
    "item": "12.3.1",       # numeração de item NR (ex.: "12.3.1")
}
```

### 4.3 Chunking Estrutural para NRs

O chunker identifica fronteiras naturais nos documentos normativos antes de aplicar
o splitter de caracteres, preservando a integridade dos itens e seções:

```python
def _split_nr_document_structurally(documents, chunk_size=1000, chunk_overlap=200):
    # 1. Detecta fronteiras: itens numerados (ex.: "4.3.2") e capítulos
    # 2. Divide o texto nessas fronteiras (seções lógicas)
    # 3. Aplica RecursiveCharacterTextSplitter dentro de cada seção
    # 4. Extrai e armazena nr_number, article, item nos metadados
```

| Parametro | Valor |
|-----------|-------|
| chunk_size | 1000 caracteres |
| chunk_overlap | 200 caracteres |
| Deteccao de itens | Regex `^\d{1,2}(\.\d+){1,5}` |
| Deteccao de capitulos | Regex `^CAPITULO|ANEXO|SECAO` |

---

## 5. Retriever Híbrido

### 5.1 Ensemble Retriever

```python
ensemble_retriever = EnsembleRetriever(
    retrievers=[bm25_retriever, vector_retriever],
    weights=[0.5, 0.5]  # 50% BM25, 50% Semantic
)
```

### 5.2 BM25 Retriever

- Busca por palavras-chave
- Funciona bem para termos tecnicos especificos (siglas de NRs, EPIs)
- Peso: 50%

### 5.3 Vector Retriever

- Busca semantica com embeddings multilíngues (768 dims)
- Encontra documentos com significado similar em português
- Peso: 50%

### 5.4 Fallback

Se o ChromaDB estiver vazio ou BM25 falhar:
```python
retriever = vector_store.as_retriever(search_kwargs={"k": 10})
```

---

## 6. Query Expansion

Antes de cada busca, o LLM reformula/expande a pergunta do usuário para maximizar
o recall semântico e léxico:

```python
def _expand_query(self, query: str) -> str:
    expansion_prompt = (
        "Reformule e expanda a pergunta abaixo para maximizar a recuperação "
        "de trechos relevantes de NRs e documentos de SST. "
        "Inclua sinônimos técnicos, siglas, termos correlatos em português."
    )
    response = self.llm.invoke([HumanMessage(content=expansion_prompt + query)])
    return response.content.strip()
```

- A expanded_query é usada para recuperação no EnsembleRetriever
- A pergunta original é usada para o reranker e para o LLM gerar a resposta
- Em caso de falha, usa a pergunta original como fallback

---

## 7. Cross-Encoder Reranker

Após o EnsembleRetriever retornar os top-k resultados, um cross-encoder pontua
cada par `(query, chunk)` e reordena para selecionar os mais relevantes:

```python
# Modelo: cross-encoder/ms-marco-MiniLM-L-6-v2 (lazy loaded)
def _rerank_documents(query: str, docs: List[Document], top_n: int = 5):
    reranker = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')
    pairs = [(query, doc.page_content) for doc in docs]
    scores = reranker.predict(pairs)
    ranked = sorted(zip(scores, docs), key=lambda x: x[0], reverse=True)
    return [doc for _, doc in ranked[:top_n]]
```

| Parametro | Valor |
|-----------|-------|
| Modelo | `cross-encoder/ms-marco-MiniLM-L-6-v2` |
| Input | top-k docs do EnsembleRetriever |
| Output | top-5 docs reordenados por relevância real |
| Carregamento | Lazy (na primeira consulta) |

---

## 8. System Prompt (SafetyAI)

### 8.1 Estrutura do Prompt

O prompt e dividido em 3 camadas:

#### Camada 1: Identidade
```
Voce e SafetyAI, um assistente de IA especializado em Saude e Seguranca 
do Trabalho (SST) no Brasil. Sua missao e auxiliar profissionais como 
Tecnicos de Seguranca, Engenheiros de Seguranca, Medicos do Trabalho 
e Enfermeiros do Trabalho.
```

#### Camada 2: Expertise
```
Voce possui expertise abrangente em:

NORMAS REGULAMENTADORAS (NRs 01-38):
- NR 01 (Disposicoes Gerais e GRO)
- NR 04 (SESMT)
- NR 05 (CIPA)
- NR 06 (EPIs)
- NR 07 (PCMSO)
- NR 09 (Avaliacao e Controle de Riscos Ocupacionais)
... [todas as 38 NRs]

PROGRAMAS E DOCUMENTOS:
- PPRA, PCMSO, PPR, PGR, PCA, LTCAT, PPP, CAT, ASOS, APR

CLASSIFICACOES:
- CBO, CID-10, CID-11, CNAE, CA/EPI

LEGISLACAO:
- CLT (artigos de seguranca)
- Portarias do MTE
- Instrucoes Normativas
```

#### Camada 3: Estilo de Comunicacao
```
Estilo de comunicacao:
- Responda de forma clara, profissional e didatica
- Use linguagem tecnica apropriada para profissionais de SST
- Formate respostas em Markdown para melhor legibilidade
- Cite sempre as fontes (NRs, legislacao)
```

### 8.2 Regras de Citacao

```
Formato EXATO da citacao (com link): 
[Norma Regulamentadora nº X (MTE)](URL_OFICIAL)

Formato EXATO da citacao (sem link): 
Norma Regulamentadora nº X (MTE)

NUNCA invente links ou diga que nao tem acesso a internet.
```

---

## 9. Cadeia RAG

### 9.1 Fluxo Completo

```python
# 1. Expandir query
expanded_query = self._expand_query(original_query)

# 2. Recuperar documentos com query expandida
raw_docs = ensemble_retriever.invoke(expanded_query)

# 3. Rerankar com cross-encoder usando query original
top_docs = _rerank_documents(original_query, raw_docs, top_n=5)

# 4. Formatar contexto e gerar resposta
result = rag_chain.invoke({
    "question": original_query,
    "expanded_query": expanded_query,
    "chat_history_messages": [...],
    "dynamic_context_texts": [...],
})
```

### 9.2 Invocacao

```python
def answer_question(self, query: str, chat_history: List[Dict], ...) -> Dict:
    expanded_query = self._expand_query(query)
    result = self.rag_chain.invoke({
        "question": query,
        "expanded_query": expanded_query,
        ...
    })
    return result
```

---

## 10. Processamento de Documentos

### 10.1 Tipos Suportados

| Extensao | Biblioteca | Descricao |
|----------|------------|-----------|
| `.pdf` | PyPDF2, PyMuPDF | Documentos PDF |
| `.docx` | python-docx | Word |
| `.txt` | Built-in | Texto puro |
| Google Docs | Google API | Documentos do Drive |

### 10.2 Re-indexacao (vectorize_nrs.py)

Ao trocar o modelo de embeddings, e obrigatorio re-indexar toda a base:

```bash
cd safety_ai_app
python scripts/vectorize_nrs.py --force-reindex
```

O script:
1. **Deleta e recria a coleção `nrs_collection` no ChromaDB** (necessário para resetar a dimensão de 384→768)
2. Re-indexa com o novo modelo multilíngue e chunking estrutural
3. Armazena metadados `nr_number`, `article`, `item` em cada chunk
4. Grava um arquivo sentinela `data/chroma_db/.embedding_model` com o nome do modelo atual

**Detecção automática de migração**: a cada execução sem `--force-reindex`, o script:
- Se o sentinela **não existir** → força re-indexação completa (estado desconhecido = seguro default)
- Se o sentinela registrar um **modelo diferente** → força re-indexação completa
- Se o sentinela bater com o modelo atual → execução incremental normal

O sentinela é gravado **somente após indexação bem-sucedida**, garantindo que execuções
interrompidas não marquem a base como indexada.

> **Nota**: `clear_docs_by_source_type()` apenas remove documentos por filtro e não reseta
> a dimensionalidade da coleção. Por isso o `--force-reindex` chama `clear_chroma_collection()`
> que faz delete+recreate completo da coleção ChromaDB.

---

## 11. Monitoramento e Logs

### 11.1 Logs de Inicializacao

```
INFO - Loaded embeddings model: sentence-transformers/paraphrase-multilingual-mpnet-base-v2
INFO - Cross-encoder reranker 'cross-encoder/ms-marco-MiniLM-L-6-v2' carregado.
INFO - ChromaDB PersistentClient inicializado em: data/chroma_db
INFO - EnsembleRetriever configurado (Vector + BM25).
INFO - NRQuestionAnswering inicializado. Retriever: Ensemble Retriever
```

### 11.2 Logs de Consulta

```
INFO - Processando pergunta: "O que diz a NR-05 sobre CIPA?" | retriever: Ensemble Retriever
INFO - Query expansion: 'O que diz a NR-05 sobre CIPA?' → 'NR-05 Norma Regulamentadora 5 CIPA...'
INFO - Reranker: 20 → top 5 documentos selecionados.
INFO - Resposta gerada.
```

---

## 12. Otimizacoes

### 12.1 Performance

| Otimizacao | Descricao |
|------------|-----------|
| Singleton | NRQuestionAnswering carregado uma vez |
| ChromaDB Persistente | Evita reindexacao |
| Lazy Reranker | CrossEncoder carregado somente na primeira consulta |
| Fallback de Retriever | Resiliencia se BM25 falhar |

### 12.2 Qualidade de Recuperacao

| Otimizacao | Descricao |
|------------|-----------|
| Embeddings multilíngues | 768 dims, otimizado para português |
| Chunking estrutural NR | Preserva itens e capítulos, chunk_size=1000 |
| Metadados enriquecidos | nr_number, article, item por chunk |
| Query Expansion | LLM expande query com termos SST correlatos |
| Cross-Encoder Reranker | Reordena top-k por relevância real (top-5 final) |

### 12.3 Qualidade de Resposta

| Otimizacao | Descricao |
|------------|-----------|
| Temperatura 0.3 | Respostas mais focadas e precisas |
| Max Tokens 8192 | Permite respostas completas |
| Ensemble Retriever | Combina busca lexica e semantica |
| System Prompt Rico | Contexto especializado em SST |

---

## 13. Limitações Conhecidas e Melhorias Futuras

| Limitação | Impacto | Melhoria Futura |
|-----------|---------|-----------------|
| Cross-encoder `ms-marco-MiniLM-L-6-v2` treinado principalmente em inglês | Reranking pode ser levemente menos preciso para queries PT-BR complexas | Avaliar `cross-encoder/mmarco-mMiniLM-L12-en-de-v1` ou similar multilíngue |
| Query expansion gera UMA variante expandida (não múltiplas em paralelo) | Recall pode ser menor para perguntas ambíguas | Gerar N variantes, buscar em paralelo, deduplicar antes do reranker |
| Reranker e modelo de embeddings são lazy-loaded | Primeira query de cada sessão é mais lenta | Pre-warm em background thread no startup da aplicação (ver tarefa #30) |
| Coleção ChromaDB requer `--force-reindex` após troca de modelo | Risco de incompatibilidade de dimensão se sentinela for deletado manualmente | Sentinel implementado; verificar dimensão via Chroma metadata se API suportar |
