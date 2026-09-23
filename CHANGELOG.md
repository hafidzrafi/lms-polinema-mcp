# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.1] - 2026-09-24

### Changed
- Migrated authentication and session refresher from Playwright/Chromium to pure async HTTP (`httpx`).
- Removed `playwright` dependency and Chromium browser download requirement.
- Replaced browser automation with direct HTTP requests, eliminating headless startup overhead.
- Reduced runtime memory footprint from ~350MB to <15MB.
- Replaced worker thread execution with native async session refresh.

## [0.1.0] - 2026-09-17

Initial release.

### Features
- `lms_list_courses`: enrolled courses for the active semester
- `lms_list_assignments`: assignment summaries, optionally filtered by course
- `lms_get_assignment_detail`: assignment instructions, attachments, and submission status
- `lms_list_materials`: course material links and metadata
- `lms_check_deadlines`: deadline summary across all enrolled courses
- Self-healing session: automatic re-authentication when cookies expire
- Async HTML scraping via `httpx` + `BeautifulSoup` with `asyncio.gather` concurrency
- Pydantic v2 domain models with strict typing
- In-memory TTL cache for course listings and session validation
- Configuration via environment variables or `.env` file
