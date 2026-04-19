# Processadores de Dados

## Visao Geral

Os processadores de dados sao classes singleton responsaveis por carregar, processar e fornecer dados de referencia para o SafetyAI.

---

## 1. CBODatabase (Classificacao Brasileira de Ocupacoes)

### Arquivo: `cbo_data_processor.py`

### 1.1 Fonte de Dados

| Item | Valor |
|------|-------|
| Arquivo | `CBO2025.xlsx` |
| Localizacao | Google Drive |
| File ID | `CBO2025_FILE_ID` |

### 1.2 Estrutura dos Dados

```python
# Colunas do Excel
required_cols = [
    'COD_OCUPACAO',      # Codigo CBO (ex: "2149-10")
    'CARGO',             # Nome da ocupacao
    'SGL_GRANDE_AREA',   # Sigla da grande area
    'NOME_GRANDE_AREA',  # Nome da grande area
    'COD_ATIVIDADE',     # Codigo da atividade
    'NOME_ATIVIDADE'     # Descricao da atividade
]
```

### 1.3 Estrutura Hierarquica

```python
_cargos_dict = {
    "cod_ocupacao": {
        "CARGO": "Nome da Ocupacao",
        "AREAS_DE_ATUACAO": {
            "Nome da Grande Area": [
                {
                    "COD_ATIVIDADE": "codigo",
                    "NOME_ATIVIDADE": "descricao"
                }
            ]
        }
    }
}
```

### 1.4 Metodos Disponaveis

| Metodo | Retorno | Descricao |
|--------|---------|-----------|
| `get_all_cargos()` | `List[Dict]` | Lista de todas as ocupacoes |
| `get_areas_by_cargo_code(cod)` | `List[str]` | Areas de atuacao por codigo |
| `get_activities_by_cargo_and_area(cod, area)` | `List[Dict]` | Atividades por ocupacao e area |
| `get_cargo_name_by_code(cod)` | `str` | Nome da ocupacao por codigo |

---

## 2. CIDDatabase (Classificacao Internacional de Doencas)

### Arquivo: `cid_data_processor.py`

### 2.1 Fontes de Dados

| Versao | Fonte | Tipo |
|--------|-------|------|
| CID-10 | `CID10.xlsx` (Google Drive) | Local/Cache |
| CID-11 | API OMS (WHO ICD API) | Tempo real |

### 2.2 Estrutura CID-10 Local

```python
# Colunas do Excel
'CAT'              # Categoria (ex: "A00")
'CAT_DESCRICAO'    # Descricao da categoria
'SUB_CAT'          # Subcategoria (ex: "A00.0")
'SUB_CAT_DESCRICAO' # Descricao da subcategoria
```

### 2.3 API ICD-11 (OMS)

```python
# Endpoint de busca
ICD_11_API_SEARCH_ENDPOINT = "https://id.who.int/icd/release/11/2025-01/mms/search"

# Autenticacao
ICD_API_AUTH_URL = "https://icdaccessmanagement.who.int/connect/token"

# Credenciais (variaveis de ambiente)
ICD_API_CLIENT_ID
ICD_API_CLIENT_SECRET
```

### 2.4 Metodos Disponaveis

| Metodo | Retorno | Descricao |
|--------|---------|-----------|
| `search_cid10_local(query)` | `List[Dict]` | Busca no CID-10 local |
| `search_cid11_text(query)` | `List[Dict]` | Busca na API CID-11 |

### 2.5 Estrutura de Retorno

```python
[
    {
        "COD_CID": "A00.0",
        "DESCRICAO_CID": "Colera devida a Vibrio cholerae 01, biotipo cholerae"
    }
]
```

---

## 3. CNAEDataProcessor (Classificacao Nacional de Atividades Economicas)

### Arquivo: `cnae_data_processor.py`

### 3.1 Fonte de Dados

| Item | Valor |
|------|-------|
| API | IBGE Servico de Dados |
| Base URL | `https://servicodados.ibge.gov.br/api/v2/cnae/` |

### 3.2 Hierarquia CNAE

```
Secoes (21)
    └── Divisoes (87)
        └── Grupos (285)
            └── Classes (673)
                └── Subclasses (1332)
```

### 3.3 Endpoints da API

| Endpoint | Descricao |
|----------|-----------|
| `/secoes` | Lista secoes |
| `/divisoes` | Lista divisoes |
| `/grupos` | Lista grupos |
| `/classes` | Lista classes |
| `/subclasses` | Lista subclasses |

### 3.4 Metodos Disponaveis

| Metodo | Retorno | Descricao |
|--------|---------|-----------|
| `get_sections(ids)` | `List[Dict]` | Secoes |
| `get_divisions(ids, section_ids)` | `List[Dict]` | Divisoes |
| `get_groups(ids, division_ids)` | `List[Dict]` | Grupos |
| `get_classes(ids, group_ids)` | `List[Dict]` | Classes |
| `get_subclasses(ids, class_ids)` | `List[Dict]` | Subclasses |
| `search_cnae_by_id(id, level)` | `List[Dict]` | Busca por ID |

