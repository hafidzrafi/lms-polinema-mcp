"""Domain exception hierarchy for LMS Polinema MCP."""


class LMSError(Exception):
    """Base exception for all LMS Polinema MCP errors."""


class SessionExpiredError(LMSError):
    """Raised when the Moodle or SPADA session is expired or missing."""


class AuthenticationError(LMSError):
    """Raised when SIAKAD login fails due to invalid credentials or server errors."""


class NetworkError(LMSError):
    """Raised when an HTTP request fails after exhaustion of retries."""


class ParseError(LMSError):
    """Raised when HTML parsing fails to locate expected DOM elements."""


class CredentialsNotFoundError(LMSError):
    """Raised when auto-refresh is attempted but no credentials are saved."""
