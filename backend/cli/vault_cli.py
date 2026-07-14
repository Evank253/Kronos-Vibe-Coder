import argparse
import getpass
import os

from backend.secrets_manager import SecretsManager


def _get_manager(args):
    vault_path = args.vault_file or os.getenv("VAULT_FILE")
    master_key = os.getenv("VAULT_MASTER_KEY")
    return SecretsManager(vault_path=vault_path, master_key=master_key)


def cmd_store(args):
    manager = _get_manager(args)
    value = args.value if args.value is not None else getpass.getpass("Secret value: ")
    manager.set_secret(args.key, value)
    print(f"Stored secret: {args.key}")


def cmd_retrieve(args):
    manager = _get_manager(args)
    value = manager.get_secret(args.key)
    if value is None:
        raise SystemExit(f"Secret not found in vault or environment: {args.key}")
    print(f"Secret found: {args.key} (length={len(value)})")


def cmd_rotate(args):
    manager = _get_manager(args)
    new_master_key = args.new_master_key or getpass.getpass("New VAULT_MASTER_KEY: ")
    manager.rotate_master_key(new_master_key)
    print("Vault master key rotated")


def build_parser():
    parser = argparse.ArgumentParser(description="Manage encrypted local vault secrets")
    parser.add_argument(
        "--vault-file",
        default=None,
        help="Path to vault file (default: VAULT_FILE env or .secrets.vault)",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    store = subparsers.add_parser("store", help="Store or update a secret")
    store.add_argument("key")
    store.add_argument("--value", default=None, help="Secret value (omit for prompt)")
    store.set_defaults(func=cmd_store)

    retrieve = subparsers.add_parser("retrieve", help="Retrieve a secret")
    retrieve.add_argument("key")
    retrieve.set_defaults(func=cmd_retrieve)

    rotate = subparsers.add_parser("rotate", help="Rotate vault master key")
    rotate.add_argument(
        "--new-master-key",
        default=None,
        help="New VAULT_MASTER_KEY (omit for secure prompt)",
    )
    rotate.set_defaults(func=cmd_rotate)

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
