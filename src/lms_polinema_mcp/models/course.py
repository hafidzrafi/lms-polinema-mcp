"""Data models representing courses in SPADA and LMS Polinema."""

from pydantic import BaseModel


class Course(BaseModel):
    """Enrolled academic course discovered from SPADA portal."""

    title: str
    moodle_id: int | None = None
    moodle_url: str | None = None
