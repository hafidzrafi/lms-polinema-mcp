"""Comprehensive unit tests for pure HTTP SessionRefresher."""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from lms_polinema_mcp.auth.credentials import CredentialStore
from lms_polinema_mcp.auth.refresh import SessionRefresher
from lms_polinema_mcp.auth.session import SessionManager
from lms_polinema_mcp.config import settings
from lms_polinema_mcp.exceptions import AuthenticationError


@pytest.fixture
def mock_credential_store():
    store = MagicMock(spec=CredentialStore)
    store.load.return_value = ("254107020084", "secret_pass")
    return store


@pytest.fixture
def mock_session_manager():
    mgr = MagicMock(spec=SessionManager)
    return mgr


@pytest.mark.asyncio
async def test_refresh_async_success(mock_credential_store, mock_session_manager):
    refresher = SessionRefresher(mock_credential_store, mock_session_manager)

    mock_client = AsyncMock()

    # 1. GET login
    resp_get_login = MagicMock(spec=httpx.Response, status_code=200)

    # 2. POST login
    resp_post_login = MagicMock(spec=httpx.Response, status_code=200)
    resp_post_login.json.return_value = {"output": "ok"}

    # 3. GET SLC
    resp_slc = MagicMock(
        spec=httpx.Response, status_code=200, url="http://slc.polinema.ac.id/spada/"
    )

    # 4. GET SPADA matakuliah
    spada_html = """
    <html>
        <div class="gallery_grid_item" title="PBO">
            <a href="https://lmsslc.polinema.ac.id/course/view.php?id=13430">Course Link</a>
        </div>
    </html>
    """
    resp_spada = MagicMock(spec=httpx.Response, status_code=200, text=spada_html)

    # 5. GET bridge
    resp_bridge = MagicMock(spec=httpx.Response, status_code=200)

    mock_client.get.side_effect = [resp_get_login, resp_slc, resp_spada, resp_bridge]
    mock_client.post.return_value = resp_post_login

    mock_client.cookies = {
        "polinema_sso": "sso_token_123",
        "POLIMASPADA": "spada_token_456",
        "MoodleSession": "moodle_token_789",
    }

    with patch("httpx.AsyncClient", return_value=mock_client):
        mock_client.__aenter__.return_value = mock_client
        moodle, spada = await refresher.refresh_async()

    assert moodle == "moodle_token_789"
    assert spada == "spada_token_456"
    mock_session_manager.save_moodle.assert_called_once_with("moodle_token_789")
    mock_session_manager.save_spada.assert_called_once_with("spada_token_456")
    mock_session_manager.invalidate_cache.assert_called_once()
    assert mock_client.get.call_args_list[3][0][0] == "https://lmsslc.polinema.ac.id/course/view.php?id=13430"


@pytest.mark.asyncio
async def test_refresh_async_fallback_to_moodle_my(mock_credential_store, mock_session_manager):
    """When SPADA has zero course bridge links, refresher must fall back to /my/."""
    refresher = SessionRefresher(mock_credential_store, mock_session_manager)

    mock_client = AsyncMock()

    resp_get_login = MagicMock(spec=httpx.Response, status_code=200)
    resp_post_login = MagicMock(spec=httpx.Response, status_code=200)
    resp_post_login.json.return_value = {"output": "ok"}
    resp_slc = MagicMock(spec=httpx.Response, status_code=200)

    # SPADA page without any moodle bridge links
    empty_spada_html = "<html><body><div>No courses</div></body></html>"
    resp_spada = MagicMock(spec=httpx.Response, status_code=200, text=empty_spada_html)
    resp_bridge = MagicMock(spec=httpx.Response, status_code=200)

    mock_client.get.side_effect = [resp_get_login, resp_slc, resp_spada, resp_bridge]
    mock_client.post.return_value = resp_post_login

    mock_client.cookies = {
        "polinema_sso": "sso_token_123",
        "POLIMASPADA": "spada_token_456",
        "MoodleSession": "moodle_token_789",
    }

    with patch("httpx.AsyncClient", return_value=mock_client):
        mock_client.__aenter__.return_value = mock_client
        moodle, spada = await refresher.refresh_async()

    assert moodle == "moodle_token_789"
    assert spada == "spada_token_456"
    # Verify fallback bridge URL was called
    expected_fallback_url = f"{settings.moodle_base_url}/my/"
    assert mock_client.get.call_args_list[3][0][0] == expected_fallback_url


