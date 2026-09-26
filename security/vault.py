from __future__ import annotations

import base64
import json
import os
import stat
from pathlib import Path
from typing import Callable

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

VAULT_DIR: Path = Path.home() / ".privategpt"
VAULT_FILE: Path = VAULT_DIR / "vault.json"
CANARY: bytes = b"PRIVATEGPT_VAULT_CANARY_v1"
DEFAULT_ITERATIONS: int = 600_000
SALT_BYTES: int = 16

_active_cipher: Fernet | None = None
_active_password: str | None = None


def set_vault_dir(path: Path) -> None:
    global VAULT_DIR, VAULT_FILE
    VAULT_DIR = path
    VAULT_FILE = VAULT_DIR / "vault.json"


def ensure_vault_dir() -> Path:
    VAULT_DIR.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(VAULT_DIR, stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR)  # 0o700
    except OSError:
        pass
    return VAULT_DIR


def is_vault_initialized() -> bool:
    return VAULT_FILE.exists()


def _derive_key(password: str, salt: bytes, iterations: int = DEFAULT_ITERATIONS) -> bytes:
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=iterations,
    )
    derived = kdf.derive(password.encode("utf-8"))
    return base64.urlsafe_b64encode(derived)


def setup_vault(password: str) -> None:
    if not password:
        raise ValueError("Password cannot be empty.")
    ensure_vault_dir()
    salt = os.urandom(SALT_BYTES)
    key = _derive_key(password=password, salt=salt, iterations=DEFAULT_ITERATIONS)
    cipher = Fernet(key)
    verifier = cipher.encrypt(CANARY).decode("utf-8")

    payload = {
        "version": 1,
        "kdf": "PBKDF2HMAC-SHA256",
        "iterations": DEFAULT_ITERATIONS,
        "salt": base64.b64encode(salt).decode("utf-8"),
        "verifier": verifier,
    }

    # Write atomically with strict permissions
    temp_path = VAULT_FILE.with_suffix(".tmp")
    temp_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    try:
        os.chmod(temp_path, stat.S_IRUSR | stat.S_IWUSR)  # 0o600
    except OSError:
        pass
    temp_path.replace(VAULT_FILE)

    global _active_cipher, _active_password
    _active_cipher = cipher
    _active_password = password


def unlock_vault(password: str) -> bool:
    if not is_vault_initialized() or not password:
        return False
    try:
        data = json.loads(VAULT_FILE.read_text(encoding="utf-8"))
        salt = base64.b64decode(data["salt"].encode("utf-8"))
        iterations = int(data.get("iterations", DEFAULT_ITERATIONS))
        verifier = data["verifier"]

        key = _derive_key(password=password, salt=salt, iterations=iterations)
        cipher = Fernet(key)
        decrypted = cipher.decrypt(verifier.encode("utf-8"))
        if decrypted == CANARY:
            global _active_cipher, _active_password
            _active_cipher = cipher
            _active_password = password
            return True
    except (InvalidToken, KeyError, ValueError, OSError, json.JSONDecodeError):
        pass
    return False


def lock_vault() -> None:
    global _active_cipher, _active_password
    _active_cipher = None
    _active_password = None


def is_unlocked() -> bool:
    return _active_cipher is not None


def get_active_cipher() -> Fernet | None:
    return _active_cipher


def encrypt_text(text: str) -> str:
    if _active_cipher is None:
        raise RuntimeError("Vault is locked. Cannot encrypt.")
    return _active_cipher.encrypt(text.encode("utf-8")).decode("utf-8")


def decrypt_text(token_str: str) -> str:
    if _active_cipher is None:
        raise RuntimeError("Vault is locked. Cannot decrypt.")
    return _active_cipher.decrypt(token_str.encode("utf-8")).decode("utf-8")


def change_password(
    old_password: str,
    new_password: str,
    reencrypt_callback: Callable[[Fernet, Fernet], None] | None = None,
) -> bool:
    if not new_password:
        return False
    if not is_vault_initialized():
        setup_vault(new_password)
        return True

    # Validate old password
    try:
        data = json.loads(VAULT_FILE.read_text(encoding="utf-8"))
        salt = base64.b64decode(data["salt"].encode("utf-8"))
        iterations = int(data.get("iterations", DEFAULT_ITERATIONS))
        verifier = data["verifier"]

        old_key = _derive_key(password=old_password, salt=salt, iterations=iterations)
        old_cipher = Fernet(old_key)
        if old_cipher.decrypt(verifier.encode("utf-8")) != CANARY:
            return False
    except Exception:
        return False

    # Derive new key
    new_salt = os.urandom(SALT_BYTES)
    new_key = _derive_key(password=new_password, salt=new_salt, iterations=DEFAULT_ITERATIONS)
    new_cipher = Fernet(new_key)

    # Re-encrypt data using callback if provided
    if reencrypt_callback is not None:
        reencrypt_callback(old_cipher, new_cipher)

    # Write new vault file
    new_verifier = new_cipher.encrypt(CANARY).decode("utf-8")
    payload = {
        "version": 1,
        "kdf": "PBKDF2HMAC-SHA256",
        "iterations": DEFAULT_ITERATIONS,
        "salt": base64.b64encode(new_salt).decode("utf-8"),
        "verifier": new_verifier,
    }

    temp_path = VAULT_FILE.with_suffix(".tmp")
    temp_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    try:
        os.chmod(temp_path, stat.S_IRUSR | stat.S_IWUSR)
    except OSError:
        pass
    temp_path.replace(VAULT_FILE)

    global _active_cipher, _active_password
    _active_cipher = new_cipher
    _active_password = new_password
    return True
