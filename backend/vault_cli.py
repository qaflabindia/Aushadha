#!/usr/bin/env python3
"""
vault_cli.py — Aushadha AES-256-GCM Vault Management CLI
=========================================================

Commands
--------
  init                  Create a new vault (prompts for master password)
  set  KEY VALUE        Encrypt and store a secret
  get  KEY              Decrypt and print a secret
  delete KEY            Remove a secret from the vault
  list                  List all stored key names (no values shown)
  rotate-password       Re-encrypt vault under a new master password
  health-check          Verify every secret can be decrypted (integrity audit)
  migrate-env [FILE]    Import non-empty values from a .env file into the vault
                        FILE defaults to .env in the current directory

Environment variables
---------------------
  VAULT_MASTER_PASSWORD   Master password — prompted interactively if absent
  VAULT_FILE_PATH         Override vault file location  (default: /code/.secrets.vault)
  VAULT_KEY_PATH          Override key-file location    (default: /code/.vault.key)

Usage examples
--------------
  # First-time setup
  python vault_cli.py init

  # Migrate all keys from backend/.env
  python vault_cli.py migrate-env backend/.env

  # Store a single secret
  python vault_cli.py set SARVAM_API_KEY sk_xxxx...

  # Retrieve it (useful in shell scripts: export VAR=$(python vault_cli.py get KEY))
  python vault_cli.py get SARVAM_API_KEY

  # Integrity audit
  python vault_cli.py health-check

  # Rotate the master password
  python vault_cli.py rotate-password
"""

import getpass
import os
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Bootstrap sys.path so this script works when called from the backend/ dir
# OR from the project root.
# ---------------------------------------------------------------------------
_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))

# Apply path defaults that match the Docker container mount before importing
# the vault module (environment variables override these at runtime).
os.environ.setdefault("VAULT_FILE_PATH", str(_HERE / ".secrets.vault"))
os.environ.setdefault("VAULT_KEY_PATH",  str(_HERE / ".vault.key"))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _require_password(prompt: str = "Vault master password: ") -> str:
    """
    Return VAULT_MASTER_PASSWORD if set, otherwise prompt without echo.
    Sets os.environ so the vault module picks it up automatically.
    """
    pwd = os.environ.get("VAULT_MASTER_PASSWORD")
    if pwd:
        return pwd
    pwd = getpass.getpass(prompt)
    if not pwd:
        _die("Master password cannot be empty.")
    os.environ["VAULT_MASTER_PASSWORD"] = pwd
    return pwd


def _die(message: str, code: int = 1) -> None:
    print(f"ERROR: {message}", file=sys.stderr)
    sys.exit(code)


def _ok(message: str) -> None:
    print(f"  OK  {message}")


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

def cmd_init() -> None:
    """Create a new vault, prompting for and confirming the master password."""
    vault_path = Path(os.environ["VAULT_FILE_PATH"])
    if vault_path.exists():
        _die(
            f"Vault already exists at {vault_path}.\n"
            "       To reset, delete the file manually and re-run init.\n"
            "       To change the password, use: python vault_cli.py rotate-password"
        )

    pwd     = getpass.getpass("Set master password : ")
    confirm = getpass.getpass("Confirm password    : ")
    if pwd != confirm:
        _die("Passwords do not match.")
    if len(pwd) < 12:
        _die("Master password must be at least 12 characters.")

    os.environ["VAULT_MASTER_PASSWORD"] = pwd

    from src.shared.secret_vault import initialize_vault, VAULT_FILE_PATH, VAULT_KEY_PATH

    initialize_vault()
    print(f"\n  Vault created : {VAULT_FILE_PATH}")

    # Optionally persist the password to a key file (useful for Docker secrets)
    save = input("\n  Save password to key file for Docker/automated use? (y/N) : ").strip().lower()
    if save == "y":
        key_file = Path(VAULT_KEY_PATH)
        key_file.parent.mkdir(parents=True, exist_ok=True)
        key_file.write_bytes(pwd.encode("utf-8"))
        try:
            key_file.chmod(0o600)
        except OSError:
            pass
        print(f"  Key file written : {key_file}  (permissions: 600)")
        print("  ADD THIS FILE TO .gitignore — never commit it.")
    print()


