"""Headless automated session refresher using Playwright."""

import contextlib
import logging

from playwright.sync_api import TimeoutError as PlaywrightTimeout
from playwright.sync_api import sync_playwright

from lms_polinema_mcp.auth.credentials import CredentialStore
from lms_polinema_mcp.auth.session import SessionManager
from lms_polinema_mcp.config import settings
from lms_polinema_mcp.exceptions import AuthenticationError

logger = logging.getLogger(__name__)


class SessionRefresher:
    """Performs headless browser automation to obtain and store fresh session cookies."""

    def __init__(
        self,
        credential_store: CredentialStore,
        session_manager: SessionManager,
    ) -> None:
        self.credential_store = credential_store
        self.session_manager = session_manager

    def refresh(self) -> None:
        """
        Execute headless authentication chain: SIAKAD -> SPADA -> LMS.

        Flow:
        1. Authenticate to SIAKAD portal with credentials.
        2. Navigate directly to SPADA gateway (http://slc.polinema.ac.id).
           The server verifies the SIAKAD session and completes SSO authorization.
        3. Navigate to SPADA course listing and click a Moodle bridge link
           to establish the authenticated MoodleSession cookie.
        4. Capture both cookies and persist them to disk.
        """
        nim, password = self.credential_store.load()
        logger.info("Initiating headless authentication session for user %s", nim)

        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            context = browser.new_context(ignore_https_errors=True)
            page = context.new_page()

            try:
                # Step 1: Login to SIAKAD portal
                login_url = f"{settings.siakad_base_url}/login"
                try:
                    page.goto(login_url, wait_until="networkidle", timeout=30_000)
                    page.fill("#username", nim)
                    page.fill("#password", password)
                    page.click("button[type='submit']")

                    page.wait_for_url(lambda u: "/login" not in u, timeout=25_000)
                    logger.info("SIAKAD authentication successful.")
                except PlaywrightTimeout as exc:
                    alert_text = ""
                    with contextlib.suppress(Exception):
                        alert_text = page.locator("#alert-login").inner_text(timeout=2000)
                    msg = (
                        f"SIAKAD login failed: {alert_text}"
                        if alert_text
                        else "SIAKAD login timed out."
                    )
                    raise AuthenticationError(msg) from exc
                except Exception as exc:
                    raise AuthenticationError(
                        f"Unexpected error during SIAKAD login: {exc}"
                    ) from exc

                # Step 2: Open SPADA gateway via SIAKAD SSO bridge
                try:
                    spada_page = context.new_page()
                    spada_page.goto(
                        "http://slc.polinema.ac.id", wait_until="networkidle", timeout=25_000
                    )
                    logger.info("SPADA portal connected: %s", spada_page.title())
                except Exception as exc:
                    raise AuthenticationError(f"Failed to connect to SPADA portal: {exc}") from exc

                # Step 3: Trigger Moodle SSO handshake by navigating to a course link
                try:
                    spada_page.goto(
                        f"{settings.spada_base_url}/?mod=matakuliah",
                        wait_until="networkidle",
                        timeout=20_000,
                    )
                    course_link = spada_page.locator("a[href*='lmsslc.polinema.ac.id']").first
                    if course_link.count() > 0:
                        with context.expect_page(timeout=15_000) as lms_page_info:
                            course_link.click()
                        lms_page = lms_page_info.value
                        lms_page.wait_for_load_state("networkidle", timeout=20_000)
                        logger.info("Moodle session established: %s", lms_page.title())
                except Exception as exc:
                    logger.warning("Course bridge navigation notice: %s", exc)

                # Step 4: Extract cookies from browser context
                cookies_dict = {c["name"]: c["value"] for c in context.cookies()}
                polimaspada = cookies_dict.get(settings.spada_cookie_name, "")
                moodle_session = cookies_dict.get(settings.moodle_cookie_name, "")

                # If MoodleSession was not yet captured, attempt direct dashboard verification
                if not moodle_session:
                    try:
                        verify_page = context.new_page()
                        verify_page.goto(
                            f"{settings.moodle_base_url}/my/",
                            wait_until="networkidle",
                            timeout=15_000,
                        )
                        cookies_dict = {c["name"]: c["value"] for c in context.cookies()}
                        moodle_session = cookies_dict.get(settings.moodle_cookie_name, "")
                    except Exception as exc:
                        logger.debug("Secondary Moodle navigation failed: %s", exc)

            finally:
                browser.close()

            if not polimaspada and not moodle_session:
                raise AuthenticationError(
                    "Failed to capture SPADA or Moodle authentication cookies."
                )

            # Step 5: Save cookies and invalidate cache
            if moodle_session:
                self.session_manager.save_moodle(moodle_session)
            if polimaspada:
                self.session_manager.save_spada(polimaspada)

            self.session_manager.invalidate_cache()
            logger.info("Authentication cookies refreshed and persisted successfully.")
