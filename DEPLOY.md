# Deploy — SafetyAI App

## Infraestrutura de Produção

| Componente | Valor |
|---|---|
| **Projeto GCP** | `safety-ai-2026` |
| **Projeto Firebase** | `safety-ai-2026` |
| **URL Cloud Run** | https://safety-ai-app-710675170484.us-central1.run.app |
| **Firebase Hosting** | https://safety-ai-2026.web.app |
| **Artifact Registry** | `us-central1-docker.pkg.dev/safety-ai-2026/safety-ai-app/safety-ai-app` |
| **Cloud Run Service** | `safety-ai-app` |
| **Região** | `us-central1` |

## Fluxo de Deploy Automático

```
Replit (edição de código)
    └─▶ GitHub push (main)
          └─▶ GitHub Actions (.github/workflows/deploy.yml)
                ├─▶ Docker build + push → Artifact Registry
                ├─▶ gcloud run deploy   → Cloud Run
                └─▶ firebase deploy     → Firebase Hosting (redirect)
```

## Configurar Deploy Automático (GitHub Actions)

### Passo 1 — Permissões da conta de serviço

Acesse **GCP Console → IAM** e adicione os papéis à conta de serviço
`safetyai-app-drive-677@safety-ai-2026.iam.gserviceaccount.com`:

| Role | Para quê |
|---|---|
| `roles/run.admin` | Implantar novas revisões no Cloud Run |
| `roles/artifactregistry.writer` | Push de imagens Docker |
| `roles/storage.objectAdmin` | Upload de source para Cloud Build |
| `roles/cloudbuild.builds.editor` | Submeter builds |
| `roles/firebase.admin` | Deploy Firebase Hosting |

### Passo 2 — Secret no GitHub

1. Acesse: https://github.com/leonardolauriquer/safety_ai_app/settings/secrets/actions
2. Clique em **"New repository secret"**
3. Nome: `GCP_SA_KEY`
4. Valor: conteúdo completo do JSON da conta de serviço

### Passo 3 — Token GitHub com scope `workflow`

O arquivo `.github/workflows/deploy.yml` requer o scope `workflow` no token:

1. Acesse: https://github.com/settings/tokens
2. Edite o token do Replit e marque o scope **`workflow`**
3. Salve — o próximo push incluirá o arquivo de workflow

---

## Deploy Manual (linha de comando)

```bash
# 1. Autenticar Docker
echo $GCP_SA_KEY | docker login \
  -u _json_key --password-stdin \
  us-central1-docker.pkg.dev

# 2. Build e push
IMAGE=us-central1-docker.pkg.dev/safety-ai-2026/safety-ai-app/safety-ai-app
docker build -t $IMAGE:latest .
docker push $IMAGE:latest

# 3. Deploy Cloud Run
gcloud run deploy safety-ai-app \
  --image=$IMAGE:latest \
  --platform=managed \
  --region=us-central1 \
  --allow-unauthenticated \
  --port=8080 --memory=4Gi --cpu=2 --timeout=300 \
  --set-env-vars="DISABLE_AUTOINDEX=1" \
  --project=safety-ai-2026

# 4. Deploy Firebase Hosting
firebase deploy --only hosting --project safety-ai-2026
```

---

## Variáveis de Ambiente no Cloud Run

| Variável | Descrição |
|---|---|
| `GOOGLE_API_KEY` | Chave da API Google (OAuth + Drive) |
| `GOOGLE_SERVICE_ACCOUNT_KEY` | JSON da conta de serviço Drive |
| `GOOGLE_CLIENT_CREDENTIALS` | Credenciais OAuth client |
| `GOOGLE_DRIVE_CENTRAL_LIBRARY_FOLDER_ID` | ID da pasta da biblioteca central |
| `GOOGLE_DRIVE_DONATION_FOLDER_ID` | ID da pasta de doações |
| `ICD_API_CLIENT_ID` / `ICD_API_CLIENT_SECRET` | API ICD-11 |
| `ADZUNA_API_KEY` / `ADZUNA_APP_ID` | API de vagas |
| `RECAPTCHA_SECRET_KEY` / `RECAPTCHA_SITE_KEY` | reCAPTCHA |
| `ADMIN_EMAILS` | E-mails com acesso Admin |
| `OAUTH_REDIRECT_URI` | URI de redirecionamento OAuth |
| `DISABLE_AUTOINDEX` | `1` — desativa indexação automática |

---

## Estrutura do Repositório

```
safety_ai_app/
├── src/safety_ai_app/      # Código principal
│   ├── web_app.py          # Entry point Streamlit
│   ├── server.py           # Proxy aiohttp (só no Replit dev)
│   ├── nr_rag_qa.py        # Pipeline RAG
│   └── web_interface/      # Páginas e componentes UI
├── data/
│   ├── chroma_db/          # ChromaDB pré-indexada (NRs 1-27)
│   └── nrs/                # PDFs oficiais das NRs
├── assets/                 # Assets estáticos
└── requirements.txt
Dockerfile                  # Imagem Docker (produção)
.dockerignore
firebase.json               # Firebase Hosting config
.firebaserc
.github/workflows/deploy.yml  # CI/CD automático
DEPLOY.md                   # Este documento
```
