#!/usr/bin/env python3
"""
migrate_to_vault.py — One-shot migration from Fernet vault + .env to AES-256-GCM vault
========================================================================================

What this script does
---------------------
  1. Reads all non-empty key=value pairs from a .env file.
  2. Optionally reads secrets from the old Fernet vault (.secrets.json.enc),
     if it still exists and its key file (.vault.key) is present.
  3. Writes every resolved secret into the new AES-256-GCM vault.
  4. Prints a checklist of required follow-up actions.

Run once from the backend/ directory:
  cd backend
  python migrate_to_vault.py

Or point it at specific files:
  python migrate_to_vault.py --env ../.env --fernet-vault .secrets.json.enc

The script never deletes or modifies the source files — it is purely additive.
Follow the printed instructions to strip values from .env and revoke exposed keys.
"""

import argparse
import getpass
import json
import logging
import os
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Bootstrap sys.path so imports resolve from backend/
# ---------------------------------------------------------------------------
_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))

logging.basicConfig(level=logging.WARNING, format="%(levelname)s  %(message)s")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _require_new_password() -> str:
    """Prompt for and confirm the master password for the new AES-256-GCM vault."""
    # If already set via environment, honour it (CI / automated use)
    if os.environ.get("VAULT_MASTER_PASSWORD"):
        print("  Using VAULT_MASTER_PASSWORD from environment.")
        return os.environ["VAULT_MASTER_PASSWORD"]

    print(
        "\n  You are creating a new AES-256-GCM vault.\n"
        "  Choose a strong master password (≥ 16 chars recommended).\n"
        "  Store it in a password manager — it cannot be recovered.\n"
    )
    while True:
        pwd     = getpass.getpass("  New vault master password : ")
        confirm = getpass.getpass("  Confirm                   : ")
        if pwd != confirm:
            print("  ERROR: passwords do not match — try again.\n")
            continue
        if len(pwd) < 12:
            print("  ERROR: must be at least 12 characters — try again.\n")
            continue
        return pwd


# ---------------------------------------------------------------------------
# Source readers
# ---------------------------------------------------------------------------

def _read_env_file(env_path: Path) -> dict:
    """
    Parse a .env file and return {key: value} for every non-empty entry.
    Strips inline comments, quotes, and placeholder values.
    """
    PLACEHOLDER_SIGNALS = (
        "your_", "placeholder", "changeme", "xxx", "todo",
        "example", "<", ">", "insert", "fill",
    )
    result: dict = {}

    if not env_path.exists():
        print(f"  WARN: .env file not found at {env_path} — skipping.")
        return result

    with open(env_path, encoding="utf-8") as fh:
        for raw in fh:
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                continue

            key, _, value = line.partition("=")
            key   = key.strip()
            value = value.strip().strip('"').strip("'")

            # Remove trailing inline comment (e.g.  KEY=value  #comment)
            if " #" in value:
                value = value[:value.index(" #")].strip()

            if not value or value.startswith("#"):
                continue

            lower_val = value.lower()
            if any(sig in lower_val for sig in PLACEHOLDER_SIGNALS):
                continue

            result[key] = value

    return result


def _read_fernet_vault(vault_path: Path, key_path: Path) -> dict:
    """
    Attempt to decrypt the old Fernet vault and return its contents.
    Returns an empty dict if either file is missing or decryption fails.
    """
    if not vault_path.exists():
        print(f"  INFO: No old Fernet vault found at {vault_path} — skipping.")
        return {}

    if not key_path.exists():
        print(f"  WARN: Old vault found but key file missing at {key_path} — skipping Fernet import.")
        return {}

    try:
        from cryptography.fernet import Fernet

        key       = key_path.read_bytes()
        fernet    = Fernet(key)
        encrypted = vault_path.read_bytes()
        if not encrypted:
            return {}
        decrypted = fernet.decrypt(encrypted)
        data      = json.loads(decrypted)
        print(f"  Read {len(data)} secret(s) from old Fernet vault.")
        return data
    except Exception as exc:
        print(f"  WARN: Could not decrypt old Fernet vault: {exc}")
        return {}


# ---------------------------------------------------------------------------
# Main migration logic
# ---------------------------------------------------------------------------

SENSITIVE_PATTERNS = ("KEY", "PASSWORD", "SECRET", "TOKEN", "PASS", "CREDENTIAL")

# Secrets known to be exposed in git history — highlighted for immediate rotation
KNOWN_EXPOSED = {
    "SARVAM_API_KEY",
    "NEO4J_PASSWORD",
    "LOCAL_AUTH_PASSWORD",
    "POSTGRES_PASSWORD",
}


