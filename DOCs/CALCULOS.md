# Algoritmos e Formulas de Calculo

## 1. Dimensionamento CIPA (NR-05)

### Arquivo: `cipa_data_processor.py`

### 1.1 Tabela de Dimensionamento (Quadro I da NR-05)

A tabela `CIPA_DIMENSIONING_TABLE` define os membros efetivos e suplentes baseados no:
- **Grau de Risco**: 1, 2, 3 ou 4
- **Numero de Empregados**: Faixas de 20 a mais de 10.000

#### Estrutura da Tabela:
```python
CIPA_DIMENSIONING_TABLE = {
    grau_risco: {
        (min_empregados, max_empregados): {
            'efetivos': N,
            'suplentes': M
        }
    }
}
```

### 1.2 Algoritmo de Calculo

```python
def get_cipa_dimensioning(grau_risco: int, num_employees: int) -> Dict:
```

#### Regras:
1. **Menos de 20 empregados**: Nao constitui CIPA formal
   - Retorna 0 efetivos e 0 suplentes
   - Observacao: Nomear representante

2. **20 a 10.000 empregados**: Consulta direta na tabela
   - Busca a faixa correspondente
   - Retorna efetivos e suplentes da tabela

3. **Mais de 10.000 empregados**: Calculo incremental
   ```python
   # Base para 5.001-10.000
   efetivos = base_efetivos
   suplentes = base_suplentes
   
   # Calculo de grupos adicionais
   remaining = num_employees - 10000
   num_groups = ceil(remaining / 2500)
   
   efetivos += num_groups * efetivos_add
   suplentes += num_groups * suplentes_add
   ```

### 1.3 Valores por Grau de Risco

| Grau de Risco | 5.001-10.000 | Incremento por 2.500 |
|---------------|--------------|----------------------|
| 1 | 8 efetivos, 6 suplentes | +1 efetivo, +1 suplente |
| 2 | 10 efetivos, 8 suplentes | +1 efetivo, +1 suplente |
| 3 | 12 efetivos, 8 suplentes | +2 efetivos, +2 suplentes |
| 4 | 13 efetivos, 10 suplentes | +2 efetivos, +2 suplentes |

---

## 2. Cronograma Eleitoral CIPA

### Arquivo: `cipa_data_processor.py`

### 2.1 Funcao Principal

```python
def calculate_election_schedule(mandate_end_date: date) -> Dict:
```

### 2.2 Datas Calculadas (Retroativamente)

| Evento | Calculo | Base Legal |
|--------|---------|------------|
| Data da Posse | 1o dia util apos termino do mandato | NR-05, 5.4.7 |
| Data da Eleicao | Minimo 30 dias antes do termino | NR-05, 5.5.3 f |
| Publicacao Edital | Minimo 60 dias antes do termino | NR-05, 5.5.1 |
| Inicio Inscricoes | 15 dias antes do fim das inscricoes | NR-05, 5.5.3 b |
| Prazo Denuncias | 30 dias apos divulgacao resultado | NR-05, 5.5.5 |

### 2.3 Funcoes Auxiliares de Dias Uteis

```python
def is_working_day(day: date, holidays: List[date]) -> bool:
    """Dia util = nao e fim de semana e nao e feriado"""
    return day.weekday() < 5 and day not in holidays

def add_working_days(start_day: date, days: int, holidays: List[date]) -> date:
    """Adiciona N dias uteis a uma data"""
```

### 2.4 Feriados Considerados

Lista `BRAZILIAN_NATIONAL_HOLIDAYS` inclui:
- Confraternizacao Universal
- Carnaval (segunda e terca)
- Paixao de Cristo
- Tiradentes
- Dia do Trabalho
- Corpus Christi
- Independencia
- Nossa Senhora Aparecida
- Finados
- Proclamacao da Republica
- Consciencia Negra
- Natal

---

## 3. Dimensionamento SESMT (NR-04)

### Arquivo: `sesmt_data_processor.py`

### 3.1 Profissionais do SESMT

| Codigo | Profissional |
|--------|--------------|
| `tecnico_seguranca` | Tecnico de Seguranca do Trabalho |
| `engenheiro_seguranca` | Engenheiro de Seguranca do Trabalho |
| `aux_tec_enfermagem` | Auxiliar/Tecnico de Enfermagem do Trabalho |
| `enfermeiro` | Enfermeiro do Trabalho |
| `medico` | Medico do Trabalho |

### 3.2 Faixas de Empregados

