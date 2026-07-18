"""Configuración del conector leída desde variables de entorno.

Convención de la plataforma: cada campo del formulario de configuración
llega como variable de entorno {ENV_PREFIX}{CAMPO} en mayúsculas.
Para este conector el prefijo es RUVIC_AD_LDAP_.

Soporta dos "sabores" de directorio, elegidos por `directory_type`, que
determina automáticamente los nombres de atributo correctos (varían
entre Active Directory y LDAP genérico):
- "active_directory": usa sAMAccountName, memberOf, userAccountControl.
- "generic_ldap": usa uid, memberOf (requiere el overlay memberOf en
  OpenLDAP — es estándar en la mayoría de instalaciones modernas).
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field

ENV_PREFIX = "RUVIC_AD_LDAP_"

_VALID_DIRECTORY_TYPES = ("active_directory", "generic_ldap")

# Atributos por defecto según el tipo de directorio.
_ATTRIBUTE_PROFILES = {
    "active_directory": {
        "username_attr": "sAMAccountName",
        "display_name_attr": "displayName",
        "email_attr": "mail",
        "group_membership_attr": "memberOf",
        "user_object_class": "(&(objectClass=user)(objectCategory=person))",
    },
    "generic_ldap": {
        "username_attr": "uid",
        "display_name_attr": "cn",
        "email_attr": "mail",
        "group_membership_attr": "memberOf",
        "user_object_class": "(objectClass=inetOrgPerson)",
    },
}


@dataclass(frozen=True)
class AdLdapConfig:
    """Parámetros de conexión a un directorio Active Directory o LDAP genérico."""

    server_host: str
    bind_dn: str
    bind_password: str
    base_dn: str
    directory_type: str = "active_directory"
    port: int = 636
    use_ssl: bool = True
    timeout: int = 20
    attributes: dict = field(default_factory=dict)

    @classmethod
    def from_env(cls) -> "AdLdapConfig":
        """Construye la configuración desde las variables RUVIC_AD_LDAP_*.

        Raises:
            ValueError: si falta un campo obligatorio o `directory_type`
                no es válido.
        """
        server_host = os.environ.get(f"{ENV_PREFIX}SERVER_HOST", "").strip()
        bind_dn = os.environ.get(f"{ENV_PREFIX}BIND_DN", "").strip()
        bind_password = os.environ.get(f"{ENV_PREFIX}BIND_PASSWORD", "")
        base_dn = os.environ.get(f"{ENV_PREFIX}BASE_DN", "").strip()

        missing = [
            name for name, val in (
                (f"{ENV_PREFIX}SERVER_HOST", server_host),
                (f"{ENV_PREFIX}BIND_DN", bind_dn),
                (f"{ENV_PREFIX}BIND_PASSWORD", bind_password),
                (f"{ENV_PREFIX}BASE_DN", base_dn),
            ) if not val
        ]
        if missing:
            raise ValueError(
                "Faltan variables de entorno del conector ad_ldap: "
                + ", ".join(missing)
                + ". Configura el conector en Settings → Conectores."
            )

        directory_type = os.environ.get(f"{ENV_PREFIX}DIRECTORY_TYPE", "active_directory").strip().lower()
        if directory_type not in _VALID_DIRECTORY_TYPES:
            raise ValueError(
                f"{ENV_PREFIX}DIRECTORY_TYPE inválido: {directory_type!r}. "
                f"Debe ser uno de: {', '.join(_VALID_DIRECTORY_TYPES)}."
            )

        use_ssl_raw = os.environ.get(f"{ENV_PREFIX}USE_SSL", "true").strip().lower()
        use_ssl = use_ssl_raw not in ("false", "0", "no")
        default_port = 636 if use_ssl else 389
        port = int(os.environ.get(f"{ENV_PREFIX}PORT", str(default_port)))

        return cls(
            server_host=server_host,
            bind_dn=bind_dn,
            bind_password=bind_password,
            base_dn=base_dn,
            directory_type=directory_type,
            port=port,
            use_ssl=use_ssl,
            timeout=int(os.environ.get(f"{ENV_PREFIX}REQUEST_TIMEOUT", "20")),
            attributes=_ATTRIBUTE_PROFILES[directory_type],
        )
