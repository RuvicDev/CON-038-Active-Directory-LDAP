# conector-ad-ldap

Conector Ruvic de **solo lectura** para Active Directory o un directorio LDAP genérico (OpenLDAP, FreeIPA, etc.).

## Capacidades

`search_user` (búsqueda parcial por usuario/nombre/correo), `get_user_groups`, `check_user_exists`. **No crea, modifica, ni elimina** usuarios ni grupos — no tiene ningún método para hacerlo, a propósito.

## Instalación

Requiere **Python ≥ 3.10**.

```bash
pip install git+https://github.com/tu-org/conector-ad-ldap.git#subdirectory=lib
```

Para desarrollo local (editable, en un venv limpio):

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ./lib
```

## Variables de entorno

| Variable | Obligatoria | Descripción |
|----------|-------------|-------------|
| `RUVIC_AD_LDAP_SERVER_HOST` | Sí | Host del controlador de dominio / servidor LDAP |
| `RUVIC_AD_LDAP_BIND_DN` / `RUVIC_AD_LDAP_BIND_PASSWORD` | Sí | Credenciales del usuario de servicio |
| `RUVIC_AD_LDAP_BASE_DN` | Sí | Punto de partida de las búsquedas (ej. `DC=miempresa,DC=com`) |
| `RUVIC_AD_LDAP_DIRECTORY_TYPE` | No | `active_directory` (default) o `generic_ldap` |
| `RUVIC_AD_LDAP_PORT` | No | Default `636` (LDAPS) o `389` si `USE_SSL=false` |
| `RUVIC_AD_LDAP_USE_SSL` | No | `true`/`false`, default `true` |
| `RUVIC_AD_LDAP_REQUEST_TIMEOUT` | No | Segundos, default `20` |

## Permisos / prerrequisitos en el directorio

1. Pide al administrador del directorio un **usuario de servicio dedicado** (nunca una cuenta de administrador de dominio).
2. Ese usuario solo necesita **permiso de lectura** sobre la `base_dn` configurada — en Active Directory, cualquier usuario autenticado normalmente ya puede leer el directorio por defecto, pero de todas formas usa una cuenta dedicada para poder auditar/rotar su acceso de forma independiente.
3. Acota la `base_dn` a la OU específica que el agente necesita consultar, en vez de la raíz completa del dominio, si es posible.

Este conector **no soporta** crear, modificar, ni eliminar usuarios/grupos (fuera de alcance a propósito — es de solo lectura).

## Cómo correr las pruebas locales

Puedes usar un contenedor Docker de OpenLDAP con datos de ejemplo:

```bash
docker run -d -p 389:389 -p 636:636 --name openldap-test \
  -e LDAP_ORGANISATION="Empresa Prueba" \
  -e LDAP_DOMAIN="empresa-prueba.com" \
  -e LDAP_ADMIN_PASSWORD="admin123" \
  osixia/openldap

export RUVIC_AD_LDAP_DIRECTORY_TYPE=generic_ldap
export RUVIC_AD_LDAP_SERVER_HOST=localhost
export RUVIC_AD_LDAP_PORT=389
export RUVIC_AD_LDAP_USE_SSL=false
export RUVIC_AD_LDAP_BIND_DN="cn=admin,dc=empresa-prueba,dc=com"
export RUVIC_AD_LDAP_BIND_PASSWORD=admin123
export RUVIC_AD_LDAP_BASE_DN="dc=empresa-prueba,dc=com"

python test_connection.py
```

Nota: la imagen `osixia/openldap` viene sin usuarios de ejemplo — para probar `search_user`/`get_user_groups` con datos reales, necesitas cargar algunos usuarios de prueba con `ldapadd` primero (ver la documentación de esa imagen).

Prueba también el caso de error:

```bash
RUVIC_AD_LDAP_BIND_PASSWORD=incorrecta python test_connection.py
# FALLO: Autenticación fallida: ...
```

## Limitaciones conocidas

- Es de solo lectura: no crea, modifica, ni elimina usuarios/grupos.
- `enabled` (cuenta activa/deshabilitada) solo tiene valor real en Active Directory; en LDAP genérico siempre es `None`.
- `get_user_groups` depende del atributo `memberOf` en la entrada del usuario — en OpenLDAP requiere el overlay `memberof` habilitado (estándar en instalaciones modernas, pero no universal).
- No pagina resultados más allá del `size_limit` configurado en cada búsqueda — para directorios muy grandes, ajusta el `limit` de `search_user` según necesites.

## Notas de integración

- El paquete pip es `ruvic-ad-ldap-connector`; el import name es `ruvic_ad_ldap_connector`.
- Dependencia externa: `ldap3` (librería pura en Python, sin dependencias de compilación C).
- Ver `SKILL.md` para los ejemplos de uso que consume el agente.