```python
EMPLOYEE_RANGE_COLUMNS = {
    "50 a 100": (50, 100),
    "101 a 250": (101, 250),
    "251 a 500": (251, 500),
    "501 a 1.000": (501, 1000),
    "1.001 a 2.000": (1001, 2000),
    "2.001 a 3.500": (2001, 3500),
    "3.501 a 5.000": (3501, 5000),
}
```

### 3.3 Algoritmo de Calculo

```python
def get_sesmt_dimensioning(grau_risco: int, num_employees: int) -> Dict:
```

#### Regras:
1. **Menos de 50 empregados**: SESMT nao obrigatorio
   - Pode haver SESMT compartilhado (consultar NR-04)

2. **50 a 5.000 empregados**: Consulta na tabela
   - Carregada do Excel `Dimensionamento_SESMT.xlsx` do Google Drive

3. **Mais de 5.000 empregados**: Calculo incremental
   ```python
   # Base para 3.501-5.000
   base_roles = SESMT_DIMENSIONING_TABLE[grau_risco][(3501, 5000)]
   
   # Grupos adicionais (cada 4.000 alem de 5.000)
   excess = num_employees - 5000
   num_groups = ceil(excess / 4000)
   
   # Adiciona profissionais conforme regra
   for role in roles:
       base_qty += additional_qty * num_groups
   ```

### 3.4 Observacoes Especiais

- Valores com `*`: Tempo parcial (minimo 3 horas/dia)
- Valores com `**`: Engenheiro de Seguranca pode acumular funcoes
- Valores com `***`: Tecnico de Enfermagem nao precisa supervisao

---

## 4. Grau de Risco por CNAE

### Arquivo: `cnae_risk_data_processor.py`

### 4.1 Fonte de Dados

- Arquivo: `grau_de_risco.xlsx` do Google Drive
- Colunas: `CNAE` e `Grau de Risco`

### 4.2 Algoritmo de Busca

```python
def get_risk_level(cnae_code: str) -> Optional[int]:
    # 1. Limpa o codigo CNAE (remove pontos, tracos, barras)
    cnae_clean = cnae_code.replace('.', '').replace('-', '').replace('/', '').strip()
    
    # 2. Busca no DataFrame
    result = df[df['CNAE'] == cnae_clean]
    
    # 3. Retorna o Grau de Risco (1, 2, 3 ou 4)
    return int(result['Grau de Risco'].iloc[0])
```

---

## 5. Calculo de Multas (NR-28)

### Arquivo: `sesmt_data_processor.py` (FinesDataProcessor)

### 5.1 Componentes do Calculo

```python
def calculate_total_fine(
    employee_range: str,      # Faixa de empregados
    recidivism: bool,         # Reincidencia
    infraction_codes: List    # Codigos das infracoes
) -> Dict:
```

### 5.2 Fatores Considerados

| Fator | Descricao |
|-------|-----------|
| Nivel da Infracao | I1, I2, I3, I4 (gravidade) |
| Faixa de Empregados | Afeta valor base |
| Reincidencia | Duplica o valor da multa |

### 5.3 Formula

```
Multa = Valor_Base(nivel, faixa) * Fator_Reincidencia

Onde:
- Valor_Base: Definido por tabela NR-28
- Fator_Reincidencia: 1 (sem) ou 2 (com)
```

---

## 6. Busca Hibrida RAG

### Arquivo: `nr_rag_qa.py`

### 6.1 Ensemble Retriever

```python
EnsembleRetriever = (
    BM25Retriever(weight=0.4) +
    VectorRetriever(weight=0.6)
)
```

### 6.2 Parametros de Busca

| Parametro | Valor | Descricao |
|-----------|-------|-----------|
| `k` | 5 | Numero de documentos retornados |
| `chunk_size` | 1000 | Tamanho dos chunks de texto |
| `chunk_overlap` | 200 | Sobreposicao entre chunks |

### 6.3 Modelo de Embeddings

- **Modelo**: `sentence-transformers/all-MiniLM-L6-v2`
- **Dimensao**: 384
- **Device**: CPU

---

## Resumo de Formulas

| Calculo | Formula Simplificada |
|---------|---------------------|
| CIPA (>10k) | `base + ceil((emp - 10000) / 2500) * incremento` |
| SESMT (>5k) | `base + ceil((emp - 5000) / 4000) * adicional` |
| Multa NR-28 | `valor_base * (2 se reincidente else 1)` |
| Cronograma | `termino_mandato - N dias (ajustado para util)` |
