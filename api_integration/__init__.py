"""API integration package.

This package provides clients and helpers for interacting with the
Zanalytics API.  The :class:`~api_integration.django_api_client.DjangoAPIClient`
class is exported at the package level for convenience.
"""

from .django_api_client import DjangoAPIClient

__all__ = ["DjangoAPIClient"]