def run_migration(
    env_path: Path,
    fernet_vault_path: Path,
    fernet_key_path: Path,
    new_vault_path: Path,
    new_key_file_path: Path,
) -> None:

    # 1. Collect secrets from all sources
    env_secrets     = _read_env_file(env_path)
    fernet_secrets  = _read_fernet_vault(fernet_vault_path, fernet_key_path)

    # env takes precedence over the old vault (it is more current)
    combined = {**fernet_secrets, **env_secrets}

    if not combined:
        print("\n  No secrets found to migrate.  Exiting.")
        return

    print(f"\n  Found {len(combined)} secret(s) to migrate.\n")

    # 2. Set up the new vault
    os.environ.setdefault("VAULT_FILE_PATH", str(new_vault_path))
    os.environ.setdefault("VAULT_KEY_PATH",  str(new_key_file_path))

    new_pwd = _require_new_password()
    os.environ["VAULT_MASTER_PASSWORD"] = new_pwd

    from src.shared.secret_vault import initialize_vault, set_secret

    initialize_vault()

    # 3. Write every secret
    migrated        : list = []
    already_exposed : list = []

    for key, value in combined.items():
        set_secret(key, value)
        is_sensitive  = any(p in key.upper() for p in SENSITIVE_PATTERNS)
        display_value = "***" if is_sensitive else (value[:40] + "…" if len(value) > 40 else value)
        migrated.append((key, display_value))
        if key in KNOWN_EXPOSED:
            already_exposed.append(key)

    # 4. Summary
    print(f"  Migrated {len(migrated)} secret(s) into {new_vault_path}:\n")
    col = max(len(k) for k, _ in migrated) + 2
    for k, v in sorted(migrated):
        marker = "  ⚠ ROTATE" if k in KNOWN_EXPOSED else ""
        print(f"    + {k:<{col}} {v}{marker}")

    # 5. Optionally persist master password to key file
    print()
    save = input(
        f"  Save master password to key file {new_key_file_path}\n"
        "  (recommended for Docker / automated environments)? (y/N) : "
    ).strip().lower()
    if save == "y":
        new_key_file_path.parent.mkdir(parents=True, exist_ok=True)
        new_key_file_path.write_bytes(new_pwd.encode("utf-8"))
        try:
            new_key_file_path.chmod(0o600)
        except OSError:
            pass
        print(f"  Key file written : {new_key_file_path}  (mode 600)")

    # 6. Post-migration checklist
    exposed_block = ""
    if already_exposed:
        exposed_block = (
            "\n  KEYS THAT WERE COMMITTED TO GIT — REVOKE IMMEDIATELY:\n"
            + "\n".join(f"    ✗  {k}" for k in sorted(already_exposed))
            + "\n"
        )

    print(f"""
  ═══════════════════════════════════════════════════════
  MIGRATION COMPLETE — REQUIRED FOLLOW-UP ACTIONS
  ═══════════════════════════════════════════════════════
{exposed_block}
  1. Verify vault integrity:
       cd backend
       python vault_cli.py health-check

  2. Strip secret *values* from backend/.env
     Leave keys present but empty:
       SARVAM_API_KEY=
       NEO4J_PASSWORD=
       LOCAL_AUTH_PASSWORD=
       ... etc.

  3. Add vault artefacts to .gitignore (if not already):
       .secrets.vault
       .vault.key

  4. Remove any previously tracked secrets from git:
       git rm --cached backend/.env
       git rm --cached data/client_secret_*.json
       git commit -m "chore: remove committed secrets"

  5. Run git-secrets or trufflehog to confirm no keys remain in history.
     Consider using: https://github.com/gitleaks/gitleaks

  6. Set VAULT_MASTER_PASSWORD in your deployment environment
     (Docker secret, Cloud Run secret, GitHub Actions secret, etc.)

  7. Delete the old Fernet vault files once you've confirmed everything works:
       rm -f backend/.secrets.json.enc  backend/.vault.key (old key)
  ═══════════════════════════════════════════════════════
""")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Migrate secrets from .env / Fernet vault to AES-256-GCM vault",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--env",
        default=str(_HERE / ".env"),
        help="Path to .env file  (default: backend/.env)",
    )
    parser.add_argument(
        "--fernet-vault",
        default=str(_HERE / ".secrets.json.enc"),
        help="Path to old Fernet vault  (default: backend/.secrets.json.enc)",
    )
    parser.add_argument(
        "--fernet-key",
        default=str(_HERE / ".vault.key"),
        help="Path to Fernet key file  (default: backend/.vault.key)",
    )
    parser.add_argument(
        "--new-vault",
        default=str(_HERE / ".secrets.vault"),
        help="Destination for new AES-256-GCM vault  (default: backend/.secrets.vault)",
    )
    parser.add_argument(
        "--new-key-file",
        default=str(_HERE / ".vault.key.new"),
        help="Destination for new key file  (default: backend/.vault.key.new)",
    )
    args = parser.parse_args()

    run_migration(
        env_path          = Path(args.env),
        fernet_vault_path = Path(args.fernet_vault),
        fernet_key_path   = Path(args.fernet_key),
        new_vault_path    = Path(args.new_vault),
        new_key_file_path = Path(args.new_key_file),
    )


if __name__ == "__main__":
    main()
