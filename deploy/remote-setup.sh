#!/bin/bash
# Runs ON THE VM as root (deploy.sh calls it over IAP SSH). Safe to re-run.
#
# Needs these environment variables:
#   APP_HOST, API_HOST  public host names (e.g. app.34-1-2-3.sslip.io)
#   ADMIN_EMAIL         Google account that becomes Admin
#   UPLOAD_DIR          folder holding the files deploy.sh copied:
#                       backend.env, app.vault, app.vault-key, root.env,
#                       ui_translations.sql, demo_docs/*.pdf
#   REPO_URL, REF       git repository and branch/commit to deploy
#   SEED_DOCS           "yes" to upload and extract the demo PDFs (runs in the background)
set -euo pipefail

: "${APP_HOST:?}" "${API_HOST:?}" "${ADMIN_EMAIL:?}" "${UPLOAD_DIR:?}" "${REPO_URL:?}" "${REF:?}"
APP_DIR=/opt/aushadha
COMPOSE=(docker compose -f docker-compose.yml -f deploy/docker-compose.prod.yml)

log() { printf '\n==> %s\n' "$*"; }

log "Waiting for Docker"
for _ in $(seq 1 90); do
  docker compose version >/dev/null 2>&1 && break
  sleep 5
done
docker compose version >/dev/null

log "Fetching code ($REF)"
if [ ! -d "$APP_DIR/.git" ]; then
  git clone --quiet "$REPO_URL" "$APP_DIR"
fi
cd "$APP_DIR"
git fetch --quiet origin
git checkout --quiet --force "$REF"
git reset --quiet --hard "origin/$REF" 2>/dev/null || true
git log -1 --format='Deploying %h %s'

log "Installing secrets"
install -m 600 "$UPLOAD_DIR/backend.env" backend/.env
install -m 600 "$UPLOAD_DIR/app.vault" backend/.secrets.vault
install -m 600 "$UPLOAD_DIR/app.vault-key" backend/.vault.key
mkdir -p deploy/demo_docs
cp "$UPLOAD_DIR"/demo_docs/*.pdf deploy/demo_docs/ 2>/dev/null || true

# Database passwords are generated once on this VM and kept, because the database volumes
# are initialised with them.
STATE=/root/aushadha-generated.env
if [ ! -f "$STATE" ]; then
  umask 077
  {
    echo "NEO4J_PASSWORD=$(openssl rand -hex 24)"
    echo "POSTGRES_PASSWORD=$(openssl rand -hex 24)"
    echo "SESSION_SECRET=$(openssl rand -hex 32)"
  } > "$STATE"
fi
set -a; . "$STATE"; set +a

from_root_env() { grep -E "^$1=" "$UPLOAD_DIR/root.env" | tail -1 | cut -d= -f2- || true; }
umask 077
cat > .env <<EOF
APP_HOST=$APP_HOST
API_HOST=$API_HOST
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=$NEO4J_PASSWORD
POSTGRES_DB=aushadha
POSTGRES_USER=aushadha_user
POSTGRES_PASSWORD=$POSTGRES_PASSWORD
SESSION_SECRET=$SESSION_SECRET
VITE_GOOGLE_CLIENT_ID=$(from_root_env VITE_GOOGLE_CLIENT_ID)
GCP_PROJECT_ID=$(from_root_env GCP_PROJECT_ID)
GCP_REGION=$(from_root_env GCP_REGION)
EOF
umask 022

# backend/.env is loaded with override=True, so it must carry the same values
python3 - <<'PY'
import os, re
path = "backend/.env"
want = {
    "NEO4J_URI": "bolt://neo4j:7687", "NEO4J_USERNAME": "neo4j",
    "NEO4J_PASSWORD": os.environ["NEO4J_PASSWORD"], "NEO4J_DATABASE": "neo4j",
    "POSTGRES_HOST": "postgres", "POSTGRES_PORT": "5432", "POSTGRES_DB": "aushadha",
    "POSTGRES_USER": "aushadha_user", "POSTGRES_PASSWORD": os.environ["POSTGRES_PASSWORD"],
}
lines = open(path).read().splitlines()
seen = set()
for i, line in enumerate(lines):
    m = re.match(r"^([A-Z0-9_]+)=", line)
    if m and m.group(1) in want:
        lines[i] = f"{m.group(1)}={want[m.group(1)]}"
        seen.add(m.group(1))
lines += [f"{k}={v}" for k, v in want.items() if k not in seen]
open(path, "w").write("\n".join(lines) + "\n")
PY

log "Building images"
"${COMPOSE[@]}" build --quiet

log "Writing database settings into the vault copy"
"${COMPOSE[@]}" run --rm --no-deps -T -e NEO4J_PASSWORD -e POSTGRES_PASSWORD backend python - <<'PY'
import os
from src.shared.secret_vault import set_secret
for k, v in {
    "NEO4J_URI": "bolt://neo4j:7687", "NEO4J_USERNAME": "neo4j",
    "NEO4J_PASSWORD": os.environ["NEO4J_PASSWORD"], "NEO4J_DATABASE": "neo4j",
    "POSTGRES_HOST": "postgres", "POSTGRES_PORT": "5432", "POSTGRES_DB": "aushadha",
    "POSTGRES_USER": "aushadha_user", "POSTGRES_PASSWORD": os.environ["POSTGRES_PASSWORD"],
}.items():
    set_secret(k, v)
print("vault updated")
PY

log "Starting the stack"
"${COMPOSE[@]}" up -d --remove-orphans

log "Waiting for the backend"
for _ in $(seq 1 60); do
  if docker exec backend python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health', timeout=3)" 2>/dev/null; then
    echo "backend healthy"; break
  fi
  sleep 5
done

log "Seeding accounts"
docker exec -i -w /code -e ADMIN_EMAIL backend python - < deploy/seed_demo.py > /root/aushadha-logins.txt
chmod 600 /root/aushadha-logins.txt
grep -c '^LOGIN ' /root/aushadha-logins.txt | xargs -I{} echo "{} demo logins created"

if [ -s "$UPLOAD_DIR/ui_translations.sql" ]; then
  log "Loading UI translations"
  docker exec -i postgres psql -q -v ON_ERROR_STOP=1 -U aushadha_user -d aushadha < "$UPLOAD_DIR/ui_translations.sql" >/dev/null
  docker exec postgres psql -At -U aushadha_user -d aushadha -c "select count(*) || ' UI strings' from ui_translations"
fi

if [ "${SEED_DOCS:-no}" = "yes" ]; then
  log "Extracting demo documents in the background (log: /var/log/aushadha-seed-docs.log)"
  setsid nohup bash -c "docker exec -i -w /code -e ADMIN_EMAIL backend python - < deploy/seed_demo_docs.py" \
    > /var/log/aushadha-seed-docs.log 2>&1 < /dev/null &
fi

# The uploaded secret copies are installed; remove the staging folder
rm -rf "$UPLOAD_DIR"
log "Done: https://$APP_HOST"
