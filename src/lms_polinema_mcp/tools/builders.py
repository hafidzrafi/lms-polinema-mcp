"""Tool implementations for LMS Polinema MCP."""

from datetime import datetime, timezone
from typing import Any


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _fmt_ts(ts: int | None) -> str | None:
    """Format a Unix timestamp to ISO 8601 string."""
    if not ts:
        return None
    return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


def _is_expired(ts: int | None) -> bool:
    if not ts:
        return False
    return ts < datetime.now(tz=timezone.utc).timestamp()


# ─── Tool: list_courses ────────────────────────────────────────────────────────

def build_list_courses(courses_raw: list[dict]) -> list[dict]:
    return [
        {
            "id": c["id"],
            "fullname": c["fullname"],
            "shortname": c["shortname"],
            "category": c.get("categoryname", ""),
            "url": f"https://lmsslc.polinema.ac.id/course/view.php?id={c['id']}",
        }
        for c in courses_raw
        if c.get("enrolledusercount", 1) > 0  # filter archived/empty
    ]


# ─── Tool: list_assignments ───────────────────────────────────────────────────

def build_list_assignments(
    courses_with_assignments: list[dict],
    full_data: bool = False,
) -> list[dict]:
    results = []
    for course in courses_with_assignments:
        course_name = course.get("fullname", "")
        course_id = course.get("id")
        for a in course.get("assignments", []):
            due_ts = a.get("duedate") or None
            item: dict[str, Any] = {
                "id": a["id"],
                "course_id": course_id,
                "course": course_name,
                "title": a["name"],
                "deadline": _fmt_ts(due_ts),
                "overdue": _is_expired(due_ts),
                "url": f"https://lmsslc.polinema.ac.id/mod/assign/view.php?id={a.get('cmid', '')}",
            }
            if full_data:
                item["intro"] = a.get("intro", "")
                item["max_grade"] = a.get("grade", 0)
                item["allow_late"] = bool(a.get("allowsubmissionsfromdate"))
            results.append(item)

    # Sort by deadline ascending (None = no deadline → last)
    results.sort(key=lambda x: x["deadline"] or "9999")
    return results


# ─── Tool: check_deadlines ───────────────────────────────────────────────────

def build_upcoming_deadlines(
    courses_with_assignments: list[dict], days: int = 7
) -> list[dict]:
    from datetime import timedelta
    now = datetime.now(tz=timezone.utc)
    cutoff = (now + timedelta(days=days)).timestamp()

    results = []
    for course in courses_with_assignments:
        for a in course.get("assignments", []):
            due_ts = a.get("duedate")
            if due_ts and now.timestamp() < due_ts <= cutoff:
                results.append({
                    "id": a["id"],
                    "course": course.get("fullname", ""),
                    "title": a["name"],
                    "deadline": _fmt_ts(due_ts),
                    "days_left": round((due_ts - now.timestamp()) / 86400, 1),
                    "url": f"https://lmsslc.polinema.ac.id/mod/assign/view.php?id={a.get('cmid', '')}",
                })

    results.sort(key=lambda x: x["days_left"])
    return results


# ─── Tool: get_assignment_detail ─────────────────────────────────────────────

def build_assignment_detail(submission_status: dict, assignment_id: int) -> dict:
    lastattempt = submission_status.get("lastattempt", {})
    submission = lastattempt.get("submission", {})
    plugins = submission.get("plugins", [])

    # Find file/text submissions
    files = []
    text = ""
    for plugin in plugins:
        if plugin["type"] == "file":
            for fa in plugin.get("fileareas", []):
                for f in fa.get("files", []):
                    files.append({
                        "name": f["filename"],
                        "url": f["fileurl"],
                        "size": f.get("filesize", 0),
                    })
        elif plugin["type"] == "onlinetext":
            for ed in plugin.get("editorfields", []):
                text = ed.get("text", "")

    grading = submission_status.get("gradingsummary", {})

    return {
        "assignment_id": assignment_id,
        "status": lastattempt.get("submissionsenabled", False),
        "submitted": bool(submission.get("status") == "submitted"),
        "submitted_at": _fmt_ts(submission.get("timemodified")),
        "graded": grading.get("submissionsneedgrading", 0) == 0,
        "files_submitted": files,
        "text_submitted": text[:500] if text else "",
        "grade_info": submission_status.get("feedback", {}),
    }


# ─── Tool: list_materials ─────────────────────────────────────────────────────

def build_list_materials(course_contents: list[dict], full_data: bool = False) -> list[dict]:
    results = []
    for section in course_contents:
        section_name = section.get("name", "")
        for mod in section.get("modules", []):
            item: dict[str, Any] = {
                "section": section_name,
                "type": mod.get("modname", ""),
                "name": mod.get("name", ""),
                "url": mod.get("url", ""),
            }
            if full_data and mod.get("contents"):
                item["files"] = [
                    {"name": f["filename"], "url": f["fileurl"]}
                    for f in mod["contents"]
                    if f.get("fileurl")
                ]
            results.append(item)
    return results


# ─── Tool: get_grades ────────────────────────────────────────────────────────

def build_grades(grade_data: dict) -> list[dict]:
    items = grade_data.get("usergrades", [{}])[0].get("gradeitems", [])
    return [
        {
            "item": g.get("itemname", "Course total"),
            "grade": g.get("gradeformatted", "-"),
            "max": g.get("grademax", 100),
            "percentage": g.get("percentageformatted", "-"),
            "feedback": g.get("feedback", ""),
        }
        for g in items
        if g.get("gradeformatted") and g.get("gradeformatted") != "-"
    ]
