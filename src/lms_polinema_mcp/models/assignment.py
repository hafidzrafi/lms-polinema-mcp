"""Data models representing assignments, submissions, and deadlines in LMS Polinema."""

from pydantic import BaseModel


class Attachment(BaseModel):
    """File attachment referenced in assignment instructions."""

    filename: str
    url: str


class AssignmentSummary(BaseModel):
    """Compact assignment summary for listings across courses."""

    assignment_id: int
    title: str
    course: str
    course_id: int
    url: str


class AssignmentDetail(BaseModel):
    """Detailed assignment record including submission status and instructions."""

    assignment_id: int
    title: str
    url: str
    description: str
    attachments: list[Attachment] = []
    submission_status: str = "Unknown"
    grading_status: str = "Unknown"
    due_date: str | None = None
    time_remaining: str | None = None
    last_modified: str | None = None


class DeadlineItem(BaseModel):
    """Summary item for active assignment deadlines."""

    course: str
    title: str
    due_date: str | None = None
    time_remaining: str | None = None
    submission_status: str = "Unknown"
    url: str
