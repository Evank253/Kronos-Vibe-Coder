import pytest

from backend.secrets_manager import SecretsManager


def test_get_secret_falls_back_to_env_when_vault_not_configured(monkeypatch):
    monkeypatch.setenv("GITHUB_OAUTH_CLIENT_SECRET", "from-env")
    manager = SecretsManager(master_key=None)

    assert manager.get_secret("GITHUB_OAUTH_CLIENT_SECRET") == "from-env"


def test_set_and_get_secret_uses_encrypted_vault(tmp_path):
    vault_path = tmp_path / "vault.bin"
    manager = SecretsManager(vault_path=vault_path, master_key="master-key")

    manager.set_secret("AI_API_KEY", "super-secret")

    assert manager.get_secret("AI_API_KEY") == "super-secret"
    assert b"super-secret" not in vault_path.read_bytes()


def test_rotate_master_key_reencrypts_existing_secrets(tmp_path):
    vault_path = tmp_path / "vault.bin"
    manager = SecretsManager(vault_path=vault_path, master_key="old-key")
    manager.set_secret("AI_API_KEY", "token-123")

    manager.rotate_master_key("new-key")

    rotated = SecretsManager(vault_path=vault_path, master_key="new-key")
    assert rotated.get_secret("AI_API_KEY") == "token-123"

    old_key_manager = SecretsManager(vault_path=vault_path, master_key="old-key")
    with pytest.raises(RuntimeError):
        old_key_manager.get_secret("AI_API_KEY")
