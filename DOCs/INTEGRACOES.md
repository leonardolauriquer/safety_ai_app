# Integracoes Externas

## Visao Geral

O SafetyAI integra-se com diversos servicos externos para fornecer dados atualizados e funcionalidades avancadas.

---

## 1. Google Drive

### 1.1 Arquivo: `google_drive_integrator.py`

### 1.2 Tipos de Autenticacao

| Tipo | Uso | Credenciais |
|------|-----|-------------|
| Service Account | Acesso automatizado a pastas compartilhadas | `service_account.json` |
| OAuth User | Acesso a documentos do usuario | `credentials.json`, `token_user.pickle` |

### 1.3 Service Account

```python
# Email da conta de servico
safetyai-app-drive-677@safetyai-472110.iam.gserviceaccount.com

# Escopos
SCOPES = ['https://www.googleapis.com/auth/drive.readonly']
```

### 1.4 Pastas do Drive

| Pasta | Conteudo | Folder ID |
|-------|----------|-----------|
| Base de Conhecimento | PDFs das NRs e documentos SST | `12ecb1RkbBuZ0GkoXGjux4wsZP7iqE_Tr` |
| Dados | Planilhas de referencia (CBO, CID, CNAE) | Varia por arquivo |

### 1.5 Arquivos do Drive

| Arquivo | File ID Constante | Descricao |
|---------|-------------------|-----------|
| CBO2025.xlsx | `CBO2025_FILE_ID` | Classificacao de Ocupacoes |
| CID10.xlsx | `CID10_FILE_ID` | Classificacao de Doencas |
| grau_de_risco.xlsx | `GRAU_DE_RISCO_FILE_ID` | Grau de Risco por CNAE |
| Dimensionamento_SESMT.xlsx | Dinamico | Tabela SESMT |

### 1.6 Metodos Principais

```python
class GoogleDriveIntegrator:
    def download_file_from_folder(self, folder_id, file_name, local_path) -> str:
        """Baixa arquivo de uma pasta para caminho local"""
    
    def download_file_from_drive(self, file_id, local_path) -> str:
        """Baixa arquivo por ID para caminho local"""
    
    def list_files_in_folder(self, folder_id) -> List[Dict]:
        """Lista arquivos em uma pasta"""
    
    def export_google_doc_as_text(self, file_id) -> str:
        """Exporta Google Doc como texto"""
```

---

## 2. OpenRouter (LLM)

### 2.1 Configuracao

| Parametro | Valor |
|-----------|-------|
| Base URL | `https://openrouter.ai/api/v1` |
| Modelo | `openai/gpt-oss-120b` |
| Provider | OpenAI-compatible API |

### 2.2 Variaveis de Ambiente

```bash
# Replit AI Integrations (preferencial)
AI_INTEGRATIONS_OPENROUTER_API_KEY=...
AI_INTEGRATIONS_OPENROUTER_BASE_URL=...

# Fallback direto
OPENROUTER_API_KEY=...
```

### 2.3 Headers Opcionais

```python
model_kwargs = {
    "extra_headers": {
        "HTTP-Referer": "https://safetyai.streamlit.app/",
        "X-Title": "SafetyAI - SST"
    }
}
```

---

## 3. API IBGE (CNAE)

### 3.1 Arquivo: `cnae_data_processor.py`

### 3.2 Base URL

```
https://servicodados.ibge.gov.br/api/v2/cnae/
```

### 3.3 Endpoints

| Endpoint | Metodo | Descricao |
|----------|--------|-----------|
| `/secoes` | GET | Lista secoes CNAE |
| `/secoes/{id}` | GET | Secao especifica |
| `/divisoes` | GET | Lista divisoes |
| `/divisoes/{id}` | GET | Divisao especifica |
| `/grupos` | GET | Lista grupos |
| `/grupos/{id}` | GET | Grupo especifico |
| `/classes` | GET | Lista classes |
| `/classes/{id}` | GET | Classe especifica |
| `/subclasses` | GET | Lista subclasses |
| `/subclasses/{id}` | GET | Subclasse especifica |

### 3.4 Exemplo de Resposta

```json
{
    "id": "0111-3/01",
    "descricao": "Cultivo de arroz",
    "grupo": {
        "id": "01.1",
        "descricao": "Producao de lavouras temporarias"
    }
}
```

---

## 4. API ICD (OMS) - CID-11

### 4.1 Arquivo: `cid_data_processor.py`

### 4.2 Autenticacao

```python
# Endpoint de autenticacao
ICD_API_AUTH_URL = "https://icdaccessmanagement.who.int/connect/token"

# Payload
{
    'grant_type': 'client_credentials',
    'client_id': ICD_API_CLIENT_ID,
    'client_secret': ICD_API_CLIENT_SECRET,
    'scope': 'icdapi_access'
}
```

