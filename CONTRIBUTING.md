# Contributing to LMS Polinema MCP

We welcome contributions from the community to improve performance, add support for more campus systems, or refine data extraction.

## Development Setup

1. Prerequisites: Python 3.11+, [`uv`](https://astral.sh/uv), and Chromium for Playwright.
2. Clone repository:
   ```bash
   git clone https://github.com/hafidzrafi/lms-polinema-mcp.git
   cd lms-polinema-mcp
   ```
3. Install dependencies:
   ```bash
   uv sync --all-extras
   uv run playwright install chromium
   ```

## Code Quality Standards

Before submitting a Pull Request, ensure that:
- Code is formatted and passes linting:
  ```bash
  uv run ruff check src/
  uv run ruff format --check src/
  ```
- All code, comments, docstrings, and log messages are in **English**.
- No decorative emojis or non-standard formatting in library source code.
- Strict type annotations are present on all function and method signatures.
- Changes include relevant updates to `CHANGELOG.md`.

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
