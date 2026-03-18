"""
AES-256-GCM Secret Vault
========================
Replaces the previous Fernet (AES-128-CBC) implementation.

Encryption scheme
-----------------
  Master password
      └─ PBKDF2-HMAC-SHA256 (600 000 iterations, 32-byte random salt)
             └─ 32-byte symmetric key  ──►  AES-256-GCM
                                              ├─ 12-byte random nonce  (per secret)
                                              ├─ ciphertext
                                              └─ 16-byte authentication tag

The vault is a single JSON file.  Structure:

  {
    "version": 2,
    "kdf": {
      "algorithm": "pbkdf2_hmac_sha256",
      "iterations": 600000,
      "salt": "<base64>"
    },
    "secrets": {
      "KEY_NAME": {
        "nonce": "<base64-12-bytes>",
        "ciphertext_tag": "<base64-(ciphertext + 16-byte GCM tag)>"
      }
    }
  }

Master password resolution (in priority order)
-----------------------------------------------
  1. VAULT_MASTER_PASSWORD  environment variable
  2. Key file at VAULT_KEY_PATH                (useful for Docker volume mounts)

If neither is available the vault degrades gracefully — get_secret() returns
the supplied default instead of raising, so the application can still fall back
to bare environment variables via env_utils.get_value_from_env().

Public API (unchanged from previous version)
--------------------------------------------
  initialize_vault()            Create vault if it does not exist yet
  set_secret(name, value)       Encrypt and store / overwrite a secret
  get_secret(name, default)     Decrypt and return a secret
  delete_secret(name)           Remove a secret
  list_secret_keys()            Return list of key names (no values)
  rotate_master_password(new)   Re-encrypt the entire vault under a new password
"""

import base64
import json
import logging
import os
import secrets
from pathlib import Path
from typing import Optional

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

# ---------------------------------------------------------------------------
# Paths  (overridable via environment variables for Docker / testing)
# ---------------------------------------------------------------------------
VAULT_FILE_PATH = Path(os.getenv("VAULT_FILE_PATH", "/code/.secrets.vault"))
VAULT_KEY_PATH  = Path(os.getenv("VAULT_KEY_PATH",  "/code/.vault.key"))

# ---------------------------------------------------------------------------
# KDF / cipher constants
# ---------------------------------------------------------------------------
_KDF_ITERATIONS = 600_000          # NIST SP 800-132 (2023) recommendation
_SALT_BYTES     = 32               # 256-bit KDF salt, stored in vault header
_NONCE_BYTES    = 12               # 96-bit GCM nonce (NIST recommended size)
_KEY_BYTES      = 32               # AES-256 → 32-byte key
_VAULT_VERSION  = 2                # bumped from Fernet v1


# ===========================================================================
# Internal helpers
# ===========================================================================

def _derive_key(password: bytes, salt: bytes) -> bytes:
    """PBKDF2-HMAC-SHA256: password + salt → 32-byte AES-256 key."""
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=_KEY_BYTES,
        salt=salt,
        iterations=_KDF_ITERATIONS,
    )
    return kdf.derive(password)


def _resolve_master_password() -> Optional[bytes]:
    """
    Return the master password bytes, or None if unavailable.
    Does not raise — callers decide how to handle the absence.
    """
    pwd = os.getenv("VAULT_MASTER_PASSWORD")
    if pwd:
        return pwd.encode("utf-8")

    if VAULT_KEY_PATH.exists():
        try:
            return VAULT_KEY_PATH.read_bytes().strip()
        except OSError as exc:
            logging.warning(f"Vault key file unreadable ({VAULT_KEY_PATH}): {exc}")

    return None


def _load_raw_vault() -> dict:
    """Load vault JSON from disk; return empty structure if not present."""
    if not VAULT_FILE_PATH.exists():
        return {"version": _VAULT_VERSION, "kdf": {}, "secrets": {}}
    try:
        return json.loads(VAULT_FILE_PATH.read_text(encoding="utf-8"))
    except Exception as exc:
        logging.error(f"Failed to read vault file {VAULT_FILE_PATH}: {exc}")
        return {"version": _VAULT_VERSION, "kdf": {}, "secrets": {}}


