# Auditoria de Performance - Safety AI

Este documento registra a investigação sobre a lentidão no carregamento inicial do aplicativo Safety AI.

## Checklist de Investigação

- [ ] Tempo de Importação de Módulos (Heavy Imports)
- [ ] Inicialização do Modelo de IA (NR RAG)
- [ ] Conexão com Google Drive (Auth Lifecycle)
- [ ] Renderização do Streamlit (Session State init)
- [ ] Sincronização em Background (Scheduler)

## Logs de Performance Adicionados

Foram adicionados logs de tempo no console (Terminal e Console do Navegador via `st.write`) nos seguintes pontos:
1. `Script Load`: Tempo total desde o início do arquivo até o `main_app_entrypoint`.
2. `Phase 1 (Styles)`: Carregamento de CSS e Fontes.
3. `Phase 2 (Auth)`: Verificação de login.
4. `Phase 3 (Backend)`: Inicialização de serviços pesados (QA, Drive).
5. `Phase 4 (Routing)`: Tempo de renderização da página solicitada.

## Histórico de Medições

| Data | Evento | Duração (s) | Notas |
| :--- | :--- | :--- | :--- |
| 2026-04-28 | Carregamento Total | - | A ser medido |
