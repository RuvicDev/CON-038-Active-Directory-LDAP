"""Validación local del conector ad_ldap: ejercita las 3 capacidades.

Requiere las env vars RUVIC_AD_LDAP_* exportadas contra un directorio de
prueba (puedes usar un contenedor Docker de OpenLDAP con datos de
ejemplo, ej. la imagen "osixia/openldap" con RUVIC_AD_LDAP_DIRECTORY_TYPE
en "generic_ldap"). Ajusta TEST_USERNAME según los datos de tu servidor.
"""

from ruvic_ad_ldap_connector import AdLdapClient, setup_logging

setup_logging("INFO")
client = AdLdapClient()

# Ajusta esto a un usuario que exista en tu directorio de prueba:
TEST_USERNAME = "jperez"

print("== 1. Buscar usuarios (coincidencia parcial) ==")
resultados = client.search_user(TEST_USERNAME[:4])  # busca con solo una parte del nombre
print(f"  {len(resultados)} resultado(s)")
for r in resultados[:5]:
    print(f"    {r}")

print(f"== 2. Validar existencia de '{TEST_USERNAME}' ==")
existe = client.check_user_exists(TEST_USERNAME)
print(f"  Existe: {existe}")

if existe:
    print(f"== 3. Consultar grupos de '{TEST_USERNAME}' ==")
    grupos = client.get_user_groups(TEST_USERNAME)
    print(f"  {len(grupos)} grupo(s)")
    for g in grupos:
        print(f"    {g}")
else:
    print(f"== 3. Se omite (el usuario '{TEST_USERNAME}' no existe en este directorio) ==")

print("== 4. Validar existencia de un usuario que NO existe (caso negativo) ==")
no_existe = client.check_user_exists("usuario_que_no_existe_123456789")
print(f"  Existe: {no_existe} (debe ser False)")
assert no_existe is False, "check_user_exists debio retornar False para un usuario inexistente"

print("\nValidación completa.")
