#!/usr/bin/env bash
# Run this ON THE VM after SCPing the lauren-nestor project there and
# dropping a filled-in .env at /opt/lauren/.env and the Drive service
# account key at /opt/lauren/gdrive-service-account.json.
set -euo pipefail

sudo apt-get update
sudo apt-get install -y python3-venv python3-pip git

# --- Ollama ---
curl -fsSL https://ollama.com/install.sh | sh
sudo systemctl enable --now ollama
ollama pull qwen2.5:14b

# --- Lauren user + workspace ---
sudo useradd -r -m -d /opt/lauren -s /usr/sbin/nologin lauren || true
sudo mkdir -p /opt/lauren/workspace
sudo chown -R lauren:lauren /opt/lauren

# --- Python env ---
cd /opt/lauren
sudo -u lauren python3 -m venv venv
sudo -u lauren ./venv/bin/pip install -r requirements.txt

# --- systemd services ---
sudo cp deploy/lauren.service /etc/systemd/system/lauren.service
sudo cp deploy/lauren-dashboard.service /etc/systemd/system/lauren-dashboard.service
sudo systemctl daemon-reload
sudo systemctl enable lauren lauren-dashboard
sudo systemctl restart lauren lauren-dashboard

echo "Lauren is up. Follow logs with: journalctl -u lauren -f"
echo "Or: tail -f /opt/lauren/experiment_log.txt"
echo "Dashboard listening on port 8080 (see deploy/dashboard for how to view it)"
