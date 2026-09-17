# lms-polinema-mcp

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python: 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![MCP: 2.x](https://img.shields.io/badge/MCP-2.x-green.svg)](https://modelcontextprotocol.io)

Model Context Protocol (MCP) server for LMS Polinema. Gives AI agents direct access to your enrolled courses, assignments, deadlines, and materials.

Compatible with Claude Code, Cursor, Antigravity, and any client implementing the Model Context Protocol.

## How It Works

Polinema does not allow students to log in directly to Moodle with credentials. Instead, authentication flows through an institutional single sign-on (SSO) gateway:

```
SIAKAD (Portal) ──> SLC (SPADA Gateway) ──> LMSSLC (Moodle)
```

1. On initial setup, `auth.py` drives headless Chromium to authenticate against SIAKAD using your NIM and password.
2. The browser obtains the wildcard SSO session cookie and connects to the SPADA gateway.
3. The SPADA gateway initiates the handshake with Moodle, issuing an authenticated `MoodleSession`.
4. Cookies are persisted locally in `~/.lms_polinema/` with strict file permissions (`0600`).
5. When cookies expire, the server automatically executes headless re-authentication in the background.

## Available Tools

| Tool | Parameters | Description |
|---|---|---|
| `lms_list_courses` | None | Lists all courses enrolled for the active semester. |
| `lms_list_assignments` | `course_id` (int, optional) | Lists assignments across all courses or filtered by course ID. |
| `lms_get_assignment_detail` | `assignment_id` (int) | Retrieves instructions, attachments, and submission status for an assignment. |
| `lms_list_materials` | `course_id` (int) | Lists files, slides, jobsheets, and learning resources for a course. |
| `lms_check_deadlines` | None | Returns active assignment deadlines and overdue items across all courses. |

## Installation

Requirements: Python 3.11+ and [uv](https://astral.sh/uv).

```bash
git clone https://github.com/hafidzrafi/lms-polinema-mcp.git
cd lms-polinema-mcp
uv sync
uv run playwright install chromium
```

Run the credential setup once:

```bash
uv run auth.py
```

Credentials are saved locally at `~/.lms_polinema/credentials.json` with user-only read/write permissions (`0600`).

## Client Configuration

Add `lms-polinema` to your MCP client configuration (`mcp_config.json` or `claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "lms-polinema": {
      "command": "uv",
      "args": [
        "run",
        "--directory",
        "/absolute/path/to/lms-polinema-mcp",
        "lms-polinema-mcp"
      ]
    }
  }
}
```

Alternatively, invoke the virtual environment python binary directly:

```json
{
  "mcpServers": {
    "lms-polinema": {
      "command": "/absolute/path/to/lms-polinema-mcp/.venv/bin/python",
      "args": ["-m", "lms_polinema_mcp.server"]
    }
  }
}
```

## Troubleshooting & Network Notes

- **Campus Wi-Fi & Tailscale/VPN:** When connected to the Polinema campus Wi-Fi network, disable Tailscale or VPN before running authentication. The campus network enforces internal DNS mappings (`10.10.92.x`), and external VPN resolvers can lead to connection timeouts due to lack of NAT loopback.
- **Unlinked Courses:** Courses in SPADA that do not have an active Moodle link set by the lecturer will return `moodle_id: null`.
- **SSL Certificates:** Institutional endpoints (`slc.polinema.ac.id`, `lmsslc.polinema.ac.id`) lack intermediate CA chains in standard certificate stores; TLS validation for these internal hosts is handled accordingly in configuration.

## License

MIT
