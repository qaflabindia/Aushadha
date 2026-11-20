#!/bin/bash
# Deploy the public Aushadha demo to a Google Compute Engine VM. Safe to re-run: existing
# resources are reused, and a re-run redeploys the latest pushed code.
#
#   deploy/deploy.sh            create/update everything and seed the demo
#   deploy/teardown.sh          delete everything this script created
#
# What it creates (all named aushadha-demo-*), in $PROJECT / $REGION:
#   VPC network + subnet  (its own network, so no default "allow SSH from anywhere" rule)
#   firewall rules        80/443 from anywhere; SSH only through Identity-Aware Proxy
#   static IP             public address; host names use sslip.io (app.<ip>.sslip.io)
#   service account       Vertex AI access for the VM, no key file
#   VM                    e2-standard-4 (4 vCPU, 16 GB), Ubuntu 24.04, 60 GB disk, Shielded VM
#
# Secrets never go through git: backend/.env, the secret vault and its key are copied from
# your main checkout over IAP SSH. Demo logins are saved to deploy/.judge-logins.env (git-ignored).
set -euo pipefail

PROJECT=${PROJECT:-$(gcloud config get-value project 2>/dev/null)}
REGION=${REGION:-asia-south1}
ZONE=${ZONE:-asia-south1-a}
NAME=${NAME:-aushadha-demo}
MACHINE=${MACHINE:-e2-standard-4}
DISK_GB=${DISK_GB:-60}
REPO_URL=${REPO_URL:-https://github.com/qaflabindia/Aushadha.git}
REF=${REF:-main}
SEED_DOCS=${SEED_DOCS:-yes}

DEPLOY_DIR=$(cd "$(dirname "$0")" && pwd)
# Secrets and demo PDFs live in the main checkout (worktrees have no backend/.env)
MAIN_DIR=${MAIN_DIR:-$(cd "$(git -C "$DEPLOY_DIR" rev-parse --path-format=absolute --git-common-dir)/.." && pwd)}
LOGINS_FILE="$DEPLOY_DIR/.judge-logins.env"

NET="$NAME-net"; SUBNET="$NAME-subnet"; IP_NAME="$NAME-ip"; TAG="$NAME"
SA_ID="$NAME-vm"; SA="$SA_ID@$PROJECT.iam.gserviceaccount.com"
G=(gcloud --project "$PROJECT" --quiet)
SSH=("${G[@]}" compute ssh "$NAME" --zone "$ZONE" --tunnel-through-iap)

log() { printf '\n==> %s\n' "$*"; }
exists() { "$@" >/dev/null 2>&1; }

for f in backend/.env backend/.secrets.vault backend/.vault.key .env; do
  [ -f "$MAIN_DIR/$f" ] || { echo "Missing $MAIN_DIR/$f" >&2; exit 1; }
done
ADMIN_EMAIL=${ADMIN_EMAIL:-$(gcloud config get-value account 2>/dev/null)}
[ -n "$PROJECT" ] && [ -n "$ADMIN_EMAIL" ] || { echo "Set PROJECT and ADMIN_EMAIL" >&2; exit 1; }

log "Project $PROJECT, $ZONE, $MACHINE"
"${G[@]}" services enable compute.googleapis.com iap.googleapis.com aiplatform.googleapis.com

log "Network and firewall"
exists "${G[@]}" compute networks describe "$NET" ||
  "${G[@]}" compute networks create "$NET" --subnet-mode custom
exists "${G[@]}" compute networks subnets describe "$SUBNET" --region "$REGION" ||
  "${G[@]}" compute networks subnets create "$SUBNET" --network "$NET" --region "$REGION" --range 10.80.0.0/24
exists "${G[@]}" compute firewall-rules describe "$NAME-allow-web" ||
  "${G[@]}" compute firewall-rules create "$NAME-allow-web" --network "$NET" \
    --allow tcp:80,tcp:443 --source-ranges 0.0.0.0/0 --target-tags "$TAG"
exists "${G[@]}" compute firewall-rules describe "$NAME-allow-iap-ssh" ||
  "${G[@]}" compute firewall-rules create "$NAME-allow-iap-ssh" --network "$NET" \
    --allow tcp:22 --source-ranges 35.235.240.0/20 --target-tags "$TAG"

log "Static IP"
exists "${G[@]}" compute addresses describe "$IP_NAME" --region "$REGION" ||
  "${G[@]}" compute addresses create "$IP_NAME" --region "$REGION"
IP=$("${G[@]}" compute addresses describe "$IP_NAME" --region "$REGION" --format 'value(address)')
APP_HOST="app.${IP//./-}.sslip.io"
API_HOST="api.${IP//./-}.sslip.io"
echo "$IP -> https://$APP_HOST"

log "Service account"
exists "${G[@]}" iam service-accounts describe "$SA" ||
  "${G[@]}" iam service-accounts create "$SA_ID" --display-name "Aushadha demo VM"
for role in roles/aiplatform.user roles/logging.logWriter roles/monitoring.metricWriter; do
  "${G[@]}" projects add-iam-policy-binding "$PROJECT" --member "serviceAccount:$SA" \
    --role "$role" --condition None >/dev/null
done

log "VM"
if ! exists "${G[@]}" compute instances describe "$NAME" --zone "$ZONE"; then
  "${G[@]}" compute instances create "$NAME" --zone "$ZONE" --machine-type "$MACHINE" \
    --subnet "$SUBNET" --address "$IP" --tags "$TAG" \
    --image-family ubuntu-2404-lts-amd64 --image-project ubuntu-os-cloud \
    --boot-disk-size "${DISK_GB}GB" --boot-disk-type pd-balanced \
    --service-account "$SA" --scopes cloud-platform \
    --shielded-secure-boot --shielded-vtpm --shielded-integrity-monitoring \
    --metadata enable-oslogin=TRUE,block-project-ssh-keys=TRUE \
    --metadata-from-file startup-script="$DEPLOY_DIR/vm-startup.sh"
fi

log "Waiting for SSH"
for _ in $(seq 1 30); do
  "${SSH[@]}" --command true >/dev/null 2>&1 && break
  sleep 10
done

log "Copying secrets and demo files (over IAP)"
STAGE=$(mktemp -d); trap 'rm -rf "$STAGE"' EXIT
chmod 700 "$STAGE"
cp "$MAIN_DIR/backend/.env" "$STAGE/backend.env"
cp "$MAIN_DIR/backend/.secrets.vault" "$STAGE/app.vault"
cp "$MAIN_DIR/backend/.vault.key" "$STAGE/app.vault-key"
cp "$MAIN_DIR/.env" "$STAGE/root.env"
cp "$DEPLOY_DIR/remote-setup.sh" "$STAGE/remote-setup.sh"
mkdir "$STAGE/demo_docs"
cp "$MAIN_DIR"/Clinical_Hypertension_Dialogue_Parts/*.pdf "$STAGE/demo_docs/" 2>/dev/null || true
# UI translations: copy the local table instead of translating again
docker exec postgres pg_dump -U aushadha_user -d aushadha --data-only --inserts \
  --on-conflict-do-nothing -t ui_translations > "$STAGE/ui_translations.sql" 2>/dev/null ||
  echo "(local translations not available; skipping)"
REMOTE_DIR="/tmp/aushadha-upload-$RANDOM"
"${SSH[@]}" --command "mkdir -m 700 $REMOTE_DIR"
"${G[@]}" compute scp --zone "$ZONE" --tunnel-through-iap --recurse "$STAGE"/* "$NAME:$REMOTE_DIR/" >/dev/null

log "Configuring and starting the app on the VM"
"${SSH[@]}" --command "sudo APP_HOST='$APP_HOST' API_HOST='$API_HOST' ADMIN_EMAIL='$ADMIN_EMAIL' \
  UPLOAD_DIR='$REMOTE_DIR' REPO_URL='$REPO_URL' REF='$REF' SEED_DOCS='$SEED_DOCS' \
  bash $REMOTE_DIR/remote-setup.sh"

log "Saving demo logins to $LOGINS_FILE"
umask 077
{
  echo "# Aushadha public demo, $(date -u +%Y-%m-%dT%H:%MZ). Do not commit."
  echo "APP_URL=https://$APP_HOST"
  "${SSH[@]}" --command "sudo cat /root/aushadha-logins.txt"
} > "$LOGINS_FILE"
echo "$(grep -c '^LOGIN ' "$LOGINS_FILE") logins saved"

cat <<EOF

App:  https://$APP_HOST
API:  https://$API_HOST
Logins: $LOGINS_FILE
Demo-document extraction log:
  ${SSH[*]} --command 'sudo tail -f /var/log/aushadha-seed-docs.log'
Google sign-in: add https://$APP_HOST to the OAuth client's Authorized JavaScript origins.
Delete everything: deploy/teardown.sh
EOF
