"""Prueba de conexión estándar del conector ad_ldap.

Firma estándar Ruvic: def test_connection() -> tuple[bool, str]
- Lee la configuración EXCLUSIVAMENTE de las env vars RUVIC_AD_LDAP_*.
- Nunca lanza excepciones; retorna (ok, mensaje).

Ejecutable también como script para pruebas locales:
    python test_connection.py
"""

from __future__ import annotations


def test_connection() -> tuple[bool, str]:
    """Verifica el bind usando las env vars RUVIC_AD_LDAP_*."""
    try:
        from ruvic_ad_ldap_connector import (
            AdLdapAuthError,
            AdLdapClient,
            AdLdapDataError,
            AdLdapNetworkError,
        )
    except ImportError:
        return (
            False,
            "La librería ruvic-ad-ldap-connector no está instalada. "
            "Instala con: pip install git+https://github.com/tu-org/"
            "conector-ad-ldap.git#subdirectory=lib",
        )

    try:
        client = AdLdapClient()  # valida config y campos obligatorios
    except ValueError as exc:
        return False, str(exc)

    try:
        client.ping()
    except AdLdapAuthError as exc:
        return False, f"Autenticación fallida: {exc}"
    except AdLdapNetworkError as exc:
        return False, f"Error de red: {exc}"
    except AdLdapDataError as exc:
        return False, f"Error de datos: {exc}"
    except Exception as exc:  # red de seguridad: jamás propagar
        return False, f"Error inesperado: {exc}"

    return True, f"Conexión exitosa a {client.config.server_host} ({client.config.directory_type})"


if __name__ == "__main__":
    ok, message = test_connection()
    print(f"{'OK' if ok else 'FALLO'}: {message}")
    raise SystemExit(0 if ok else 1)
