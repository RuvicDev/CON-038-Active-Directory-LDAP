"""Conector Ruvic para Active Directory / LDAP (solo lectura)."""

from .client import AdLdapClient
from .config import ENV_PREFIX, AdLdapConfig
from .exceptions import (
    AdLdapAuthError,
    AdLdapConfigError,
    AdLdapConnectorError,
    AdLdapDataError,
    AdLdapNetworkError,
)
from .logging_utils import setup_logging

__all__ = [
    "ENV_PREFIX",
    "AdLdapAuthError",
    "AdLdapClient",
    "AdLdapConfig",
    "AdLdapConfigError",
    "AdLdapConnectorError",
    "AdLdapDataError",
    "AdLdapNetworkError",
    "setup_logging",
]

__version__ = "1.0.0"
