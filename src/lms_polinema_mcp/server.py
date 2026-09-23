"""LMS Polinema MCP Server implementation."""

import logging

from mcp.server.mcpserver import MCPServer

from lms_polinema_mcp.auth.credentials import CredentialStore
from lms_polinema_mcp.auth.refresh import SessionRefresher
from lms_polinema_mcp.auth.session import SessionManager
from lms_polinema_mcp.cache import TTLCache
from lms_polinema_mcp.config import settings
from lms_polinema_mcp.exceptions import (
    AuthenticationError,
    CredentialsNotFoundError,
    SessionExpiredError,
)
from lms_polinema_mcp.models.assignment import (
    AssignmentDetail,
    AssignmentSummary,
    DeadlineItem,
)
from lms_polinema_mcp.models.course import Course
from lms_polinema_mcp.models.material import CourseMaterial
from lms_polinema_mcp.services.http import create_moodle_client, create_spada_client
from lms_polinema_mcp.services.moodle import MoodleScraper
from lms_polinema_mcp.services.spada import SpadaScraper

logger = logging.getLogger(__name__)

mcp = MCPServer("lms-polinema-mcp")

_session_manager = SessionManager()
_credential_store = CredentialStore()
_refresher = SessionRefresher(_credential_store, _session_manager)
_course_cache: TTLCache[list[Course]] = TTLCache(ttl_seconds=settings.course_cache_ttl_seconds)


async def _get_authenticated_sessions(force_refresh: bool = False) -> tuple[str, str]:
    """
    Return active (moodle_session, polimaspada) cookies, performing auto-refresh if necessary.

    Raises:
        CredentialsNotFoundError: If no stored credentials exist for refresh.
        AuthenticationError: If automated session refresh fails.
    """
    if not force_refresh:
        try:
            session = _session_manager.get_valid_session()
            spada_data = _session_manager.load_spada() or {}
            polimaspada = spada_data.get(settings.spada_cookie_name, "")
            if polimaspada:
                return session["MoodleSession"], polimaspada
        except SessionExpiredError:
            logger.info("Session expired or missing. Checking stored credentials for auto-refresh.")

    if not _credential_store.exists():
        raise CredentialsNotFoundError(
            "LMS session expired and no stored credentials found. "
            "Please run 'uv run auth.py' to configure."
        )

    try:
        moodle_session, polimaspada = await _refresher.refresh_async()
        return moodle_session, polimaspada
    except AuthenticationError as exc:
        raise AuthenticationError(
            f"Failed to automatically refresh LMS session: {exc}. "
            "Please run 'uv run auth.py' to re-authenticate."
        ) from exc
    except Exception as exc:
        raise AuthenticationError(
            f"Unexpected error refreshing LMS session: {exc}. "
            "Please run 'uv run auth.py' to re-authenticate."
        ) from exc


@mcp.tool()
async def lms_list_courses() -> list[Course]:
    """Return all enrolled academic courses for the current semester from SPADA portal."""
    cached = _course_cache.get("enrolled")
    if cached is not None:
        return cached

    _, polimaspada = await _get_authenticated_sessions()
    async with create_spada_client(polimaspada) as client:
        scraper = SpadaScraper(client)
        try:
            courses = await scraper.get_enrolled_courses()
        except SessionExpiredError:
            # SPADA cookie expired while Moodle was valid; trigger forced refresh and retry once
            _session_manager.invalidate_cache()
            _, polimaspada = await _get_authenticated_sessions(force_refresh=True)
            async with create_spada_client(polimaspada) as retry_client:
                retry_scraper = SpadaScraper(retry_client)
                courses = await retry_scraper.get_enrolled_courses()

    _course_cache.set("enrolled", courses)
    return courses


@mcp.tool()
async def lms_list_assignments(course_id: int | None = None) -> list[AssignmentSummary]:
    """Return all active assignments, optionally filtered by specific course_id."""
    courses = await lms_list_courses()
    moodle_session, _ = await _get_authenticated_sessions()

    async with create_moodle_client(moodle_session) as client:
        scraper = MoodleScraper(client)
        return await scraper.get_all_assignments(courses, course_id_filter=course_id)


@mcp.tool()
async def lms_get_assignment_detail(assignment_id: int) -> AssignmentDetail:
    """Return complete assignment details including instructions, attachments, and submission status."""
    moodle_session, _ = await _get_authenticated_sessions()
    async with create_moodle_client(moodle_session) as client:
        scraper = MoodleScraper(client)
        return await scraper.get_assignment_detail(assignment_id)


@mcp.tool()
async def lms_list_materials(course_id: int) -> list[CourseMaterial]:
    """Return all educational material items (slides, documents, folders) for a specific course."""
    moodle_session, _ = await _get_authenticated_sessions()
    async with create_moodle_client(moodle_session) as client:
        scraper = MoodleScraper(client)
        modules = await scraper.get_course_modules(course_id)
        return [m for m in modules if isinstance(m, CourseMaterial)]


@mcp.tool()
async def lms_check_deadlines() -> list[DeadlineItem]:
    """Return deadline summary for all active assignments across all enrolled courses."""
    courses = await lms_list_courses()
    moodle_session, _ = await _get_authenticated_sessions()

    async with create_moodle_client(moodle_session) as client:
        scraper = MoodleScraper(client)
        return await scraper.get_deadlines(courses)


def main() -> None:
    """Start MCP stdio server transport."""
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
