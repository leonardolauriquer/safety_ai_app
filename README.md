# 🤖 safety_ai_app: Apoio Inteligente para Profissionais de SESMT e SSMA

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.9%2B-blue?logo=python" alt="Python Version">
  <img src="https://img.shields.io/badge/Google%20Gemma-API-green?logo=google" alt="Google Gemma API">
  <img src="https://img.shields.io/badge/License-MIT-blue" alt="License">
</p>

## 🌟 Visão Geral do Projeto

O `safety_ai_app` é uma aplicação inovadora desenvolvida por **Leo, um Engenheiro de Software**, com o objetivo de aplicar a inteligência artificial para atender às complexas necessidades dos profissionais da área de **Medicina e Segurança do Trabalho**, incluindo Engenheiros de Segurança, Técnicos de Segurança e profissionais da saúde que atuam no **SESMT (Serviço Especializado em Engenharia de Segurança e Medicina do Trabalho)**. Este projeto foca em fornecer apoio inteligente baseado nas **Normas Regulamentadoras (NRs) e NBRs (Normas Brasileiras)**, abrangendo também aspectos de **Saúde, Segurança e Meio Ambiente (SSMA)**.

A IA, como o **Google Gemma (API gratuita)**, será utilizada para processar e analisar vastos volumes de informações regulatórias e documentação técnica, tornando o conhecimento acessível e prático para o dia a dia desses profissionais. O projeto visa também a criação de **interfaces de usuário intuitivas**, incluindo uma potencial **interface web**, para tornar a poderosa funcionalidade de IA acessível e eficiente.

## ✨ Funcionalidades Principais da Aplicação

O `safety_ai_app` oferece as seguintes capacidades para profissionais do SESMT:

*   **Consultoria Inteligente e Dúvidas (NRs/NBRs):** Oferece respostas e orientação baseadas nas Normas Regulamentadoras e NBRs do Brasil, ajudando profissionais a sanar dúvidas complexas sobre legislação e aplicação prática.
*   **Análise Documental de SSMA:** Utiliza modelos de IA de ponta (através da API gratuita do Google Gemma) para analisar documentos técnicos, laudos, planos e relatórios relacionados a Saúde, Segurança e Meio Ambiente, identificando informações relevantes e conformidades.
*   **Monitoramento de Atualizações Regulatórias:** Informa proativamente sobre as NRs que estão sendo modificadas, revogadas ou publicadas, mantendo os profissionais atualizados com as últimas exigências legais.
*   **Abrangência SSMA:** Integra conceitos e informações de Meio Ambiente, garantindo uma abordagem completa para Saúde, Segurança e Meio Ambiente.
*   **Interface de Linha de Comando (CLI):** Uma interface robusta e amigável para interagir com a aplicação, facilitando a consulta e análise inicial.
*   **Boas-vindas Personalizadas:** Saudações amigáveis ao iniciar, como "Olá, Leo! Tudo pronto para revolucionar com IA.".
*   **Mensagens de Status Claras:** Indicações visuais sobre o processo, incluindo "Vamos auxiliar com suas necessidades de SESMT e SSMA utilizando o Google Gemma (API gratuita)!" e "Verificando Modelos Disponíveis com 'generateContent'".
*   **Encerramento da Interação:** Mensagem de finalização, como "Análise concluída. Até a próxima!".
*   **Potencial Interface Web:** Projetado para eventualmente incluir uma interface de usuário baseada na web para uma experiência mais visual e interativa.

## 🚀 Como Usar e Instalar

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
    *(\*\*Nota:\*\* Se `requirements.txt` não existir, você pode criar um após instalar as bibliotecas necessárias, como `google-generativeai`, usando `pip freeze > requirements.txt`)*

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
    Siga as instruções na CLI para interagir com a aplicação e obter suporte para suas necessidades de SESMT e SSMA.

## 📂 Estrutura do Projeto