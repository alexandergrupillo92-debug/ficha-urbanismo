# -*- coding: utf-8 -*-
"""
logic_informe.py
-----------------
Genera el "Informe de Inspección de Vivienda" (Modelo 1 - Clásico) en formato
Word (.docx), igual al aprobado para el caso Tacarigua, a partir de los datos
capturados en el formulario web.

Sigue el mismo patrón que logic_ficha.py y logic_semaforo.py: una función
generar_*(data, fotos_paths, destino_path) que arma el archivo final y lo
guarda en disco, para que app.py la invoque y luego ofrezca el archivo para
descarga.

Requiere:
    pip install Pillow
(No requiere python-docx: se edita directamente el XML interno de la
plantilla, que ya trae el membrete institucional, los 4 cuadros, el diseño
aprobado y el bloque de firma).

Estructura esperada en el repo:
    logic_informe.py
    assets/
        informe_template.docx   <-- plantilla con tokens {{...}}
"""

import io
import os
import shutil
import zipfile
import xml.sax.saxutils as saxutils

from PIL import Image, ImageOps

TEMPLATE_PATH = os.path.join(os.path.dirname(__file__), "assets", "informe_template.docx")

# Datos fijos de quien firma el informe (ajusta aquí si cambia el director/a)
FIRMANTE_NOMBRE = "LIC. Emili Montero"
FIRMANTE_CARGO = "DIRECTOR DE HÁBITAT Y VIVIENDA"
FIRMANTE_RESOLUCION = "Según Resolución N°075-2025"
FIRMANTE_FECHA_RESOLUCION = "De fecha 14 de Agosto de 2025"

# Tamaño final de cada foto dentro del cuadro (debe coincidir con lo que
# define la plantilla: 7cm x 7cm cuadradas). 700px equivale a ~250 dpi de
# impresión a ese tamaño: nítido en papel y en pantalla, pero mucho más
# liviano que subir la foto de la cámara tal cual.
FOTO_PX = 700
FOTO_CALIDAD_JPEG = 78

# Catálogo de áreas de la vivienda para el Cuadro 2 (Descripción de la
# Inspección Ocular). En el formulario se muestran TODAS como checkbox;
# el inspector solo marca las que presentan patología, y únicamente esas
# aparecen como filas en el informe final.
# Formato: (clave, etiqueta, tiene_cantidad)
AREAS_DISPONIBLES = [
    ("techo", "Techo", False),
    ("sala", "Sala", False),
    ("cocina", "Cocina", False),
    ("comedor", "Comedor", False),
    ("banos", "Baños", True),
    ("cuartos", "Cuartos", True),
    ("frente", "Frente de la casa", False),
    ("fachada_posterior", "Fachada posterior", False),
    ("pared_izq", "Pared lateral izquierda", False),
    ("pared_der", "Pared lateral derecha", False),
]


def _esc(valor):
    """Escapa texto para insertarlo de forma segura dentro de un <w:t>."""
    if valor is None:
        valor = ""
    return saxutils.escape(str(valor))


def _construir_recomendaciones_xml(recomendaciones):
    """
    Genera el bloque XML de la lista numerada de recomendaciones
    (cuadro 3), a partir de una lista de strings.
    """
    partes = []
    for i, texto in enumerate(recomendaciones, start=1):
        texto = texto.strip()
        if not texto:
            continue
        partes.append(
            '<w:p><w:pPr><w:spacing w:after="40"/></w:pPr>'
            '<w:r><w:rPr><w:b/><w:bCs/></w:rPr>'
            f'<w:t xml:space="preserve">{i}. </w:t></w:r>'
            f'<w:r><w:t>{_esc(texto)}</w:t></w:r></w:p>'
        )
    if not partes:
        # Nunca dejar el cuadro vacío
        partes.append(
            '<w:p><w:r><w:t>Sin recomendaciones registradas.</w:t></w:r></w:p>'
        )
    return "".join(partes)


