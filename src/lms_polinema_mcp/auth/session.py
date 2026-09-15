"""Moodle session management — capture, save, load, validate via MoodleSession cookie."""

import json
import time
from pathlib import Path
from typing import Optional

import httpx

from lms_polinema_mcp.config import (
    MOODLE_BASE_URL,
    MOODLE_SESSION_FILE,
    SESSION_DIR,
)


class SessionManager:
    def __init__(self):
        SESSION_DIR.mkdir(parents=True, exist_ok=True)

    def save(self, moodle_session: str, sesskey: str = "") -> None:
        data = {
            "MoodleSession": moodle_session,
            "sesskey": sesskey,
            "saved_at": time.time(),
        }
        MOODLE_SESSION_FILE.write_text(json.dumps(data, indent=2))

    def load(self) -> Optional[dict]:
        if not MOODLE_SESSION_FILE.exists():
            return None
        try:
            return json.loads(MOODLE_SESSION_FILE.read_text())
        except Exception:
            return None

    def validate(self, moodle_session: str) -> bool:
        """Check if session is still valid by hitting a Moodle page."""
        try:
            resp = httpx.get(
                f"{MOODLE_BASE_URL}/user/profile.php",
                cookies={"MoodleSession": moodle_session},
                follow_redirects=False,
                timeout=10,
                verify=False,
            )
            # Valid session → 200 on profile page
            # Expired session → 303 redirect to login
            return resp.status_code == 200
        except Exception:
            return False

    def get_valid_session(self) -> Optional[dict]:
        """Load and validate session. Returns None if expired or missing."""
        data = self.load()
        if data and self.validate(data["MoodleSession"]):
            return data
        return None
