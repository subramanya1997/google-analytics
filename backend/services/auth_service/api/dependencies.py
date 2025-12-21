"""
Shared API dependencies for the auth service.
"""

from functools import lru_cache

from services.auth_service.services.auth_service import AuthenticationService


@lru_cache(maxsize=1)
def get_auth_service() -> AuthenticationService:
    """
    Get cached authentication service instance.
    Using lru_cache to ensure only one instance is created.
    """
    return AuthenticationService()