def _construir_filas_inspeccion_xml(filas):
    """
    Genera las filas del Cuadro 2 (Descripción de la Inspección Ocular),
    una por cada área marcada con patología.

    filas: lista de dicts {"elemento": str, "observacion": str}
    """
    tcpr_izq = (
        '<w:tcPr><w:tcW w:w="2500" w:type="dxa"/>'
        '<w:tcMar><w:top w:w="50" w:type="dxa"/><w:left w:w="120" w:type="dxa"/>'
        '<w:bottom w:w="50" w:type="dxa"/><w:right w:w="120" w:type="dxa"/></w:tcMar>'
        '<w:vAlign w:val="center"/></w:tcPr>'
    )
    tcpr_der = (
        '<w:tcPr><w:tcW w:w="6850" w:type="dxa"/>'
        '<w:tcMar><w:top w:w="50" w:type="dxa"/><w:left w:w="120" w:type="dxa"/>'
        '<w:bottom w:w="50" w:type="dxa"/><w:right w:w="120" w:type="dxa"/></w:tcMar>'
        '<w:vAlign w:val="center"/></w:tcPr>'
    )
    partes = []
    for fila in filas:
        elemento = _esc(fila.get("elemento", ""))
        observacion = _esc(fila.get("observacion", ""))
        partes.append(
            "<w:tr><w:tc>" + tcpr_izq +
            f'<w:p><w:r><w:rPr><w:b/><w:bCs/></w:rPr><w:t>{elemento}</w:t></w:r></w:p>'
            "</w:tc><w:tc>" + tcpr_der +
            f'<w:p><w:r><w:t xml:space="preserve">{observacion}</w:t></w:r></w:p>'
            "</w:tc></w:tr>"
        )
    if not partes:
        partes.append(
            "<w:tr><w:tc>" + tcpr_izq +
            "<w:p><w:r><w:t>—</w:t></w:r></w:p></w:tc><w:tc>" + tcpr_der +
            "<w:p><w:r><w:t>No se registraron áreas con patología.</w:t></w:r></w:p></w:tc></w:tr>"
        )
    return "".join(partes)


def _preparar_foto_cuadrada(ruta_origen, lado_px=FOTO_PX):
    """
    Recorta al centro y redimensiona una foto subida por el usuario para
    que quede cuadrada (igual proporción que el recuadro de 6cm x 6cm de
    la plantilla). Devuelve los bytes JPEG listos para incrustar.
    """
    img = Image.open(ruta_origen)
    img = ImageOps.exif_transpose(img)  # respeta la orientación de la cámara
    img = img.convert("RGB")

    ancho, alto = img.size
    lado = min(ancho, alto)
    izq = (ancho - lado) // 2
    arriba = (alto - lado) // 2
    img = img.crop((izq, arriba, izq + lado, arriba + lado))
    img = img.resize((lado_px, lado_px), Image.LANCZOS)

    # Se crea una imagen "limpia" (sin EXIF/ICC ni otros metadatos de la
    # cámara) para que el archivo final pese lo menos posible.
    limpia = Image.new("RGB", img.size)
    limpia.paste(img)

    buf = io.BytesIO()
    limpia.save(buf, format="JPEG", quality=FOTO_CALIDAD_JPEG, optimize=True)
    return buf.getvalue()


