"""Domain models for LMS Polinema MCP server."""

from lms_polinema_mcp.models.assignment import (
    AssignmentDetail,
    AssignmentSummary,
    Attachment,
    DeadlineItem,
)
from lms_polinema_mcp.models.course import Course
from lms_polinema_mcp.models.material import CourseMaterial, ModuleType

__all__ = [
    "AssignmentDetail",
    "AssignmentSummary",
    "Attachment",
    "Course",
    "CourseMaterial",
    "DeadlineItem",
    "ModuleType",
]
