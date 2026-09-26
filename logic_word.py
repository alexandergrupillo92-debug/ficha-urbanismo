"""
Generación de la FICHA DE INSPECCIÓN Y ESTATUS FÍSICO DE LOS PROYECTOS SUVI-PTIH
en formato Word (.docx), reemplazando la salida anterior en PDF (reportlab).

Reglas clave pedidas por el usuario:
  - Cualquier campo que el usuario deje en blanco (o no escriba) NO aparece en la
    ficha final -- ni la etiqueta ni el valor. No se usan textos de relleno como
    "No especificado" o "No registrada".
  - El membrete institucional (logos + marca de agua + pie "Brión un legado de
    Identidad") se coloca como imagen de fondo a página completa, igual que en
    reporte_tecnico.docx, usando la misma técnica de ancla flotante detrás del
    texto (behindDoc) en el header de la sección.

Este archivo se puede usar como reemplazo de la parte de generación de
documento de logic.py: importar `generar_word` y llamarla donde antes se
llamaba a `generar_pdf`.
"""

import os
from datetime import datetime

from docx import Document
from docx.shared import Cm, Pt, Emu, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn
from docx.oxml import parse_xml

# ------------------------------------------------------------------
# Constantes de estilo (colores tomados de la ficha en PDF existente)
# ------------------------------------------------------------------
C_AZUL = RGBColor(0x16, 0x29, 0x4A)
C_ORO = RGBColor(0xD4, 0xAC, 0x0D)
C_ROJO = RGBColor(0xC0, 0x39, 0x2B)
C_VERDE = RGBColor(0x27, 0xAE, 0x60)
C_GRIS_ETIQUETA = RGBColor(0x5B, 0x53, 0x46)

RUTA_MEMBRETE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "membrete_fondo.jpg")

TITULO_FICHA = "FICHA DE INSPECCIÓN Y ESTATUS FÍSICO DE LOS PROYECTOS SUVI-PTIH"

# Página carta en EMU (1 in = 914400 EMU) -- igual que en reporte_tecnico.docx
PAGINA_ANCHO_EMU = 7772400
PAGINA_ALTO_EMU = 10058400

SIN_PATOLOGIA = ["ninguna", "ninguno", "no", "n/a", "none", "0", ""]


def _limpio(valor):
    """Normaliza un valor: strip() y None -> ''. Usar para decidir si un campo está en blanco."""
    if valor is None:
        return ""
    return str(valor).strip()


def ruta_word(nombre_urbanismo, carpeta):
    slug = nombre_urbanismo.replace(" ", "_")
    fecha_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    return os.path.join(carpeta, f"Ficha_{slug}_{fecha_str}.docx")


def calcular_estadisticas(unidades):
    total = len(unidades)
    cant_pat = sum(1 for u in unidades if _limpio(u.get("patologia")).lower() not in SIN_PATOLOGIA)
    cant_friso = sum(1 for u in unidades if u.get("friso", "") in ["Pendiente", "Deteriorado"])
    cant_techo = sum(1 for u in unidades if any(
        k in _limpio(u.get("techo")).lower() for k in
        ["humedad", "filtracion", "filtraciones", "deteriorada", "sin cubierta"]))
    cant_elec = sum(1 for u in unidades if u.get("electricidad_unidad", "") == "Clandestina")
    cant_banos = sum(1 for u in unidades if any(
        k in _limpio(u.get("banos")) for k in ["Sin", "proceso", "Fuera", "Otro"]))

    pct = lambda c: (c / total * 100) if total else 0.0
    return (
        total, cant_pat, cant_friso, cant_techo, cant_banos, cant_elec,
        pct(cant_pat), pct(cant_friso), pct(cant_techo), pct(cant_banos), pct(cant_elec)
    )


