"""LMS Polinema API & HTML Client

Mengambil data kursus, tugas, materi, dan status pengumpulan dari:
1. SPADA (slc.polinema.ac.id/spada) untuk discovery mata kuliah semester ini
2. LMS Moodle (lmsslc.polinema.ac.id) untuk detail tugas, modul materi, dan batas waktu
"""

import json
import re
from typing import Any, Optional
from bs4 import BeautifulSoup
import httpx

from lms_polinema_mcp.config import MOODLE_BASE_URL, SPADA_BASE_URL, SPADA_SESSION_FILE


class LMSClient:
    def __init__(self, moodle_session: str):
        self.moodle_session = moodle_session
        self.spada_cookie = self._load_spada_cookie()
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept-Language": "id-ID,id;q=0.9,en-US;q=0.8",
        }
        self.client = httpx.Client(
            cookies={"MoodleSession": self.moodle_session},
            headers=self.headers,
            follow_redirects=True,
            verify=False,
            timeout=25.0,
        )

    def _load_spada_cookie(self) -> str:
        if SPADA_SESSION_FILE.exists():
            try:
                data = json.loads(SPADA_SESSION_FILE.read_text())
                return data.get("POLIMASPADA", "")
            except Exception:
                pass
        return ""

    def get_enrolled_courses(self) -> list[dict[str, Any]]:
        """Ambil daftar mata kuliah semester ini dari SPADA portal."""
        courses = []
        cookies = {}
        if self.spada_cookie:
            cookies["POLIMASPADA"] = self.spada_cookie

        try:
            r = httpx.get(
                f"{SPADA_BASE_URL}/?mod=matakuliah",
                cookies=cookies,
                headers=self.headers,
                verify=False,
                timeout=15.0,
            )
            soup = BeautifulSoup(r.text, "html.parser")
            cards = soup.find_all("div", class_="gallery_grid_item")
            for c in cards:
                title = c.get("title", "").strip()
                if not title:
                    caption = c.find(class_="gallery_image_title")
                    title = caption.text.strip() if caption else ""
                
                a_tag = c.find("a")
                href = a_tag["href"] if a_tag and a_tag.has_attr("href") else ""
                
                # Extract moodle course ID if present
                moodle_id = None
                if "id=" in href:
                    match = re.search(r"id=(\d+)", href)
                    if match:
                        moodle_id = int(match.group(1))

                courses.append({
                    "title": title,
                    "moodle_id": moodle_id,
                    "moodle_url": href if moodle_id else None,
                })
        except Exception as e:
            # Fallback jika SPADA offline, gunakan fallback hardcoded atau Moodle dashboard
            pass

        return courses

    def get_course_modules(self, course_id: int) -> list[dict[str, Any]]:
        """Ambil semua materi dan aktivitas dari suatu mata kuliah di LMS Moodle."""
        r = self.client.get(f"{MOODLE_BASE_URL}/course/view.php?id={course_id}")
        soup = BeautifulSoup(r.text, "html.parser")

        modules = []
        for a in soup.find_all("a", href=re.compile(r"/mod/")):
            href = a["href"]
            inst = a.find(class_="instancename")
            name = inst.text.strip() if inst else a.get_text(strip=True)
            
            # Format clean name (hapus tulisan 'Assignment', 'File', dll di akhir)
            clean_name = re.sub(r"\s+(Assignment|File|Folder|Quiz|URL|Page|Forum)$", "", name, flags=re.I).strip()
            
            mod_type = ""
            if "/mod/" in href:
                mod_type = href.split("/mod/")[1].split("/")[0]

            match_id = re.search(r"id=(\d+)", href)
            mod_id = int(match_id.group(1)) if match_id else None

            # Hindari duplikasi link activity yang sama
            if not any(m.get("url") == href for m in modules):
                modules.append({
                    "id": mod_id,
                    "name": clean_name or name,
                    "type": mod_type,
                    "url": href,
                })

        return modules

    def get_all_assignments(self, course_id_filter: Optional[int] = None) -> list[dict[str, Any]]:
        """Kumpulkan semua tugas dari seluruh mata kuliah aktif."""
        courses = self.get_enrolled_courses()
        all_assignments = []

        target_courses = [c for c in courses if c.get("moodle_id")]
        if course_id_filter:
            target_courses = [c for c in target_courses if c.get("moodle_id") == course_id_filter]

        for c in target_courses:
            cid = c["moodle_id"]
            cname = c["title"]
            modules = self.get_course_modules(cid)
            assign_modules = [m for m in modules if m["type"] == "assign"]

            for m in assign_modules:
                all_assignments.append({
                    "course": cname,
                    "course_id": cid,
                    "assignment_id": m["id"],
                    "title": m["name"],
                    "url": m["url"],
                })

        return all_assignments

    def get_assignment_detail(self, assignment_id: int) -> dict[str, Any]:
        """Ambil detail instruksi, batas waktu, dan status submission tugas."""
        url = f"{MOODLE_BASE_URL}/mod/assign/view.php?id={assignment_id}"
        r = self.client.get(url)
        soup = BeautifulSoup(r.text, "html.parser")

        title_elem = soup.find("h2") or soup.find("h3")
        title = title_elem.text.strip() if title_elem else "Tugas"

        # Deskripsi / instruksi tugas
        intro = soup.find(id="intro")
        description = intro.get_text(separator="\n", strip=True) if intro else ""

        # Attachment files
        attachments = []
        if intro:
            for a in intro.find_all("a", href=True):
                attachments.append({
                    "filename": a.get_text(strip=True),
                    "url": a["href"],
                })

        # Parse tabel submission
        info = {
            "title": title,
            "assignment_id": assignment_id,
            "url": url,
            "description": description,
            "attachments": attachments,
            "submission_status": "Unknown",
            "grading_status": "Unknown",
            "due_date": "Not specified",
            "time_remaining": "Not specified",
            "last_modified": "-",
        }

        table = soup.find("table", class_="generaltable")
        if table:
            for row in table.find_all("tr"):
                th = row.find("th")
                td = row.find("td")
                if th and td:
                    header = th.text.strip().lower()
                    val = td.text.strip()
                    if "submission status" in header:
                        info["submission_status"] = val
                    elif "grading status" in header:
                        info["grading_status"] = val
                    elif "due date" in header:
                        info["due_date"] = val
                    elif "time remaining" in header:
                        info["time_remaining"] = val
                    elif "last modified" in header:
                        info["last_modified"] = val

        return info
