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

        Raises:
            CredentialsNotFoundError: If no credentials exist on disk.
            AuthenticationError: If SIAKAD login or SSO bridge fails.
        """
        nim, password = self.credential_store.load()
        logger.info("Initiating headless authentication session for user %s", nim)

        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            context = browser.new_context(ignore_https_errors=True)
            page = context.new_page()

            # Step 1: Login to SIAKAD
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
                browser.close()
                msg = (
                    f"SIAKAD login failed: {alert_text}"
                    if alert_text
                    else "SIAKAD login timed out."
                )
                raise AuthenticationError(msg) from exc
            except Exception as exc:
                browser.close()
                raise AuthenticationError(f"Unexpected error during SIAKAD login: {exc}") from exc

            # Step 2: Navigate to SIAKAD LMS Connector page
            slc_url = f"{settings.siakad_base_url}{settings.siakad_lms_path}"
            try:
                page.goto(slc_url, wait_until="networkidle", timeout=20_000)
            except Exception as exc:
                logger.warning("Failed direct navigation to LMS connector, retrying: %s", exc)
                page.goto(slc_url, wait_until="domcontentloaded", timeout=20_000)

            # Step 3: Trigger LMS connection bridge
            try:
                connect_btn = (
                    page.locator("a, button").filter(has_text="Connect to LMS Polinema").first
                )
                connect_btn.wait_for(state="visible", timeout=15_000)

                with context.expect_page(timeout=10_000) as new_page_info:
                    connect_btn.click()
                new_page = new_page_info.value
                new_page.wait_for_load_state("networkidle", timeout=20_000)
            except Exception:
                # If popup was not triggered, button might redirect the current page
                try:
                    connect_btn = (
                        page.locator("a, button").filter(has_text="Connect to LMS Polinema").first
                    )
                    connect_btn.click()
                    page.wait_for_load_state("networkidle", timeout=15_000)
                except Exception as exc:
                    logger.warning("Failed to trigger Connect button automatically: %s", exc)

            # Step 4: Extract cookies from browser context
            cookies_dict = {c["name"]: c["value"] for c in context.cookies()}
            polimaspada = cookies_dict.get(settings.spada_cookie_name, "")
            moodle_session = cookies_dict.get(settings.moodle_cookie_name, "")

            # If MoodleSession was not immediately captured, trigger LMS navigation explicitly
            if not moodle_session:
                try:
                    lms_page = context.new_page()
                    lms_page.goto(
                        f"{settings.moodle_base_url}/my/", wait_until="networkidle", timeout=15_000
                    )
                    cookies_dict = {c["name"]: c["value"] for c in context.cookies()}
                    moodle_session = cookies_dict.get(settings.moodle_cookie_name, "")
                except Exception as exc:
                    logger.debug("Failed secondary Moodle navigation: %s", exc)

            browser.close()

            if not moodle_session:
                raise AuthenticationError("Failed to obtain MoodleSession cookie from SSO bridge.")

            # Step 5: Save cookies and invalidate cache
            self.session_manager.save_moodle(moodle_session)
            if polimaspada:
                self.session_manager.save_spada(polimaspada)
            self.session_manager.invalidate_cache()
            logger.info("Session refreshed and saved successfully.")
