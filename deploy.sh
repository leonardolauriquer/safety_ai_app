#!/bin/bash
set -e

PROJECT_ID="safety-ai-2026"
REGION="us-central1"
SERVICE="safety-ai-app"
IMAGE="us-central1-docker.pkg.dev/$PROJECT_ID/safety-ai-app/$SERVICE"

echo "=== SafetyAI — Deploy Firebase Hosting + Cloud Run ==="
echo ""

command -v gcloud >/dev/null || { echo "ERRO: gcloud nao encontrado. Instala em https://cloud.google.com/sdk/docs/install"; exit 1; }
command -v firebase >/dev/null || { echo "ERRO: firebase-tools nao encontrado. Corre: npm install -g firebase-tools"; exit 1; }
command -v docker >/dev/null || { echo "ERRO: docker nao encontrado. Instala em https://docs.docker.com/get-docker/"; exit 1; }

echo "[1/6] Autenticacao no Google Cloud..."
gcloud auth login --no-launch-browser
gcloud config set project $PROJECT_ID

echo ""
echo "[2/6] Activar APIs necessarias..."
gcloud services enable \
  run.googleapis.com \
  containerregistry.googleapis.com \
  cloudbuild.googleapis.com \
  secretmanager.googleapis.com \
  --project=$PROJECT_ID

echo ""
echo "[3/6] Criar secrets no Secret Manager..."
echo "      (sera pedido o valor de cada secret — copia do painel do Replit)"

create_secret() {
  local NAME=$1
  if gcloud secrets describe $NAME --project=$PROJECT_ID &>/dev/null; then
    echo "  [ja existe] $NAME — a saltar"
  else
    echo -n "  Valor para $NAME: "
    read -rs VALUE
    echo ""
    echo -n "$VALUE" | gcloud secrets create $NAME --data-file=- --project=$PROJECT_ID
    echo "  [criado] $NAME"
  fi
}

create_secret GOOGLE_API_KEY
create_secret GOOGLE_SERVICE_ACCOUNT_KEY
create_secret GOOGLE_CLIENT_CREDENTIALS
create_secret GOOGLE_DRIVE_CENTRAL_LIBRARY_FOLDER_ID
create_secret GOOGLE_DRIVE_DONATION_FOLDER_ID
create_secret ADZUNA_API_KEY
create_secret ADZUNA_APP_ID
create_secret ICD_API_CLIENT_ID
create_secret ICD_API_CLIENT_SECRET
create_secret RECAPTCHA_SECRET_KEY
create_secret RECAPTCHA_SITE_KEY

if ! gcloud secrets describe ADMIN_EMAILS --project=$PROJECT_ID &>/dev/null; then
  echo -n "leolr.trab@gmail.com" | gcloud secrets create ADMIN_EMAILS --data-file=- --project=$PROJECT_ID
fi

echo ""
echo "[4/6] Build e push da imagem Docker..."
gcloud auth configure-docker --quiet
docker build -t $IMAGE:latest .
docker push $IMAGE:latest
echo "  Imagem publicada: $IMAGE:latest"

echo ""
echo "[5/6] Deploy no Cloud Run..."
gcloud run deploy $SERVICE \
  --image $IMAGE:latest \
  --platform managed \
  --region $REGION \
  --allow-unauthenticated \
  --port 8080 \
  --memory 4Gi \
  --cpu 2 \
  --min-instances 1 \
  --max-instances 5 \
  --timeout 3600 \
  --set-secrets="\
GOOGLE_API_KEY=GOOGLE_API_KEY:latest,\
GOOGLE_SERVICE_ACCOUNT_KEY=GOOGLE_SERVICE_ACCOUNT_KEY:latest,\
GOOGLE_CLIENT_CREDENTIALS=GOOGLE_CLIENT_CREDENTIALS:latest,\
GOOGLE_DRIVE_CENTRAL_LIBRARY_FOLDER_ID=GOOGLE_DRIVE_CENTRAL_LIBRARY_FOLDER_ID:latest,\
GOOGLE_DRIVE_DONATION_FOLDER_ID=GOOGLE_DRIVE_DONATION_FOLDER_ID:latest,\
ADZUNA_API_KEY=ADZUNA_API_KEY:latest,\
ADZUNA_APP_ID=ADZUNA_APP_ID:latest,\
ICD_API_CLIENT_ID=ICD_API_CLIENT_ID:latest,\
ICD_API_CLIENT_SECRET=ICD_API_CLIENT_SECRET:latest,\
RECAPTCHA_SECRET_KEY=RECAPTCHA_SECRET_KEY:latest,\
RECAPTCHA_SITE_KEY=RECAPTCHA_SITE_KEY:latest,\
ADMIN_EMAILS=ADMIN_EMAILS:latest" \
  --project $PROJECT_ID

CLOUD_RUN_URL=$(gcloud run services describe $SERVICE --region $REGION --project $PROJECT_ID --format="value(status.url)")
echo "  Cloud Run URL: $CLOUD_RUN_URL"

echo ""
echo "[6/6] Deploy Firebase Hosting..."
firebase login
firebase deploy --only hosting --project $PROJECT_ID

echo ""
echo "============================================"
echo " Deploy concluido!"
echo " URL: https://$PROJECT_ID.web.app"
echo "============================================"