def cmd_set(key: str, value: str) -> None:
    _require_password()
    from src.shared.secret_vault import set_secret
    set_secret(key, value)
    _ok(f"'{key}' stored in vault.")


def cmd_get(key: str) -> None:
    _require_password()
    from src.shared.secret_vault import get_secret
    value = get_secret(key)
    if value is None:
        _die(f"Key '{key}' not found in vault.")
    # Print raw value so this works in shell substitution:
    #   export FOO=$(python vault_cli.py get FOO)
    print(value)


def cmd_delete(key: str) -> None:
    _require_password()
    from src.shared.secret_vault import delete_secret
    delete_secret(key)
    _ok(f"'{key}' deleted from vault.")


def cmd_list() -> None:
    _require_password()
    from src.shared.secret_vault import list_secret_keys
    keys = list_secret_keys()
    if not keys:
        print("  (vault is empty)")
        return
    print(f"\n  {len(keys)} secret(s) stored:\n")
    for k in keys:
        print(f"    {k}")
    print()


def cmd_rotate_password() -> None:
    """Re-encrypt the vault under a new master password."""
    print("Current master password needed to decrypt existing secrets.")
    _require_password("Current master password: ")

    from src.shared.secret_vault import rotate_master_password, VAULT_KEY_PATH

    new_pwd = getpass.getpass("New master password    : ")
    confirm = getpass.getpass("Confirm new password   : ")
    if new_pwd != confirm:
        _die("Passwords do not match.")
    if len(new_pwd) < 12:
        _die("Master password must be at least 12 characters.")

    rotate_master_password(new_pwd)

    # Update in-memory env and key file if it exists
    os.environ["VAULT_MASTER_PASSWORD"] = new_pwd
    key_file = Path(VAULT_KEY_PATH)
    if key_file.exists():
        key_file.write_bytes(new_pwd.encode("utf-8"))
        try:
            key_file.chmod(0o600)
        except OSError:
            pass
        print(f"  Key file updated : {key_file}")

    _ok("Master password rotated. Update VAULT_MASTER_PASSWORD in your environment.")


def cmd_health_check() -> None:
    """Attempt to decrypt every secret and report pass/fail per key."""
    _require_password()

    from cryptography.exceptions import InvalidTag
    from src.shared.secret_vault import (
        _decrypt_value,
        _derive_key_from_vault,
        _load_raw_vault,
    )

    vault   = _load_raw_vault()
    entries = vault.get("secrets", {})

    if not entries:
        print("  Vault is empty — nothing to check.")
        return

    key    = _derive_key_from_vault(vault)
    passed = []
    failed = []

    for name, entry in entries.items():
        try:
            _decrypt_value(key, entry)
            passed.append(name)
        except InvalidTag:
            failed.append((name, "TAMPERED — authentication tag mismatch"))
        except Exception as exc:
            failed.append((name, str(exc)))

    print(f"\n  Health Check — {len(passed)} passed / {len(failed)} failed\n")
    for k in passed:
        print(f"    PASS  {k}")
    for k, reason in failed:
        print(f"    FAIL  {k}  →  {reason}", file=sys.stderr)
    print()

    if failed:
        sys.exit(1)


