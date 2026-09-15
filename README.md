# lms-polinema-mcp

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python: 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![MCP: 2.x](https://img.shields.io/badge/MCP-2.x-green.svg)](https://modelcontextprotocol.io)

An [MCP (Model Context Protocol)](https://modelcontextprotocol.io) server that exposes LMS Polinema course data — assignments, deadlines, and materials — to AI agents via STDIO transport.

Supports **Claude Desktop**, **Cursor**, **VS Code**, **Antigravity CLI**, and any other MCP-compatible client.

---

## How It Works

Polinema does not allow students to log in to Moodle directly. Authentication goes through SIAKAD (the university portal), which issues a session for SPADA (the course gateway), which then bridges to Moodle. This server automates that chain using a headless Chromium browser on first run, saves the resulting cookies to `~/.lms_polinema/`, and reuses them on subsequent calls. If the session expires, the browser flow runs again automatically in the background.

---

## Available Tools

| Tool | Parameters | Returns |
|---|---|---|
| `lms_list_courses` | — | Enrolled courses for the current semester |
| `lms_list_assignments` | `course_id` _(int, optional)_ | Assignment summaries, optionally filtered by course |
| `lms_get_assignment_detail` | `assignment_id` _(int)_ | Assignment instructions, attachments, and submission status |
| `lms_list_materials` | `course_id` _(int)_ | Slides, jobsheets, and other resources for a course |
| `lms_check_deadlines` | — | Deadline summary across all enrolled courses |

---

## Installation

**Requirements:** Python 3.11+, [`uv`](https://astral.sh/uv)

```bash
git clone https://github.com/hafidzrafi/lms-polinema-mcp.git
cd lms-polinema-mcp
uv sync
uv run playwright install chromium
```

### Authentication Setup

Run once to store credentials and obtain the initial session:

```bash
uv run python auth.py
```

Credentials are saved as JSON to `~/.lms_polinema/credentials.json` with `0600` permissions (user-readable only). Session cookies are saved separately to `~/.lms_polinema/`.

> **Note:** Credentials are stored as plaintext. Ensure your home directory is appropriately secured.

---

## MCP Client Configuration

### Using `uv run` (recommended, cross-platform)

```json
{
  "mcpServers": {
    "lms-polinema": {
      "command": "uv",
      "args": [
        "run",
        "--directory",
        "/path/to/lms-polinema-mcp",
        "lms-polinema-mcp"
      ]
    }
  }
}
```

### Using the virtual environment directly

**macOS / Linux:**
```json
{
  "mcpServers": {
    "lms-polinema": {
      "command": "/path/to/lms-polinema-mcp/.venv/bin/python",
      "args": ["-m", "lms_polinema_mcp.server"]
    }
  }
}
```

**Windows:**
```json
{
  "mcpServers": {
    "lms-polinema": {
      "command": "C:\\path\\to\\lms-polinema-mcp\\.venv\\Scripts\\python.exe",
      "args": ["-m", "lms_polinema_mcp.server"]
    }
  }
}
```

---

## Configuration

Settings can be overridden via environment variables or a `.env` file in the project root:

| Variable | Default | Description |
|---|---|---|
| `LMS_POLINEMA_HTTP_TIMEOUT` | `20.0` | HTTP request timeout (seconds) |
| `LMS_POLINEMA_COURSE_CACHE_TTL_SECONDS` | `1800` | Course list cache lifetime (seconds) |
| `LMS_POLINEMA_SESSION_CACHE_TTL_SECONDS` | `300` | Session validation cache lifetime (seconds) |
| `LMS_POLINEMA_SIAKAD_BASE_URL` | `https://siakad.polinema.ac.id` | SIAKAD portal base URL |
| `LMS_POLINEMA_MOODLE_BASE_URL` | `https://lmsslc.polinema.ac.id` | Moodle instance base URL |

See [`.env.example`](.env.example) for the full list.

---

## Adapting for Other Institutions

This server scrapes HTML from a standard Moodle 3.x installation. To adapt it for a different university:

1. Update `SIAKAD_BASE_URL`, `SPADA_BASE_URL`, and `MOODLE_BASE_URL` in `config.py` or via `.env`.
2. Modify `src/lms_polinema_mcp/auth/refresh.py` to match your institution's SSO login flow.
3. The `MoodleScraper` in `src/lms_polinema_mcp/services/moodle.py` uses standard Moodle selectors (`#intro`, `.generaltable`, `/mod/assign/`) and should work on most Moodle 3.x–4.x deployments without modification.

---

## Known Limitations

- **Moodle Web Services API is disabled** on this instance. All data is retrieved by scraping HTML pages.
- **Session TTL is short** on this Moodle instance (~30 min idle). The server re-authenticates automatically, but the first tool call after expiry will take longer than usual (~10–20 seconds).
- **SSL verification is disabled** for campus domains due to an intermediate CA not present in the default Python trust store. This is scoped only to requests targeting `lmsslc.polinema.ac.id` and `slc.polinema.ac.id`.

---

## License

MIT License © 2026 [Hafidz Rafi' Rabbani](https://github.com/hafidzrafi)