### 4.3 Endpoint de Busca

```python
ICD_11_API_SEARCH_ENDPOINT = "https://id.who.int/icd/release/11/2025-01/mms/search"
```

### 4.4 Parametros de Busca

| Parametro | Valor | Descricao |
|-----------|-------|-----------|
| `q` | Termo de busca | Query string |
| `flatResults` | `True` | Resultados planos |
| `medicalCodingMode` | `True` | Modo de codificacao medica |

### 4.5 Headers

```python
headers = {
    'Authorization': f"Bearer {token}",
    'Accept': 'application/json',
    'Accept-Language': 'pt',
    'API-Version': 'v2'
}
```

### 4.6 Variaveis de Ambiente

```bash
ICD_API_CLIENT_ID=...
ICD_API_CLIENT_SECRET=...
```

---

## 5. FTP Ministerio do Trabalho (CA/EPI)

### 5.1 Arquivo: `ca_data_processor.py`

### 5.2 Configuracao

| Parametro | Valor |
|-----------|-------|
| Host | `ftp.mtps.gov.br` |
| Caminho | `/portal/fiscalizacao/seguranca-e-saude-no-trabalho/caepi/` |
| Arquivo | `tgg_export_caepi.zip` |
| Autenticacao | Anonima |

### 5.3 Processo de Download

```python
with ftplib.FTP(FTP_HOST) as ftp:
    ftp.login()  # Login anonimo
    ftp.retrbinary(f'RETR {file_path}', fp.write)
```

### 5.4 Formato do Arquivo

- ZIP contendo TXT
- Delimitador: `|` (pipe)
- Encoding: UTF-8 (fallback: cp1252, latin1)

---

## 6. API Adzuna (Vagas de Emprego)

### 6.1 Arquivo: `job_api_integrator.py`

### 6.2 Configuracao

| Parametro | Valor |
|-----------|-------|
| Base URL | `https://api.adzuna.com/v1/api/jobs/br/search/` |
| Pais | Brasil (`br`) |

### 6.3 Variaveis de Ambiente

```bash
ADZUNA_APP_ID=...
ADZUNA_API_KEY=...
```

### 6.4 Parametros de Busca

| Parametro | Descricao |
|-----------|-----------|
| `what` | Termo de busca (ex: "seguranca do trabalho") |
| `where` | Localizacao (ex: "Sao Paulo") |
| `results_per_page` | Numero de resultados |

---

## 7. Replit AI Integrations

### 7.1 OpenRouter Integration

O SafetyAI utiliza a integracao OpenRouter do Replit, que:
- Gerencia automaticamente a chave de API
- Fornece URL base pre-configurada
- Permite rotacao de chaves

### 7.2 Variaveis Automaticas

```bash
# Preenchidas automaticamente pelo Replit
AI_INTEGRATIONS_OPENROUTER_API_KEY
AI_INTEGRATIONS_OPENROUTER_BASE_URL
```

---

## 8. Resumo de APIs

| Servico | Tipo | Autenticacao | Frequencia |
|---------|------|--------------|------------|
| Google Drive | REST API | OAuth/Service Account | Sob demanda |
| OpenRouter | REST API (OpenAI-compat) | API Key | Cada chat |
| IBGE CNAE | REST API | Nenhuma | Cada busca |
| OMS ICD-11 | REST API | OAuth | Cada busca |
| FTP MTE | FTP | Anonima | Diaria |
| Adzuna | REST API | API Key | Cada busca |

---

## 9. Tratamento de Erros

### 9.1 Padrao de Retry

```python
try:
    response = requests.get(url, timeout=10)
    response.raise_for_status()
except requests.exceptions.HTTPError as e:
    logger.error(f"Erro HTTP: {e}")
except requests.exceptions.ConnectionError as e:
    logger.error(f"Erro de conexao: {e}")
except requests.exceptions.Timeout as e:
    logger.error(f"Timeout: {e}")
```

### 9.2 Fallbacks

| Servico | Fallback |
|---------|----------|
| OpenRouter | Tenta Replit Integration, depois API Key direta |
| CID-11 | Usa CID-10 local se API falhar |
| CA/EPI | Usa cache Parquet se FTP falhar |
| CNAE Risco | Retorna None se Excel nao carregar |

---

## 10. Limites e Quotas

| Servico | Limite |
|---------|--------|
| IBGE | Sem limite documentado |
| OMS ICD | Rate limit por token |
| Adzuna | Varia por plano |
| Google Drive | 1 bilhao de queries/dia (API) |
| FTP MTE | Conexoes simultaneas limitadas |
