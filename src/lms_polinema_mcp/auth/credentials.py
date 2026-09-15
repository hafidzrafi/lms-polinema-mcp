"""Credential storage manager for SIAKAD authentication."""

import getpass
import json
import logging
import os
import sys

from lms_polinema_mcp.config import settings
from lms_polinema_mcp.exceptions import CredentialsNotFoundError

logger = logging.getLogger(__name__)


class CredentialStore:
    """Manages persistent SIAKAD user credentials for automated session refresh."""

    def __init__(self) -> None:
        settings.session_dir.mkdir(parents=True, exist_ok=True)

    def save(self, nim: str, password: str) -> None:
        """Write credentials to disk with restricted 0o600 file permissions."""
        if not settings.credentials_file:
            raise ValueError("Credentials file path is not configured.")

        data = {"nim": nim, "password": password}
        settings.credentials_file.write_text(json.dumps(data, indent=2))
        try:
            os.chmod(settings.credentials_file, 0o600)
        except OSError as exc:
            logger.warning("Failed to set 0600 file permissions: %s", exc)

    def load(self) -> tuple[str, str]:
        """Return stored (nim, password) or raise CredentialsNotFoundError."""
        if not self.exists():
            raise CredentialsNotFoundError(
                f"No credentials found at {settings.credentials_file}. "
                "Run 'lms-polinema-auth' to configure."
            )

        try:
            data = json.loads(settings.credentials_file.read_text())
            return data["nim"], data["password"]
        except Exception as exc:
            raise CredentialsNotFoundError(f"Failed to read credentials: {exc}") from exc

    def exists(self) -> bool:
        """Return True if the credential file exists and contains valid JSON."""
        return bool(settings.credentials_file and settings.credentials_file.exists())

    def delete(self) -> None:
        """Remove stored credentials from disk."""
        if settings.credentials_file and settings.credentials_file.exists():
            settings.credentials_file.unlink()


def main() -> None:
    """CLI entrypoint to configure SIAKAD credentials interactively."""
    store = CredentialStore()
    print(f"LMS {settings.institution_name} MCP - Credential Setup")
    print("--------------------------------------------------")

    if store.exists():
        resp = input("Existing credentials found. Overwrite? [y/N]: ").strip().lower()
        if resp != "y":
            print("Operation canceled.")
            return

    nim = input("Enter NIM     : ").strip()
    if not nim:
        print("Error: NIM cannot be empty.")
        sys.exit(1)

    password = getpass.getpass("Enter Password: ").strip()
    if not password:
        print("Error: Password cannot be empty.")
        sys.exit(1)

    store.save(nim, password)
    print("Credentials saved successfully.")


if __name__ == "__main__":
    main()