def generar_informe_docx(data, fotos_paths, docx_path):
    """
    Arma el informe final y lo guarda en `docx_path`.

    data: dict con las llaves:
        fecha, direccion, parroquia, tipo_vivienda, ambientes,
        nombre, cedula, telefono, adultos, menores, condicion,
        obs_estructura, obs_techo, obs_electricas, obs_sanitarias,
        obs_acabados, recomendaciones (list[str]),
        captions (list[str] con 4 elementos, uno por foto)

    fotos_paths: lista de 4 rutas a las fotos subidas por el usuario,
        en el mismo orden que las leyendas (Fig. 1 a Fig. 4).

    docx_path: ruta destino del .docx generado.
    """
    if not os.path.exists(TEMPLATE_PATH):
        raise FileNotFoundError(
            f"No se encontró la plantilla en {TEMPLATE_PATH}. "
            "Verifica que assets/informe_template.docx esté en el repo."
        )
    if len(fotos_paths) != 4:
        raise ValueError("Se requieren exactamente 4 fotos para el Registro Fotográfico.")

    captions = data.get("captions") or []
    while len(captions) < 4:
        captions.append("")

    total_habitantes = int(data.get("adultos", 0)) + int(data.get("menores", 0))
    habitantes_txt = (
        f"{total_habitantes} personas "
        f"({data.get('adultos', 0)} adultos y {data.get('menores', 0)} menores)"
    )

    reemplazos = {
        "{{FECHA}}": _esc(data.get("fecha", "")),
        "{{DIRECCION}}": _esc(data.get("direccion", "")),
        "{{PARROQUIA}}": _esc(data.get("parroquia", "")),
        "{{TIPO_VIVIENDA}}": _esc(data.get("tipo_vivienda", "")),
        "{{AMBIENTES}}": _esc(data.get("ambientes", "")),
        "{{NOMBRE}}": _esc(data.get("nombre", "")),
        "{{CEDULA}}": _esc(data.get("cedula", "")),
        "{{TELEFONO}}": _esc(data.get("telefono", "")),
        "{{HABITANTES}}": _esc(habitantes_txt),
        "{{CONDICION}}": _esc(data.get("condicion", "")),
        "{{FILAS_INSPECCION_XML}}": _construir_filas_inspeccion_xml(
            data.get("inspeccion", [])
        ),
        "{{CAPTION_1}}": _esc(captions[0]),
        "{{CAPTION_2}}": _esc(captions[1]),
        "{{CAPTION_3}}": _esc(captions[2]),
        "{{CAPTION_4}}": _esc(captions[3]),
        "{{RECOMENDACIONES_XML}}": _construir_recomendaciones_xml(
            data.get("recomendaciones", [])
        ),
    }

    with zipfile.ZipFile(TEMPLATE_PATH, "r") as zin:
        document_xml = zin.read("word/document.xml").decode("utf-8")

        for token, valor in reemplazos.items():
            document_xml = document_xml.replace(token, valor)

        fotos_bytes = [_preparar_foto_cuadrada(p) for p in fotos_paths]
        media_map = {
            "word/media/image1.jpg": fotos_bytes[0],
            "word/media/image2.jpg": fotos_bytes[1],
            "word/media/image3.jpg": fotos_bytes[2],
            "word/media/image4.jpg": fotos_bytes[3],
        }

        os.makedirs(os.path.dirname(docx_path) or ".", exist_ok=True)
        with zipfile.ZipFile(docx_path, "w", zipfile.ZIP_DEFLATED) as zout:
            for item in zin.infolist():
                if item.filename == "word/document.xml":
                    zout.writestr(item, document_xml.encode("utf-8"))
                elif item.filename in media_map:
                    zout.writestr(item, media_map[item.filename])
                else:
                    zout.writestr(item, zin.read(item.filename))

    return docx_path


if __name__ == "__main__":
    # Prueba rápida local: genera un informe de ejemplo usando 4 fotos
    # cualesquiera que le pases por línea de comandos.
    import sys

    fotos = sys.argv[1:5]
    if len(fotos) != 4:
        print("Uso: python logic_informe.py foto1.jpg foto2.jpg foto3.jpg foto4.jpg")
        sys.exit(1)

    data_prueba = {
        "fecha": "15 de septiembre de 2026",
        "direccion": "Sector Los Pinos, Calle Principal, Casa N°12",
        "parroquia": "Higuerote",
        "tipo_vivienda": "Unifamiliar de bloque, 1 nivel (85 m²)",
        "ambientes": "3 habitaciones, 1 baño, cocina, sala-comedor",
        "nombre": "Carlos Eduardo Pérez",
        "cedula": "V-12.345.678",
        "telefono": "(0414) 555-1212",
        "adultos": 2,
        "menores": 1,
        "condicion": "Propietario",
        "inspeccion": [
            {"elemento": "Techo", "observacion": "Techo de platabanda sin filtraciones aparentes."},
            {"elemento": "Baños (2)", "observacion": "Ambos baños sin revestimiento de paredes ni instalaciones completas."},
            {"elemento": "Fachada posterior", "observacion": "Presenta grietas verticales y desprendimiento de friso."},
            {"elemento": "Cuartos (1)", "observacion": "Falta puerta interna en una habitación."},
        ],
        "recomendaciones": [
            "Colocar puertas internas en las habitaciones señaladas.",
            "Dar mantenimiento preventivo a las instalaciones eléctricas.",
        ],
        "captions": [
            "Fig. 1 — Fachada principal de la vivienda",
            "Fig. 2 — Vista de la sala-comedor",
            "Fig. 3 — Cocina",
            "Fig. 4 — Baño",
        ],
    }

    generar_informe_docx(data_prueba, fotos, "informe_prueba.docx")
    print("Generado: informe_prueba.docx")
