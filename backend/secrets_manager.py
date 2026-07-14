import base64
import json
import os
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC


class SecretsManager:
    _FORMAT_MAGIC = b"KV1"
    _SALT_SIZE = 16

    def __init__(self, vault_path=None, master_key=None):
        self.vault_path = Path(vault_path or os.getenv("VAULT_FILE", ".secrets.vault"))
        self.master_key = master_key or os.getenv("VAULT_MASTER_KEY")
        self._cache = None

    @property
    def is_configured(self):
        return bool(self.master_key)

    def get_secret(self, key, default=None):
        if not self.is_configured:
            return os.getenv(key, default)
        secrets = self._load_vault()
        if key in secrets:
            return secrets[key]
        return os.getenv(key, default)

    def set_secret(self, key, value):
        if not self.is_configured:
            raise RuntimeError("VAULT_MASTER_KEY must be set to store secrets")
        secrets = self._load_vault()
        secrets[key] = value
        self._write_vault(secrets)

    def rotate_master_key(self, new_master_key):
        if not self.is_configured:
            raise RuntimeError("Vault is not configured")
        if not new_master_key:
            raise RuntimeError("New VAULT_MASTER_KEY cannot be empty")
        secrets = self._load_vault()
        self.master_key = new_master_key
        self._write_vault(secrets)

    def _load_vault(self):
        if self._cache is not None:
            return dict(self._cache)
        if not self.vault_path.exists():
            self._cache = {}
            return {}
        payload = self.vault_path.read_bytes()
        if not payload.startswith(self._FORMAT_MAGIC):
            raise RuntimeError("Vault data is invalid")
        salt_start = len(self._FORMAT_MAGIC)
        salt_end = salt_start + self._SALT_SIZE
        salt = payload[salt_start:salt_end]
        encrypted_payload = payload[salt_end:]
        fernet = self._build_fernet(self.master_key, salt)
        try:
            plaintext = fernet.decrypt(encrypted_payload)
        except InvalidToken as exc:
            raise RuntimeError("Unable to decrypt vault; check VAULT_MASTER_KEY") from exc
        data = json.loads(plaintext.decode("utf-8"))
        if not isinstance(data, dict):
            raise RuntimeError("Vault data is invalid")
        self._cache = data
        return dict(data)

    def _write_vault(self, secrets):
        self.vault_path.parent.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(secrets, sort_keys=True).encode("utf-8")
        salt = os.urandom(self._SALT_SIZE)
        fernet = self._build_fernet(self.master_key, salt)
        encrypted = fernet.encrypt(payload)
        vault_data = self._FORMAT_MAGIC + salt + encrypted
        fd = os.open(self.vault_path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "wb") as vault_file:
            vault_file.write(vault_data)
        self._cache = dict(secrets)

    @staticmethod
    def _build_fernet(master_key, salt):
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=1000000,
        )
        derived_key = kdf.derive(master_key.encode("utf-8"))
        fernet_key = base64.urlsafe_b64encode(derived_key)
        return Fernet(fernet_key)


_default_manager = SecretsManager()


def get_secret(key, default=None):
    return _default_manager.get_secret(key, default)
