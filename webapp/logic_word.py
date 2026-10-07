"""
Generación de la FICHA DE INSPECCIÓN Y ESTATUS FÍSICO DE LOS PROYECTOS SUVI-PTIH
en formato Word (.docx) -- versión 2.

Cambios de esta versión respecto a la v1:
  - Paleta de color: encabezados de tabla en azul clarito (#D6E4F0), texto
    negro en todo el documento (se eliminó el azul marino fuerte y el
    semáforo de colores rojo/verde).
  - Se eliminó el campo "ÁREA / DISTRIBUCIÓN".
  - "META (PLANIFICADO)" y "UNIDADES INSPECCIONADAS" se fusionaron en una
    sola línea.
  - La Sección II ya NO usa Friso/Techo/Baños/Electricidad/Patología/% Obra:
    ahora es un registro por ETAPAS CONSTRUCTIVAS por unidad (Estructura 30%,
    Cerramientos 25%, Cubierta de Techo 20%, Acabados 25%). "Culminada" no
    tiene peso propio: equivale a que Acabados llegó a 100%.
  - La Sección III cambia de "Resumen estadístico de patologías y fallas" a
    "RESUMEN ACTUAL DE LOS TRABAJOS": avance físico promedio del proyecto +
    conteo de unidades por etapa ACTUAL (categorías que no se solapan).
  - "DIRECCIÓN DE VIVIENDA Y HÁBITAT · RIF G-20002924-2" se movió al
    membrete (imagen de fondo), debajo de "ALCALDÍA DEL MUNICIPIO
    BOLIVARIANO DE BRIÓN", en vez de ir en el cuerpo del documento.

Cambio de esta revisión (corrección PARALIZADO):
  - Antes, si alguna unidad tenía etapa_actual == "Paralizado", la Sección
    III se OCULTABA por completo. Ahora, en ese caso, la sección se sigue
    mostrando pero cambia de modo: en vez de "en qué etapa está trabajando
    cada unidad actualmente", cuenta cuántas unidades YA tienen cada etapa
    culminada (100%), tomado de porcentajes_por_unidad, igual que en la
    ficha de Terrazas de la Arboleda.

Reglas que se mantienen:
  - Cualquier campo que el usuario deje en blanco NO aparece en la ficha
    (sin textos de relleno).
  - El membrete se inserta como imagen de fondo a página completa, anclada
    detrás del texto (behindDoc), igual que en reporte_tecnico.docx.
"""

import io
import os
from datetime import datetime

from docx import Document
from docx.shared import Cm, Pt, Emu, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.oxml import parse_xml

try:
    from PIL import Image as PILImage
except ImportError:
    PILImage = None

# ------------------------------------------------------------------
# Estilo
# ------------------------------------------------------------------
NEGRO = RGBColor(0x1A, 0x1A, 0x1A)
GRIS_ETIQUETA = RGBColor(0x5B, 0x53, 0x46)
HEX_HEADER_TABLA = "D6E4F0"       # azul clarito -- fondo de encabezados de tabla
HEX_BORDE_TITULO = "7FA8D9"       # azul medio -- línea bajo los títulos de sección

RUTA_MEMBRETE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "membrete_fondo.jpg")

TITULO_FICHA = "FICHA DE INSPECCIÓN Y ESTATUS FÍSICO DE LOS PROYECTOS SUVI-PTIH"
TEXTO_DEPENDENCIA = "DIRECCIÓN DE VIVIENDA Y HÁBITAT · RIF G-20002924-2"

# Página carta en EMU (1 in = 914400 EMU)
PAGINA_ANCHO_EMU = 7772400
PAGINA_ALTO_EMU = 10058400

# ------------------------------------------------------------------
# Etapas constructivas y sus pesos (deben sumar 100)
# ------------------------------------------------------------------
ETAPAS = [
    ("estructura", "Estructura", 30),
    ("cerramientos", "Cerramientos", 25),
    ("cubierta_techo", "Cubierta de Techo", 20),
    ("acabados", "Acabados", 25),
]
CLAVES_ETAPA = [c for c, _, _ in ETAPAS]
OPC_ETAPA_CONSTRUCTIVA = [nombre for _, nombre, _ in ETAPAS] + ["Culminada", "Paralizado"]


def _limpio(valor):
    if valor is None:
        return ""
    return str(valor).strip()


