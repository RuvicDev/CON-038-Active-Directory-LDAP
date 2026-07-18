"""Excepciones propias del conector AD/LDAP.

Separan los tipos de fallo que el usuario debe distinguir: configuración
inválida, autenticación (bind), red, y datos (usuario/grupo inexistente).
"""


class AdLdapConnectorError(Exception):
    """Error base del conector."""


class AdLdapConfigError(AdLdapConnectorError):
    """Configuración inválida: falta un campo requerido."""


class AdLdapAuthError(AdLdapConnectorError):
    """El bind (usuario de servicio + contraseña) fue rechazado por el
    directorio — credenciales inválidas o cuenta bloqueada/deshabilitada."""


class AdLdapNetworkError(AdLdapConnectorError):
    """No se pudo alcanzar el servidor (DNS, timeout, conexión rechazada,
    o error de TLS/certificado)."""


class AdLdapDataError(AdLdapConnectorError):
    """La operación es válida pero el usuario/grupo no existe, o la
    búsqueda LDAP fue rechazada por el servidor."""
