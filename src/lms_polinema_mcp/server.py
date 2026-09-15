"""LMS Polinema MCP Server

Menyediakan tools resmi untuk AI Agents dalam mengakses:
- Daftar mata kuliah aktif semester ini di Polinema
- Seluruh tugas (assignments), status pengumpulan, dan tenggat waktu (due date)
- Detail instruksi dan file attachment tugas
- Modul dan materi perkuliahan (jobsheet, slide, modul)
"""

from typing import Any, Optional
from mcp.server.mcpserver import MCPServer

from lms_polinema_mcp.api.moodle import LMSClient
from lms_polinema_mcp.auth.session import SessionManager

mcp = MCPServer("lms-polinema-mcp")
_session_manager = SessionManager()


def _get_client() -> LMSClient:
    session = _session_manager.get_valid_session()
    if not session:
        raise RuntimeError(
            "❌ Sesi LMS Polinema belum terautentikasi atau sudah kedaluwarsa.\n"
            "Jalankan: uv run python auth.py di direktori lms-polinema-mcp"
        )
    return LMSClient(moodle_session=session["MoodleSession"])


@mcp.tool()
def lms_list_courses() -> list[dict[str, Any]]:
    """Dapatkan daftar seluruh mata kuliah aktif semester ini di Polinema beserta Moodle course ID dan URL."""
    client = _get_client()
    return client.get_enrolled_courses()


@mcp.tool()
def lms_list_assignments(course_id: Optional[int] = None) -> list[dict[str, Any]]:
    """Daftar seluruh tugas kuliah dari semua mata kuliah aktif, atau difilter berdasarkan course_id."""
    client = _get_client()
    return client.get_all_assignments(course_id_filter=course_id)


@mcp.tool()
def lms_get_assignment_detail(assignment_id: int) -> dict[str, Any]:
    """Ambil rincian instruksi tugas, file attachment, batas waktu (due date), time remaining, dan status submission."""
    client = _get_client()
    return client.get_assignment_detail(assignment_id)


@mcp.tool()
def lms_list_materials(course_id: int) -> list[dict[str, Any]]:
    """Dapatkan seluruh file materi, jobsheet, dan slide pertemuan untuk suatu mata kuliah di LMS."""
    client = _get_client()
    modules = client.get_course_modules(course_id)
    return [m for m in modules if m["type"] != "assign"]


@mcp.tool()
def lms_check_deadlines() -> list[dict[str, Any]]:
    """Periksa ringkasan tenggat waktu (due dates) tugas-tugas aktif dan sisa waktu pengumpulan dari semua mata kuliah."""
    client = _get_client()
    all_assigns = client.get_all_assignments()
    deadlines = []
    for a in all_assigns:
        detail = client.get_assignment_detail(a["assignment_id"])
        deadlines.append({
            "course": a["course"],
            "task": a["title"],
            "due_date": detail.get("due_date"),
            "time_remaining": detail.get("time_remaining"),
            "submission_status": detail.get("submission_status"),
            "url": a["url"],
        })
    return deadlines


def main():
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
