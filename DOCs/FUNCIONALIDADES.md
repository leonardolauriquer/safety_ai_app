# Funcionalidades do SafetyAI

## Indice de Paginas

O SafetyAI possui 20 paginas organizadas por categoria:

## 1. Autenticacao e Sincronizacao

### 1.1 Pagina de Login (`web_app.py`)
- **Funcao**: `_render_login_page()`
- **Recursos**:
  - Autenticacao via Google OAuth
  - Design Cyber-Neon com glassmorphism
  - Lista de recursos do app
  - Responsivo para web e mobile

### 1.2 Pagina de Sincronizacao (`sync_page.py`)
- **Funcao**: `render_page()`
- **Recursos**:
  - Sincronizacao com Google Drive
  - Download de documentos da base de conhecimento
  - Processamento de PDFs para o ChromaDB
  - Barra de progresso

## 2. Chat e IA

### 2.1 Chat com IA (`chat_page.py`)
- **Funcao**: `render_page()`
- **Recursos**:
  - Chat interativo com assistente SafetyAI
  - Sistema RAG para consulta de NRs
  - Historico de conversas
  - Citacoes com links para fontes
  - Modelo: `openai/gpt-oss-120b` via OpenRouter

## 3. Consultas Rapidas

### 3.1 Consulta CBO (`cbo_consult_page.py`)
- **Funcao**: `render_page()`
- **Recursos**:
  - Busca por codigo ou nome de ocupacao
  - Hierarquia: Grande Area > Ocupacao > Atividades
  - Fonte: Excel CBO2025 do Google Drive

### 3.2 Consulta CID (`cid_consult_page.py`)
- **Funcao**: `render_page()`
- **Recursos**:
  - Busca CID-10 (local, Excel do Drive)
  - Busca CID-11 (API OMS em tempo real)
  - Pesquisa por codigo ou descricao

### 3.3 Consulta CNAE (`cnae_consult_page.py`)
- **Funcao**: `render_page()`
- **Recursos**:
  - Navegacao hierarquica: Secoes > Divisoes > Grupos > Classes > Subclasses
  - Grau de Risco automatico por CNAE
  - Fonte: API IBGE + Excel de Grau de Risco

### 3.4 Consulta CA/EPI (`ca_consult_page.py`)
- **Funcao**: `render_page()`
- **Recursos**:
  - Busca por numero de CA ou descricao
  - Informacoes: Fabricante, Validade, Situacao
  - Fonte: FTP do Ministerio do Trabalho (mtps.gov.br)

### 3.5 Consulta de Multas (`fines_consult_page.py`)
- **Funcao**: `render_page()`
- **Recursos**:
  - Calculo de multas por NR
  - Considera faixas de empregados e reincidencia
  - Base: NR-28

## 4. Dimensionamentos

### 4.1 Dimensionamento CIPA (`cipa_sizing_page.py`)
- **Funcao**: `render_page()`
- **Recursos**:
  - Calculo de membros efetivos e suplentes
  - Baseado em Grau de Risco e numero de empregados
  - Cronograma eleitoral automatico
  - Base: NR-05, Quadro I

### 4.2 Dimensionamento SESMT (`sesmt_sizing_page.py`)
- **Funcao**: `render_page()`
- **Recursos**:
  - Calculo de profissionais necessarios:
    - Tecnico de Seguranca
    - Engenheiro de Seguranca
    - Auxiliar/Tecnico de Enfermagem
    - Enfermeiro do Trabalho
    - Medico do Trabalho
  - Base: NR-04

### 4.3 Dimensionamento Brigada (`emergency_brigade_sizing_page.py`)
- **Funcao**: `render_page()`
- **Recursos**:
  - Calculo de brigadistas
  - Considera grau de risco e populacao fixa

### 4.4 Pagina de Dimensionamentos (`sizing_page.py`)
- **Funcao**: `render_page()`
- **Hub** para todos os dimensionamentos

## 5. Geracao de Documentos

### 5.1 Gerador de APR (`apr_generator_page.py`)
- **Funcao**: `render_page()`
- **Recursos**:
  - Formulario completo para APR
  - Campos: Atividade, Riscos, Medidas de Controle
  - Captura de assinatura digital
  - Geracao de DOCX a partir de template

### 5.2 Gerador de ATA (`ata_generator_page.py`)
- **Funcao**: `render_page()`
- **Recursos**:
  - Formulario para atas de reuniao
  - Campos: Participantes, Pauta, Deliberacoes
  - Geracao de DOCX a partir de template

## 6. Base de Conhecimento

### 6.1 Gerenciador de Base (`knowledge_base_page.py`)
- **Funcao**: `render_page()`
- **Recursos**:
  - Visualizacao de documentos indexados
  - Upload de novos documentos
  - Gerenciamento do ChromaDB

### 6.2 Biblioteca (`library_page.py`)
- **Funcao**: `render_page()`
- **Recursos**:
  - Navegacao por documentos no Google Drive
  - Download de arquivos
  - Organizacao por pastas

## 7. Educacao e Entretenimento

### 7.1 Jogos Educativos (`games_page.py`)
- **Funcao**: `render_page()`
- **Recursos**:
  - Quiz sobre SST
  - Palavras Cruzadas sobre NRs

### 7.2 Quiz (`quiz_game.py`)
- **Recursos**:
  - Perguntas de multipla escolha
  - Pontuacao e ranking

### 7.3 Palavras Cruzadas (`crossword_game.py`)
- **Recursos**:
  - Grid interativo
  - Temas de SST

## 8. Informacoes Externas

### 8.1 Feed de Noticias (`news_feed_page.py`)
- **Funcao**: `render_page()`
- **Recursos**:
  - Noticias de SST de fontes RSS
  - Atualizacao automatica

### 8.2 Quadro de Vagas (`jobs_board_page.py`)
- **Funcao**: `render_page()`
- **Recursos**:
  - Vagas de emprego em SST
  - Integracao com API Adzuna
  - Filtros por localizacao

## 9. Configuracoes

### 9.1 Pagina de Configuracoes (`settings_page.py`)
- **Funcao**: `render_page()`
- **Recursos**:
  - Preferencias do usuario
  - Configuracoes de conta
  - Gestao de credenciais

### 9.2 Pagina Inicial (`home_page.py`)
- **Funcao**: `render_page()`
- **Recursos**:
  - Dashboard com resumo
  - Acesso rapido aos recursos

### 9.3 Consultas Rapidas Hub (`quick_queries_page.py`)
- **Funcao**: `render_page()`
- **Hub** para todas as consultas

## Navegacao

A navegacao e controlada pelo `web_app.py`:
- Sidebar com menu de paginas
- Icones Tabler (SVG inline)
- Session state para controle de pagina ativa
