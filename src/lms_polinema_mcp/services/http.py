"""HTTP client factories for SPADA and Moodle requests."""

import httpx

from lms_polinema_mcp.config import settings


def create_moodle_client(moodle_session: str) -> httpx.AsyncClient:
    """
    Return an async HTTP client pre-configured for Moodle requests.

    SSL verification is disabled (verify=False) because the university Moodle
    server uses an intermediate Certificate Authority (GeoTrust / DigiCert)
    that is not present in the default Python OpenSSL bundle on macOS.
    """
    return httpx.AsyncClient(
        cookies={settings.moodle_cookie_name: moodle_session},
        headers={
            "User-Agent": "Mozilla/5.0 (compatible; lms-polinema-mcp/2.0)",
            "Accept-Language": "en-US,en;q=0.9",
        },
        follow_redirects=True,
        verify=False,
        timeout=settings.http_timeout,
    )


def create_spada_client(polimaspada: str) -> httpx.AsyncClient:
    """Return an async HTTP client pre-configured for SPADA portal requests."""
    return httpx.AsyncClient(
        cookies={settings.spada_cookie_name: polimaspada},
        headers={
            "User-Agent": "Mozilla/5.0 (compatible; lms-polinema-mcp/2.0)",
            "Accept-Language": "en-US,en;q=0.9",
        },
        follow_redirects=True,
        verify=False,
        timeout=settings.http_timeout,
    )
