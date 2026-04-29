# Correção de Build e Deploy - Safety AI 2026

## Histórico - Antes da Atualização
O build do projeto no Google Cloud falhava durante o passo de cópia de arquivos no Docker:
```
Step 8/12 : COPY safety_ai_app/data ./data
COPY failed: file not found in build context or excluded by .dockerignore: stat safety_ai_app/data: file does not exist
```
Isso impedia o deploy automático via Cloud Build e instâncias inconsistentes entre projetos (`safety-ai-2026` vs `safetyai-472110`).

## Lógica da Correção
1. **Contexto de Build**: O arquivo `.gcloudignore` possuía uma regra genérica `data/` que excluía a pasta necessária para a RAG (Retrieval-Augmented Generation) da transmissão para o Google Cloud. Removemos esta regra para permitir o upload dos arquivos JSON/ChromaDB fundamentais.
2. **Padronização de Projeto**: Consolidamos as configurações de deploy para o ID de projeto `safety-ai-2026`, garantindo que imagens, serviços e segredos estejam no mesmo ambiente.
3. **Sincronização de Scripts**: Atualizamos o `deploy.sh` e `cloudbuild.yaml` para refletirem as mesmas configurações de CPU (2), Memória (2Gi) e variáveis de ambiente (incluindo acesso a secrets).

## Alterações Realizadas

### [CORRIGIDO] [.gcloudignore](file:///c:/Dev/safety_ai_app-1/.gcloudignore)
- **Antes**: Tinha `data/` nas exclusões.
- **Depois**: Removida a linha `data/`. Adicionada exclusão específica para `safety_ai_app/data/rag_logs/` (evitando arquivos de log grandes).

### [PADRONIZADO] [cloudbuild.yaml](file:///c:/Dev/safety_ai_app-1/cloudbuild.yaml)
- **Antes**: Referenciava `safetyai-472110`.
- **Depois**: Referencia agora `safety-ai-2026`.

### [AJUSTADO] [Dockerfile](file:///c:/Dev/safety_ai_app-1/Dockerfile)
- Validado que o caminho `safety_ai_app/data` está correto para o build context da raiz.

### [SINCRONIZADO] [deploy.sh](file:///c:/Dev/safety_ai_app-1/deploy.sh)
- Configurado para sempre usar o projeto `safety-ai-2026` por padrão.

## Próximos Passos
- Executar `gcloud builds submit .` para validar o build no ambiente de produção.
- Verificar o faturamento (billing) da conta `safety-ai-2026`, que se encontra desativado.