@pytest.mark.asyncio
async def test_refresh_async_invalid_credentials(mock_credential_store, mock_session_manager):
    refresher = SessionRefresher(mock_credential_store, mock_session_manager)

    mock_client = AsyncMock()
    resp_get = MagicMock(spec=httpx.Response, status_code=200)
    resp_post = MagicMock(spec=httpx.Response, status_code=200)
    resp_post.json.return_value = {"output": "Username atau password salah"}

    mock_client.get.return_value = resp_get
    mock_client.post.return_value = resp_post
    mock_client.cookies = {}

    with patch("httpx.AsyncClient", return_value=mock_client):
        mock_client.__aenter__.return_value = mock_client
        with pytest.raises(AuthenticationError, match="SIAKAD login failed"):
            await refresher.refresh_async()


@pytest.mark.asyncio
async def test_refresh_async_non_json_response(mock_credential_store, mock_session_manager):
    """When server returns HTML error page instead of JSON, raises AuthenticationError."""
    refresher = SessionRefresher(mock_credential_store, mock_session_manager)

    mock_client = AsyncMock()
    resp_get = MagicMock(spec=httpx.Response, status_code=200)
    resp_post = MagicMock(spec=httpx.Response, status_code=500, text="<html>500 Server Error</html>")
    resp_post.json.side_effect = ValueError("Invalid JSON")

    mock_client.get.return_value = resp_get
    mock_client.post.return_value = resp_post

    with patch("httpx.AsyncClient", return_value=mock_client):
        mock_client.__aenter__.return_value = mock_client
        with pytest.raises(AuthenticationError, match="non-JSON response"):
            await refresher.refresh_async()


@pytest.mark.asyncio
async def test_refresh_async_network_error(mock_credential_store, mock_session_manager):
    """When network fails during login POST, catches RequestError specifically."""
    refresher = SessionRefresher(mock_credential_store, mock_session_manager)

    mock_client = AsyncMock()
    resp_get = MagicMock(spec=httpx.Response, status_code=200)
    mock_client.get.return_value = resp_get
    mock_client.post.side_effect = httpx.ConnectError("Connection refused")

    with patch("httpx.AsyncClient", return_value=mock_client):
        mock_client.__aenter__.return_value = mock_client
        with pytest.raises(AuthenticationError, match="Network error during SIAKAD login POST"):
            await refresher.refresh_async()


@pytest.mark.asyncio
async def test_refresh_async_missing_spada_cookie(mock_credential_store, mock_session_manager):
    refresher = SessionRefresher(mock_credential_store, mock_session_manager)

    mock_client = AsyncMock()
    resp_get_login = MagicMock(spec=httpx.Response, status_code=200)
    resp_post_login = MagicMock(spec=httpx.Response, status_code=200)
    resp_post_login.json.return_value = {"output": "ok"}
    resp_slc = MagicMock(spec=httpx.Response, status_code=200)

    mock_client.get.side_effect = [resp_get_login, resp_slc]
    mock_client.post.return_value = resp_post_login
    # Missing POLIMASPADA cookie
    mock_client.cookies = {"polinema_sso": "token"}

    with patch("httpx.AsyncClient", return_value=mock_client):
        mock_client.__aenter__.return_value = mock_client
        with pytest.raises(AuthenticationError, match="did not issue POLIMASPADA"):
            await refresher.refresh_async()


def test_refresh_sync_wrapper(mock_credential_store, mock_session_manager):
    refresher = SessionRefresher(mock_credential_store, mock_session_manager)
    with patch.object(refresher, "refresh_async", new_callable=AsyncMock) as mock_async:
        mock_async.return_value = ("moodle_123", "spada_456")
        res = refresher.refresh()
        assert res == ("moodle_123", "spada_456")
        mock_async.assert_called_once()
