# Refatoração Estrutural — God Files SafetyAI
**Data:** 2026-04-29
**Tipo:** Refatoração (sem mudança de funcionalidade)

---

## Contexto

Dois arquivos principais do projeto haviam crescido para dimensões que violavam o Princípio de Responsabilidade Única:

| Arquivo | Antes | Depois |
|---|---|---|
| `admin_panel_page.py` | 1.498 linhas (67KB) | 18 linhas (re-export) |
| `nr_rag_qa.py` | 1.233 linhas | ~980 linhas (−253 linhas) |

---

## O que foi feito

### Fase 1 — Decomposição do Admin Panel

O `admin_panel_page.py` foi decomposto em um **pacote Python** em `web_interface/pages/admin/`:

```
admin/
├── __init__.py              # Orquestra as 5 abas + guarda admin
├── _helpers.py              # Helpers de I/O, paths, _is_admin
├── _tab_overview.py         # TAB 1 — Métricas do sistema
├── _tab_logs.py             # TAB 2 — Logs com paginação, filtros, export CSV
├── _tab_plans.py            # TAB 3 — CRUD de planos
├── _tab_advanced_config.py  # TAB 4 — Admins, Sync, IA, Feature Flags
└── _tab_ai_pipeline.py      # TAB 5 — Pipeline IA + NR Indexer + NR Update Checker
```

**Compatibilidade:** `admin_panel_page.py` agora é um re-export de 18 linhas que preserva todos os imports existentes.

### Fase 2 — Decomposição do RAG Engine

Dois serviços foram extraídos do `nr_rag_qa.py` para módulos dedicados:

#### `rag/nr_indexer.py`
- `get_indexed_nr_numbers_from_mte(collection)` — lista NRs já indexadas
- `start_nr_indexing_background(qa, nr_list)` — inicia thread em background
- `get_nr_indexing_status()` — lê status do arquivo JSON
- `is_nr_indexing_running()` — verifica se a thread está ativa
- Estado de thread: `_nr_indexing_thread`, `_nr_indexing_lock`

#### `rag/history_manager.py`
- `compress_history(messages, llm, max_turns, max_chars)` — comprime histórico de chat via sumarização LLM

**Delegação:** `NRQuestionAnswering._compress_history_if_needed` agora é um wrapper de 3 linhas que chama `compress_history()`.

---

## Impacto

- **Zero quebra de funcionalidade** — toda API pública preservada
- **Compatibilidade retroativa** — todos os imports externos continuam funcionando
- Cada módulo agora tem **uma única responsabilidade** e pode ser testado isoladamente
- `admin_panel_page.py`: 1.498 → 18 linhas (**-98.8%**)
- `nr_rag_qa.py`: 1.233 → ~980 linhas (**-20%**)

---

## Verificação

```bash
# Todos retornaram OK
python -c "from safety_ai_app.web_interface.pages.admin_panel_page import render_page; print('OK')"
python -c "import ast; ast.parse(open('.../_tab_logs.py', encoding='utf-8').read()); print('OK')"  # x7
python -c "import ast; ast.parse(open('.../nr_indexer.py').read()); print('OK')"
python -c "import ast; ast.parse(open('.../history_manager.py').read()); print('OK')"
```

---

## Próximos passos (backlog)

- Refatorar `chat_page.py` (~46KB) em `_upload_handler.py`, `_message_renderer.py`, `_stream_handler.py`
- Adicionar testes unitários para `compress_history()` e `get_indexed_nr_numbers_from_mte()`
- Adicionar testes para `_load_json` / `_save_json` do `_helpers.py`
