"""Credential storage manager for SIAKAD authentication."""

import contextlib
import json
import logging
import os

from lms_polinema_mcp.config import settings
from lms_polinema_mcp.exceptions import CredentialsNotFoundError

logger = logging.getLogger(__name__)


class CredentialStore:
    """Manages persistent SIAKAD user credentials for automated session refresh."""

    def __init__(self) -> None:
        settings.session_dir.mkdir(parents=True, exist_ok=True)
        with contextlib.suppress(OSError):
            os.chmod(settings.session_dir, 0o700)

    def save(self, nim: str, password: str) -> None:
        """Write credentials to disk atomically with restricted 0o600 file permissions."""
        if not settings.credentials_file:
            raise ValueError("Credentials file path is not configured.")

        data = {"nim": nim, "password": password}
        flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC
        fd = os.open(settings.credentials_file, flags, 0o600)
        with open(fd, "w", encoding="utf-8") as f:
            f.write(json.dumps(data, indent=2))

    def load(self) -> tuple[str, str]:
        """Return stored (nim, password) or raise CredentialsNotFoundError."""
        if not self.exists():
            raise CredentialsNotFoundError(
                f"No credentials found at {settings.credentials_file}. "
                "Run 'uv run auth.py' to configure."
            )

        try:
            data = json.loads(settings.credentials_file.read_text())
            return data["nim"], data["password"]
        except (OSError, json.JSONDecodeError, KeyError) as exc:
            raise CredentialsNotFoundError(f"Failed to read credentials: {exc}") from exc

    def exists(self) -> bool:
        """Return True if the credential file exists and contains valid JSON."""
        return bool(settings.credentials_file and settings.credentials_file.exists())

    def delete(self) -> None:
        """Remove stored credentials from disk."""
        if settings.credentials_file and settings.credentials_file.exists():
            settings.credentials_file.unlink()