def _slug_etapa(nombre_etapa):
    """'Cubierta de Techo' -> 'cubierta_techo' (para comparar con CLAVES_ETAPA)."""
    n = _limpio(nombre_etapa).lower()
    for clave, nombre, _ in ETAPAS:
        if n == nombre.lower() or n == clave:
            return clave
    return None


def calcular_porcentajes_etapas(etapa_actual, porcentaje_dentro_etapa):
    """A partir de la etapa actual de una unidad y el % dentro de esa etapa,
    calcula el % de cada una de las 4 etapas con peso (Estructura, Cerramientos,
    Cubierta de Techo, Acabados). Si etapa_actual es 'Culminada', todas quedan en 100."""
    if _limpio(etapa_actual).lower() == "culminada":
        return {c: 100.0 for c in CLAVES_ETAPA}

    clave_actual = _slug_etapa(etapa_actual)
    if clave_actual is None:
        return {c: 0.0 for c in CLAVES_ETAPA}

    try:
        pct = float(porcentaje_dentro_etapa)
    except (TypeError, ValueError):
        pct = 0.0
    pct = max(0.0, min(100.0, pct))

    idx_actual = CLAVES_ETAPA.index(clave_actual)
    resultado = {}
    for i, clave in enumerate(CLAVES_ETAPA):
        if i < idx_actual:
            resultado[clave] = 100.0
        elif i == idx_actual:
            resultado[clave] = pct
        else:
            resultado[clave] = 0.0
    return resultado


def porcentaje_total_unidad(porcentajes_etapas):
    total = 0.0
    for clave, _, peso in ETAPAS:
        total += peso * porcentajes_etapas.get(clave, 0.0) / 100.0
    return total


# ------------------------------------------------------------------
# Membrete de fondo a página completa + línea de dependencia/RIF superpuesta
# ------------------------------------------------------------------
def _insertar_membrete_fondo(section, ruta_imagen):
    if not os.path.isfile(ruta_imagen):
        return

    header = section.header
    header.is_linked_to_previous = False
    for p in list(header.paragraphs):
        p.text = ""

    p = header.paragraphs[0] if header.paragraphs else header.add_paragraph()
    run = p.add_run()

    rId, _image = header.part.get_or_add_image(ruta_imagen)

    xml_imagen = (
        '<w:drawing xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" '
        'xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing" '
        'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" '
        'xmlns:pic="http://schemas.openxmlformats.org/drawingml/2006/picture" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        '<wp:anchor distT="0" distB="0" distL="0" distR="0" simplePos="0" '
        'relativeHeight="1" behindDoc="1" locked="0" layoutInCell="1" allowOverlap="1">'
        '<wp:simplePos x="0" y="0"/>'
        '<wp:positionH relativeFrom="page"><wp:posOffset>0</wp:posOffset></wp:positionH>'
        '<wp:positionV relativeFrom="page"><wp:posOffset>0</wp:posOffset></wp:positionV>'
        f'<wp:extent cx="{PAGINA_ANCHO_EMU}" cy="{PAGINA_ALTO_EMU}"/>'
        '<wp:effectExtent l="0" t="0" r="0" b="0"/>'
        '<wp:wrapNone/>'
        '<wp:docPr id="1" name="MembreteFondo"/>'
        '<wp:cNvGraphicFramePr><a:graphicFrameLocks noChangeAspect="1"/></wp:cNvGraphicFramePr>'
        '<a:graphic><a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/picture">'
        '<pic:pic><pic:nvPicPr><pic:cNvPr id="0" name="membrete_fondo.jpg"/><pic:cNvPicPr/></pic:nvPicPr>'
        f'<pic:blipFill><a:blip r:embed="{rId}"/><a:stretch><a:fillRect/></a:stretch></pic:blipFill>'
        f'<pic:spPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="{PAGINA_ANCHO_EMU}" cy="{PAGINA_ALTO_EMU}"/></a:xfrm>'
        '<a:prstGeom prst="rect"/></pic:spPr></pic:pic></a:graphicData></a:graphic></wp:anchor></w:drawing>'
    )
    run._r.append(parse_xml(xml_imagen))

    # Línea "DIRECCIÓN DE VIVIENDA Y HÁBITAT · RIF ..." superpuesta en el
    # membrete, debajo de "ALCALDÍA DEL MUNICIPIO BOLIVARIANO DE BRIÓN"
    # (cuadro de texto flotante posicionado sobre la imagen).
    p2 = header.add_paragraph()
    run2 = p2.add_run()
    xml_textbox = (
        '<w:pict xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" '
        'xmlns:v="urn:schemas-microsoft-com:vml" xmlns:w10="urn:schemas-microsoft-com:office:word">'
        '<v:shape id="TxtRif" o:spid="_x0000_s2001" type="#_x0000_t202" '
        'style="position:absolute;margin-left:199.5pt;margin-top:74.5pt;width:300pt;height:16pt;z-index:3;'
        'mso-position-horizontal-relative:page;mso-position-vertical-relative:page;mso-wrap-style:none" '
        'xmlns:o="urn:schemas-microsoft-com:office:office" filled="f" stroked="f">'
        '<v:textbox style="mso-fit-shape-to-text:t" inset="0,0,0,0">'
        '<w:txbxContent>'
        '<w:p><w:pPr><w:spacing w:after="0"/></w:pPr><w:r>'
        '<w:rPr><w:rFonts w:ascii="Arial" w:hAnsi="Arial"/><w:b/><w:color w:val="16294A"/><w:sz w:val="15"/></w:rPr>'
        f'<w:t xml:space="preserve">{TEXTO_DEPENDENCIA}</w:t>'
        '</w:r></w:p>'
        '</w:txbxContent>'
        '</v:textbox>'
        '</v:shape>'
        '</w:pict>'
    )
    run2._r.append(parse_xml(xml_textbox))


