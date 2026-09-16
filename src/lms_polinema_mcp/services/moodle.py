"""HTML parser and scraper for Moodle LMS courses and assignments."""

import asyncio
import logging
import re

import httpx
from bs4 import BeautifulSoup

from lms_polinema_mcp.config import settings
from lms_polinema_mcp.exceptions import ParseError
from lms_polinema_mcp.models.assignment import (
    AssignmentDetail,
    AssignmentSummary,
    Attachment,
    DeadlineItem,
)
from lms_polinema_mcp.models.course import Course
from lms_polinema_mcp.models.material import CourseMaterial

logger = logging.getLogger(__name__)

_MOD_TYPE_SUFFIX_RE = re.compile(r"\s+(Assignment|File|Folder|Quiz|URL|Page|Forum)$", re.IGNORECASE)
_SUBMISSION_TABLE_FIELDS = {
    "submission status": "submission_status",
    "grading status": "grading_status",
    "due date": "due_date",
    "time remaining": "time_remaining",
    "last modified": "last_modified",
}


class MoodleScraper:
    """Scrapes module, assignment, and submission data from Moodle LMS pages."""

    def __init__(self, client: httpx.AsyncClient) -> None:
        self.client = client

    async def get_course_modules(self, course_id: int) -> list[CourseMaterial | AssignmentSummary]:
        """
        Fetch all activity modules and assignments for a single course page.

        Returns a list of CourseMaterial items or AssignmentSummary items.
        """
        url = f"{settings.moodle_base_url}/course/view.php?id={course_id}"
        try:
            resp = await self.client.get(url)
            resp.raise_for_status()
        except Exception as exc:
            logger.warning("Failed to fetch course modules for course %d: %s", course_id, exc)
            return []

        soup = BeautifulSoup(resp.text, "html.parser")
        items: list[CourseMaterial | AssignmentSummary] = []
        seen_urls: set[str] = set()

        for a_tag in soup.find_all("a", href=re.compile(r"/mod/")):
            href = a_tag["href"].strip()
            if href in seen_urls:
                continue
            seen_urls.add(href)

            inst = a_tag.find(class_="instancename")
            raw_name = inst.text.strip() if inst else a_tag.get_text(strip=True)
            clean_name = _MOD_TYPE_SUFFIX_RE.sub("", raw_name).strip() or raw_name

            mod_type = ""
            if "/mod/" in href:
                mod_type = href.split("/mod/")[1].split("/")[0]

            id_match = re.search(r"id=(\d+)", href)
            mod_id = int(id_match.group(1)) if id_match else None

            if mod_type == "assign" and mod_id is not None:
                items.append(
                    AssignmentSummary(
                        assignment_id=mod_id,
                        title=clean_name,
                        course="",  # populated by caller when course context is known
                        course_id=course_id,
                        url=href,
                    )
                )
            else:
                items.append(
                    CourseMaterial(
                        id=mod_id,
                        name=clean_name,
                        type=mod_type,
                        url=href,
                    )
                )

        return items

    async def get_assignment_detail(self, assignment_id: int) -> AssignmentDetail:
        """Fetch complete assignment instructions and submission table."""
        url = f"{settings.moodle_base_url}/mod/assign/view.php?id={assignment_id}"
        try:
            resp = await self.client.get(url)
            resp.raise_for_status()
        except Exception as exc:
            raise ParseError(f"Failed to fetch assignment page {assignment_id}: {exc}") from exc

        soup = BeautifulSoup(resp.text, "html.parser")

        title_elem = soup.find("h2") or soup.find("h3")
        title = title_elem.text.strip() if title_elem else "Assignment"

        intro = soup.find(id="intro")
        description = intro.get_text(separator="\n", strip=True) if intro else ""

        attachments: list[Attachment] = []
        if intro:
            for a_link in intro.find_all("a", href=True):
                filename = a_link.get_text(strip=True)
                if filename:
                    attachments.append(Attachment(filename=filename, url=a_link["href"]))

        fields: dict[str, str | None] = {
            "submission_status": "Unknown",
            "grading_status": "Unknown",
            "due_date": None,
            "time_remaining": None,
            "last_modified": None,
        }

        table = soup.find("table", class_="generaltable")
        if table:
            for row in table.find_all("tr"):
                th = row.find("th")
                td = row.find("td")
                if th and td:
                    header = th.text.strip().lower()
                    val = td.text.strip()
                    for key_substr, field_key in _SUBMISSION_TABLE_FIELDS.items():
                        if key_substr in header:
                            fields[field_key] = val
                            break

        return AssignmentDetail(
            assignment_id=assignment_id,
            title=title,
            url=url,
            description=description,
            attachments=attachments,
            submission_status=fields["submission_status"] or "Unknown",
            grading_status=fields["grading_status"] or "Unknown",
            due_date=fields["due_date"],
            time_remaining=fields["time_remaining"],
            last_modified=fields["last_modified"],
        )

    async def get_all_assignments(
        self, courses: list[Course], course_id_filter: int | None = None
    ) -> list[AssignmentSummary]:
        """
        Concurrently fetch assignment summaries across all active courses.

        Uses asyncio.gather to perform course page requests in parallel.
        """
        targets = [c for c in courses if c.moodle_id is not None]
        if course_id_filter is not None:
            targets = [c for c in targets if c.moodle_id == course_id_filter]

        if not targets:
            return []

        sem = asyncio.Semaphore(5)

        async def _fetch_course_assignments(course: Course) -> list[AssignmentSummary]:
            assert course.moodle_id is not None
            async with sem:
                modules = await self.get_course_modules(course.moodle_id)
            return [
                item.model_copy(update={"course": course.title})
                for item in modules
                if isinstance(item, AssignmentSummary)
            ]

        results = await asyncio.gather(*[_fetch_course_assignments(c) for c in targets])
        all_assignments: list[AssignmentSummary] = []
        for subset in results:
            all_assignments.extend(subset)

        return all_assignments

    async def get_deadlines(self, courses: list[Course]) -> list[DeadlineItem]:
        """
        Concurrently fetch deadline items for all assignments across all courses.

        Step 1: Parallel fetch of assignment lists across courses.
        Step 2: Parallel fetch of assignment details for all discovered assignments.
        """
        assignments = await self.get_all_assignments(courses)
        if not assignments:
            return []

        sem = asyncio.Semaphore(5)

        async def _fetch_deadline(summary: AssignmentSummary) -> DeadlineItem:
            try:
                async with sem:
                    detail = await self.get_assignment_detail(summary.assignment_id)
                return DeadlineItem(
                    course=summary.course,
                    title=summary.title,
                    due_date=detail.due_date,
                    time_remaining=detail.time_remaining,
                    submission_status=detail.submission_status,
                    url=summary.url,
                )
            except Exception as exc:
                logger.warning(
                    "Failed to fetch detail for deadline %d: %s", summary.assignment_id, exc
                )
                return DeadlineItem(
                    course=summary.course,
                    title=summary.title,
                    due_date=None,
                    time_remaining=None,
                    submission_status="Unknown",
                    url=summary.url,
                )

        deadlines = await asyncio.gather(*[_fetch_deadline(a) for a in assignments])
        return list(deadlines)
