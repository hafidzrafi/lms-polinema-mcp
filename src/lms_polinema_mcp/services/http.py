"""HTTP client factories for SPADA and Moodle requests."""

import httpx

from lms_polinema_mcp import __version__
from lms_polinema_mcp.config import settings


def create_moodle_client(moodle_session: str) -> httpx.AsyncClient:
    """Return an async HTTP client pre-configured for Moodle requests."""
    return httpx.AsyncClient(
        cookies={settings.moodle_cookie_name: moodle_session},
        headers={
            "User-Agent": f"Mozilla/5.0 (compatible; lms-polinema-mcp/{__version__})",
            "Accept-Language": "en-US,en;q=0.9",
        },
        follow_redirects=True,
        verify=settings.http_verify_ssl,
        timeout=settings.http_timeout,
    )


def create_spada_client(polimaspada: str) -> httpx.AsyncClient:
    """Return an async HTTP client pre-configured for SPADA portal requests."""
    return httpx.AsyncClient(
        cookies={settings.spada_cookie_name: polimaspada},
        headers={
            "User-Agent": f"Mozilla/5.0 (compatible; lms-polinema-mcp/{__version__})",
            "Accept-Language": "en-US,en;q=0.9",
        },
        follow_redirects=True,
        verify=settings.http_verify_ssl,
        timeout=settings.http_timeout,
    )