def _save_raw_vault(data: dict) -> None:
    VAULT_FILE_PATH.parent.mkdir(parents=True, exist_ok=True)
    VAULT_FILE_PATH.write_text(
        json.dumps(data, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    # Restrict to owner-read/write only (rw-------)
    try:
        VAULT_FILE_PATH.chmod(0o600)
    except OSError:
        pass  # Windows or read-only FS — best-effort


def _derive_key_from_vault(vault: dict) -> bytes:
    """Derive the AES key using the KDF parameters embedded in the vault."""
    kdf_meta = vault.get("kdf", {})
    salt_b64 = kdf_meta.get("salt")
    if not salt_b64:
        raise ValueError(
            "Vault has no KDF metadata — was it initialised? "
            "Run: python vault_cli.py init"
        )
    salt = base64.b64decode(salt_b64)
    pwd  = _resolve_master_password()
    if pwd is None:
        raise RuntimeError(
            "Vault master password not found.  "
            "Set the VAULT_MASTER_PASSWORD environment variable "
            f"or place the password in {VAULT_KEY_PATH}"
        )
    return _derive_key(pwd, salt)


def _encrypt_value(key: bytes, plaintext: str) -> dict:
    """AES-256-GCM encrypt a string; return {nonce, ciphertext_tag} as base64."""
    nonce        = secrets.token_bytes(_NONCE_BYTES)
    aesgcm       = AESGCM(key)
    ct_with_tag  = aesgcm.encrypt(nonce, plaintext.encode("utf-8"), None)
    return {
        "nonce":           base64.b64encode(nonce).decode(),
        "ciphertext_tag":  base64.b64encode(ct_with_tag).decode(),
    }


def _decrypt_value(key: bytes, entry: dict) -> str:
    """AES-256-GCM decrypt an entry produced by _encrypt_value.  Raises InvalidTag on tampering."""
    nonce       = base64.b64decode(entry["nonce"])
    ct_with_tag = base64.b64decode(entry["ciphertext_tag"])
    aesgcm      = AESGCM(key)
    return aesgcm.decrypt(nonce, ct_with_tag, None).decode("utf-8")


# ===========================================================================
# Public API
# ===========================================================================

def initialize_vault() -> None:
    """
    Create a new, empty vault with a freshly generated KDF salt.
    No-op if the vault file already exists.
    Raises RuntimeError if VAULT_MASTER_PASSWORD is not set.
    """
    if VAULT_FILE_PATH.exists():
        return

    # Validate that a password is available before writing anything
    if _resolve_master_password() is None:
        raise RuntimeError(
            "Cannot initialise vault: VAULT_MASTER_PASSWORD is not set "
            f"and no key file found at {VAULT_KEY_PATH}"
        )

    salt  = secrets.token_bytes(_SALT_BYTES)
    vault = {
        "version": _VAULT_VERSION,
        "kdf": {
            "algorithm":  "pbkdf2_hmac_sha256",
            "iterations": _KDF_ITERATIONS,
            "salt":       base64.b64encode(salt).decode(),
        },
        "secrets": {},
    }
    _save_raw_vault(vault)
    logging.info(f"AES-256-GCM vault initialised at {VAULT_FILE_PATH}")


def set_secret(name: str, value: str) -> None:
    """
    Encrypt *value* under *name* and persist it to the vault.
    Initialises the vault automatically if it does not yet exist.
    """
    initialize_vault()
    vault          = _load_raw_vault()
    key            = _derive_key_from_vault(vault)
    vault["secrets"][name] = _encrypt_value(key, value)
    _save_raw_vault(vault)


def get_secret(name: str, default: Optional[str] = None) -> Optional[str]:
    """
    Decrypt and return the secret stored under *name*.
    Returns *default* (None by default) if:
      - the key does not exist in the vault
      - the vault master password is unavailable
      - decryption fails (e.g. tampered ciphertext — InvalidTag)
    """
    vault = _load_raw_vault()
    entry = vault.get("secrets", {}).get(name)
    if entry is None:
        return default

    try:
        key = _derive_key_from_vault(vault)
        return _decrypt_value(key, entry)
    except InvalidTag:
        logging.error(
            f"AES-GCM authentication failed for secret '{name}'. "
            "Vault may have been tampered with."
        )
        return default
    except RuntimeError as exc:
        # Master password unavailable — degrade gracefully
        logging.debug(f"Vault master password unavailable: {exc}")
        return default
    except Exception as exc:
        logging.error(f"Failed to decrypt secret '{name}': {exc}")
        return default


def delete_secret(name: str) -> None:
    """Remove the secret stored under *name*. Silent no-op if not found."""
    vault = _load_raw_vault()
    if name in vault.get("secrets", {}):
        del vault["secrets"][name]
        _save_raw_vault(vault)


def list_secret_keys() -> list:
    """Return a sorted list of all secret key names (values are never exposed)."""
    vault = _load_raw_vault()
    return sorted(vault.get("secrets", {}).keys())


def rotate_master_password(new_password: str) -> None:
    """
    Re-encrypt the entire vault under a new master password.
    The *old* password must still be resolvable via VAULT_MASTER_PASSWORD
    or the key file before calling this function.

    After completion the vault is re-written with a fresh KDF salt.
    The caller is responsible for updating VAULT_MASTER_PASSWORD / the key file.
    """
    vault   = _load_raw_vault()
    old_key = _derive_key_from_vault(vault)

    # 1. Decrypt all secrets with the old key
    plaintext_secrets: dict = {}
    for name, entry in vault.get("secrets", {}).items():
        plaintext_secrets[name] = _decrypt_value(old_key, entry)

    # 2. Fresh salt + new key
    new_salt = secrets.token_bytes(_SALT_BYTES)
    new_key  = _derive_key(new_password.encode("utf-8"), new_salt)

    # 3. Re-encrypt and save
    new_vault = {
        "version": _VAULT_VERSION,
        "kdf": {
            "algorithm":  "pbkdf2_hmac_sha256",
            "iterations": _KDF_ITERATIONS,
            "salt":       base64.b64encode(new_salt).decode(),
        },
        "secrets": {
            name: _encrypt_value(new_key, val)
            for name, val in plaintext_secrets.items()
        },
    }
    _save_raw_vault(new_vault)
    logging.info("Vault successfully re-encrypted with new master password.")
