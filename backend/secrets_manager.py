import base64
import hashlib
import json
import os
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken


class SecretsManager:
    def __init__(self, vault_path=None, master_key=None):
        self.vault_path = Path(vault_path or os.getenv("VAULT_FILE", ".secrets.vault"))
        self.master_key = master_key or os.getenv("VAULT_MASTER_KEY")
        self._fernet = self._build_fernet(self.master_key) if self.master_key else None
        self._cache = None

    @property
    def is_configured(self):
        return self._fernet is not None

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
        secrets = self._load_vault()
        self.master_key = new_master_key
        self._fernet = self._build_fernet(new_master_key)
        self._write_vault(secrets)

    def _load_vault(self):
        if self._cache is not None:
            return dict(self._cache)
        if not self.vault_path.exists():
            self._cache = {}
            return {}
        payload = self.vault_path.read_bytes()
        try:
            plaintext = self._fernet.decrypt(payload)
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
        encrypted = self._fernet.encrypt(payload)
        self.vault_path.write_bytes(encrypted)
        os.chmod(self.vault_path, 0o600)
        self._cache = dict(secrets)

    @staticmethod
    def _build_fernet(master_key):
        digest = hashlib.sha256(master_key.encode("utf-8")).digest()
        fernet_key = base64.urlsafe_b64encode(digest)
        return Fernet(fernet_key)


_default_manager = SecretsManager()


def get_secret(key, default=None):
    return _default_manager.get_secret(key, default)
