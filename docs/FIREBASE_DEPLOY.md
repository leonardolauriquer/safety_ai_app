# Deploy: Firebase Hosting + Cloud Run

## Pré-requisitos

- Conta Google Cloud com billing activado
- [Firebase CLI](https://firebase.google.com/docs/cli) instalado (`npm install -g firebase-tools`)
- [gcloud CLI](https://cloud.google.com/sdk/docs/install) instalado e autenticado
- Projecto Firebase: `safetyai-472110`

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
PROJECT_ID="safetyai-472110"

gcloud services enable secretmanager.googleapis.com --project=$PROJECT_ID

# Criar cada secret (substituir VALUE pelo valor real)
for SECRET in GOOGLE_API_KEY GOOGLE_SERVICE_ACCOUNT_KEY GOOGLE_CLIENT_CREDENTIALS \
  GOOGLE_DRIVE_CENTRAL_LIBRARY_FOLDER_ID GOOGLE_DRIVE_DONATION_FOLDER_ID \
  ICD_API_CLIENT_ID ICD_API_CLIENT_SECRET ADZUNA_API_KEY ADZUNA_APP_ID \
  RECAPTCHA_SECRET_KEY RECAPTCHA_SITE_KEY ADMIN_EMAILS; do
  printf "➤ $SECRET: "; read -r VALUE
  gcloud secrets create "$SECRET" --project="$PROJECT_ID" --replication-policy="automatic" 2>/dev/null || true
  printf '%s' "$VALUE" | gcloud secrets versions add "$SECRET" --data-file=- --project="$PROJECT_ID"
  echo "  ✓ $SECRET"
done
```

---

## 3. Construir e publicar a imagem Docker

```bash
PROJECT_ID="safetyai-472110"
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

## 4. Conceder acesso ao Secret Manager para o Cloud Run SA

```bash
PROJECT_ID="safetyai-472110"
PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format='value(projectNumber)')
SA="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:$SA" \
  --role="roles/secretmanager.secretAccessor" \
  --condition=None
```

---

## 5. Fazer deploy no Cloud Run

```bash
PROJECT_ID="safetyai-472110"
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
  --set-secrets="GOOGLE_API_KEY=GOOGLE_API_KEY:latest,GOOGLE_SERVICE_ACCOUNT_KEY=GOOGLE_SERVICE_ACCOUNT_KEY:latest,GOOGLE_CLIENT_CREDENTIALS=GOOGLE_CLIENT_CREDENTIALS:latest,GOOGLE_DRIVE_CENTRAL_LIBRARY_FOLDER_ID=GOOGLE_DRIVE_CENTRAL_LIBRARY_FOLDER_ID:latest,GOOGLE_DRIVE_DONATION_FOLDER_ID=GOOGLE_DRIVE_DONATION_FOLDER_ID:latest,ICD_API_CLIENT_ID=ICD_API_CLIENT_ID:latest,ICD_API_CLIENT_SECRET=ICD_API_CLIENT_SECRET:latest,ADZUNA_API_KEY=ADZUNA_API_KEY:latest,ADZUNA_APP_ID=ADZUNA_APP_ID:latest,RECAPTCHA_SECRET_KEY=RECAPTCHA_SECRET_KEY:latest,RECAPTCHA_SITE_KEY=RECAPTCHA_SITE_KEY:latest,ADMIN_EMAILS=ADMIN_EMAILS:latest" \
  --project $PROJECT_ID
```

---

## 6. Activar Firebase Hosting (opcional)

```bash
firebase deploy --only hosting --project safetyai-472110
```

A URL final será: `https://safetyai-472110.web.app`

---

## Nota sobre o ChromaDB

O Cloud Run usa armazenamento efémero — os dados do ChromaDB **não persistem** entre deployments ou arranques de novas instâncias. Com `--min-instances 1`, uma instância fica sempre activa e os dados persistem durante o funcionamento normal.

Para persistência total, considera migrar o ChromaDB para Cloud Filestore NFS ou uma solução gerida de vector database (ex: Pinecone, Weaviate Cloud).

---

## Actualizações futuras

```bash
PROJECT_ID="safetyai-472110"
IMAGE="us-central1-docker.pkg.dev/$PROJECT_ID/safety-ai-app/safety-ai-app"

gcloud builds submit --tag $IMAGE --project=$PROJECT_ID .
gcloud run deploy safety-ai-app --image $IMAGE --region us-central1 --project $PROJECT_ID
```