# ------------------------------------------------------------------
# Helpers de tabla/texto
# ------------------------------------------------------------------
def _set_cell_text(cell, texto, *, bold=False, size=9, color=NEGRO, italic=False, alignment=None):
    cell.text = ""
    p = cell.paragraphs[0]
    if alignment is not None:
        p.alignment = alignment
    run = p.add_run(texto)
    run.bold = bold
    run.italic = italic
    run.font.size = Pt(size)
    run.font.color.rgb = color
    return run


def _shade_cell(cell, hex_color):
    shd = parse_xml(f'<w:shd xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" '
                     f'w:val="clear" w:fill="{hex_color}"/>')
    cell._tc.get_or_add_tcPr().append(shd)


def _quitar_bordes_tabla(table):
    tbl_pr = table._tbl.tblPr
    borders = parse_xml(
        '<w:tblBorders xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        '<w:top w:val="none" w:sz="0" w:space="0" w:color="auto"/>'
        '<w:left w:val="none" w:sz="0" w:space="0" w:color="auto"/>'
        '<w:bottom w:val="none" w:sz="0" w:space="0" w:color="auto"/>'
        '<w:right w:val="none" w:sz="0" w:space="0" w:color="auto"/>'
        '<w:insideH w:val="single" w:sz="4" w:color="E5E7E9"/>'
        '<w:insideV w:val="none" w:sz="0" w:space="0" w:color="auto"/>'
        '</w:tblBorders>'
    )
    tbl_pr.append(borders)


def _titulo_seccion(doc, texto):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(10)
    p.paragraph_format.space_after = Pt(2)
    run = p.add_run(texto)
    run.bold = True
    run.font.size = Pt(11)
    run.font.color.rgb = NEGRO
    p_border = p._p.get_or_add_pPr()
    borde = parse_xml(
        '<w:pBdr xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        f'<w:bottom w:val="single" w:sz="8" w:space="4" w:color="{HEX_BORDE_TITULO}"/>'
        '</w:pBdr>'
    )
    p_border.append(borde)
    return p


def _preparar_imagen_comprimida(ruta_foto, lado_cm=8.0, dpi=200, calidad=85):
    """Redimensiona y comprime una foto para que ocupe poco espacio en el
    .docx (se muestra a lado_cm x lado_cm). Devuelve un BytesIO en JPEG
    listo para add_picture, o None si no se pudo procesar (se usa el
    archivo original como respaldo)."""
    if PILImage is None:
        return None
    try:
        lado_px = int(round(lado_cm / 2.54 * dpi))
        im = PILImage.open(ruta_foto)
        im = im.convert("RGB")
        w, h = im.size
        lado_corto = min(w, h)
        # recorte centrado a cuadrado (la celda es cuadrada 8x8)
        izq = (w - lado_corto) // 2
        arr = (h - lado_corto) // 2
        im = im.crop((izq, arr, izq + lado_corto, arr + lado_corto))
        im = im.resize((lado_px, lado_px), PILImage.LANCZOS)
        buf = io.BytesIO()
        im.save(buf, format="JPEG", quality=calidad, optimize=True)
        buf.seek(0)
        return buf
    except Exception:
        return None


