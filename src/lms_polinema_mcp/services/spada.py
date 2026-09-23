"""HTML parser and scraper for the SPADA course discovery portal."""

import logging
import re

import httpx
from bs4 import BeautifulSoup

from lms_polinema_mcp.config import settings
from lms_polinema_mcp.exceptions import ParseError, SessionExpiredError
from lms_polinema_mcp.models.course import Course

logger = logging.getLogger(__name__)


class SpadaScraper:
    """Scrapes enrolled academic courses from the SPADA student portal."""

    def __init__(self, client: httpx.AsyncClient) -> None:
        self.client = client

    async def get_enrolled_courses(self) -> list[Course]:
        """
        Fetch and parse the enrolled course list from SPADA.

        Raises:
            SessionExpiredError: If SPADA session is invalid or user is not logged in.
            ParseError: If parsing fails to process the page structure.
        """
        url = f"{settings.spada_base_url}/?mod=matakuliah"
        try:
            resp = await self.client.get(url)
            resp.raise_for_status()
        except (httpx.HTTPStatusError, httpx.RequestError) as exc:
            raise ParseError(f"Failed to fetch SPADA course page: {exc}") from exc

        text = resp.text

        # Validate that the page is an authenticated view rather than a guest/login page.
        # `and` binds tighter than `or` in Python, so parentheses are required to express intent.
        if "IDXPG='GES'" in text or ("gsi_btn" in text and "gallery_grid_item" not in text):
            raise SessionExpiredError("SPADA session is expired or unauthenticated.")

        soup = BeautifulSoup(text, "html.parser")
        cards = soup.find_all("div", class_="gallery_grid_item")
        if not cards:
            # If logged in but zero courses found, check if it's genuinely empty
            logger.info("Zero course cards found on SPADA matakuliah page.")
            return []

        courses: list[Course] = []
        for card in cards:
            title = card.get("title", "").strip()
            if not title:
                caption = card.find(class_="gallery_image_title")
                title = caption.text.strip() if caption else "Unknown Course"

            a_tag = card.find("a")
            href = a_tag["href"].strip() if a_tag and a_tag.has_attr("href") else None

            moodle_id: int | None = None
            moodle_url: str | None = None

            if href and "lmsslc.polinema.ac.id" in href:
                moodle_url = href
                id_match = re.search(r"id=(\d+)", href)
                if id_match:
                    moodle_id = int(id_match.group(1))

            courses.append(
                Course(
                    title=title,
                    moodle_id=moodle_id,
                    moodle_url=moodle_url,
                )
            )

        logger.info("Successfully parsed %d courses from SPADA.", len(courses))
        return courses
