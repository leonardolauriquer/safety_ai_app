# Deploy: Firebase Hosting + Cloud Run

## Pré-requisitos

- Conta Google Cloud com billing activado
- [Firebase CLI](https://firebase.google.com/docs/cli) instalado (`npm install -g firebase-tools`)
- [gcloud CLI](https://cloud.google.com/sdk/docs/install) instalado e autenticado
- Projecto Firebase: `safety-ai-2026`

---

## 1. Configurar o projecto Firebase

```bash
firebase login
firebase use safety-ai-2026
```

> **Importante**: Antes do deploy, alinhe o projeto `gcloud` com o Firebase para evitar erros 403:
> ```bash
> gcloud config set project safety-ai-2026
> ```

---

## 2. Criar secrets no Google Cloud Secret Manager

```bash
PROJECT_ID="safety-ai-2026"

gcloud services enable secretmanager.googleapis.com --project=$PROJECT_ID

# Criar cada secret (substituir VALUE pelo valor real)
# OAUTH_REDIRECT_URI = https://safety-ai-2026.web.app (valor fixo)
for SECRET in GOOGLE_API_KEY GOOGLE_SERVICE_ACCOUNT_KEY GOOGLE_CLIENT_CREDENTIALS \
  GOOGLE_DRIVE_CENTRAL_LIBRARY_FOLDER_ID GOOGLE_DRIVE_DONATION_FOLDER_ID \
  ICD_API_CLIENT_ID ICD_API_CLIENT_SECRET ADZUNA_API_KEY ADZUNA_APP_ID \
  RECAPTCHA_SECRET_KEY RECAPTCHA_SITE_KEY ADMIN_EMAILS OAUTH_REDIRECT_URI; do
  printf "➤ $SECRET: "; read -r VALUE
  gcloud secrets create "$SECRET" --project="$PROJECT_ID" --replication-policy="automatic" 2>/dev/null || true
  printf '%s' "$VALUE" | gcloud secrets versions add "$SECRET" --data-file=- --project="$PROJECT_ID"
  echo "  ✓ $SECRET"
done
```

---

## 3. Configurar URIs de redirecionamento OAuth no Google Cloud Console

> **Passo obrigatório** — sem isso, o login com Google redireciona para `localhost` em produção.

1. Acede a [Google Cloud Console → APIs & Services → Credentials](https://console.cloud.google.com/apis/credentials?project=safety-ai-2026)
2. Clica no teu **OAuth 2.0 Client ID** (o mesmo referenciado em `GOOGLE_CLIENT_CREDENTIALS`)
3. Em **Authorized redirect URIs**, adiciona:
   - `https://safety-ai-2026.web.app`
   - `https://safety-ai-app-710675170484.us-central1.run.app`
4. Clica **Save**

---

## 4. Construir e publicar a imagem Docker

```bash
PROJECT_ID="safety-ai-2026"
REGION="us-central1"
IMAGE="$REGION-docker.pkg.dev/$PROJECT_ID/safety-ai-app/safety-ai-app"

# Criar repositório Artifact Registry (só uma vez)
gcloud artifacts repositories create safety-ai-app \
  --repository-format=docker \
  --location=$REGION \
  --project=$PROJECT_ID 2>/dev/null || true

gcloud auth configure-docker $REGION-docker.pkg.dev --quiet

# Build e push via Cloud Build
gcloud builds submit --tag $IMAGE --project=$PROJECT_ID .
```

---

## 5. Conceder acesso ao Secret Manager para o Cloud Run SA

```bash
PROJECT_ID="safety-ai-2026"
PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format='value(projectNumber)')
SA="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:$SA" \
  --role="roles/secretmanager.secretAccessor" \
  --condition=None
```

---

## 6. Fazer deploy no Cloud Run

```bash
PROJECT_ID="safety-ai-2026"
REGION="us-central1"
IMAGE="$REGION-docker.pkg.dev/$PROJECT_ID/safety-ai-app/safety-ai-app:latest"

gcloud run deploy safety-ai-app \
  --image $IMAGE \
  --platform managed \
  --region $REGION \
  --allow-unauthenticated \
  --memory 4Gi \
  --cpu 2 \
  --min-instances 1 \
  --max-instances 5 \
  --timeout 3600 \
  --set-secrets="GOOGLE_API_KEY=GOOGLE_API_KEY:latest,GOOGLE_SERVICE_ACCOUNT_KEY=GOOGLE_SERVICE_ACCOUNT_KEY:latest,GOOGLE_CLIENT_CREDENTIALS=GOOGLE_CLIENT_CREDENTIALS:latest,GOOGLE_DRIVE_CENTRAL_LIBRARY_FOLDER_ID=GOOGLE_DRIVE_CENTRAL_LIBRARY_FOLDER_ID:latest,GOOGLE_DRIVE_DONATION_FOLDER_ID=GOOGLE_DRIVE_DONATION_FOLDER_ID:latest,ICD_API_CLIENT_ID=ICD_API_CLIENT_ID:latest,ICD_API_CLIENT_SECRET=ICD_API_CLIENT_SECRET:latest,ADZUNA_API_KEY=ADZUNA_API_KEY:latest,ADZUNA_APP_ID=ADZUNA_APP_ID:latest,RECAPTCHA_SECRET_KEY=RECAPTCHA_SECRET_KEY:latest,RECAPTCHA_SITE_KEY=RECAPTCHA_SITE_KEY:latest,ADMIN_EMAILS=ADMIN_EMAILS:latest,OAUTH_REDIRECT_URI=OAUTH_REDIRECT_URI:latest" \
  --project $PROJECT_ID
```

---

## 7. Activar Firebase Hosting (opcional)

```bash
firebase deploy --only hosting --project safety-ai-2026
```

A URL final será: `https://safety-ai-2026.web.app`

---

## Nota sobre o ChromaDB

O Cloud Run usa armazenamento efémero — os dados do ChromaDB **não persistem** entre deployments ou arranques de novas instâncias. Com `--min-instances 1`, uma instância fica sempre activa e os dados persistem durante o funcionamento normal.

Para persistência total, considera migrar o ChromaDB para Cloud Filestore NFS ou uma solução gerida de vector database (ex: Pinecone, Weaviate Cloud).

---

## Corrigir OAuth em deploy existente (login redireccionava para localhost)

Se o serviço já está no ar mas o login do Google redireccionava para `localhost`, faz isto no **Cloud Shell**:

```bash
PROJECT_ID="safety-ai-2026"
REGION="us-central1"

# 1. Criar o secret OAUTH_REDIRECT_URI
echo -n "https://safety-ai-2026.web.app" | \
  gcloud secrets create OAUTH_REDIRECT_URI \
    --data-file=- \
    --project=$PROJECT_ID \
    --replication-policy=automatic 2>/dev/null || \
  echo -n "https://safety-ai-2026.web.app" | \
  gcloud secrets versions add OAUTH_REDIRECT_URI --data-file=- --project=$PROJECT_ID

# 2. Re-deploy o Cloud Run com o novo secret (sem rebuildar a imagem)
IMAGE="$REGION-docker.pkg.dev/$PROJECT_ID/safety-ai-app/safety-ai-app:latest"
gcloud run deploy safety-ai-app \
  --image $IMAGE \
  --region $REGION \
  --set-secrets="GOOGLE_API_KEY=GOOGLE_API_KEY:latest,GOOGLE_SERVICE_ACCOUNT_KEY=GOOGLE_SERVICE_ACCOUNT_KEY:latest,GOOGLE_CLIENT_CREDENTIALS=GOOGLE_CLIENT_CREDENTIALS:latest,GOOGLE_DRIVE_CENTRAL_LIBRARY_FOLDER_ID=GOOGLE_DRIVE_CENTRAL_LIBRARY_FOLDER_ID:latest,GOOGLE_DRIVE_DONATION_FOLDER_ID=GOOGLE_DRIVE_DONATION_FOLDER_ID:latest,ICD_API_CLIENT_ID=ICD_API_CLIENT_ID:latest,ICD_API_CLIENT_SECRET=ICD_API_CLIENT_SECRET:latest,ADZUNA_API_KEY=ADZUNA_API_KEY:latest,ADZUNA_APP_ID=ADZUNA_APP_ID:latest,RECAPTCHA_SECRET_KEY=RECAPTCHA_SECRET_KEY:latest,RECAPTCHA_SITE_KEY=RECAPTCHA_SITE_KEY:latest,ADMIN_EMAILS=ADMIN_EMAILS:latest,OAUTH_REDIRECT_URI=OAUTH_REDIRECT_URI:latest" \
  --project $PROJECT_ID
```

> **Nota**: Também tens de adicionar `https://safety-ai-2026.web.app` como URI de redirecionamento autorizado no Google Cloud Console (ver Secção 3 acima).

---

## Actualizações futuras (nova versão de código)

```bash
PROJECT_ID="safety-ai-2026"
IMAGE="us-central1-docker.pkg.dev/$PROJECT_ID/safety-ai-app/safety-ai-app"

gcloud builds submit --tag $IMAGE --project=$PROJECT_ID .
gcloud run deploy safety-ai-app --image $IMAGE --region us-central1 --project $PROJECT_ID
```
