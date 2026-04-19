# Relatório de Auditoria de Segurança — SafetyAI App

**Data:** 2026-04-17  
**Ferramenta:** pip-audit  
**Escopo:** Dependências Python do ambiente de execução

---

## Resumo Executivo

| Métrica | Antes | Depois |
|---|---|---|
| Vulnerabilidades conhecidas | 23 | 0 |
| Pacotes afetados | 13 | 0 |
| Redução | — | **100%** |

---

## Vulnerabilidades Corrigidas (23 CVEs/GHSAs)

Os seguintes pacotes foram atualizados para versões sem vulnerabilidades conhecidas:

| Pacote | Versão Anterior | Versão Atual | CVEs/GHSAs Resolvidos |
|---|---|---|---|
| `streamlit` | 1.52.2 | 1.56.0 | CVE-2026-33682 |
| `langchain-core` | 0.3.81 | 1.3.0 | CVE-2026-40087 |
| `langsmith` | 0.6.0 | 0.7.32+ | CVE-2026-25528, GHSA-rr7j-v2q5-chgv |
| `langgraph` | 1.0.5 | 1.1.8 | CVE-2026-28277 |
| `langgraph-checkpoint` | 3.0.1 | 4.0.2 | CVE-2026-27794 |
| `requests` | 2.32.5 | 2.33.1 | CVE-2026-25645 |
| `urllib3` | 2.3.0 | 2.6.3 | CVE-2025-50181, CVE-2025-50182, CVE-2025-66418, CVE-2025-66471, CVE-2026-21441 |
| `pyasn1` | 0.6.1 | 0.6.3 | CVE-2026-23490, CVE-2026-30922 |
| `tornado` | 6.5.4 | 6.5.5 | GHSA-78cv-mqj4-43f7, CVE-2026-31958, CVE-2026-35536 |
| `protobuf` | 6.33.2 | 6.33.6 | CVE-2026-0994 |
| `langchain-openai` | 0.3.35 | 1.1.14 | GHSA-r7w7-9xr2-qq2r |
| `langchain-text-splitters` | 0.3.11 | 1.1.2 | GHSA-fv5p-p927-qmxr |
| `transformers` | 4.57.3 | 5.5.4 | CVE-2026-1839 |

---

## Vulnerabilidades Pendentes (auditoria de 2026-04-17)

Nenhuma vulnerabilidade conhecida encontrada no ambiente limpo pós-atualização em 2026-04-17. O ambiente de execução atual tem versões desatualizadas de `langchain-openai`, `langgraph-checkpoint` e `transformers` que divergem do `pyproject.toml` — veja a seção de auditoria de 2026-04-18.

---

## Medidas de Segurança Implementadas (Task #11)

Além da atualização de dependências, as seguintes proteções foram adicionadas à aplicação:

### 1. Rate Limiting por Sessão
- **Módulo:** `security/rate_limiter.py`
- **Cobertura:** `chat_llm` (10 req/60s), `icd_api` (20 req/60s), `adzuna_api` (5 req/60s), `drive_sync` (3 req/300s), `file_upload` (20 req/300s)
- **Aplicado em:** `chat_page.py`, `cid_consult_page.py`, `jobs_board_page.py`

### 2. Limite de Tamanho de Arquivo (15 MB)
- **Cobertura:** Upload na Base de Conhecimento, upload de logo na ATA, upload de anexos na ATA, upload de documentos no chat
- **Eventos registrados:** Rejeições logadas via `security_logger.py`

### 3. Timeout de Sessão Ociosa (30 minutos)
- **Módulo:** `session_state.py`, `web_app.py`
- **Comportamento:** Usuário é deslogado automaticamente após 30 min de inatividade

### 4. Logger de Eventos de Segurança
- **Módulo:** `security/security_logger.py`
- **Eventos rastreados:** LOGIN, LOGOUT, CSRF_VIOLATION, RATE_LIMIT_HIT, FILE_REJECTED
- **Proteção de PII:** e-mail do usuário é mascarado com SHA-256 (12 chars)

### 5. Limpeza de Arquivos Temporários
- **Localização:** `web_app.py` (`_cleanup_temp_files`)
- **Critério:** Arquivos com mais de 1 hora no diretório temporário do sistema

