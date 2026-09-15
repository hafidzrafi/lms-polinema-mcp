#!/usr/bin/env python3
"""Interactive setup script for LMS Polinema MCP credentials and session."""

import getpass
import sys
from pathlib import Path

# Ensure src package is importable when executed directly
sys.path.insert(0, str(Path(__file__).parent / "src"))

from lms_polinema_mcp.auth.credentials import CredentialStore
from lms_polinema_mcp.auth.refresh import SessionRefresher
from lms_polinema_mcp.auth.session import SessionManager
from lms_polinema_mcp.config import settings
from lms_polinema_mcp.exceptions import AuthenticationError


def main() -> None:
    """Run interactive setup to store credentials and perform initial login."""
    print(f"LMS {settings.institution_name} MCP - Setup and Authentication")
    print("==================================================")

    store = CredentialStore()
    session_mgr = SessionManager()

    if store.exists():
        response = input("Existing credentials found. Re-authenticate? [y/N]: ").strip().lower()
        if response != "y":
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
    print("Credentials stored successfully.")
    print("Starting automated authentication via headless browser...")

    refresher = SessionRefresher(store, session_mgr)
    try:
        refresher.refresh()
        print(f"Authentication successful. Session saved to {settings.session_dir}")
    except AuthenticationError as exc:
        print(f"Authentication failed: {exc}")
        sys.exit(1)
    except Exception as exc:
        print(f"Unexpected error occurred during authentication: {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()
