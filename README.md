# Safety AI App 🤖💡

## Assistente Especializado em Saúde e Segurança do Trabalho (SST) com Inteligência Artificial

O **Safety AI App** é um chatbot inteligente projetado para ser seu assistente amigável e especializado em Saúde e Segurança do Trabalho (SST), com foco nas Normas Regulamentadoras (NRs) do Brasil. Construído com Python, Streamlit, Google Gemini e ChromaDB, este aplicativo visa facilitar a consulta de informações complexas e aprimorar o conhecimento em SST, tanto para fins de trabalho, estudo ou uso pessoal.

### ✨ Principais Funcionalidades

*   **Chatbot Inteligente (RAG)**: Interaja com um assistente virtual capaz de responder a perguntas complexas sobre NRs e tópicos de SST. Utiliza a arquitetura Retrieval-Augmented Generation (RAG) para buscar informações em documentos carregados.
*   **Base de Conhecimento Dinâmica**: Carregue seus próprios documentos (atualmente PDFs) para expandir a base de conhecimento do chatbot. O sistema processa o texto, divide-o em 'chunks' e os armazena em um banco de dados vetorial (ChromaDB) para consulta rápida e relevante.
*   **Melhoria Contínua da Resposta**: O chatbot foi refinado para fornecer respostas mais claras, concisas, amigáveis e bem formatadas (usando negritos, listas e parágrafos curtos), facilitando a compreensão de informações técnicas.
*   **Gestão Segura de Credenciais**: Implementação robusta para garantir que chaves de API e outros segredos sensíveis não sejam acidentalmente versionados no controle de código-fonte (Git).
*   **Fluxo de Trabalho Git Otimizado**: Scripts de automação (`git_push.bat`) com tratamento seguro de credenciais, garantindo pushes eficientes e sem incidentes para o GitHub.
*   **Interface Intuitiva com Streamlit**: Uma interface de usuário simples e responsiva que permite navegar entre as funcionalidades de Home, Chat e Biblioteca de documentos.

### 🚀 Novidades e Destaques Recentes

*   **Links de Download para Documentos (Em Breve!)**: Preparação para que o chatbot possa incluir links diretos para os documentos de origem nas suas respostas, permitindo que o usuário consulte a fonte original para mais detalhes. Isso transformará o chatbot em uma ferramenta de referência completa.
*   **Refinamento da Ingestão de Documentos**: Melhorias na forma como os documentos são processados e armazenados no ChromaDB, garantindo que metadados importantes (como URLs de origem) sejam associados a cada pedaço de informação.
*   **Melhor Tratamento do Histórico de Conversa**: O sistema agora gerencia de forma mais eficaz o histórico do chat, permitindo que o Gemini mantenha o contexto e forneça respostas mais coerentes ao longo da interação.

### 🛠️ Como Começar

Para rodar o Safety AI App localmente, siga os passos abaixo:

1.  **Clone o Repositório:**
    ```bash
    git clone https://github.com/leonardolauriquer/safety_ai_app.git
    cd safety_ai_app
    ```

2.  **Configuração do Ambiente Python com Poetry:**
    Certifique-se de ter o [Poetry](https://python-poetry.org/docs/#installation) instalado. O Poetry gerenciará as dependências do projeto.

    ```bash
    # Instala as dependências do projeto
    poetry install

    # Ativa o ambiente virtual do Poetry
    poetry shell
    ```

3.  **Variáveis de Ambiente:**
    Crie um arquivo `.env` na raiz do projeto (`safety_ai_app/`) e adicione sua chave da API do Google Gemini:

    ```
    GOOGLE_API_KEY=SUA_CHAVE_API_DO_GOOGLE
    ```
    Você pode obter uma chave API em [Google AI Studio](https://aistudio.google.com/app/apikey).

4.  **Configuração de Credenciais do Google Drive (se aplicável):**
    Para funcionalidades que requerem acesso ao Google Drive, coloque seu arquivo `service_account_key.json` na raiz do projeto. **Este arquivo é ignorado pelo Git** e não será versionado para sua segurança.

### ▶️ Como Executar o Aplicativo

Após configurar o ambiente e as variáveis, você pode iniciar o aplicativo Streamlit:

```bash
# Certifique-se de estar no ambiente virtual do Poetry (poetry shell)
streamlit run src/safety_ai_app/web_app.py
