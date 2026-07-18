"""Cliente para consultar Active Directory o un directorio LDAP genérico.

Capacidades:
- search_user():       buscar usuarios por nombre, usuario o correo (coincidencia parcial).
- get_user_groups():   consultar los grupos a los que pertenece un usuario.
- check_user_exists(): validar si una cuenta existe (búsqueda exacta, rápida).

Este conector es de **solo lectura** — no crea, modifica, ni elimina
usuarios/grupos. Es intencional: los directorios corporativos suelen
tener flujos de aprobación propios para cambios de identidad, que este
conector no debe saltarse.

Autenticación: bind simple (usuario de servicio + contraseña) contra el
directorio, con LDAPS (TLS) por defecto. Las credenciales SIEMPRE
provienen de variables de entorno RUVIC_AD_LDAP_* (ver
config.AdLdapConfig.from_env). Prohibido hardcodearlas.
"""

from __future__ import annotations

from typing import Any

import ldap3
from ldap3.core.exceptions import (
    LDAPBindError,
    LDAPException,
    LDAPSocketOpenError,
)
from ldap3.utils.conv import escape_filter_chars

from .config import AdLdapConfig
from .exceptions import AdLdapAuthError, AdLdapDataError, AdLdapNetworkError
from .logging_utils import get_logger

_AD_DISABLED_BIT = 2  # bit ACCOUNTDISABLE dentro de userAccountControl (solo AD)


