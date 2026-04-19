# Painel de Administração — SafetyAI

Manual completo para administradores do SafetyAI.

---

## Como aceder ao Painel

1. Faça login com uma conta Google cujo email esteja configurado em `ADMIN_EMAILS`.
2. Na barra lateral, abra o expander **🔧 Administração**.
3. Clique em **Painel Admin**.

**Requisito:** o email deve constar na variável de ambiente `ADMIN_EMAILS` (separado por vírgula se houver múltiplos admins). Exemplo: `leolr.trab@gmail.com,outro@empresa.com`.

---

## Aba 1 — Visão Geral

Dashboard com 9 cards de métricas em tempo real:

| Card | Descrição |
|---|---|
| Documentos na Base de Conhecimento | Total de chunks no ChromaDB |
| Última Sincronização | Data/hora e resultado (OK / Falhou) |
| Próxima Sincronização | ETA do próximo ciclo automático |
| Score da Última Avaliação de IA | Média das 4 métricas RAG |
| Estado do Warmup | Se os modelos já foram pré-carregados |
| Modelo de Embeddings | Nome do modelo Sentence Transformer activo |
| Log da Aplicação | Tamanho do ficheiro `logs/app.log` |
| Logs RAG | Tamanho total em `data/rag_logs/` |
| Modelo de IA Activo | Modelo OpenRouter em uso |

Na parte inferior, mostra o estado actual de todas as **Feature Flags**.

---

## Aba 2 — Logs do Sistema

### 2a. Logs da Aplicação
- Lê as últimas N linhas de `logs/app.log` (formato JSONL).
- **Filtros:** nível (`DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`) e texto livre.
- **Controlo de quantidade:** 50, 200, 500 ou 1000 linhas.
- **Exportar CSV:** botão para download dos registos filtrados.

### 2b. Eventos de Segurança
- Lê `logs/security.log` com eventos: login, logout, rate limit, injecção de prompt, etc.
- Filtro por tipo de evento.

### 2c. Pipeline RAG
- Lista todos os ficheiros de log em `data/rag_logs/*.jsonl`.
- Mostra tabela com: query, modelo, latência, chunks recuperados, tamanho da resposta.
- Gráfico de latência por chamada.

---

## Aba 3 — Planos & Preços

Editar os planos de subscrição guardados em `data/plans/plans.json`.

### Como editar um plano
1. Seleccione o plano no dropdown.
2. Altere nome, descrição, preços e funcionalidades.
3. Clique em **💾 Salvar Plano**.

### Funcionalidades configuráveis por plano
- Mensagens de chat por dia (-1 = ilimitado)
- Sincronização da Base de Conhecimento
- Geração de Documentos (APR, ATA)
- Quadro de Empregos, Jogos, Consultas Rápidas, Dimensionamentos
- Feed de Notícias, Personalização Visual, Suporte Prioritário

### Estrutura do ficheiro `plans.json`
```json
{
  "plans": [
    {
      "id": "free",
      "name": "Gratuito",
      "price_monthly": 0.0,
      "price_yearly": 0.0,
      "currency": "BRL",
      "description": "Acesso básico.",
      "features": { ... }
    }
  ]
}
```

---

## Aba 4 — Configurações Avançadas

### 4a. Gestão de Administradores
- Veja a lista de admins actuais (lida de `ADMIN_EMAILS`).
- Adicione admins para a sessão actual (temporário).
- **Para persistir:** actualize o secret `ADMIN_EMAILS` no painel do Replit, separando emails por vírgula.

### 4b. Sincronização Automática
- Veja o estado do scheduler (a correr / parado, intervalo, última/próxima execução).
- Ajuste o intervalo (5 min a 24 h).
- Clique **🔄 Sincronizar Agora** para forçar sincronização imediata.

### 4c. Configurações de IA
Guardadas em `data/ai_config.json`. Requer reinício do app para aplicar:

| Parâmetro | Descrição |
|---|---|
| Modelo activo | ID do modelo OpenRouter (ex: `openai/gpt-4o-mini`) |
| Temperatura factual | 0.1 para consultas de NRs |
| Temperatura documentos | 0.5 para geração de APR/ATA |
| Máx. tokens de histórico | Quando comprimir histórico (padrão 16000) |
| Máx. turnos de histórico | Número de turnos antes de comprimir (padrão 10) |
| Threshold guardrail | Score mínimo para resposta fora do domínio SST |
| Top-K chunks | Número de chunks recuperados por query |
| Peso BM25 | Balanço entre pesquisa por palavras-chave e semântica |

### 4d. Feature Flags
Activar/desactivar funcionalidades globalmente. Guardadas em `data/feature_flags.json`.

Funcionalidades disponíveis: Chat, Biblioteca, Base de Conhecimento, Quadro de Empregos, Feed de Notícias, Jogos, Consultas Rápidas, Dimensionamentos, APR, ATA.

---

## Aba 5 — Pipeline de IA

### Última Avaliação
- Mostra métricas da avaliação RAG mais recente: Fidelidade, Relevância, Cobertura, Precisão.
- Tabela de resultados por pergunta, com destaque para falhas.

### Tendência Histórica
- Gráfico de linha com as últimas 10 avaliações.
- Tabela do histórico completo.

### Golden Set
- Distribuição das 35 perguntas por NR e tipo de consulta.
- Caminho: `data/eval/golden_set.json`

### Executar Avaliação
```bash
# Avaliação completa
python safety_ai_app/scripts/evaluate_rag.py

# Avaliação rápida (5 perguntas)
python safety_ai_app/scripts/evaluate_rag.py --limit 5
```

Ou use o botão **▶ Executar Avaliação Rápida** directamente no painel.

---

## Ficheiros de Dados

| Ficheiro | Conteúdo |
|---|---|
| `data/plans/plans.json` | Definição dos planos de subscrição |
| `data/ai_config.json` | Configurações do pipeline de IA |
| `data/feature_flags.json` | Flags de activação de funcionalidades |
| `data/eval/golden_set.json` | Conjunto de avaliação RAG (35 perguntas) |
| `data/eval/results/` | Resultados das avaliações (JSON por data) |
| `data/rag_logs/` | Logs de chamadas ao pipeline RAG (JSONL) |
| `logs/app.log` | Log geral da aplicação (JSON estruturado, rotativo 5 MB) |
| `logs/security.log` | Eventos de segurança |

---

## Adicionar Novos Administradores (permanente)

1. Aceda ao painel do Replit.
2. Vá a **Secrets** (ou variáveis de ambiente).
3. Edite a variável `ADMIN_EMAILS`.
4. Adicione o novo email separado por vírgula: `leolr.trab@gmail.com,novo@empresa.com`
5. Reinicie o app para aplicar.