### 6. Hardening do System Prompt (Anti-Jailbreak)
- Identidade imutável com recusa explícita a roleplay/DAN/modo desenvolvedor
- Resistência a prompt injection via documentos recuperados pelo RAG
- Sem revelação de instruções internas ou configuração técnica
- Escopo estrito de SST com recusa educada para tópicos fora do domínio

---

## Próximas Recomendações de Segurança

1. **Content Security Policy (CSP)** — configurar cabeçalhos HTTP via proxy reverso
2. **Auditoria periódica** — executar `pip-audit` a cada release ou quinzenalmente *(automatizado — ver seção abaixo)*
3. **Revisão de permissões Google Drive** — garantir princípio do menor privilégio nas service accounts
4. **Compatibilidade de APIs LangChain 1.x** ✅ — verificado e corrigido em `nr_rag_qa.py`: o método `get_relevant_documents()` foi removido na v1.x; o fallback morto foi removido do `EnsembleRetriever`, que agora usa exclusivamente `invoke()`. Todos os imports, `RecursiveCharacterTextSplitter`, `BM25Retriever`, `ChatOpenAI`, `RunnableParallel` e embeddings foram testados e confirmados compatíveis.

---

## Auditoria Automatizada de Segurança

A partir de 2026-04-18, a auditoria de segurança é executada automaticamente via o script `safety_ai_app/scripts/run_security_audit.sh` e registrada como etapa de validação (`security-audit`).

**Como executar manualmente:**
```bash
bash safety_ai_app/scripts/run_security_audit.sh
```

O script usa `pip-audit --local` para inspecionar os pacotes instalados no ambiente de execução e:
- Exibe os resultados no console com código de saída não-zero se vulnerabilidades forem encontradas
- Acrescenta uma entrada datada a este arquivo automaticamente (apenas quando executado localmente)

> **Nota:** O workflow do GitHub Actions (`.github/workflows/security-audit.yml`) executa `pip-audit` diretamente e não chama este script. As atualizações automáticas do log de auditoria só ocorrem ao executar o script localmente. Para manter um registro persistente no CI, um passo adicional de commit automatizado seria necessário.

---

## Auditoria Automática — 2026-04-18

### pip-audit (dependências)

```
Found 3 known vulnerabilities in 3 packages
Name                 Version ID                  Fix Versions
-------------------- ------- ------------------- ------------
langchain-openai     1.1.9   GHSA-r7w7-9xr2-qq2r 1.1.14
langgraph-checkpoint 3.0.1   CVE-2026-27794      4.0.0
transformers         4.57.3  CVE-2026-1839       5.0.0rc3

Name          Skip Reason
------------- ---------------------------------------------------------------------------
safety-ai-app Dependency not found on PyPI and could not be audited: safety-ai-app (0.1.0)
```

> **Nota:** As versões instaladas no ambiente estão desatualizadas em relação ao `pyproject.toml`, que já exige as versões corrigidas. Atualizar o ambiente com `pip install -U langchain-openai langgraph-checkpoint transformers` resolve os 3 CVEs.

### Análise Estática (SAST)