# ------------------------------------------------------------------
# Membrete de fondo a página completa (mismo patrón que reporte_tecnico.docx)
# ------------------------------------------------------------------
def _insertar_membrete_fondo(section, ruta_imagen):
    """Inserta la imagen de membrete como fondo de página completa, anclada
    detrás del texto (behindDoc="1"), en el header de la sección -- idéntico
    al patrón encontrado en reporte_tecnico.docx (membrete_fondo.jpg)."""
    if not os.path.isfile(ruta_imagen):
        return

    header = section.header
    header.is_linked_to_previous = False
    # Limpiar cualquier párrafo por defecto del header
    for p in list(header.paragraphs):
        p.text = ""

    p = header.paragraphs[0] if header.paragraphs else header.add_paragraph()
    run = p.add_run()

    rId, _image = header.part.get_or_add_image(ruta_imagen)

    xml = (
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
    run._r.append(parse_xml(xml))


# ------------------------------------------------------------------
# Helpers de estilo de texto/párrafo
# ------------------------------------------------------------------
def _set_cell_text(cell, texto, *, bold=False, size=9, color=None, italic=False, alignment=None):
    cell.text = ""
    p = cell.paragraphs[0]
    if alignment is not None:
        p.alignment = alignment
    run = p.add_run(texto)
    run.bold = bold
    run.italic = italic
    run.font.size = Pt(size)
    if color is not None:
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
    run.font.color.rgb = C_AZUL
    # línea dorada debajo, simulando el HRFlowable del PDF
    p_border = p._p.get_or_add_pPr()
    borde = parse_xml(
        '<w:pBdr xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        '<w:bottom w:val="single" w:sz="8" w:space="4" w:color="D4AC0D"/>'
        '</w:pBdr>'
    )
    p_border.append(borde)
    return p


def generar_word(sesion, carpeta):
    archivo_salida = ruta_word(sesion["urbanismo"], carpeta)
    doc = Document()

    section = doc.sections[0]
    section.page_width = Emu(PAGINA_ANCHO_EMU)
    section.page_height = Emu(PAGINA_ALTO_EMU)
    section.top_margin = Cm(4.4)
    section.bottom_margin = Cm(2.4)
    section.left_margin = Cm(1.6)
    section.right_margin = Cm(1.6)

    _insertar_membrete_fondo(section, RUTA_MEMBRETE)

    # -- Encabezado del documento (dependencia + título) --------------
    p_dep = doc.add_paragraph()
    p_dep.paragraph_format.space_after = Pt(4)
    run_dep = p_dep.add_run("DIRECCIÓN DE VIVIENDA Y HÁBITAT · RIF G-20002924-2")
    run_dep.bold = True
    run_dep.font.size = Pt(9)
    run_dep.font.color.rgb = C_AZUL

    p_tit = doc.add_paragraph()
    p_tit.paragraph_format.space_after = Pt(8)
    run_tit = p_tit.add_run(TITULO_FICHA)
    run_tit.bold = True
    run_tit.font.size = Pt(14)
    run_tit.font.color.rgb = C_AZUL

    # -- I. DATOS GENERALES --------------------------------------------
    _titulo_seccion(doc, "I. DATOS GENERALES Y DIAGNÓSTICO DE SERVICIOS")

    area_m2 = _limpio(sesion.get("area_m2"))
    cuartos = _limpio(sesion.get("cuartos"))
    banos_modelo = _limpio(sesion.get("banos_modelo"))
    descripcion_area = ""
    if area_m2 or cuartos or banos_modelo:
        partes = []
        if area_m2:
            partes.append(f"{area_m2} m2")
        if cuartos:
            partes.append(f"{cuartos} Hab")
        if banos_modelo:
            partes.append(f"{banos_modelo} Baño(s)")
        partes.append("Sala, Comedor, Cocina")
        descripcion_area = " / ".join(partes)

    total_plan = len(sesion.get("plan_unidades", []))
    total_hechas = len(sesion.get("unidades", []))
    avances = []
    for u in sesion.get("unidades", []):
        try:
            avances.append(float(u.get("avance_obra") or 0))
        except (TypeError, ValueError):
            pass
    avance_promedio = (sum(avances) / len(avances)) if avances else None

    parroquia = _limpio(sesion.get("parroquia"))
    lat = _limpio(sesion.get("latitud"))
    lon = _limpio(sesion.get("longitud"))

    # Cada entrada: (etiqueta, valor_ya_formateado). Si valor es "" se omite la fila entera.
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
        ("ÁREA / DISTRIBUCIÓN:", descripcion_area),
        ("AÑO DE CONSTRUCCIÓN:", _limpio(sesion.get("anio_construccion"))),
        ("META (PLANIFICADO):", f"{total_plan} unidades" if total_plan else ""),
        ("UNIDADES INSPECCIONADAS:",
         f"{total_hechas} de {total_plan} ({(total_hechas / total_plan * 100) if total_plan else 0:.0f}%)" if total_plan else ""),
        ("AVANCE FÍSICO PROMEDIO:",
         f"{avance_promedio:.0f}% (según las {total_hechas} unidades ya inspeccionadas)" if avance_promedio is not None else ""),
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
        t_gen.columns[0].width = Cm(4.6)
        t_gen.columns[1].width = Cm(13.2)
        for i, (etiqueta, valor) in enumerate(filas_generales):
            row = t_gen.rows[i]
            row.cells[0].width = Cm(4.6)
            row.cells[1].width = Cm(13.2)
            _set_cell_text(row.cells[0], etiqueta, bold=True, size=8, color=C_GRIS_ETIQUETA)
            _set_cell_text(row.cells[1], valor, size=8)
        _quitar_bordes_tabla(t_gen)

    # -- II. REGISTRO FÍSICO DE UNIDADES -------------------------------
    unidades = sesion.get("unidades", [])
    if unidades:
        _titulo_seccion(doc, "II. REGISTRO FÍSICO DE UNIDADES HABITACIONALES")

        encabezados = ["Grupo", "Unidad", "Propietario / Estatus / Tel.", "Friso",
                        "Techo / Cubierta", "Baños", "Electricidad", "Patología", "% Obra"]
        anchos = [1.7, 1.4, 3.2, 1.6, 2.7, 2.7, 1.6, 2.0, 1.4]

        t_uni = doc.add_table(rows=1, cols=len(encabezados))
        t_uni.autofit = False
        for j, h in enumerate(encabezados):
            cell = t_uni.rows[0].cells[j]
            cell.width = Cm(anchos[j])
            _set_cell_text(cell, h, bold=True, size=7, color=C_ORO, alignment=WD_ALIGN_PARAGRAPH.CENTER)
            _shade_cell(cell, "16294A")

        for u in unidades:
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
            r0.font.size = Pt(7)
            if estatus:
                p1 = prop_cell.add_paragraph()
                r1 = p1.add_run(f"({estatus})")
                r1.italic = True
                r1.font.size = Pt(6)
                r1.font.color.rgb = C_GRIS_ETIQUETA
            if telefono:
                p2 = prop_cell.add_paragraph()
                r2 = p2.add_run(f"Tel: {telefono}")
                r2.font.size = Pt(6)
                r2.font.color.rgb = C_GRIS_ETIQUETA

            _set_cell_text(row.cells[0], _limpio(u.get("grupo")), size=7)
            _set_cell_text(row.cells[1], _limpio(u.get("unidad")), size=7)

            friso = _limpio(u.get("friso"))
            color_friso = C_ROJO if friso in ["Pendiente", "Deteriorado"] else C_VERDE
            _set_cell_text(row.cells[3], friso, size=7, bold=True, color=color_friso)

            techo = _limpio(u.get("techo"))
            color_techo = C_ROJO if any(k in techo.lower() for k in
                                         ["humedad", "filtracion", "filtraciones", "deteriorada", "sin cubierta"]) else C_VERDE
            _set_cell_text(row.cells[4], techo, size=7, bold=True, color=color_techo)

            banos = _limpio(u.get("banos"))
            color_banos = C_ROJO if any(k in banos for k in ["Sin", "proceso", "Fuera", "Otro"]) else C_VERDE
            _set_cell_text(row.cells[5], banos, size=7, bold=True, color=color_banos)

            elec = _limpio(u.get("electricidad_unidad"))
            color_elec = C_ROJO if elec == "Clandestina" else C_VERDE
            _set_cell_text(row.cells[6], elec, size=7, bold=True, color=color_elec)

            patologia = _limpio(u.get("patologia")) or "Ninguna"
            color_pat = C_VERDE if patologia.lower() in SIN_PATOLOGIA else C_ROJO
            _set_cell_text(row.cells[7], patologia, size=7, bold=True, color=color_pat)

            avance = u.get("avance_obra")
            avance_str = _limpio(avance)
            texto_avance = f"{avance_str}%" if avance_str else ""
            color_avance = C_VERDE if avance_str == "100" else (C_ROJO if avance_str in ("0", "") else None)
            _set_cell_text(row.cells[8], texto_avance, size=7, bold=True, color=color_avance,
                           alignment=WD_ALIGN_PARAGRAPH.CENTER)

    # -- III. RESUMEN ESTADÍSTICO --------------------------------------
    if unidades:
        _titulo_seccion(doc, "III. RESUMEN ESTADÍSTICO DE PATOLOGÍAS Y FALLAS")
        tot, c_pat, c_friso, c_techo, c_banos, c_elec, p_pat, p_friso, p_techo, p_banos, p_elec = calcular_estadisticas(unidades)

        filas_resumen = [
            ("Patologías Registradas", f"{c_pat} / {tot}", f"{p_pat:.1f}%"),
            ("Friso Pendiente / Deteriorado", f"{c_friso} / {tot}", f"{p_friso:.1f}%"),
            ("Techo o Entrepiso Afectado", f"{c_techo} / {tot}", f"{p_techo:.1f}%"),
            ("Baños con Deficiencias", f"{c_banos} / {tot}", f"{p_banos:.1f}%"),
            ("Conexión Eléctrica Clandestina", f"{c_elec} / {tot}", f"{p_elec:.1f}%"),
        ]
        t_res = doc.add_table(rows=1, cols=3)
        t_res.autofit = False
        anchos_res = [9.6, 4.5, 4.5]
        for j, h in enumerate(["Indicador", "Afectados", "Porcentaje"]):
            cell = t_res.rows[0].cells[j]
            cell.width = Cm(anchos_res[j])
            align = WD_ALIGN_PARAGRAPH.CENTER if j > 0 else None
            _set_cell_text(cell, h, bold=True, size=8, color=C_ORO, alignment=align)
            _shade_cell(cell, "16294A")
        for indicador, afectados, porcentaje in filas_resumen:
            row = t_res.add_row()
            for j, ancho in enumerate(anchos_res):
                row.cells[j].width = Cm(ancho)
            _set_cell_text(row.cells[0], indicador, size=8)
            _set_cell_text(row.cells[1], afectados, size=8, alignment=WD_ALIGN_PARAGRAPH.CENTER)
            _set_cell_text(row.cells[2], porcentaje, size=8, alignment=WD_ALIGN_PARAGRAPH.CENTER)

    # -- OBSERVACIONES GENERALES ---------------------------------------
    observaciones = _limpio(sesion.get("observaciones_generales"))
    if observaciones:
        _titulo_seccion(doc, "OBSERVACIONES GENERALES")
        p_obs = doc.add_paragraph()
        run_obs = p_obs.add_run(observaciones)
        run_obs.font.size = Pt(9)

    # -- IV. REGISTRO FOTOGRÁFICO ---------------------------------------
    fotos_disponibles = [u for u in unidades if u.get("foto") and os.path.isfile(u.get("foto"))]
    if fotos_disponibles:
        _titulo_seccion(doc, "IV. REGISTRO FOTOGRÁFICO")
        cols_galeria = 3
        filas_necesarias = (len(fotos_disponibles) + cols_galeria - 1) // cols_galeria
        t_gal = doc.add_table(rows=filas_necesarias, cols=cols_galeria)
        t_gal.autofit = False
        for idx, u in enumerate(fotos_disponibles):
            r, c = divmod(idx, cols_galeria)
            celda = t_gal.rows[r].cells[c]
            celda.width = Cm(6.0)
            p_img = celda.paragraphs[0]
            p_img.alignment = WD_ALIGN_PARAGRAPH.CENTER
            run_img = p_img.add_run()
            try:
                run_img.add_picture(u["foto"], width=Cm(5.4))
            except Exception:
                p_img.add_run("(no se pudo cargar la imagen)")
            p_cap = celda.add_paragraph()
            p_cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
            run_cap = p_cap.add_run(f"{_limpio(u.get('grupo'))} — {_limpio(u.get('unidad'))}")
            run_cap.bold = True
            run_cap.font.size = Pt(8)
            run_cap.font.color.rgb = C_AZUL

    doc.save(archivo_salida)
    return archivo_salida
