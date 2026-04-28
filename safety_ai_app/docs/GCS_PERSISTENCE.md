# Persistência de Dados com Google Cloud Storage (GCS)

Este documento descreve a implementação da persistência para o ChromaDB no projeto Safety AI App, garantindo que os documentos processados não sejam perdidos quando o container do Cloud Run é reiniciado.

## Visão Geral

O Cloud Run utiliza um sistema de arquivos efêmero. Para persistir os dados do banco vetorial:
1.  **Startup**: A aplicação baixa o estado mais recente do banco do GCS para o diretório local.
2.  **Runtime**: Toda vez que um documento é adicionado ou removido, a aplicação sincroniza o diretório local de volta para o GCS.

## Configuração

### Variáveis de Ambiente
- `GCS_BUCKET_NAME`: Nome do bucket no GCS. Se não definido, o sistema tentará usar `safety-ai-storage-[PROJECT-ID]`.
- `GOOGLE_CLOUD_PROJECT`: ID do projeto no GCP (necessário para inferir o nome do bucket padrão).

### Permissões IAM
A Service Account do Cloud Run deve ter o papel:
- `roles/storage.objectAdmin` no bucket alvo.

## Estrutura no Bucket
Os arquivos do banco são armazenados sob o prefixo `chroma_db/` no bucket:
```text
gs://[BUCKET_NAME]/chroma_db/
    ├── chroma.sqlite3
    └── ...
```

## Arquitetura de Sincronização

A lógica está centralizada na classe `GCSStorageManager` em `storage_manager.py`.

### Fluxo de Escrita
Sempre que um dos seguintes métodos em `NRQuestionAnswering` for chamado, um upload imediato para o GCS é disparado:
- `remove_document_by_id`

## Lógica da Implementação (Antes vs Depois)

### Antes da Atualização
- O `NRQuestionAnswering` inicializava o ChromaDB localmente no diretório `data/chroma_db`.
- Operações de modificação eram salvas apenas localmente via `persist()`.
- No ambiente do Cloud Run, os dados eram perdidos após o restart do container pois o volume local é efêmero.

### Após a Atualização
- Foi criada a classe `GCSStorageManager` (`storage_manager.py`) para encapsular a lógica de upload/download do diretório `chroma_db/`.
- **Startup**: No `__init__` de `NRQuestionAnswering`, é chamado `storage_manager.sync_from_gcs()` ANTES da inicialização do ChromaDB Client. Isso restaura o estado global do banco para o ambiente efêmero.
- **Runtime**: Foi adicionada uma chamada a `storage_manager.sync_to_gcs()` após cada operação que altera o banco (adição de documentos, remoção, limpeza total).
- **Consistência**: O uso de `persist()` local garante que os arquivos estejam prontos no disco antes de serem enviados para o bucket.

## Checklist de Implementação

- [x] Criar `storage_manager.py` com suporte a Google Cloud Storage.
- [x] Implementar detecção automática de Bucket baseada no Project ID.
- [x] Integrar `GCSStorageManager` no fluxo de inicialização do `NRQuestionAnswering`.
- [x] Adicionar hooks de sincronização para operações de escrita (add/delete).
- [x] Validar sintaxe e integridade dos arquivos alterados.
- [x] Atualizar documentação técnica e README.


## Troubleshooting

### Logs de Sincronização
Procure por logs contendo `GCSStorageManager` para verificar o status das sincronizações:
- `Sincronização GCS -> Local concluída`
- `Sincronização Local -> GCS concluída`

### Erros de Permissão
Se vir erros de `403 Forbidden`, verifique se a Service Account tem permissão para escrever no bucket.
