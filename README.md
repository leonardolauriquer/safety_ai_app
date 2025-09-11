# 🤖 safety_ai_app: Revolucionando a Segurança de Texto com IA

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.9%2B-blue?logo=python" alt="Python Version">
  <img src="https://img.shields.io/badge/Google%20Gemma-API-green?logo=google" alt="Google Gemma API">
  <img src="https://img.shields.io/badge/License-MIT-blue" alt="License">
</p>

## 🌟 Visão Geral do Projeto

O `safety_ai_app` é uma aplicação inovadora desenvolvida por **Leo, um Engenheiro de Software**, com o objetivo de explorar e aplicar a inteligência artificial para diversas finalidades, incluindo a **análise de segurança de texto**. Este projeto destaca-se pela sua capacidade de utilizar APIs de IA avançadas, como o **Google Gemma (API gratuita)**, para identificar e sinalizar possíveis conteúdos inseguros ou inadequados em textos, contribuindo para ambientes digitais mais seguros.

Além da sua funcionalidade central de análise de texto, o projeto também visa a criação de **interfaces de usuário**, incluindo uma potencial **interface web**, para tornar a poderosa funcionalidade de IA acessível e intuitiva.

## ✨ Funcionalidades Principais da Aplicação

O `safety_ai_app` oferece as seguintes capacidades:

*   **Análise de Segurança de Texto:** Utiliza modelos de IA de ponta (através da API gratuita do Google Gemma) para avaliar e identificar potenciais riscos ou conteúdos inseguros em textos fornecidos.
*   **Interface de Linha de Comando (CLI):** Uma interface robusta e amigável para interagir com a aplicação, permitindo que os usuários insiram textos diretamente para análise.
*   **Boas-vindas Personalizadas:** Saudações amigáveis ao iniciar, como "Olá, Leo! Tudo pronto para revolucionar com IA.".
*   **Mensagens de Status Claras:** Indicações visuais sobre o processo de análise, incluindo "Vamos analisar a segurança de um texto utilizando o Google Gemma (API gratuita)!" e "Verificando Modelos Disponíveis com 'generateContent'".
*   **Encerramento da Análise:** Mensagem de finalização, como "Encerrando a análise de segurança. Até a próxima!".
*   **Potencial Interface Web:** Projetado para eventualmente incluir uma interface de usuário baseada na web para uma experiência mais visual e interativa.

## �� Como Usar e Instalar

Para clonar e executar este projeto, você precisará ter o Git e o Python (versão 3.9 ou superior) instalados em sua máquina.

### Pré-requisitos

*   [**Git**](https://git-scm.com/downloads)
*   [**Python 3.9+**](https://www.python.org/downloads/)

### Passos de Instalação e Execução

1.  **Clone o Repositório:**
    ```bash
    git clone https://github.com/leonardolauriquer/safety_ai_app.git
    cd safety_ai_app
    ```

2.  **Crie e Ative um Ambiente Virtual (Recomendado):**
    ```bash
    python -m venv venv
    # No Windows
    .\venv\Scripts\activate
    # No macOS/Linux
    source venv/bin/activate
    ```

3.  **Instale as Dependências:**
    ```bash
    pip install -r requirements.txt
    ```
    *(**Nota:** Se `requirements.txt` não existir, você pode criar um após instalar as bibliotecas necessárias, como `google-generativeai`, usando `pip freeze > requirements.txt`)*

4.  **Configure suas Credenciais (API Key):**
    A aplicação utiliza a API do Google Gemma. Você precisará de uma chave de API gratuita. Obtenha uma em [Google AI Studio](https://aistudio.google.com/app/apikey) e configure-a como uma variável de ambiente ou em um arquivo de configuração (`.env`) que a aplicação possa ler.

    Exemplo (criando um arquivo `.env` na raiz do projeto):
    ```
    GOOGLE_API_KEY="SUA_CHAVE_DE_API_AQUI"
    ```

5.  **Execute a Aplicação:**
    ```bash
    python src/safety_ai_app/__main__.py
    ```
    Siga as instruções na CLI para interagir com a aplicação e realizar análises de texto.

## �� Estrutura do Projeto
