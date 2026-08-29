#!/usr/bin/env bash
# Run this in Cloud Shell (console.cloud.google.com -> ">_" icon), after
# `git clone https://github.com/rayan-marroun/lauren-nestor.git && cd lauren-nestor`
#
# Sets up everything except the VM itself: APIs, Firestore, the approval
# service, the Drive service account, and the budget hard-stop.
set -euo pipefail

PROJECT_ID=$(gcloud config get-value project 2>/dev/null)
REGION="us-central1"
BUDGET_EUR="235"

if [ -z "$PROJECT_ID" ]; then
  echo "No active project set. Run: gcloud config set project YOUR_PROJECT_ID"
  exit 1
fi
echo "Using project: $PROJECT_ID"

echo "== Enabling APIs =="
gcloud services enable \
  compute.googleapis.com \
  run.googleapis.com \
  cloudfunctions.googleapis.com \
  cloudbuild.googleapis.com \
  firestore.googleapis.com \
  drive.googleapis.com \
  billingbudgets.googleapis.com \
  pubsub.googleapis.com \
  artifactregistry.googleapis.com \
  iam.googleapis.com \
  iap.googleapis.com

PROJECT_NUMBER=$(gcloud projects describe "$PROJECT_ID" --format='value(projectNumber)')
DEFAULT_SA="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"

echo "== Firestore (for the approval service's state) =="
gcloud firestore databases create --location="$REGION" --type=firestore-native || \
  echo "(already exists, skipping)"

echo "== Deploying the approval service to Cloud Run =="
gcloud run deploy lauren-approval \
  --source=deploy/approval_service \
  --region="$REGION" \
  --allow-unauthenticated \
  --quiet

gcloud projects add-iam-policy-binding "$PROJECT_ID" \
  --member="serviceAccount:${DEFAULT_SA}" \
  --role="roles/datastore.user" --quiet

APPROVAL_URL=$(gcloud run services describe lauren-approval --region="$REGION" --format='value(status.url)')

echo "== Pub/Sub topic + budget hard-stop Cloud Function =="
gcloud pubsub topics create lauren-budget-alerts || echo "(already exists, skipping)"

gcloud functions deploy lauren-budget-stop \
  --gen2 \
  --runtime=python312 \
  --region="$REGION" \
  --source=deploy/budget_alert_function \
  --entry-point=stop_vm_on_budget_alert \
  --trigger-topic=lauren-budget-alerts \
  --set-env-vars="GCP_PROJECT_ID=${PROJECT_ID},GCP_ZONE=${REGION}-a,GCP_INSTANCE_NAME=lauren-nestor-vm" \
  --quiet

gcloud projects add-iam-policy-binding "$PROJECT_ID" \
  --member="serviceAccount:${DEFAULT_SA}" \
  --role="roles/compute.instanceAdmin.v1" --quiet

BILLING_ACCOUNT=$(gcloud billing accounts list --format='value(ACCOUNT_ID)' --limit=1)
gcloud billing budgets create \
  --billing-account="$BILLING_ACCOUNT" \
  --display-name="Lauren Nestor hard cap" \
  --budget-amount="${BUDGET_EUR}EUR" \
  --threshold-rule=percent=0.9 \
  --all-updates-rule-pubsub-topic="projects/${PROJECT_ID}/topics/lauren-budget-alerts"

echo ""
echo "=================================================================="
echo "DONE. Save these -- you'll need them for the .env file and Drive:"
echo "  Approval service URL:  $APPROVAL_URL"
echo "  VM's service account:  $DEFAULT_SA"
echo "  (this is the VM's own identity -- no key file needed, Lauren"
echo "   authenticates as herself automatically once she's running on it)"
echo "=================================================================="
echo ""
echo "Manual steps now (can't be scripted):"
echo "  1. In Google Drive, create a folder e.g. 'Lauren Nestor'."
echo "  2. Share it with $DEFAULT_SA as Editor."
echo "  3. Copy the folder ID from its URL (the part after /folders/)."
echo "  4. Make Lauren's own Gmail account, turn on 2-Step Verification,"
echo "     then generate an App Password at myaccount.google.com/apppasswords."
