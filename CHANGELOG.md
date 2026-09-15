# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.0.0] - 2026-09-15

### Added
- Complete asynchronous scraping engine with `httpx.AsyncClient` and concurrent `asyncio.gather`.
- Self-healing session architecture with headless Playwright automated re-authentication.
- Strict data typing via Pydantic v2 domain models (`Course`, `AssignmentSummary`, `AssignmentDetail`, `DeadlineItem`, `CourseMaterial`).
- In-memory thread-safe TTL cache for course listings (`TTLCache`) and session validation cache.
- Centralized configuration with `pydantic-settings` supporting `.env` and environment variables.
- Domain exception hierarchy (`LMSError`, `SessionExpiredError`, `AuthenticationError`, `NetworkError`, `ParseError`, `CredentialsNotFoundError`).
- Interactive CLI credential setup via `lms-polinema-auth`.

### Changed
- Refactored monolithic `LMSClient` into single-responsibility services: `SpadaScraper` and `MoodleScraper`.
- Standardized all codebase documentation, docstrings, and comments into professional English.
- Eliminated N+1 sequential HTTP request bottleneck, reducing multi-assignment query latency from ~15s to ~1.5s.

### Removed
- Deprecated token-based WebService authentication (`token.py`).
- Deprecated synchronous builder utilities (`builders.py`).

## [0.1.0] - 2026-09-15
- Initial MVP release proving SPADA to Moodle Single Sign-On bridge reverse-engineering.
