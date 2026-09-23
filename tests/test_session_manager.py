"""Unit tests for SessionManager persistence, validation, and caching."""

from unittest.mock import MagicMock, patch

import httpx
import pytest

from lms_polinema_mcp.auth.session import SessionManager
from lms_polinema_mcp.config import settings
from lms_polinema_mcp.exceptions import SessionExpiredError


@pytest.fixture
def temp_session_dir(tmp_path, monkeypatch):
    session_dir = tmp_path / "sessions"
    session_dir.mkdir()
    moodle_file = session_dir / "moodle_session.json"
    spada_file = session_dir / "spada_session.json"

    monkeypatch.setattr(settings, "session_dir", session_dir)
    monkeypatch.setattr(settings, "moodle_session_file", moodle_file)
    monkeypatch.setattr(settings, "spada_session_file", spada_file)
    return session_dir


def test_save_and_load_moodle(temp_session_dir):
    mgr = SessionManager()
    assert mgr.load_moodle() is None

    mgr.save_moodle("test_moodle_cookie_123")
    loaded = mgr.load_moodle()

    assert loaded is not None
    assert loaded["MoodleSession"] == "test_moodle_cookie_123"
    assert loaded["saved_at"] > 0


def test_save_and_load_spada(temp_session_dir):
    mgr = SessionManager()
    assert mgr.load_spada() is None

    mgr.save_spada("test_spada_cookie_456")
    loaded = mgr.load_spada()

    assert loaded is not None
    assert loaded[settings.spada_cookie_name] == "test_spada_cookie_456"


def test_validate_moodle_success(temp_session_dir):
    mgr = SessionManager()
    mock_resp = MagicMock(spec=httpx.Response, status_code=200, text="<html>Dashboard User</html>")

    with patch("httpx.get", return_value=mock_resp):
        assert mgr.validate_moodle("valid_session") is True


def test_validate_moodle_expired_redirect(temp_session_dir):
    mgr = SessionManager()
    # 303 Redirect to login
    mock_resp = MagicMock(spec=httpx.Response, status_code=303, text="")

    with patch("httpx.get", return_value=mock_resp):
        assert mgr.validate_moodle("expired_session") is False


def test_validate_moodle_guest_session(temp_session_dir):
    mgr = SessionManager()
    # 200 OK but contains login/index.php redirect link
    mock_resp = MagicMock(
        spec=httpx.Response,
        status_code=200,
        text="<html><a href='https://lmsslc.polinema.ac.id/login/index.php'>Login</a></html>",
    )

    with patch("httpx.get", return_value=mock_resp):
        assert mgr.validate_moodle("guest_session") is False


def test_get_valid_session_caching(temp_session_dir):
    mgr = SessionManager()
    mgr.save_moodle("test_session_cached")
    # Invalidate initial save cache to force network validation check
    mgr.invalidate_cache()

    mock_resp = MagicMock(spec=httpx.Response, status_code=200, text="<html>Dashboard</html>")
    with patch("httpx.get", return_value=mock_resp) as mock_get:
        # First call hits network validation
        sess1 = mgr.get_valid_session()
        assert sess1["MoodleSession"] == "test_session_cached"
        assert mock_get.call_count == 1

        # Second call returns from in-memory cache
        sess2 = mgr.get_valid_session()
        assert sess2["MoodleSession"] == "test_session_cached"
        assert mock_get.call_count == 1

        # After invalidation, hits network again
        mgr.invalidate_cache()
        sess3 = mgr.get_valid_session()
        assert sess3["MoodleSession"] == "test_session_cached"
        assert mock_get.call_count == 2


def test_get_valid_session_raises_when_missing(temp_session_dir):
    mgr = SessionManager()
    with pytest.raises(SessionExpiredError, match="No Moodle session found"):
        mgr.get_valid_session()
