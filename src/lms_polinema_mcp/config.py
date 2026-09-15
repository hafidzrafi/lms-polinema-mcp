"""LMS Polinema MCP - Configuration"""

from pathlib import Path

# ─── SIAKAD (auth entry point) ─────────────────────────────────────────────────
SIAKAD_BASE_URL = "https://siakad.polinema.ac.id"

# ─── Moodle LMS ────────────────────────────────────────────────────────────────
MOODLE_BASE_URL = "https://lmsslc.polinema.ac.id"

# ─── SPADA Portal (course discovery + SSO bridge) ──────────────────────────────
SPADA_BASE_URL = "https://slc.polinema.ac.id/spada"
SPADA_COOKIE_NAME = "POLIMASPADA"

# ─── A known Moodle course URL from SPADA — used to trigger SSO bridge ─────────
# Update this if the course ID changes (any enrolled course works)
SPADA_LMS_BRIDGE_URL = "https://lmsslc.polinema.ac.id/my/"

# ─── Session storage ───────────────────────────────────────────────────────────
SESSION_DIR = Path.home() / ".lms_polinema"
MOODLE_SESSION_FILE = SESSION_DIR / "moodle_session.json"
SPADA_SESSION_FILE = SESSION_DIR / "spada_session.json"

# ─── Institution branding ──────────────────────────────────────────────────────
INSTITUTION = "Polinema"
INSTITUTION_FULL = "Politeknik Negeri Malang"

