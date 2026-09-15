"""Session management module with validation and in-memory caching."""

import json
import logging
import os
import threading
import time
from typing import TypedDict

import httpx

from lms_polinema_mcp.config import settings
from lms_polinema_mcp.exceptions import SessionExpiredError

logger = logging.getLogger(__name__)


class SessionData(TypedDict):
    """Moodle session storage representation."""

    MoodleSession: str
    saved_at: float


class SessionManager:
    """Manages persistence and validity of Moodle and SPADA session cookies."""

    def __init__(self) -> None:
        settings.session_dir.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._cached_session: SessionData | None = None
        self._cache_timestamp: float = 0.0

    def save_moodle(self, moodle_session: str) -> None:
        """Persist Moodle session cookie to disk with 0o600 permissions."""
        if not settings.moodle_session_file:
            return

        data = {
            settings.moodle_cookie_name: moodle_session,
            "saved_at": time.time(),
        }
        settings.moodle_session_file.write_text(json.dumps(data, indent=2))
        try:
            os.chmod(settings.moodle_session_file, 0o600)
        except OSError as exc:
            logger.warning("Failed to set 0600 file permissions: %s", exc)

        with self._lock:
            self._cached_session = {"MoodleSession": moodle_session, "saved_at": data["saved_at"]}
            self._cache_timestamp = time.time()

    def save_spada(self, polimaspada: str) -> None:
        """Persist SPADA portal session cookie to disk with 0o600 permissions."""
        if not settings.spada_session_file:
            return

        data = {
            settings.spada_cookie_name: polimaspada,
            "saved_at": time.time(),
        }
        settings.spada_session_file.write_text(json.dumps(data, indent=2))
        try:
            os.chmod(settings.spada_session_file, 0o600)
        except OSError as exc:
            logger.warning("Failed to set 0600 file permissions: %s", exc)

    def load_moodle(self) -> SessionData | None:
        """Read Moodle session from disk or return None if missing."""
        if not settings.moodle_session_file or not settings.moodle_session_file.exists():
            return None
        try:
            raw = json.loads(settings.moodle_session_file.read_text())
            cookie = raw.get(settings.moodle_cookie_name) or raw.get("MoodleSession")
            if not cookie:
                return None
            return {"MoodleSession": cookie, "saved_at": raw.get("saved_at", 0.0)}
        except Exception as exc:
            logger.debug("Failed to read Moodle session file: %s", exc)
            return None

    def load_spada(self) -> dict | None:
        """Read SPADA session from disk or return None if missing."""
        if not settings.spada_session_file or not settings.spada_session_file.exists():
            return None
        try:
            return json.loads(settings.spada_session_file.read_text())
        except Exception as exc:
            logger.debug("Failed to read SPADA session file: %s", exc)
            return None

    def validate_moodle(self, moodle_session: str) -> bool:
        """
        Validate Moodle session against the live server.

        Moodle at lmsslc.polinema.ac.id uses a valid TLS certificate, but the
        intermediate CA is not trusted by the default Python OpenSSL trust store
        on macOS, hence verify=False is required here.
        """
        try:
            resp = httpx.get(
                f"{settings.moodle_base_url}/my/",
                cookies={settings.moodle_cookie_name: moodle_session},
                follow_redirects=False,
                timeout=10.0,
                verify=False,
            )
            # Valid session returns 200 OK. Expired session issues a 303 redirect to login.
            if resp.status_code != 200:
                return False
            # Guard against guest sessions: Moodle can return 200 on /my/ for anonymous
            # users but embed a login redirect link in the page body.
            return "login/index.php" not in resp.text
        except Exception as exc:
            logger.warning("Moodle session validation network check failed: %s", exc)
            return False

    def get_valid_session(self) -> SessionData:
        """
        Return a validated Moodle session or raise SessionExpiredError.

        Session validation results are cached in memory for session_cache_ttl_seconds
        to prevent redundant HTTP roundtrips across successive tool calls.
        """
        with self._lock:
            now = time.time()
            if (
                self._cached_session
                and (now - self._cache_timestamp) < settings.session_cache_ttl_seconds
            ):
                return self._cached_session

        stored = self.load_moodle()
        if not stored:
            raise SessionExpiredError("No Moodle session found on disk.")

        if not self.validate_moodle(stored["MoodleSession"]):
            with self._lock:
                self._cached_session = None
            raise SessionExpiredError("Moodle session has expired or is invalid.")

        with self._lock:
            self._cached_session = stored
            self._cache_timestamp = time.time()

        return stored

    def invalidate_cache(self) -> None:
        """Invalidate the in-memory validation cache."""
        with self._lock:
            self._cached_session = None
            self._cache_timestamp = 0.0