def generar_word(sesion, carpeta):
    slug = sesion["urbanismo"].replace(" ", "_")
    fecha_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    archivo_salida = os.path.join(carpeta, f"Ficha_{slug}_{fecha_str}.docx")

    doc = Document()
    section = doc.sections[0]
    section.page_width = Emu(PAGINA_ANCHO_EMU)
    section.page_height = Emu(PAGINA_ALTO_EMU)
    section.top_margin = Cm(3.6)
    section.bottom_margin = Cm(2.4)
    section.left_margin = Cm(1.6)
    section.right_margin = Cm(1.6)

    _insertar_membrete_fondo(section, RUTA_MEMBRETE)

    p_tit = doc.add_paragraph()
    p_tit.paragraph_format.space_after = Pt(8)
    run_tit = p_tit.add_run(TITULO_FICHA)
    run_tit.bold = True
    run_tit.font.size = Pt(14)
    run_tit.font.color.rgb = NEGRO

    # -- I. DATOS GENERALES --------------------------------------------
    _titulo_seccion(doc, "I. DATOS GENERALES Y DIAGNÓSTICO DE SERVICIOS")

    total_plan = len(sesion.get("plan_unidades", []))
    total_hechas = len(sesion.get("unidades", []))
    parroquia = _limpio(sesion.get("parroquia"))
    lat = _limpio(sesion.get("latitud"))
    lon = _limpio(sesion.get("longitud"))

    filas_generales = [
        ("FECHA INSPECCIÓN:", _limpio(sesion.get("fecha_inspeccion"))),
        ("PROYECTO / URBANISMO:", _limpio(sesion.get("urbanismo"))),
        ("UBICACIÓN:", _limpio(sesion.get("ubicacion"))),
        ("PARROQUIA:", f"{parroquia}, Brión" if parroquia else ""),
        ("ENTE EJECUTOR:", _limpio(sesion.get("ente_ejecutor"))),
        ("TENENCIA TIERRA:", _limpio(sesion.get("tenencia"))),
        ("RIESGOS:", _limpio(sesion.get("riesgos"))),
        ("TIPOLOGÍA:", _limpio(sesion.get("tipologia"))),
        ("TECNOLOGÍA CONSTRUCTIVA:", _limpio(sesion.get("tecnologia_constructiva"))),
        ("AÑO DE CONSTRUCCIÓN:", _limpio(sesion.get("anio_construccion"))),
        ("UNIDADES INSPECCIONADAS:",
         f"{total_hechas} de {total_plan} proyectadas ({(total_hechas / total_plan * 100) if total_plan else 0:.0f}%)" if total_plan else ""),
        ("ACERAS/BROCALES:", _limpio(sesion.get("aceras"))),
        ("AGUAS BLANCAS:", _limpio(sesion.get("aguas_blancas"))),
        ("AGUAS SERVIDAS:", _limpio(sesion.get("aguas_servidas"))),
        ("SANEAMIENTO:", _limpio(sesion.get("saneamiento"))),
        ("RED ELÉCTRICA:", _limpio(sesion.get("electricidad"))),
        ("INSPECTOR:", _limpio(sesion.get("inspector"))),
        ("UBICACIÓN GPS:", f"{lat}, {lon}" if (lat and lon) else ""),
    ]
    filas_generales = [(et, val) for et, val in filas_generales if val]

    if filas_generales:
        t_gen = doc.add_table(rows=len(filas_generales), cols=2)
        t_gen.autofit = False
        for i, (etiqueta, valor) in enumerate(filas_generales):
            row = t_gen.rows[i]
            row.cells[0].width = Cm(4.6)
            row.cells[1].width = Cm(13.2)
            _set_cell_text(row.cells[0], etiqueta, bold=True, size=8, color=GRIS_ETIQUETA)
            _set_cell_text(row.cells[1], valor, size=8)
        _quitar_bordes_tabla(t_gen)

    # -- II. REGISTRO POR ETAPAS CONSTRUCTIVAS --------------------------
    unidades = sesion.get("unidades", [])
    porcentajes_por_unidad = []
    for u in unidades:
        pcts = calcular_porcentajes_etapas(u.get("etapa_actual"), u.get("porcentaje_etapa"))
        porcentajes_por_unidad.append(pcts)

    if unidades:
        _titulo_seccion(doc, "II. REGISTRO POR ETAPAS CONSTRUCTIVAS")

        NOMBRES_CORTOS = {
            "estructura": "Estructura",
            "cerramientos": "Cerramientos",
            "cubierta_techo": "Cubierta Techo",
            "acabados": "Acabados",
        }
        encabezados = ["Grupo", "Unidad", "Propietario / Estatus / Tel."] + \
                      [f"{NOMBRES_CORTOS[clave]}\n({peso}%)" for clave, _, peso in ETAPAS]
        anchos = [1.5, 1.3, 3.4] + [2.65] * 4

        t_uni = doc.add_table(rows=1, cols=len(encabezados))
        t_uni.autofit = False
        for j, h in enumerate(encabezados):
            cell = t_uni.rows[0].cells[j]
            cell.width = Cm(anchos[j])
            _set_cell_text(cell, h, bold=True, size=8, alignment=WD_ALIGN_PARAGRAPH.CENTER)
            _shade_cell(cell, HEX_HEADER_TABLA)

        for u, pcts in zip(unidades, porcentajes_por_unidad):
            row = t_uni.add_row()
            for j, ancho in enumerate(anchos):
                row.cells[j].width = Cm(ancho)

            telefono = _limpio(u.get("telefono"))
            estatus = _limpio(u.get("estatus"))
            propietario = _limpio(u.get("propietario")) or "Sin Identificar"
            prop_cell = row.cells[2]
            prop_cell.text = ""
            p0 = prop_cell.paragraphs[0]
            r0 = p0.add_run(propietario)
            r0.bold = True
            r0.font.size = Pt(8)
            r0.font.color.rgb = NEGRO
            if estatus:
                p1 = prop_cell.add_paragraph()
                r1 = p1.add_run(f"({estatus})")
                r1.italic = True
                r1.font.size = Pt(7)
                r1.font.color.rgb = GRIS_ETIQUETA
            if telefono:
                p2 = prop_cell.add_paragraph()
                r2 = p2.add_run(f"Tel: {telefono}")
                r2.font.size = Pt(7)
                r2.font.color.rgb = GRIS_ETIQUETA

            _set_cell_text(row.cells[0], _limpio(u.get("grupo")), size=8)
            _set_cell_text(row.cells[1], _limpio(u.get("unidad")), size=8)

            for k, (clave, _, _) in enumerate(ETAPAS):
                valor = pcts.get(clave, 0.0)
                _set_cell_text(row.cells[3 + k], f"{valor:.0f}%", size=8,
                               alignment=WD_ALIGN_PARAGRAPH.CENTER)

    # -- III. RESUMEN ACTUAL DE LOS TRABAJOS -----------------------------
    # Si alguna unidad está marcada "Paralizado", la sección ya NO se
    # oculta: en vez de "en qué etapa está trabajando cada unidad
    # actualmente", se muestra cuántas unidades YA tienen cada etapa
    # culminada (100%), tomado directamente de porcentajes_por_unidad.
    hay_paralizado = any(_limpio(u.get("etapa_actual")).lower() == "paralizado" for u in unidades)

    ETIQUETAS_CULMINADA = {
        "estructura": "Unidades con Estructura culminada",
        "cerramientos": "Unidades con Cerramientos culminados",
        "cubierta_techo": "Unidades con Cubierta de Techo culminada",
        "acabados": "Unidades con Acabados culminados",
    }

    if unidades:
        _titulo_seccion(doc, "III. RESUMEN ACTUAL DE LOS TRABAJOS")

        p_nota = doc.add_paragraph()
        if hay_paralizado:
            texto_nota = (
                "Los trabajos se encuentran PARALIZADOS. El conteo por etapa refleja "
                "cuántas unidades tienen esa etapa culminada (100%), según el registro "
                "por etapas constructivas."
            )
        else:
            texto_nota = (
                "El conteo por etapa refleja en qué está trabajando cada unidad ACTUALMENTE "
                "(no cuántas ya completaron esa etapa)."
            )
        r_nota = p_nota.add_run(texto_nota)
        r_nota.italic = True
        r_nota.font.size = Pt(8)
        r_nota.font.color.rgb = GRIS_ETIQUETA

        totales = [porcentaje_total_unidad(p) for p in porcentajes_por_unidad]
        avance_promedio = (sum(totales) / len(totales)) if totales else 0.0
        tot_unidades = len(unidades)

        filas_resumen = [("Avance físico promedio del proyecto", f"{avance_promedio:.0f}%")]

        # "Culminada" es un estatus que se marca aparte en etapa_actual; no
        # se deriva del % de Acabados (una unidad puede tener sus 4 etapas
        # en 100% sin que el inspector la haya pasado a "Culminada" todavía).
        conteo_culminadas = sum(
            1 for u in unidades if _limpio(u.get("etapa_actual")).lower() == "culminada"
        )

        if hay_paralizado:
            for clave, nombre, _ in ETAPAS:
                culminadas_etapa = sum(
                    1 for p in porcentajes_por_unidad if p.get(clave, 0.0) >= 100
                )
                filas_resumen.append((ETIQUETAS_CULMINADA[clave], f"{culminadas_etapa} de {tot_unidades}"))
            filas_resumen.append(("Unidades Culminadas", f"{conteo_culminadas} de {tot_unidades}"))
        else:
            conteo_etapa = {clave: 0 for clave, _, _ in ETAPAS}
            for u in unidades:
                etapa = _limpio(u.get("etapa_actual"))
                if etapa.lower() != "culminada":
                    clave = _slug_etapa(etapa)
                    if clave:
                        conteo_etapa[clave] += 1
            for clave, nombre, _ in ETAPAS:
                filas_resumen.append((f"Unidades actualmente en {nombre}", f"{conteo_etapa[clave]} de {tot_unidades}"))
            filas_resumen.append(("Unidades Culminadas", f"{conteo_culminadas} de {tot_unidades}"))

        t_res = doc.add_table(rows=1, cols=2)
        t_res.autofit = False
        for j, h in enumerate(["Indicador", "Valor"]):
            cell = t_res.rows[0].cells[j]
            cell.width = Cm(9.6) if j == 0 else Cm(9.4)
            align = WD_ALIGN_PARAGRAPH.CENTER if j > 0 else None
            _set_cell_text(cell, h, bold=True, size=8, alignment=align)
            _shade_cell(cell, HEX_HEADER_TABLA)
        for indicador, valor in filas_resumen:
            row = t_res.add_row()
            row.cells[0].width = Cm(9.6)
            row.cells[1].width = Cm(9.4)
            _set_cell_text(row.cells[0], indicador, size=8)
            _set_cell_text(row.cells[1], valor, size=8, bold=True, alignment=WD_ALIGN_PARAGRAPH.CENTER)

    # -- OBSERVACIONES GENERALES ---------------------------------------
    observaciones = _limpio(sesion.get("observaciones_generales"))
    if observaciones:
        _titulo_seccion(doc, "OBSERVACIONES GENERALES")
        p_obs = doc.add_paragraph()
        run_obs = p_obs.add_run(observaciones)
        run_obs.font.size = Pt(9)
        run_obs.font.color.rgb = NEGRO

    # -- IV. REGISTRO FOTOGRÁFICO ---------------------------------------
    # Máximo 8 fotos, 4 por hoja (cuadrícula 2x2) a 8x8 cm, comprimidas para
    # mantener el .docx liviano.
    fotos_disponibles = [u for u in unidades if u.get("foto") and os.path.isfile(u.get("foto"))][:8]
    if fotos_disponibles:
        _titulo_seccion(doc, "IV. REGISTRO FOTOGRÁFICO")
        cols_galeria = 2
        for idx, u in enumerate(fotos_disponibles):
            col = idx % cols_galeria
            if col == 0:
                if idx > 0 and idx % 4 == 0:
                    doc.add_page_break()
                fila_actual = doc.add_table(rows=1, cols=cols_galeria)
                fila_actual.autofit = False
            celda = fila_actual.rows[0].cells[col]
            celda.width = Cm(8.6)
            p_img = celda.paragraphs[0]
            p_img.alignment = WD_ALIGN_PARAGRAPH.CENTER
            run_img = p_img.add_run()
            imagen_lista = _preparar_imagen_comprimida(u["foto"])
            try:
                if imagen_lista is not None:
                    run_img.add_picture(imagen_lista, width=Cm(8.0), height=Cm(8.0))
                else:
                    run_img.add_picture(u["foto"], width=Cm(8.0), height=Cm(8.0))
            except Exception:
                p_img.add_run("(no se pudo cargar la imagen)")
            p_cap = celda.add_paragraph()
            p_cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
            run_cap = p_cap.add_run(f"{_limpio(u.get('grupo'))} — {_limpio(u.get('unidad'))}")
            run_cap.bold = True
            run_cap.font.size = Pt(8)
            run_cap.font.color.rgb = NEGRO

    doc.save(archivo_salida)
    return archivo_salida
