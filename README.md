# lms-polinema-mcp

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python: 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![MCP: 2.x](https://img.shields.io/badge/MCP-2.x-green.svg)](https://modelcontextprotocol.io)

An MCP server for LMS Polinema. Gives AI agents access to your courses, assignments, deadlines, and materials.

Works with Claude Code, Cursor, Antigravity, or any MCP-compatible client.

## How it works

Polinema does not allow direct Moodle logins with student credentials. Authentication flows through an institutional single sign-on chain: SIAKAD (academic portal) → SLC (SPADA gateway) → LMSSLC (Moodle).

On first run, `auth.py` drives headless Chromium to authenticate via SIAKAD (NIM and password), exchanges tokens through SLC, and captures the authenticated `MoodleSession`. Session cookies are saved to `~/.lms_polinema/`. When a session expires, the server re-authenticates automatically in the background.

## Tools

| Tool | Parameters | Returns |
|---|---|---|
| `lms_list_courses` | - | Enrolled courses for the current semester |
| `lms_list_assignments` | `course_id` (int, optional) | Assignments, optionally filtered by course |
| `lms_get_assignment_detail` | `assignment_id` (int) | Instructions, attachments, submission status |
| `lms_list_materials` | `course_id` (int) | Slides, jobsheets, and other course files |
| `lms_check_deadlines` | - | Deadline summary across all courses |

## Installation

Requires Python 3.11+ and [uv](https://astral.sh/uv).

```bash
git clone https://github.com/hafidzrafi/lms-polinema-mcp.git
cd lms-polinema-mcp
uv sync
uv run playwright install chromium
```

Run once to set up credentials:

```bash
uv run auth.py
```

Credentials are stored as plaintext JSON at `~/.lms_polinema/credentials.json` (`0600` permissions).

## Configuration

Add to your MCP client config:

```json
{
  "mcpServers": {
    "lms-polinema": {
      "command": "uv",
      "args": ["run", "--directory", "/path/to/lms-polinema-mcp", "lms-polinema-mcp"]
    }
  }
}
```

Or use the virtualenv directly:

**macOS / Linux:** `.venv/bin/python -m lms_polinema_mcp.server`

**Windows:** `.venv\Scripts\python.exe -m lms_polinema_mcp.server`

Settings can be overridden via environment variables or a `.env` file:

| Variable | Default | Description |
|---|---|---|
| `LMS_POLINEMA_HTTP_TIMEOUT` | `20.0` | Request timeout (seconds) |
| `LMS_POLINEMA_COURSE_CACHE_TTL_SECONDS` | `1800` | Course list cache lifetime |
| `LMS_POLINEMA_SESSION_CACHE_TTL_SECONDS` | `300` | Session validation cache lifetime |
| `LMS_POLINEMA_SIAKAD_BASE_URL` | `https://siakad.polinema.ac.id` | SIAKAD portal URL |
| `LMS_POLINEMA_MOODLE_BASE_URL` | `https://lmsslc.polinema.ac.id` | Moodle URL |

See [`.env.example`](.env.example) for the full list.

## Known limitations

- All data is retrieved by scraping HTML. The Moodle Web Services API is disabled on this instance.
- Courses without an active Moodle link configured by the lecturer will return `moodle_id: null`.
- Sessions expire after ~30 min idle. Re-auth happens automatically in the background.
- SSL verification is disabled for `lmsslc.polinema.ac.id` and `slc.polinema.ac.id` due to a missing intermediate CA.

## License

MIT License - Hafidz Rafi' Rabbani