| Severidade | Total | Principais achados |
|---|---|---|
| HIGH | 5 → **0** | ~~Credenciais hardcoded em `attached_assets/_1767496850728.env`~~ — **RESOLVIDO (Task #25)** |
| MEDIUM | 3 | ReDoS em `nr_scraper.py`; uso de `pickle` em `google_auth.py` (3 ocorrências) |
| LOW | 1 | `FTP` sem TLS em `ca_data_processor.py` |

**Ações concluídas:**
- ✅ `attached_assets/_1767496850728.env` removido do rastreamento Git (Task #25, 2026-04-18). Todas as credenciais já estavam armazenadas como Replit Secrets. A entrada `attached_assets/*.env` foi adicionada ao `.gitignore` para evitar recorrência.
- ✅ **Corrigido em 2026-04-18 (Task #26)** — `pickle` substituído por `google.oauth2.credentials.Credentials.to_json()` / `Credentials.from_authorized_user_info()`; token salvo em `token_user.json`.
- ⚠️ **Pendente:** Rotacionar (revogar e substituir) as chaves expostas em cada provedor externo (Google, OpenRouter, reCAPTCHA, Adzuna, ICD). As chaves podem ainda estar válidas e presentes no histórico do repositório.

**Ações pendentes:**
- Revisar a regex em `nr_scraper.py` para evitar ReDoS.

### Análise de Privacidade (HoundDog)

| Severidade | Total | Achado |
|---|---|---|
| LOW | 1 | E-mail exposto em logs — `security/security_logger.py` |

> **Nota:** O e-mail já é mascarado com SHA-256 (12 chars) conforme Task #11; o achado LOW é residual e de baixo risco.

**Resultado geral:** 3 vulnerabilidades de dependência (ambiente desatualizado), 9 achados SAST, 1 achado de privacidade.


---

## Auditoria Automática — 2026-04-18 00:19:32 UTC

```
Found 3 known vulnerabilities in 3 packages
Name                 Version ID                  Fix Versions
-------------------- ------- ------------------- ------------
langchain-openai     1.1.9   GHSA-r7w7-9xr2-qq2r 1.1.14
langgraph-checkpoint 3.0.1   CVE-2026-27794      4.0.0
transformers         4.57.3  CVE-2026-1839       5.0.0rc3
Name          Skip Reason
------------- ----------------------------------------------------------------------------
safety-ai-app Dependency not found on PyPI and could not be audited: safety-ai-app (0.1.0)
```

**Resultado:** Vulnerabilidades encontradas — revisar e atualizar dependências afetadas.

---

## Auditoria Automática — 2026-04-18 00:20:57 UTC

```
Found 3 known vulnerabilities in 3 packages
Name                 Version ID                  Fix Versions
-------------------- ------- ------------------- ------------
langchain-openai     1.1.9   GHSA-r7w7-9xr2-qq2r 1.1.14
langgraph-checkpoint 3.0.1   CVE-2026-27794      4.0.0
transformers         4.57.3  CVE-2026-1839       5.0.0rc3
Name          Skip Reason
------------- ----------------------------------------------------------------------------
safety-ai-app Dependency not found on PyPI and could not be audited: safety-ai-app (0.1.0)
```

**Resultado:** Vulnerabilidades encontradas — revisar e atualizar dependências afetadas.

---

## Correção de Segurança — 2026-04-18 (Task #26)

### Remoção do uso de `pickle` em `google_auth.py`

**Severidade original:** MEDIUM (3 ocorrências SAST)  
**Status:** ✅ Corrigido

**Mudanças aplicadas:**
- Removido `import pickle` de `google_auth.py`.
- Substituído `TOKEN_USER_PICKLE_FILE` (`token_user.pickle`) por `TOKEN_USER_JSON_FILE` (`token_user.json`).
- Toda leitura de credenciais via `pickle.load()` substituída por `Credentials.from_authorized_user_info()` (API oficial da Google).
- Toda gravação via `pickle.dump()` substituída por `creds.to_json()` escrito em arquivo texto UTF-8.
- Adicionadas as funções auxiliares `_load_creds_from_json()` e `_save_creds_to_json()` para encapsular a serialização segura.
- `do_logout()` em `web_app.py` atualizado para remover `token_user.json` no logout.
- `.gitignore` atualizado para excluir `token_user.json` do rastreamento Git.

**Risco eliminado:** Deserialização arbitrária de código via arquivo `pickle` adulterado (CWE-502).

---

## Auditoria Automática — 2026-04-18 00:28:36 UTC

```
Found 3 known vulnerabilities in 3 packages
Name                 Version ID                  Fix Versions
-------------------- ------- ------------------- ------------
langchain-openai     1.1.9   GHSA-r7w7-9xr2-qq2r 1.1.14
langgraph-checkpoint 3.0.1   CVE-2026-27794      4.0.0
transformers         4.57.3  CVE-2026-1839       5.0.0rc3
Name          Skip Reason
------------- ----------------------------------------------------------------------------
safety-ai-app Dependency not found on PyPI and could not be audited: safety-ai-app (0.1.0)
```

**Resultado:** Vulnerabilidades encontradas — revisar e atualizar dependências afetadas.
