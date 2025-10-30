# Cómo generar el APK (automatizado)

He añadido dos artefactos al repositorio:

- `buildozer.spec` — configuración mínima para Buildozer.
- `.github/workflows/android-build.yml` — workflow de GitHub Actions que construye el APK usando la imagen `kivy/buildozer` y sube el APK resultante como artefacto.

Pasos para obtener el APK sin instalar Buildozer localmente:

1. Sube (push) este repositorio a GitHub en un repo público o privado.
2. En GitHub, ve a la pestaña "Actions" y verás el workflow "Android APK build". Ejecutará automáticamente en cada push a `main` o `master`, o puedes ejecutarlo manualmente con "Run workflow".
3. Cuando termine la ejecución, en la página del workflow busca la sección "Artifacts" y descarga el artefacto `lactasegura-apk`.

Notas y recomendaciones:
- El primer build descargará SDK/NDK y puede tardar bastante (varios GB). Ten paciencia.
- Si el workflow falla por versiones de NDK/SDK, ajusta `android.ndk` o `android.api` en `buildozer.spec`.
- Para un APK de producción (signed), genera un keystore y modifica `buildozer.spec` con los parámetros de firma, luego cambia el comando a `buildozer android release`.

Si prefieres que yo mismo suba y lance el workflow, dame la URL del repo GitHub y los permisos necesarios (o invítame como colaborador); puedo empujar los cambios y ejecutar el workflow por ti.
