# Padronização do Project ID (safety-ai-2026)

## Relatório de Alterações — 2026-04-20

Esta tarefa consistiu em padronizar o Project ID do Google Cloud Platform (GCP) para `safety-ai-2026` em todos os scripts de automação e documentações, corrigindo a divergência onde alguns arquivos utilizavam `safetyai-472110`.

### Antes da Atualização (Inconsistente)
- `cloudbuild.yaml`: `safetyai-472110`
- `.gcloudignore`: `safetyai-472110`
- `scripts/push_secrets_to_gcp.py`: `safetyai-472110`
- `DEPLOY.md`: Mix de `safetyai-472110` e `safety-ai-2026`
- `DOCs/INTEGRACOES.md`: Referência a conta de serviço em `safetyai-472110`
- `DOCs/FIREBASE_DEPLOY.md`: `safetyai-472110`

### Após a Atualização (Padronizado)
- Todos os arquivos acima agora utilizam exclusivamente `safety-ai-2026`.

---

## Check-list de Implementação

- [x] Atualizar `cloudbuild.yaml` com `safety-ai-2026`.
- [x] Atualizar `.gcloudignore` com `safety-ai-2026`.
- [x] Atualizar `scripts/push_secrets_to_gcp.py` com `safety-ai-2026`.
- [x] Atualizar `DEPLOY.md` (infraestrutura e comandos manuais).
- [x] Atualizar `DOCs/INTEGRACOES.md` (email da conta de serviço).
- [x] Atualizar `DOCs/FIREBASE_DEPLOY.md` (passos de configuração e deploy).
- [x] Atualizar `DOCs/README.md` com a nova entrada.

## Lógica Utilizada
A padronização foi feita visando garantir que as ferramentas de CI/CD (Cloud Build, GitHub Actions) e scripts auxiliares apontem para o projeto correto, evitando falhas de permissão ou deploys em ambientes errados. O ID `safety-ai-2026` foi escolhido conforme solicitado pelo usuário.

## Próximos Passos
1. Validar o build no Google Cloud Build usando o novo ID.
2. Certificar-se de que a conta de serviço `safetyai-app-drive-677@safety-ai-2026.iam.gserviceaccount.com` tem as permissões necessárias no novo projeto.
