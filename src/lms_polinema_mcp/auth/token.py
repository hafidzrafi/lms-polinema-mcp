"""Moodle token management — save, load, validate."""

import json
import time
from pathlib import Path
from typing import Optional

import httpx

from lms_polinema_mcp.config import (
    MOODLE_BASE_URL,
    MOODLE_SERVICE,
    MOODLE_TOKEN_FILE,
    SESSION_DIR,
)


class TokenManager:
    def __init__(self):
        SESSION_DIR.mkdir(parents=True, exist_ok=True)

    def save(self, token: str, username: str) -> None:
        data = {
            "token": token,
            "username": username,
            "saved_at": time.time(),
        }
        MOODLE_TOKEN_FILE.write_text(json.dumps(data, indent=2))

    def load(self) -> Optional[str]:
        if not MOODLE_TOKEN_FILE.exists():
            return None
        try:
            data = json.loads(MOODLE_TOKEN_FILE.read_text())
            return data.get("token")
        except Exception:
            return None

    def validate(self, token: str) -> bool:
        """Test token against core_webservice_get_site_info."""
        try:
            resp = httpx.get(
                f"{MOODLE_BASE_URL}/webservice/rest/server.php",
                params={
                    "wstoken": token,
                    "wsfunction": "core_webservice_get_site_info",
                    "moodlewsrestformat": "json",
                },
                timeout=10,
            )
            data = resp.json()
            return "sitename" in data
        except Exception:
            return False

    def get_valid_token(self) -> Optional[str]:
        """Load token and validate it. Returns None if invalid/missing."""
        token = self.load()
        if token and self.validate(token):
            return token
        return None


def generate_token(username: str, password: str) -> str:
    """POST to Moodle token endpoint and return wstoken."""
    resp = httpx.post(
        f"{MOODLE_BASE_URL}/login/token.php",
        data={
            "username": username,
            "password": password,
            "service": MOODLE_SERVICE,
        },
        timeout=15,
    )
    resp.raise_for_status()
    data = resp.json()

    if "token" not in data:
        error = data.get("error", "Unknown error")
        raise ValueError(f"Token generation failed: {error}")

    return data["token"]
