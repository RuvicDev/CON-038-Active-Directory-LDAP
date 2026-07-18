---
name: ad-ldap
description: "Usa la librería ruvic_ad_ldap_connector para consultar Active Directory o un directorio LDAP genérico (solo lectura) - buscar usuarios por nombre/usuario/correo (search_user), consultar a qué grupos pertenece un usuario (get_user_groups), y validar si una cuenta existe (check_user_exists). Úsala cuando el usuario pida buscar a alguien en el directorio corporativo, ver a qué grupos pertenece, o confirmar si una cuenta existe. Este conector NO crea, modifica, ni elimina usuarios ni grupos — es de solo lectura."
triggers:
- active directory
- ldap
- directorio corporativo
- buscar usuario
- grupos de usuario
- validar cuenta
---

# Conector Active Directory / LDAP (ruvic_ad_ldap_connector)

Librería Python de **solo lectura** para consultar Active Directory o un directorio LDAP genérico. Está **preinstalada en el runtime** cuando el conector está configurado (si no, instálala con `pip install git+https://github.com/tu-org/conector-ad-ldap.git#subdirectory=lib`).

## Regla crítica de credenciales

El código generado **NUNCA hardcodea credenciales**. Siempre se leen de variables de entorno, disponibles cuando el conector `ad_ldap` está configurado:

| Variable | Contenido |
|----------|-----------|
| `RUVIC_AD_LDAP_SERVER_HOST` / `..._BIND_DN` / `..._BIND_PASSWORD` / `..._BASE_DN` | Siempre requeridas |
| `RUVIC_AD_LDAP_DIRECTORY_TYPE` | `active_directory` o `generic_ldap` |
| `RUVIC_AD_LDAP_PORT` / `..._USE_SSL` | (opcional) default `636`/`true` |
| `RUVIC_AD_LDAP_REQUEST_TIMEOUT` | (opcional) segundos, default `20` |

El código generado **NUNCA** usa nombres de variable con segmento de alias (`_DEFAULT_`, `_TEST_`, `_PRODUCCION_`, etc.) — siempre `RUVIC_AD_LDAP_{CAMPO}` tal cual, sin importar cuántas instancias de este conector haya configuradas. Esto aplica salvo que dichos nombres aparezcan explícitamente en una sección autogenerada al final de este skill.

Si estas variables NO existen, el conector no está configurado: no generes código que lo use; indica al usuario que lo configure en **Settings → Conectores**.

## Conexión (siempre igual)

```python
from ruvic_ad_ldap_connector import AdLdapClient

client = AdLdapClient()  # lee RUVIC_AD_LDAP_* del entorno automáticamente
```

El código generado nunca necesita saber si el directorio es Active Directory o LDAP genérico — el conector traduce los nombres de atributo automáticamente según cómo se configuró.

## Capacidad 1 — Buscar usuarios

Búsqueda por coincidencia parcial en usuario, nombre para mostrar, o correo:

```python
resultados = client.search_user("perez")
for u in resultados:
    estado = "activo" if u["enabled"] else "deshabilitado" if u["enabled"] is False else "sin dato"
    print(f"{u['username']} - {u['display_name']} - {u['email']} ({estado})")
```

`enabled` solo tiene valor real en Active Directory — en LDAP genérico siempre es `None`, porque ese concepto no existe de forma estándar en ese esquema.

## Capacidad 2 — Consultar los grupos de un usuario

```python
grupos = client.get_user_groups("jperez")
for g in grupos:
    print(g["name"])
```

Lanza `AdLdapDataError` si el usuario no existe — usa `check_user_exists` primero si no estás seguro.

## Capacidad 3 — Validar si una cuenta existe

Búsqueda exacta, más rápida que `search_user` para este propósito específico:

```python
if client.check_user_exists("jperez"):
    print("La cuenta existe")
else:
    print("La cuenta no existe")
```

## Este conector es de SOLO LECTURA — no intentes lo contrario

No tiene métodos para crear, modificar, deshabilitar, ni eliminar usuarios o grupos, a propósito. Si el usuario pide algo de esto, informa que esta versión del conector no lo soporta — los cambios de identidad en un directorio corporativo suelen requerir flujos de aprobación propios que este conector no debe saltarse.

## Manejo de errores

```python
from ruvic_ad_ldap_connector import AdLdapAuthError, AdLdapNetworkError, AdLdapDataError

try:
    client.search_user("perez")
except AdLdapAuthError:
    print("El usuario de servicio no pudo autenticarse — revisa la configuración del conector")
except AdLdapNetworkError:
    print("No se pudo conectar al directorio — revisa la red/VPN")
except AdLdapDataError as e:
    print(f"Error de datos: {e}")  # ej. usuario no encontrado
```

## Buenas prácticas al generar código

1. Lee credenciales SOLO de las variables `RUVIC_AD_LDAP_*` (el constructor de `AdLdapClient` ya lo hace).
2. Nunca imprimas `RUVIC_AD_LDAP_BIND_PASSWORD` en logs ni en la salida.
3. No intentes crear/modificar/eliminar usuarios o grupos: este conector no lo soporta a propósito.
4. `search_user` es para búsquedas exploratorias (coincidencia parcial); `check_user_exists` es para confirmar un usuario exacto conocido — usa la que corresponda, no `search_user` para simplemente confirmar existencia.
5. No inventes atributos que no vinieron en la respuesta — si `email` o `display_name` son `None`, repórtalo como "sin dato", no lo completes con una suposición.
