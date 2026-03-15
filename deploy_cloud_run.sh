#!/bin/bash

# Configuration
PROJECT_ID="gemini-live-hackathon-490213"
SERVICE_NAME="google-hackathon"
REGION="europe-west1"

echo "🚀 Deploying $SERVICE_NAME to Cloud Run in $REGION (Integrated Frontend + Backend)..."

# Build and Push using Cloud Build (this will use the new Multi-stage Dockerfile)
gcloud builds submit --tag europe-west1-docker.pkg.dev/$PROJECT_ID/cloud-run-source-deploy/google_hackathon/google-hackathon

# Deploy to Cloud Run
# CRITICAL: We use --max-instances 1 because this app uses in-memory state for WebSocket routing.
# We also set a long timeout to prevent Cloud Run from killing the bidi-streaming connection.
gcloud run deploy $SERVICE_NAME \
  --image europe-west1-docker.pkg.dev/$PROJECT_ID/cloud-run-source-deploy/google_hackathon/google-hackathon \
  --platform managed \
  --region $REGION \
  --allow-unauthenticated \
  --max-instances 1 \
  --min-instances 1 \
  --timeout 600 \
  --cpu-boost \
  --memory 2Gi

echo "✅ Deployment complete!"
