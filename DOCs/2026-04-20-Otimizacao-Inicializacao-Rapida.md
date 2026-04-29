# Otimização de Inicialização Rápida e Deferimento de Tarefas Pesadas

## Data: 2026-04-20
## Especialistas: Arquiteto de Software, QA, DevOps

### Problema
A aplicação apresentava lentidão excessiva no arranque devido a:
1. Sincronização síncrona com o Google Cloud Storage (GCS) no construtor do objeto de IA (`NRQuestionAnswering`).
2. Disparo imediato de tarefas pesadas (Warmup do modelo de embedding, auto-indexamento de NRs e agendador de sincronização) em cada execução do Streamlit durante o login.
3. Consultas desnecessárias ao banco de dados (OAuth check) antes mesmo do usuário estar logado ou de haver um callback de retorno.

### Solução Implementada
Adotamos uma estratégia de "Lazy Initialization" e "Manual Triggering" para componentes pesados.

#### 1. Lógica Antes vs. Depois

**NRQuestionAnswering.__init__**
- **Antes**: Sincronizava obrigatoriamente com o GCS no construtor.
- **Depois**: Adicionado parâmetro `sync_on_init=True` (padrão mantido para compatibilidade, mas passado como `False` no cache do app).

**web_app.py (main_app_entrypoint)**
- **Antes**: Chamava `_trigger_model_warmup_once()`, `_trigger_nr_autoindex_once()` e `_start_auto_sync_scheduler()` logo após o login, em cada rerun.
- **Depois**: Removido do fluxo principal. Essas tarefas agora são disparadas apenas quando o usuário entra na página de Sincronização e clica em "Sincronizar Agora" ou "Continuar sem sincronizar".

**web_app.py (OAuth Check)**
- **Antes**: Chamava `get_user_drive_service_wrapper()` (acesso ao DB) em cada rerun, mesmo antes do login.
- **Depois**: Apenas chama se houver um código de retorno (`code`) na URL ou se o estado da sessão indicar que uma autenticação está pendente.

#### 2. Mudanças nos Arquivos

- **src/safety_ai_app/nr_rag_qa.py**: 
  - Atualizado `__init__` para aceitar `sync_on_init`.
- **src/safety_ai_app/web_app.py**:
  - `get_qa_instance_cached` corrigido para `sync_on_init=False`.
  - Fluxo principal otimizado para evitar disparos automáticos.
- **src/safety_ai_app/web_interface/pages/sync_page.py**:
  - Incorporadas as chamadas de inicialização pesada nos botões de ação do usuário.

### Checklist de Execução
- [x] Modificar construtor de `NRQuestionAnswering`.
- [x] Otimizar `get_qa_instance_cached` no `web_app.py`.
- [x] Deferir tarefas pesadas no `web_app.py`.
- [x] Otimizar verificações de OAuth no `web_app.py`.
- [x] Integrar triggers manuais na `sync_page.py`.
- [x] Documentar mudanças em `Docs/`.
- [x] Atualizar índice `Docs/README.md`.

### Próximos Passos (A Fazer)
- [ ] Monitorar tempo de resposta do banco de dados em produção (PostgreSQL no GCR).
- [ ] Verificar se o warmup em background na `sync_page` não impacta a primeira consulta do chat (se o usuário for muito rápido).
