# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-09-15

Initial release.

### Features
- `lms_list_courses` — enrolled courses for the active semester
- `lms_list_assignments` — assignment summaries, optionally filtered by course
- `lms_get_assignment_detail` — assignment instructions, attachments, and submission status
- `lms_list_materials` — course slides, jobsheets, and other resources
- `lms_check_deadlines` — deadline summary across all enrolled courses
- Self-healing session: headless Playwright re-authentication when cookies expire
- Async HTML scraping via `httpx` + `BeautifulSoup` with `asyncio.gather` concurrency
- Pydantic v2 domain models with strict typing
- In-memory TTL cache for course listings and session validation
- Configuration via environment variables or `.env` file
