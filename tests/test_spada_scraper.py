"""Unit tests for SPADA scraper."""

from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest

from lms_polinema_mcp.exceptions import ParseError, SessionExpiredError
from lms_polinema_mcp.services.spada import SpadaScraper


@pytest.mark.asyncio
async def test_get_enrolled_courses_success():
    html_content = """
    <html>
        <body>
            <div class="gallery_grid_item" title="Bahasa Inggris 2">
                <a href="https://lmsslc.polinema.ac.id/course/view.php?id=13430">Link</a>
            </div>
            <div class="gallery_grid_item" title="Pemrograman Berbasis Objek">
                <a href="https://lmsslc.polinema.ac.id/course/view.php?id=13150">Link</a>
            </div>
            <div class="gallery_grid_item">
                <div class="gallery_image_title">Desain dan Pemrograman Web</div>
                <a href="https://other.link">Link</a>
            </div>
        </body>
    </html>
    """
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_resp = MagicMock(spec=httpx.Response, status_code=200, text=html_content)
    mock_client.get.return_value = mock_resp

    scraper = SpadaScraper(mock_client)
    courses = await scraper.get_enrolled_courses()

    assert len(courses) == 3
    assert courses[0].title == "Bahasa Inggris 2"
    assert courses[0].moodle_id == 13430
    assert courses[0].moodle_url == "https://lmsslc.polinema.ac.id/course/view.php?id=13430"

    assert courses[1].title == "Pemrograman Berbasis Objek"
    assert courses[1].moodle_id == 13150

    assert courses[2].title == "Desain dan Pemrograman Web"
    assert courses[2].moodle_id is None
    assert courses[2].moodle_url is None


@pytest.mark.asyncio
async def test_get_enrolled_courses_guest_session_error():
    guest_html = "<html><script>var IDXPG='GES';</script></html>"
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_resp = MagicMock(spec=httpx.Response, status_code=200, text=guest_html)
    mock_client.get.return_value = mock_resp

    scraper = SpadaScraper(mock_client)
    with pytest.raises(SessionExpiredError, match="SPADA session is expired"):
        await scraper.get_enrolled_courses()


@pytest.mark.asyncio
async def test_get_enrolled_courses_unauthenticated_gsi_error():
    gsi_html = "<html><div class='gsi_btn'>Login with Google</div></html>"
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_resp = MagicMock(spec=httpx.Response, status_code=200, text=gsi_html)
    mock_client.get.return_value = mock_resp

    scraper = SpadaScraper(mock_client)
    with pytest.raises(SessionExpiredError, match="SPADA session is expired"):
        await scraper.get_enrolled_courses()


@pytest.mark.asyncio
async def test_get_enrolled_courses_empty_authenticated():
    empty_html = "<html><script>var IDXPG='2f91e811';</script><body><div>No courses</div></body></html>"
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_resp = MagicMock(spec=httpx.Response, status_code=200, text=empty_html)
    mock_client.get.return_value = mock_resp

    scraper = SpadaScraper(mock_client)
    courses = await scraper.get_enrolled_courses()
    assert courses == []


@pytest.mark.asyncio
async def test_get_enrolled_courses_network_error():
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.get.side_effect = httpx.ConnectError("Network down")

    scraper = SpadaScraper(mock_client)
    with pytest.raises(ParseError, match="Failed to fetch SPADA course page"):
        await scraper.get_enrolled_courses()
