"""Comprehensive unit test suite for MoodleScraper."""

from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest

from lms_polinema_mcp.exceptions import ParseError
from lms_polinema_mcp.models.assignment import AssignmentSummary
from lms_polinema_mcp.models.course import Course
from lms_polinema_mcp.models.material import CourseMaterial
from lms_polinema_mcp.services.moodle import MoodleScraper

SAMPLE_COURSE_HTML = """
<html>
  <body>
    <div class="course-content">
      <div class="activity">
        <a href="https://lmsslc.polinema.ac.id/mod/assign/view.php?id=101">
          <span class="instancename">Jobsheet 01 Assignment</span>
        </a>
      </div>
      <div class="activity">
        <a href="https://lmsslc.polinema.ac.id/mod/resource/view.php?id=201">
          <span class="instancename">Slide Bab 01 File</span>
        </a>
      </div>
      <div class="activity">
        <a href="https://lmsslc.polinema.ac.id/mod/folder/view.php?id=301">
          <span class="instancename">Kumpulan Modul Folder</span>
        </a>
      </div>
      <!-- Duplicate link should be ignored -->
      <div class="activity">
        <a href="https://lmsslc.polinema.ac.id/mod/resource/view.php?id=201">
          <span class="instancename">Slide Bab 01 File</span>
        </a>
      </div>
    </div>
  </body>
</html>
"""

SAMPLE_ASSIGN_WITH_DUE_DATE_HTML = """
<html>
  <body>
    <h2>Jobsheet 01 Submission</h2>
    <div id="intro">
      <p>Silakan unggah laporan jobsheet 1 di sini.</p>
      <a href="https://lmsslc.polinema.ac.id/pluginfile.php/123/mod_assign/intro/Jobsheet01.pdf">Jobsheet01.pdf</a>
    </div>
    <div class="submissionstatustable">
      <table class="generaltable">
        <tr>
          <th>Submission status</th>
          <td>Submitted for grading</td>
        </tr>
        <tr>
          <th>Grading status</th>
          <td>Not graded</td>
        </tr>
        <tr>
          <th>Due date</th>
          <td>Thursday, 3 September 2026, 12:00 AM</td>
        </tr>
        <tr>
          <th>Time remaining</th>
          <td>Assignment was submitted 1 hour 5 mins early</td>
        </tr>
        <tr>
          <th>Last modified</th>
          <td>Wednesday, 2 September 2026, 10:54 PM</td>
        </tr>
      </table>
    </div>
  </body>
</html>
"""

SAMPLE_ASSIGN_WITHOUT_DUE_DATE_HTML = """
<html>
  <body>
    <h3>Programming Task</h3>
    <div id="intro">
      <p>Tugas mandiri tanpa batas waktu.</p>
    </div>
    <table class="generaltable">
      <tr>
        <th>Submission status</th>
        <td>No attempt</td>
      </tr>
      <tr>
        <th>Grading status</th>
        <td>Not graded</td>
      </tr>
      <tr>
        <th>Last modified</th>
        <td>-</td>
      </tr>
    </table>
  </body>
</html>
"""


@pytest.mark.asyncio
async def test_get_course_modules_success():
    """Verify parsing of course modules separating assignments and materials."""
    mock_client = AsyncMock()
    mock_resp = MagicMock(spec=httpx.Response, status_code=200, text=SAMPLE_COURSE_HTML)
    mock_client.get.return_value = mock_resp

    scraper = MoodleScraper(mock_client)
    items = await scraper.get_course_modules(course_id=13430)

    assert len(items) == 3

    # Check Assignment
    assignment = next(it for it in items if isinstance(it, AssignmentSummary))
    assert assignment.assignment_id == 101
    assert assignment.title == "Jobsheet 01"
    assert assignment.url == "https://lmsslc.polinema.ac.id/mod/assign/view.php?id=101"

    # Check File Resource Material
    file_material = next(it for it in items if isinstance(it, CourseMaterial) and it.id == 201)
    assert file_material.name == "Slide Bab 01"
    assert file_material.type == "resource"

    # Check Folder Material
    folder_material = next(it for it in items if isinstance(it, CourseMaterial) and it.id == 301)
    assert folder_material.name == "Kumpulan Modul"
    assert folder_material.type == "folder"


@pytest.mark.asyncio
async def test_get_course_modules_http_error():
    """Verify graceful error recovery when fetching course modules fails."""
    mock_client = AsyncMock()
    mock_resp = MagicMock(spec=httpx.Response, status_code=500)
    mock_resp.raise_for_status.side_effect = httpx.HTTPStatusError(
        "500 Server Error", request=MagicMock(), response=mock_resp
    )
    mock_client.get.return_value = mock_resp

    scraper = MoodleScraper(mock_client)
    items = await scraper.get_course_modules(course_id=13430)

    assert items == []


@pytest.mark.asyncio
async def test_get_assignment_detail_with_due_date():
    """Verify parsing of assignment detail including due date and attachment."""
    mock_client = AsyncMock()
    mock_resp = MagicMock(spec=httpx.Response, status_code=200, text=SAMPLE_ASSIGN_WITH_DUE_DATE_HTML)
    mock_client.get.return_value = mock_resp

    scraper = MoodleScraper(mock_client)
    detail = await scraper.get_assignment_detail(assignment_id=101)

    assert detail.assignment_id == 101
    assert detail.title == "Jobsheet 01 Submission"
    assert "Silakan unggah laporan" in detail.description
    assert detail.due_date == "Thursday, 3 September 2026, 12:00 AM"
    assert detail.submission_status == "Submitted for grading"
    assert detail.grading_status == "Not graded"
    assert detail.time_remaining == "Assignment was submitted 1 hour 5 mins early"
    assert detail.last_modified == "Wednesday, 2 September 2026, 10:54 PM"
    assert len(detail.attachments) == 1
    assert detail.attachments[0].filename == "Jobsheet01.pdf"


