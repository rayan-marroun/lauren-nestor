#!/usr/bin/env bash
# Run this in Cloud Shell, AFTER 01_setup_infra.sh and after you've:
#   - filled in .env (cp .env.example .env, then nano .env)
#   - confirmed gdrive-service-account.json exists in this directory
# Creates the VM, ships the code + secrets to it, and starts Lauren.
set -euo pipefail

PROJECT_ID=$(gcloud config get-value project 2>/dev/null)
VM_NAME="lauren-nestor-vm"
DEFAULT_ZONE="us-central1-a"

if [ -z "$PROJECT_ID" ]; then
  echo "No active project set. Run: gcloud config set project YOUR_PROJECT_ID"
  exit 1
fi

if [ ! -f .env ]; then
  echo "No .env found. Run: cp .env.example .env && nano .env -- fill it in first."
  exit 1
fi
if [ ! -f gdrive-service-account.json ]; then
  echo "gdrive-service-account.json missing -- did 01_setup_infra.sh run?"
  exit 1
fi

EXISTING_ZONE=$(gcloud compute instances list --filter="name=${VM_NAME}" --format='value(zone.basename())' 2>/dev/null || true)

if [ -n "$EXISTING_ZONE" ]; then
  ZONE="$EXISTING_ZONE"
  echo "== Found existing instance '$VM_NAME' in zone $ZONE, skipping creation =="
else
  ZONE="$DEFAULT_ZONE"
  echo "== Creating the VM (spot instance) in $ZONE =="
  gcloud compute instances create "$VM_NAME" \
    --project="$PROJECT_ID" \
    --zone="$ZONE" \
    --machine-type=n2-standard-8 \
    --image-family=ubuntu-2204-lts \
    --image-project=ubuntu-os-cloud \
    --boot-disk-size=100GB \
    --boot-disk-type=pd-balanced \
    --provisioning-model=SPOT \
    --instance-termination-action=STOP \
    --scopes=cloud-platform
fi

echo "== Waiting for SSH to come up =="
for i in $(seq 1 20); do
  if gcloud compute ssh "$VM_NAME" --zone="$ZONE" --tunnel-through-iap --command="echo ready" 2>/dev/null; then
    break
  fi
  echo "not ready yet, retrying in 15s ($i/20)..."
  sleep 15
done

echo "== Copying the project (incl. .env and the Drive key) to the VM =="
gcloud compute scp --recurse . "${VM_NAME}:~/lauren-nestor" --zone="$ZONE" --tunnel-through-iap

echo "== Installing + starting Lauren on the VM =="
gcloud compute ssh "$VM_NAME" --zone="$ZONE" --tunnel-through-iap --command="
  sudo mkdir -p /opt/lauren &&
  sudo rsync -a ~/lauren-nestor/ /opt/lauren/ &&
  cd /opt/lauren &&
  chmod +x deploy/startup-script.sh &&
  bash deploy/startup-script.sh
"

echo ""
echo "Lauren is running. To watch her:"
echo "  gcloud compute ssh $VM_NAME --zone=$ZONE --tunnel-through-iap --command='journalctl -u lauren -f'"