def cmd_migrate_env(env_path: str = ".env") -> None:
    """
    Read every non-empty key=value pair from *env_path* and write it to the vault.

    Keys matching SENSITIVE_PATTERNS are flagged; their values are masked in output.
    After migration the script prints an action list for what to do next.
    """
    env_file = Path(env_path)
    if not env_file.exists():
        _die(f".env file not found at {env_file.resolve()}")

    _require_password()

    from src.shared.secret_vault import initialize_vault, set_secret

    initialize_vault()

    SENSITIVE = ("KEY", "PASSWORD", "SECRET", "TOKEN", "PASS", "CREDENTIAL")

    migrated: list[tuple[str, str]] = []
    skipped:  list[str]             = []

    with open(env_file, encoding="utf-8") as fh:
        for raw_line in fh:
            line = raw_line.strip()

            # Skip blank lines and pure comments
            if not line or line.startswith("#"):
                continue

            if "=" not in line:
                continue

            key, _, value = line.partition("=")
            key   = key.strip()
            value = value.strip().strip('"').strip("'")

            # Skip inline-comment-only values like VALUE=#some_key
            if not value or value.startswith("#"):
                skipped.append(key)
                continue

            # Skip comment-style placeholder values like VALUE="your_key_here"
            lower_val = value.lower()
            if any(ph in lower_val for ph in ("your_", "placeholder", "changeme", "xxx", "todo")):
                skipped.append(f"{key} (placeholder)")
                continue

            set_secret(key, value)
            is_sensitive = any(pat in key.upper() for pat in SENSITIVE)
            display_val  = "***" if is_sensitive else (value[:40] + "…" if len(value) > 40 else value)
            migrated.append((key, display_val))

    print(f"\n  Migrated {len(migrated)} secret(s) into vault:\n")
    for k, v in migrated:
        print(f"    + {k:<45} {v}")

    if skipped:
        print(f"\n  Skipped {len(skipped)} empty/placeholder key(s):")
        for s in skipped:
            print(f"    - {s}")

    print("""
  ─────────────────────────────────────────────────────
  REQUIRED NEXT STEPS
  ─────────────────────────────────────────────────────
  1. Verify vault contents:
       python vault_cli.py list
       python vault_cli.py health-check

  2. Strip secret *values* from the .env file
     (keep keys with empty values so the schema is visible):
       SARVAM_API_KEY=
       NEO4J_PASSWORD=
       ... etc.

  3. Ensure vault file is gitignored:
       echo ".secrets.vault" >> .gitignore

  4. CRITICAL — ROTATE any key that was previously committed to git:
       SARVAM_API_KEY  → revoke at platform.sarvam.ai and issue new key
       NEO4J_PASSWORD  → change immediately in Neo4j and .env
       LOCAL_AUTH_PASSWORD → rotate and update docker-compose / deployment

  5. Run: git rm --cached backend/.env  (if it was ever staged)
          git rm --cached data/client_secret_*.json
  ─────────────────────────────────────────────────────
""")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

_USAGE = """
Aushadha Vault CLI  —  AES-256-GCM

Usage:  python vault_cli.py <command> [args]

Commands:
  init                     Create new vault (interactive password setup)
  set    KEY VALUE          Store / overwrite a secret
  get    KEY                Print a secret value (safe for shell substitution)
  delete KEY                Remove a secret
  list                      List all key names
  rotate-password           Re-encrypt vault with a new master password
  health-check              Verify all secrets decrypt correctly
  migrate-env [FILE]        Import .env file into vault  (default: .env)

Environment:
  VAULT_MASTER_PASSWORD    Master password (prompted if absent)
  VAULT_FILE_PATH          Vault file path  (default: ./backend/.secrets.vault)
  VAULT_KEY_PATH           Key file path    (default: ./backend/.vault.key)
"""


def main() -> None:
    args = sys.argv[1:]
    if not args:
        print(_USAGE)
        sys.exit(0)

    cmd = args[0]

    if cmd == "init":
        cmd_init()
    elif cmd == "set":
        if len(args) != 3:
            _die("Usage: vault_cli.py set KEY VALUE")
        cmd_set(args[1], args[2])
    elif cmd == "get":
        if len(args) != 2:
            _die("Usage: vault_cli.py get KEY")
        cmd_get(args[1])
    elif cmd == "delete":
        if len(args) != 2:
            _die("Usage: vault_cli.py delete KEY")
        cmd_delete(args[1])
    elif cmd == "list":
        cmd_list()
    elif cmd == "rotate-password":
        cmd_rotate_password()
    elif cmd == "health-check":
        cmd_health_check()
    elif cmd == "migrate-env":
        env_file = args[1] if len(args) > 1 else ".env"
        cmd_migrate_env(env_file)
    else:
        print(f"Unknown command: {cmd}", file=sys.stderr)
        print(_USAGE)
        sys.exit(1)


if __name__ == "__main__":
    main()
