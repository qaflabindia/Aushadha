#!/bin/bash
# Delete everything deploy/deploy.sh created: VM (and its disk with all demo data),
# static IP, firewall rules, network, and the service account with its role bindings.
# Asks for confirmation unless run with --yes.
set -uo pipefail

PROJECT=${PROJECT:-$(gcloud config get-value project 2>/dev/null)}
REGION=${REGION:-asia-southeast1}
ZONE=${ZONE:-asia-southeast1-b}
NAME=${NAME:-aushadha-demo}
SA="$NAME-vm@$PROJECT.iam.gserviceaccount.com"
G=(gcloud --project "$PROJECT" --quiet)

cat <<EOF
This permanently deletes, in project $PROJECT:
  VM $NAME ($ZONE) and its disk, including all demo data
  static IP $NAME-ip, firewall rules $NAME-allow-web and $NAME-allow-iap-ssh
  network $NAME-net, subnet $NAME-subnet
  service account $SA and its project role bindings
EOF
if [ "${1:-}" != "--yes" ]; then
  read -r -p "Type the name '$NAME' to confirm: " answer
  [ "$answer" = "$NAME" ] || { echo "Cancelled."; exit 1; }
fi

step() { printf '\n==> %s\n' "$1"; shift; "$@" || echo "   (not found or already deleted)"; }

step "VM" "${G[@]}" compute instances delete "$NAME" --zone "$ZONE" --delete-disks all
step "Static IP" "${G[@]}" compute addresses delete "$NAME-ip" --region "$REGION"
step "Firewall (web)" "${G[@]}" compute firewall-rules delete "$NAME-allow-web"
step "Firewall (IAP SSH)" "${G[@]}" compute firewall-rules delete "$NAME-allow-iap-ssh"
step "Subnet" "${G[@]}" compute networks subnets delete "$NAME-subnet" --region "$REGION"
step "Network" "${G[@]}" compute networks delete "$NAME-net"
for role in roles/aiplatform.user roles/logging.logWriter roles/monitoring.metricWriter; do
  step "Role binding $role" "${G[@]}" projects remove-iam-policy-binding "$PROJECT" \
    --member "serviceAccount:$SA" --role "$role" --condition None
done
step "Service account" "${G[@]}" iam service-accounts delete "$SA"

LOGINS="$(cd "$(dirname "$0")" && pwd)/.judge-logins.env"
[ -f "$LOGINS" ] && rm -f "$LOGINS" && echo "Removed $LOGINS"
echo "Teardown finished."
