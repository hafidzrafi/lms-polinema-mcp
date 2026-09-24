"""Pure HTTP automated session refresher for SIAKAD, SPADA, and Moodle."""

import asyncio
import json
import logging

import httpx
from bs4 import BeautifulSoup

from lms_polinema_mcp.auth.credentials import CredentialStore
from lms_polinema_mcp.auth.session import SessionManager
from lms_polinema_mcp.config import settings
from lms_polinema_mcp.exceptions import AuthenticationError

logger = logging.getLogger(__name__)

# SIAKAD reverse proxy returns 404 HTML if a non-browser User-Agent is presented.
# A standard cross-platform desktop browser header ensures compatibility across macOS, Linux, and Windows.
_DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/128.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "X-Requested-With": "XMLHttpRequest",
}


class SessionRefresher:
    """Performs lightweight, pure HTTP authentication to capture and persist session cookies."""

    def __init__(
        self,
        credential_store: CredentialStore,
        session_manager: SessionManager,
    ) -> None:
        self.credential_store = credential_store
        self.session_manager = session_manager

    async def refresh_async(self) -> tuple[str, str]:
        """
        Execute 4-step pure HTTP authentication chain:
        1. Login to SIAKAD via jQuery AJAX POST.
        2. Follow SLC SSO handshake with polinema_sso cookie to establish POLIMASPADA.
        3. Discover Moodle course bridge link from SPADA.
        4. Navigate to bridge link to establish MoodleSession.
        """
        nim, password = self.credential_store.load()
        logger.info("Initiating pure HTTP authentication for user %s", nim)

        async with httpx.AsyncClient(
            verify=settings.http_verify_ssl,
            follow_redirects=True,
            timeout=settings.http_timeout,
            headers=_DEFAULT_HEADERS,
        ) as client:
            # Step 1: Visit login page to initialize cookies
            login_url = f"{settings.siakad_base_url}/login"
            try:
                r_get = await client.get(login_url)
                r_get.raise_for_status()
            except httpx.HTTPStatusError as exc:
                raise AuthenticationError(
                    f"SIAKAD login page returned HTTP {exc.response.status_code}."
                ) from exc
            except httpx.RequestError as exc:
                raise AuthenticationError(
                    f"Failed to reach SIAKAD login page: {exc}"
                ) from exc

            # Step 2: POST login form
            post_headers = {
                "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
                "Referer": login_url,
            }
            try:
                r_post = await client.post(
                    login_url,
                    data={"username": nim, "password": password},
                    headers=post_headers,
                )
                r_post.raise_for_status()
            except httpx.HTTPStatusError as exc:
                raise AuthenticationError(
                    f"SIAKAD login POST returned HTTP {exc.response.status_code}."
                ) from exc
            except httpx.RequestError as exc:
                raise AuthenticationError(
                    f"Network error during SIAKAD login POST: {exc}"
                ) from exc

            try:
                data = r_post.json()
            except (json.JSONDecodeError, ValueError) as exc:
                raise AuthenticationError(
                    f"SIAKAD portal returned non-JSON response (status {r_post.status_code}). "
                    "Portal may be undergoing maintenance."
                ) from exc

            output_status = data.get("output")
            if output_status != "ok":
                raise AuthenticationError(
                    f"SIAKAD login failed: {output_status or 'Invalid response from portal'}"
                )

            polinema_sso = client.cookies.get("polinema_sso", "")

            # Step 3: Access SLC gateway to establish POLIMASPADA
            slc_cookies = {"polinema_sso": polinema_sso} if polinema_sso else None
            try:
                r_slc = await client.get("https://slc.polinema.ac.id", cookies=slc_cookies)
                r_slc.raise_for_status()
            except httpx.HTTPStatusError as exc:
                raise AuthenticationError(
                    f"SPADA gateway returned HTTP {exc.response.status_code}."
                ) from exc
            except httpx.RequestError as exc:
                raise AuthenticationError(
                    f"Failed to connect to SPADA gateway: {exc}"
                ) from exc

            polimaspada = client.cookies.get(settings.spada_cookie_name, "")
            if not polimaspada:
                raise AuthenticationError("SPADA gateway did not issue POLIMASPADA session cookie.")

            # Step 4: Discover Moodle bridge link from SPADA matakuliah page
            spada_courses_url = f"{settings.spada_base_url}/?mod=matakuliah"
            try:
                r_spada = await client.get(spada_courses_url)
                r_spada.raise_for_status()
            except httpx.HTTPStatusError as exc:
                raise AuthenticationError(
                    f"SPADA course page returned HTTP {exc.response.status_code}."
                ) from exc
            except httpx.RequestError as exc:
                raise AuthenticationError(
                    f"Failed to fetch SPADA course page: {exc}"
                ) from exc

            soup = BeautifulSoup(r_spada.text, "html.parser")
            bridge_url = None
            for a_tag in soup.find_all("a", href=True):
                href = a_tag["href"]
                if "lmsslc.polinema.ac.id" in href:
                    bridge_url = href
                    break

            if not bridge_url:
                # Fallback to direct Moodle dashboard
                bridge_url = f"{settings.moodle_base_url}/my/"

            # Step 5: Establish MoodleSession via bridge
            try:
                r_bridge = await client.get(bridge_url)
                r_bridge.raise_for_status()
            except httpx.HTTPStatusError as exc:
                raise AuthenticationError(
                    f"Moodle bridge returned HTTP {exc.response.status_code}."
                ) from exc
            except httpx.RequestError as exc:
                raise AuthenticationError(
                    f"Failed to establish Moodle session: {exc}"
                ) from exc

            moodle_session = client.cookies.get(settings.moodle_cookie_name, "")
            if not moodle_session:
                raise AuthenticationError("Moodle bridge did not issue MoodleSession cookie.")

            # Persist captured cookies
            self.session_manager.save_moodle(moodle_session)
            self.session_manager.save_spada(polimaspada)
            self.session_manager.invalidate_cache()

            logger.info("Pure HTTP authentication completed successfully.")
            return moodle_session, polimaspada

    def refresh(self) -> tuple[str, str]:
        """Synchronous wrapper for CLI utilities."""
        return asyncio.run(self.refresh_async())
