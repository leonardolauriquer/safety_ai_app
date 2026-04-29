# Modernização da Arquitetura RAG - Fase 2

Este documento detalha a refatoração e modularização do sistema RAG (Retrieval-Augmented Generation) do Safety AI, realizada na Fase 2 do plano de evolução.

## Lógica Antes da Atualização (Monolítica)
Anteriormente, toda a inteligência do RAG estava concentrada no arquivo `nr_rag_qa.py`, que funcionava como um "God Object".

### Características do Antigo `nr_rag_qa.py`:
- **Embeddings**: Embutidos na classe principal com lógica de lazy loading manual.
- **Retriever**: Lógica de `EnsembleRetriever` e BM25 misturada com a gestão do banco vetorial.
- **Indexação**: O algoritmo de splitting estrutural de NRs era um método privado difícil de testar isoladamente.
- **Guardrails**: Padrões de Regex e lógica de verificação de domínio espalhados pelo arquivo.
- **Manutenção**: Alta complexidade (>1700 linhas), dificultando a identificação de bugs e a adição de novos modelos.

---

## Lógica Após a Atualização (Modular)
A arquitetura foi decomposta no pacote `src/safety_ai_app/rag/`, separando responsabilidades em submódulos especializados.

### Nova Estrutura de Pacotes:
- **`rag/embeddings.py`**: Isola o `CustomHuggingFaceEmbeddings`. Facilita a troca de modelos de embedding no futuro.
- **`rag/retriever.py`**: Centraliza o `EnsembleRetriever` e a lógica de reranking.
- **`rag/indexer.py`**: Contém o `split_nr_document_structurally` e utilitários de ingestão.
- **`rag/qa_chain.py`**: Gerencia a cadeia LangChain, guardrails (jailbreak/off-domain) e limpeza de texto.
- **`rag/warmup.py`**: Lógica de pré-aquecimento de modelos em background.
- **`rag/__init__.py`**: Facade que expõe uma interface limpa para o resto do app.

### Benefícios Alcançados:
1. **Baixo Acoplamento**: Mudanças no modelo de embedding não afetam a lógica de busca ou a interface do usuário.
2. **Alta Coesão**: Cada módulo faz apenas uma coisa bem feita.
3. **Testabilidade**: Agora é possível criar testes unitários para o splitter ou para os guardrails sem carregar o ChromaDB.
4. **Prontidão para API**: A lógica RAG agora pode ser facilmente importada em um servidor FastAPI (Fase 3).

## Checklist de Implementação:
- [x] Criar pacote `safety_ai_app.rag`.
- [x] Extrair lógica de embeddings para `embeddings.py`.
- [x] Extrair lógica de retriever e reranking para `retriever.py`.
- [x] Extrair algoritmo de splitting estrutural para `indexer.py`.
- [x] Extrair guardrails e cadeia RAG para `qa_chain.py`.
- [x] Refatorar `nr_rag_qa.py` para atuar como Facade.
- [x] Validar imports e dependências circulares.
- [x] Manter retrocompatibilidade com o Streamlit.

---
*Documentação gerada em: 2026-04-28*