class AdLdapClient:
    """Cliente de solo lectura para Active Directory o LDAP genérico.

    Args:
        config: configuración de conexión. Si se omite, se lee de las
            variables de entorno RUVIC_AD_LDAP_* (comportamiento estándar
            en el runtime de la plataforma).

    Ejemplo:
        >>> client = AdLdapClient()  # lee RUVIC_AD_LDAP_* del entorno
        >>> client.search_user("jperez")
        [{'dn': 'CN=Juan Perez,OU=Users,DC=empresa,DC=com', 'username': 'jperez', ...}]
    """

    def __init__(self, config: AdLdapConfig | None = None) -> None:
        self.config = config or AdLdapConfig.from_env()
        self._logger = get_logger()

    # ------------------------------------------------------------------ #
    # Conexión
    # ------------------------------------------------------------------ #

    def _connect(self) -> ldap3.Connection:
        server = ldap3.Server(
            self.config.server_host,
            port=self.config.port,
            use_ssl=self.config.use_ssl,
            connect_timeout=self.config.timeout,
        )
        try:
            conn = ldap3.Connection(
                server,
                user=self.config.bind_dn,
                password=self.config.bind_password,
                auto_bind=True,
                receive_timeout=self.config.timeout,
            )
        except LDAPBindError as exc:
            raise AdLdapAuthError(
                f"Bind rechazado para {self.config.bind_dn!r}: {exc}. Revisa el "
                "usuario de servicio y la contraseña."
            ) from exc
        except LDAPSocketOpenError as exc:
            raise AdLdapNetworkError(
                f"No se pudo conectar a {self.config.server_host}:{self.config.port}: {exc}"
            ) from exc
        except LDAPException as exc:
            raise AdLdapNetworkError(f"Error de conexión LDAP: {exc}") from exc
        return conn

    # ------------------------------------------------------------------ #
    # Ping / prueba de conexión
    # ------------------------------------------------------------------ #

    def ping(self) -> bool:
        """Verifica el bind conectando y cerrando de inmediato."""
        conn = self._connect()
        conn.unbind()
        self._logger.info(
            "Ping exitoso a %s (%s)", self.config.server_host, self.config.directory_type
        )
        return True

    # ------------------------------------------------------------------ #
    # Capacidad 1: buscar usuarios
    # ------------------------------------------------------------------ #

    def search_user(self, query: str, limit: int = 20) -> list[dict[str, Any]]:
        """Busca usuarios por coincidencia parcial en usuario, nombre o correo.

        Args:
            query: texto a buscar (ej. "perez", "jperez", "juan.perez@empresa.com").
            limit: máximo de resultados (default 20).

        Returns:
            Lista de dicts con "dn", "username", "display_name", "email",
            y "enabled" (solo tiene sentido en Active Directory; en LDAP
            genérico siempre es `None`, porque ese concepto no existe de
            forma estándar en el esquema LDAP básico).

        Ejemplo:
            >>> client.search_user("perez")
            [{'dn': 'CN=Juan Perez,...', 'username': 'jperez', 'display_name': 'Juan Pérez', ...}]
        """
        if not query or not query.strip():
            raise AdLdapDataError("El término de búsqueda no puede estar vacío.")

        attrs = self.config.attributes
        escaped = escape_filter_chars(query.strip())
        search_filter = (
            f"(&{attrs['user_object_class']}"
            f"(|({attrs['username_attr']}=*{escaped}*)"
            f"({attrs['display_name_attr']}=*{escaped}*)"
            f"({attrs['email_attr']}=*{escaped}*)))"
        )

        conn = self._connect()
        try:
            attributes_to_fetch = [
                attrs["username_attr"], attrs["display_name_attr"], attrs["email_attr"],
            ]
            if self.config.directory_type == "active_directory":
                attributes_to_fetch.append("userAccountControl")

            ok = conn.search(
                search_base=self.config.base_dn,
                search_filter=search_filter,
                attributes=attributes_to_fetch,
                size_limit=limit,
            )
            if not ok and conn.result.get("description") not in ("success", "sizeLimitExceeded"):
                raise AdLdapDataError(f"Búsqueda LDAP rechazada: {conn.result}")

            results = []
            for entry in conn.entries:
                results.append(self._entry_to_user_dict(entry, attrs))
        finally:
            conn.unbind()

        self._logger.info("search_user %r: %d resultado(s)", query, len(results))
        return results

    def _entry_to_user_dict(self, entry, attrs: dict[str, str]) -> dict[str, Any]:
        enabled = None
        if self.config.directory_type == "active_directory" and "userAccountControl" in entry:
            try:
                uac = int(entry["userAccountControl"].value)
                enabled = not bool(uac & _AD_DISABLED_BIT)
            except (TypeError, ValueError):
                enabled = None

        def _get(attr_name: str) -> str | None:
            if attr_name in entry:
                val = entry[attr_name].value
                return val if val else None
            return None

        return {
            "dn": str(entry.entry_dn),
            "username": _get(attrs["username_attr"]),
            "display_name": _get(attrs["display_name_attr"]),
            "email": _get(attrs["email_attr"]),
            "enabled": enabled,
        }

    # ------------------------------------------------------------------ #
    # Capacidad 2: consultar los grupos de un usuario
    # ------------------------------------------------------------------ #

    def get_user_groups(self, username: str) -> list[dict[str, str]]:
        """Consulta los grupos a los que pertenece un usuario.

        Args:
            username: usuario exacto (ej. "jperez").

        Returns:
            Lista de dicts con "dn" y "name" (el CN extraído del DN) de
            cada grupo.

        Ejemplo:
            >>> client.get_user_groups("jperez")
            [{'dn': 'CN=Ventas,OU=Grupos,DC=empresa,DC=com', 'name': 'Ventas'}, ...]

        Raises:
            AdLdapDataError: si el usuario no existe.
        """
        attrs = self.config.attributes
        escaped = escape_filter_chars(username.strip())
        search_filter = f"(&{attrs['user_object_class']}({attrs['username_attr']}={escaped}))"

        conn = self._connect()
        try:
            conn.search(
                search_base=self.config.base_dn,
                search_filter=search_filter,
                attributes=[attrs["group_membership_attr"]],
                size_limit=1,
            )
            if not conn.entries:
                raise AdLdapDataError(f"Usuario no encontrado: {username!r}")

            entry = conn.entries[0]
            group_dns = []
            if attrs["group_membership_attr"] in entry:
                raw = entry[attrs["group_membership_attr"]].value
                group_dns = raw if isinstance(raw, list) else ([raw] if raw else [])

            groups = []
            for dn in group_dns:
                name = self._extract_cn(dn)
                groups.append({"dn": dn, "name": name})
        finally:
            conn.unbind()

        self._logger.info("get_user_groups %r: %d grupo(s)", username, len(groups))
        return groups

    @staticmethod
    def _extract_cn(dn: str) -> str:
        """Extrae el valor de CN= de un Distinguished Name, sin depender de
        librerías adicionales de parseo de DN."""
        first_component = dn.split(",")[0]
        if "=" in first_component:
            return first_component.split("=", 1)[1]
        return dn

    # ------------------------------------------------------------------ #
    # Capacidad 3: validar si una cuenta existe
    # ------------------------------------------------------------------ #

    def check_user_exists(self, username: str) -> bool:
        """Valida si una cuenta de usuario existe (búsqueda exacta, barata).

        Args:
            username: usuario exacto (ej. "jperez").

        Returns:
            `True` si existe, `False` si no.

        Ejemplo:
            >>> client.check_user_exists("jperez")
            True
        """
        if not username or not username.strip():
            raise AdLdapDataError("El nombre de usuario no puede estar vacío.")

        attrs = self.config.attributes
        escaped = escape_filter_chars(username.strip())
        search_filter = f"(&{attrs['user_object_class']}({attrs['username_attr']}={escaped}))"

        conn = self._connect()
        try:
            conn.search(
                search_base=self.config.base_dn,
                search_filter=search_filter,
                attributes=[attrs["username_attr"]],
                size_limit=1,
            )
            exists = len(conn.entries) > 0
        finally:
            conn.unbind()

        self._logger.info("check_user_exists %r: %s", username, exists)
        return exists
