# SECRETS.md

## Overview

Kronos supports a vault-first secret model:

- **Primary**: encrypted local vault file (`.secrets.vault`)
- **Fallback**: plain environment variables (existing `.env` behavior)

If `VAULT_MASTER_KEY` is set, secrets are read from the vault first.
If `VAULT_MASTER_KEY` is not set, the app uses normal environment variables.

## Local Vault Setup

1. Export a strong master key:

```bash
export VAULT_MASTER_KEY='replace-with-long-random-value'
```

2. Store secrets in the vault:

```bash
python -m backend.cli.vault_cli store GITHUB_OAUTH_CLIENT_SECRET
python -m backend.cli.vault_cli store AI_API_KEY
```

3. Retrieve a secret:

```bash
python -m backend.cli.vault_cli retrieve GITHUB_OAUTH_CLIENT_SECRET
```

## Rotate the Vault Master Key

Use the CLI rotation command:

```bash
python -m backend.cli.vault_cli rotate
```

This decrypts existing vault content with the current key and re-encrypts with the new key.

## GitHub Actions / CI

Set these repository secrets:

- `VAULT_MASTER_KEY`
- `AI_API_KEY` (if needed by your workflows)
- `GITHUB_OAUTH_CLIENT_SECRET` (if needed by your workflows)

The CI workflow passes them through environment variables, so plaintext secrets are not committed to git.

## Security Notes

- Keep `.secrets.vault` out of source control.
- Never commit real values to `.env.example`.
- Rotate `VAULT_MASTER_KEY` and affected API credentials if exposure is suspected.
