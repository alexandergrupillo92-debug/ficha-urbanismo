# Ficha de Inspección de Urbanismo — App Android

Convierte tu script de consola en una app real con pantallas táctiles.
La lógica de generación del PDF (Reportlab) es la misma que ya tenías, solo
cambió la forma de introducir los datos: ahora es con formularios en vez de
texto por teclado.

## Cómo obtener el archivo APK (gratis, sin instalar nada en tu PC)

1. Crea una cuenta gratuita en https://github.com si no tienes una.
2. Crea un repositorio nuevo (puede ser privado).
3. Sube estos 5 elementos tal cual están, respetando la carpeta:
   - `main.py`
   - `logic.py`
   - `buildozer.spec`
   - `.github/workflows/build.yml`
   - `README.md`
4. Ve a la pestaña **Actions** de tu repositorio. Se iniciará una compilación
   automática (tarda entre 15 y 25 minutos la primera vez).
5. Cuando termine (círculo verde ✅), entra a esa ejecución y descarga el
   archivo `ficha-urbanismo-apk` en "Artifacts". Es un .zip que contiene el
   `.apk`.

## Cómo instalarlo en cada teléfono

1. Pasa el `.apk` a cada teléfono (WhatsApp, Google Drive, USB, lo que sea).
2. Al abrirlo, Android pedirá permitir "instalar apps de origen desconocido"
   — se acepta una sola vez.
3. Se instala como cualquier app normal: aparece con su ícono, se abre y se
   usa. Nadie ve el código, solo las pantallas.

## Qué cambia respecto al script original

- **No se pierde el progreso al apagar la pantalla**: al ser una app
  instalada (no un script corriendo en Pydroid3), Android la maneja como
  cualquier otra app. Además, cada unidad que guardas se escribe de
  inmediato en el archivo de progreso (igual que hacía tu script), así que
  aunque el sistema cierre la app puedes volver a abrirla, escribir el mismo
  nombre de urbanismo y continúa donde quedó.
- El PDF se genera exactamente igual (mismo diseño, mismas estadísticas).
- Cada persona que instale el APK puede trabajar su propio urbanismo de
  forma independiente en su teléfono.

## Si quieres modificar algo más adelante

- Los textos de las pantallas están en `main.py`.
- Las listas de opciones (parroquias, tipos de techo, etc.) y la generación
  del PDF están en `logic.py` — cualquier cambio ahí se refleja igual en el
  PDF final.
- Después de editar, solo hace falta volver a subir los cambios a GitHub
  (`git push`) y la Action generará un nuevo APK automáticamente.
