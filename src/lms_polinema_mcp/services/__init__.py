"""Scraping and HTTP services for LMS Polinema MCP."""

from lms_polinema_mcp.services.http import create_moodle_client, create_spada_client
from lms_polinema_mcp.services.moodle import MoodleScraper
from lms_polinema_mcp.services.spada import SpadaScraper

__all__ = [
    "MoodleScraper",
    "SpadaScraper",
    "create_moodle_client",
    "create_spada_client",
]
