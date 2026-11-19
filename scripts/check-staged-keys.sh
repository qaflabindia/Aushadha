#!/bin/sh
# Pre-commit guard: refuse to commit private keys, credential files or API keys.
# Runs from the husky pre-commit hook. Checks only what is staged.

status=0
staged=$(git diff --cached --name-only --diff-filter=ACMR)
[ -z "$staged" ] && exit 0

# 1. File names that must never be committed.
blocked_names=$(printf '%s\n' "$staged" | grep -iE \
  '(^|/)(\.env|\.env\..*|.*\.env|.*\.pem|.*\.key|.*\.p12|.*\.pfx|id_rsa|id_ed25519|\.vault\.key|.*\.vault|credentials\.json|token\.json|secrets\.(json|ya?ml)|client_secret_.*\.json|.*service-account.*\.json|.*sa-key.*\.json|.*-credentials\.json)$' \
  | grep -viE '(^|/)(example\.env|\.env\.example)$')
if [ -n "$blocked_names" ]; then
  echo "BLOCKED: these files hold keys or credentials and must not be committed:" >&2
  printf '%s\n' "$blocked_names" | sed 's/^/  /' >&2
  status=1
fi

# 2. Secrets pasted into any staged text file.
pattern='-----BEGIN ([A-Z]+ )?PRIVATE KEY-----|AIza[0-9A-Za-z_-]{35}|sk-(proj-|ant-)?[A-Za-z0-9_-]{32,}|AKIA[0-9A-Z]{16}|gh[pousr]_[A-Za-z0-9]{36}|xox[baprs]-[A-Za-z0-9-]{10,}'
hits=$(printf '%s\n' "$staged" | while IFS= read -r f; do
  [ -n "$f" ] || continue
  [ "$f" = "scripts/check-staged-keys.sh" ] && continue
  git show ":$f" 2>/dev/null | grep -IqE -e "$pattern" && printf '%s\n' "$f"
done)
if [ -n "$hits" ]; then
  echo "BLOCKED: these files contain what looks like a private key or API key:" >&2
  printf '%s\n' "$hits" | sed 's/^/  /' >&2
  status=1
fi

if [ $status -ne 0 ]; then
  echo "Keep secrets in ignored files (e.g. backend/.env) and unstage them: git restore --staged <file>" >&2
fi
exit $status