@pytest.mark.asyncio
async def test_get_assignment_detail_without_due_date():
    """Verify assignment detail parsing when lecturer does not configure due date."""
    mock_client = AsyncMock()
    mock_resp = MagicMock(spec=httpx.Response, status_code=200, text=SAMPLE_ASSIGN_WITHOUT_DUE_DATE_HTML)
    mock_client.get.return_value = mock_resp

    scraper = MoodleScraper(mock_client)
    detail = await scraper.get_assignment_detail(assignment_id=102)

    assert detail.assignment_id == 102
    assert detail.title == "Programming Task"
    assert detail.due_date is None
    assert detail.time_remaining is None
    assert detail.submission_status == "No attempt"
    assert detail.grading_status == "Not graded"
    assert detail.last_modified == "-"
    assert detail.attachments == []


@pytest.mark.asyncio
async def test_get_assignment_detail_http_error():
    """Verify ParseError is raised when assignment page fetch fails."""
    mock_client = AsyncMock()
    mock_resp = MagicMock(spec=httpx.Response, status_code=404)
    mock_resp.raise_for_status.side_effect = httpx.HTTPStatusError(
        "404 Not Found", request=MagicMock(), response=mock_resp
    )
    mock_client.get.return_value = mock_resp

    scraper = MoodleScraper(mock_client)
    with pytest.raises(ParseError, match="Failed to fetch assignment page 101"):
        await scraper.get_assignment_detail(assignment_id=101)


@pytest.mark.asyncio
async def test_get_all_assignments_with_and_without_filter():
    """Verify filtering assignments across courses and enriching course name."""
    mock_client = AsyncMock()
    scraper = MoodleScraper(mock_client)

    course_pbo = Course(title="Pemrograman Berbasis Objek", moodle_id=13430)
    course_metnum = Course(title="Metode Numerik", moodle_id=13459)
    course_no_moodle = Course(title="Agama", moodle_id=None)

    courses = [course_pbo, course_metnum, course_no_moodle]

    # Mock get_course_modules for each course
    assign_pbo = AssignmentSummary(
        assignment_id=101,
        course="",
        course_id=13430,
        title="Jobsheet 01",
        url="https://lmsslc.polinema.ac.id/mod/assign/view.php?id=101",
    )
    assign_metnum = AssignmentSummary(
        assignment_id=201,
        course="",
        course_id=13459,
        title="Tugas Galat",
        url="https://lmsslc.polinema.ac.id/mod/assign/view.php?id=201",
    )

    async def mock_modules(course_id: int):
        if course_id == 13430:
            return [assign_pbo]
        if course_id == 13459:
            return [assign_metnum]
        return []

    scraper.get_course_modules = AsyncMock(side_effect=mock_modules)

    # 1. Fetch all assignments
    all_assigns = await scraper.get_all_assignments(courses)
    assert len(all_assigns) == 2
    course_names = {a.course for a in all_assigns}
    assert course_names == {"Pemrograman Berbasis Objek", "Metode Numerik"}

    # 2. Fetch with filter
    filtered = await scraper.get_all_assignments(courses, course_id_filter=13430)
    assert len(filtered) == 1
    assert filtered[0].title == "Jobsheet 01"
    assert filtered[0].course == "Pemrograman Berbasis Objek"


@pytest.mark.asyncio
async def test_get_deadlines_concurrent_success():
    """Verify gathering deadlines concurrently across courses."""
    mock_client = AsyncMock()
    scraper = MoodleScraper(mock_client)

    course_pbo = Course(title="PBO", moodle_id=13430)
    assign = AssignmentSummary(
        assignment_id=101,
        course="PBO",
        course_id=13430,
        title="Jobsheet 01",
        url="https://lmsslc.polinema.ac.id/mod/assign/view.php?id=101",
    )

    scraper.get_all_assignments = AsyncMock(return_value=[assign])

    mock_detail = MagicMock(
        due_date="Thursday, 3 September 2026",
        time_remaining="1 hour early",
        submission_status="Submitted for grading",
    )
    scraper.get_assignment_detail = AsyncMock(return_value=mock_detail)

    deadlines = await scraper.get_deadlines([course_pbo])
    assert len(deadlines) == 1
    assert deadlines[0].course == "PBO"
    assert deadlines[0].title == "Jobsheet 01"
    assert deadlines[0].due_date == "Thursday, 3 September 2026"
    assert deadlines[0].submission_status == "Submitted for grading"


@pytest.mark.asyncio
async def test_get_deadlines_partial_failure():
    """Verify fallback to Unknown submission status when a single deadline detail fails."""
    mock_client = AsyncMock()
    scraper = MoodleScraper(mock_client)

    course = Course(title="PBO", moodle_id=13430)
    assign = AssignmentSummary(
        assignment_id=101,
        course="PBO",
        course_id=13430,
        title="Broken Task",
        url="https://lmsslc.polinema.ac.id/mod/assign/view.php?id=101",
    )

    scraper.get_all_assignments = AsyncMock(return_value=[assign])
    scraper.get_assignment_detail = AsyncMock(side_effect=ParseError("Network error"))

    deadlines = await scraper.get_deadlines([course])
    assert len(deadlines) == 1
    assert deadlines[0].title == "Broken Task"
    assert deadlines[0].due_date is None
    assert deadlines[0].submission_status == "Unknown"
