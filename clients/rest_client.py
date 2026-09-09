"""Backward-compatible name for the generic HTTP client.

New API services should import :class:`HttpClient` from ``http_client``.
Existing flows can continue using ``RestClient`` during the migration.
"""

from clients.http_client import HttpClient


class RestClient(HttpClient):
    """Compatibility wrapper kept for existing services and flows."""
