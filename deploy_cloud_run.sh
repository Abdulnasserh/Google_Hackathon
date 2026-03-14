#!/bin/bash

# Configuration
PROJECT_ID=$(gcloud config get-value project)
SERVICE_NAME="ai-pc-technician-backend"
REGION="us-central1"

echo "🚀 Deploying $SERVICE_NAME to Cloud Run in $REGION..."

# Build and Push using Cloud Build
gcloud builds submit --tag gcr.io/$PROJECT_ID/$SERVICE_NAME

# Deploy to Cloud Run
gcloud run deploy $SERVICE_NAME \
  --image gcr.io/$PROJECT_ID/$SERVICE_NAME \
  --platform managed \
  --region $REGION \
  --allow-unauthenticated \
  --set-env-vars="DEMO_AGENT_MODEL=gemini-2.5-flash-native-audio-preview-12-2025"

echo "✅ Deployment complete!"
