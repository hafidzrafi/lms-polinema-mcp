"""Data models representing course materials, files, and resources in LMS Polinema."""

from pydantic import BaseModel


class ModuleType:
    """Standard module activity type identifiers in Moodle."""

    RESOURCE = "resource"
    FOLDER = "folder"
    URL = "url"
    PAGE = "page"
    FORUM = "forum"
    QUIZ = "quiz"
    ASSIGN = "assign"


class CourseMaterial(BaseModel):
    """Educational material or non-assignment activity item within a course."""

    id: int | None = None
    name: str
    type: str
    url: str