### 3.5 Integracao com Grau de Risco

```python
# Automaticamente adiciona grau de risco aos resultados
for item in data:
    cnae_id = item.get('id')
    if cnae_id:
        risk_level = self._risk_processor.get_risk_level(cnae_id)
        item['grau_de_risco'] = risk_level
```

---

## 4. CNAERiskDataProcessor (Grau de Risco)

### Arquivo: `cnae_risk_data_processor.py`

### 4.1 Fonte de Dados

| Item | Valor |
|------|-------|
| Arquivo | `grau_de_risco.xlsx` |
| Localizacao | Google Drive |
| File ID | `GRAU_DE_RISCO_FILE_ID` |

### 4.2 Estrutura do Excel

```python
# Colunas
'CNAE'          # Codigo CNAE (ex: "0111-3/01")
'Grau de Risco' # Valor 1, 2, 3 ou 4
```

### 4.3 Processamento do CNAE

```python
# Limpeza do codigo
df['CNAE'] = df['CNAE'].str.replace('.', '')
df['CNAE'] = df['CNAE'].str.replace('-', '')
df['CNAE'] = df['CNAE'].str.replace('/', '')
df['CNAE'] = df['CNAE'].str.strip()
```

### 4.4 Metodo Principal

```python
def get_risk_level(self, cnae_code: str) -> Optional[int]:
    """
    Retorna o Grau de Risco (1-4) para um codigo CNAE.
    Retorna None se nao encontrado.
    """
```

---

## 5. CADataProcessor (Certificado de Aprovacao)

### Arquivo: `ca_data_processor.py`

### 5.1 Fonte de Dados

| Item | Valor |
|------|-------|
| Servidor | FTP `ftp.mtps.gov.br` |
| Caminho | `/portal/fiscalizacao/seguranca-e-saude-no-trabalho/caepi/` |
| Arquivo | `tgg_export_caepi.zip` |

### 5.2 Fluxo de Atualizacao

```
1. Verifica se precisa atualizar (_should_update_data)
2. Baixa ZIP do FTP (_download_ca_file)
3. Extrai TXT do ZIP
4. Parseia TXT para DataFrame (_parse_ca_txt_to_df)
5. Salva em Parquet (cache local)
6. Atualiza data de ultima atualizacao
```

### 5.3 Mapeamento de Colunas

```python
column_mapping = {
    'NR REGISTRO CA': 'ca_numero',
    'EQUIPAMENTO': 'equipamento_tipo',
    'DESCRICAO': 'descricao_detalhada',
    'FABRICANTE': 'fabricante_nome',
    'SITUACAO': 'situacao_ca',
    'VALIDADE': 'validade_ca',
    'REFERENCIA': 'referencia_fabricante',
    'PROCESSO': 'processo_numero',
    # ... mais campos
}
```

### 5.4 Cache Local

| Arquivo | Descricao |
|---------|-----------|
| `data/ca_data.parquet` | Dados processados |
| `data/ca_last_update.txt` | Data da ultima atualizacao |

### 5.5 Metodos Disponaveis

| Metodo | Retorno | Descricao |
|--------|---------|-----------|
| `get_ca_data()` | `DataFrame` | Todos os dados de CA |
| `search_ca(term)` | `DataFrame` | Busca por termo |

### 5.6 Campos de Busca

```python
searchable_cols = [
    'ca_numero',
    'equipamento_tipo',
    'descricao_detalhada',
    'fabricante_nome',
    'referencia_fabricante',
    'aprovacao_ca',
    'situacao_ca',
    'marca_ca',
    'cor_equipamento'
]
```

---

## 6. Padrao Singleton

Todos os processadores usam o padrao Singleton:

```python
class DataProcessor:
    _instance: Optional['DataProcessor'] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DataProcessor, cls).__new__(cls)
            # Inicializa dados
        return cls._instance
```

---

## 7. Caching

### Streamlit Cache

```python
@st.cache_resource
def _load_data():
    """Carrega dados uma vez e mantém em cache"""

@st.cache_data(ttl=timedelta(hours=24))
def _get_cached_data():
    """Cache com TTL de 24 horas"""
```

### LRU Cache

```python
@lru_cache(maxsize=1)
def _load_sesmt_data():
    """Cache funcional para dados imutaveis"""
```

---

## Resumo de Fontes

| Processador | Fonte | Tipo | Atualizacao |
|-------------|-------|------|-------------|
| CBO | Google Drive Excel | Cache | Sob demanda |
| CID-10 | Google Drive Excel | Cache | Sob demanda |
| CID-11 | API OMS | Tempo real | Cada busca |
| CNAE | API IBGE | Tempo real | Cada busca |
| Grau de Risco | Google Drive Excel | Cache | Sob demanda |
| CA/EPI | FTP Ministerio | Cache 24h | Diaria |
