import json
import os
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.graphics.shapes import Circle, Drawing, Path, Rect, String
from reportlab.platypus import (
    HRFlowable, Image, KeepTogether, Paragraph, SimpleDocTemplate,
    Spacer, Table, TableStyle,
)

try:
    from PIL import Image as PILImage
except ImportError:
    PILImage = None

OPC_PARROQUIA = ["Higuerote", "Curiepe", "Tacarigua"]
OPC_TENENCIA = ["Ejido municipal", "Privado", "Urbanismo G.M.V.V."]
OPC_ACERAS = ["Bueno", "Regular", "Inexistente"]
OPC_AGUAS_BLANCAS = ["Red de distribución", "Pozo profundo", "Cisterna"]

OPC_AGUAS_SERVIDAS = [
    "Red de cloacas",
    "Red hacia planta de tratamiento",
    "Descarga directa / Sin red",
    "Pozo séptico (Unifamiliar)"
]
OPC_SANEAMIENTO = [
    "Planta de tratamiento (Operativa)",
    "Planta de tratamiento (Fuera de servicio)",
    "Laguna de oxidación (Operativa)",
    "Laguna de oxidación (Fuera de servicio)",
    "Pozo séptico (Operativo)",
    "Pozo séptico (Colapsado)",
    "Ninguno"
]

OPC_TIPO = ["Edificios", "Casas"]
OPC_ESTATUS = ["Habitado", "Desocupado", "En Construcción", "Asignado no Habitado"]
OPC_FRISO = ["Bueno", "Pendiente", "Deteriorado"]
OPC_ELECTRICIDAD = ["Reglamentaria", "Clandestina"]

OPC_TECHO_CASAS = [
    "Losa techo en buen estado",
    "Losa techo con filtraciones",
    "Láminas de techo en buen estado",
    "Láminas de techo deterioradas",
    "Sin cubierta de techo"
]

OPC_TECHO_EDIFICIOS = [
    "Losa de entrepiso en buen estado",
    "Losa de entrepiso con humedad",
    "Losa de entrepiso con filtraciones",
    "Losa techo en buen estado",
    "Losa techo con filtraciones"
]

OPC_BANOS_COND = [
    "Completo",
    "Sin revestimiento cerámico",
    "Sin piezas sanitarias",
    "En proceso de culminación",
    "Fuera de servicio"
]

OPC_PATOLOGIAS = ["Ninguna", "Grietas", "Fisuras", "Humedad", "Filtraciones"]
SIN_PATOLOGIA = ["ninguna", "ninguno", "no", "n/a", "none", "0", ""]


def carpeta_guardado(preferida):
    os.makedirs(preferida, exist_ok=True)
    return preferida


def ruta_progreso(nombre_urbanismo, carpeta):
    slug = nombre_urbanismo.replace(" ", "_")
    return os.path.join(carpeta, f".progreso_{slug}.json")


def ruta_pdf(nombre_urbanismo, carpeta):
    slug = nombre_urbanismo.replace(" ", "_")
    fecha_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    return os.path.join(carpeta, f"Ficha_{slug}_{fecha_str}.pdf")


def guardar_progreso(sesion, carpeta):
    try:
        with open(ruta_progreso(sesion["urbanismo"], carpeta), "w", encoding="utf-8") as f:
            json.dump(sesion, f, ensure_ascii=False, indent=2)
        return True
    except Exception:
        return False


def cargar_progreso(nombre_urbanismo, carpeta):
    ruta = ruta_progreso(nombre_urbanismo, carpeta)
    if os.path.isfile(ruta):
        try:
            with open(ruta, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return None
    return None


def calcular_estadisticas(unidades):
    total = len(unidades)
    cant_pat = sum(1 for u in unidades if u.get("patologia", "").strip().lower() not in SIN_PATOLOGIA)
    cant_friso = sum(1 for u in unidades if u.get("friso", "") in ["Pendiente", "Deteriorado"])
    cant_techo = sum(1 for u in unidades if any(
        k in u.get("techo", "").lower() for k in
        ["humedad", "filtracion", "filtraciones", "deteriorada", "sin cubierta"]))
    cant_elec = sum(1 for u in unidades if u.get("electricidad_unidad", "") == "Clandestina")
    cant_banos = sum(1 for u in unidades if any(
        k in u.get("banos", "") for k in ["Sin", "proceso", "Fuera", "Otro"]))

    pct = lambda c: (c / total * 100) if total else 0.0
    return (
        total, cant_pat, cant_friso, cant_techo, cant_banos, cant_elec,
        pct(cant_pat), pct(cant_friso), pct(cant_techo), pct(cant_banos), pct(cant_elec)
    )


def crear_sello_vectorial():
    d = Drawing(70, 70)
    d.add(Circle(35, 35, 33, fillColor=colors.HexColor("#16294A"), strokeColor=colors.HexColor("#FFD700"), strokeWidth=2))
    p = Path(fillColor=None, strokeColor=colors.HexColor("#FFD700"), strokeWidth=2)
    p.moveTo(35, 52); p.lineTo(50, 40); p.lineTo(45, 40); p.lineTo(45, 25); p.lineTo(25, 25); p.lineTo(25, 40); p.lineTo(20, 40); p.closePath()
    d.add(Rect(31, 25, 8, 9, fillColor=colors.HexColor("#FFD700"), strokeColor=None))
    d.add(String(35, 56, "ALCALDÍA DE BRIÓN", textAnchor="middle", fontSize=3.8, fillColor=colors.white, fontName="Times-Bold"))
    d.add(String(35, 17, "HÁBITAT Y VIVIENDA", textAnchor="middle", fontSize=3.8, fillColor=colors.HexColor("#FFD700"), fontName="Times-Bold"))
    d.add(String(35, 11, "ESTADO MIRANDA", textAnchor="middle", fontSize=3.2, fillColor=colors.HexColor("#E5E7E9"), fontName="Times-Roman"))
    return d


ANCHO_MAX_FOTO = 1.8 * cm
ALTO_MAX_FOTO = 2.2 * cm

RUTA_MEMBRETE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "membrete_fondo.jpg")


def dibujar_fondo(c, doc):
    ancho_pagina, alto_pagina = letter
    if os.path.isfile(RUTA_MEMBRETE):
        c.drawImage(RUTA_MEMBRETE, 0, 0, width=ancho_pagina, height=alto_pagina,
                    preserveAspectRatio=False, mask="auto")


def celda_foto(ruta_foto, estilo_vacio):
    if not ruta_foto or not os.path.isfile(ruta_foto) or PILImage is None:
        return Paragraph("-", estilo_vacio)
    try:
        im = PILImage.open(ruta_foto)
        w, h = im.size
        ancho = ANCHO_MAX_FOTO
        alto = ancho * h / w
        if alto > ALTO_MAX_FOTO:
            alto = ALTO_MAX_FOTO
            ancho = alto * w / h
        return Image(ruta_foto, width=ancho, height=alto)
    except Exception:
        return Paragraph("-", estilo_vacio)


def generar_pdf(sesion, carpeta):
    archivo_salida = ruta_pdf(sesion["urbanismo"], carpeta)
    doc = SimpleDocTemplate(
        archivo_salida, pagesize=letter,
        leftMargin=1.3 * cm, rightMargin=1.3 * cm,
        topMargin=4.6 * cm, bottomMargin=2.6 * cm,
    )

    elementos = []
    styles = getSampleStyleSheet()

    c_azul = colors.HexColor("#16294A")
    c_oro = colors.HexColor("#D4AC0D")
    c_rojo = colors.HexColor("#C0392B")
    c_verde = colors.HexColor("#27AE60")

    st_inst = ParagraphStyle("Inst", parent=styles["Normal"], fontName="Times-Bold", fontSize=9, leading=11, textColor=c_oro)
    st_tit = ParagraphStyle("Tit", parent=styles["Normal"], fontName="Times-Bold", fontSize=13, leading=15, textColor=colors.white)
    st_sub = ParagraphStyle("Sub", parent=styles["Normal"], fontName="Times-Roman", fontSize=8, textColor=colors.HexColor("#D5D8DC"))
    st_sec = ParagraphStyle("Sec", parent=styles["Normal"], fontName="Times-Bold", fontSize=10, textColor=c_azul)
    st_etiqueta = ParagraphStyle("Etiq", parent=styles["Normal"], fontName="Times-Bold", fontSize=8, textColor=colors.HexColor("#5B5346"))
    st_valor = ParagraphStyle("Val", parent=styles["Normal"], fontName="Times-Roman", fontSize=8, textColor=colors.black)

    st_th = ParagraphStyle("TH", parent=styles["Normal"], fontName="Times-Bold", fontSize=7, leading=8.5, textColor=c_oro, alignment=1)
    st_tb = ParagraphStyle("TB", parent=styles["Normal"], fontName="Times-Roman", fontSize=7, leading=8.5)
    st_tb_alerta = ParagraphStyle("TBA", parent=styles["Normal"], fontName="Times-Bold", fontSize=7, leading=8.5, textColor=c_rojo)
    st_tb_ok = ParagraphStyle("TBO", parent=styles["Normal"], fontName="Times-Bold", fontSize=7, leading=8.5, textColor=c_verde)
    st_prop = ParagraphStyle("Prop", parent=styles["Normal"], fontName="Times-Bold", fontSize=7, leading=8)
    st_link = ParagraphStyle("Link", parent=styles["Normal"], fontName="Times-Roman", fontSize=8, textColor=colors.HexColor("#1155CC"))

    elementos.extend([
        Paragraph("DIRECCIÓN DE VIVIENDA Y HÁBITAT · RIF G-20002924-2", ParagraphStyle("Dep", parent=styles["Normal"], fontName="Times-Bold", fontSize=8, textColor=c_azul)),
        Spacer(1, 4),
        Paragraph("FICHA DE INSPECCIÓN Y ESTATUS FÍSICO DE URBANISMO", ParagraphStyle("TitDoc", parent=styles["Normal"], fontName="Times-Bold", fontSize=13, textColor=c_azul)),
        Spacer(1, 10),
        Paragraph("I. DATOS GENERALES Y DIAGNÓSTICO DE SERVICIOS", st_sec),
        HRFlowable(width="100%", thickness=1, color=c_oro, spaceBefore=3, spaceAfter=6),
    ])

    f_dato = lambda l, v: [Paragraph(l, st_etiqueta), Paragraph(str(v), st_valor)]

    area_m2 = (sesion.get("area_m2") or "").strip()
    cuartos = (sesion.get("cuartos") or "").strip()
    banos_modelo = (sesion.get("banos_modelo") or "").strip()
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
    else:
        descripcion_area = "No especificada"

    total_plan = len(sesion.get("plan_unidades", []))
    total_hechas = len(sesion.get("unidades", []))

    avances = []
    for u in sesion.get("unidades", []):
        try:
            avances.append(float(u.get("avance_obra") or 0))
        except (TypeError, ValueError):
            pass
    avance_promedio = (sum(avances) / len(avances)) if avances else 0

    filas_generales = [
        f_dato("FECHA INSPECCIÓN:", sesion.get('fecha_inspeccion', "")), f_dato("PROYECTO / URBANISMO:", sesion['urbanismo']), f_dato("UBICACIÓN:", sesion['ubicacion']),
        f_dato("PARROQUIA:", sesion['parroquia'] + ", Brión"), f_dato("ENTE EJECUTOR:", sesion.get('ente_ejecutor') or "No especificado"),
        f_dato("TENENCIA TIERRA:", sesion['tenencia']), f_dato("RIESGOS:", sesion['riesgos']),
        f_dato("TIPOLOGÍA:", sesion.get('tipologia') or "No especificada"), f_dato("TECNOLOGÍA CONSTRUCTIVA:", sesion.get('tecnologia_constructiva') or "No especificada"),
        f_dato("ÁREA / DISTRIBUCIÓN:", descripcion_area), f_dato("AÑO DE CONSTRUCCIÓN:", sesion.get('anio_construccion') or "No especificado"),
        f_dato("META (PLANIFICADO):", f"{total_plan} unidades"),
        f_dato("UNIDADES INSPECCIONADAS:", f"{total_hechas} de {total_plan} ({(total_hechas / total_plan * 100) if total_plan else 0:.0f}%)"),
        f_dato("AVANCE FÍSICO PROMEDIO:", f"{avance_promedio:.0f}% (según las {total_hechas} unidades ya inspeccionadas)"),
        f_dato("ACERAS/BROCALES:", sesion['aceras']), f_dato("AGUAS BLANCAS:", sesion['aguas_blancas']), f_dato("AGUAS SERVIDAS:", sesion['aguas_servidas']),
        f_dato("SANEAMIENTO:", sesion['saneamiento']), f_dato("RED ELÉCTRICA:", sesion['electricidad']),
    ]

    if (sesion.get("inspector") or "").strip():
        filas_generales.append(f_dato("INSPECTOR:", sesion["inspector"].strip()))


    lat = (sesion.get("latitud") or "").strip()
    lon = (sesion.get("longitud") or "").strip()
    if lat and lon:
        enlace = f'<link href="https://www.google.com/maps?q={lat},{lon}"><u>Ver ubicación satelital ({lat}, {lon})</u></link>'
        filas_generales.append([Paragraph("UBICACIÓN GPS:", st_etiqueta), Paragraph(enlace, st_link)])
    else:
        filas_generales.append(f_dato("UBICACIÓN GPS:", "No registrada"))

    t_gen = Table(filas_generales, colWidths=[4.5 * cm, 13.6 * cm])
    t_gen.setStyle(TableStyle([("LINEBELOW", (0, 0), (-1, -1), 0.5, colors.HexColor("#E5E7E9")), ("PADDING", (0, 0), (-1, -1), 3)]))
    elementos.extend([t_gen, Spacer(1, 14), Paragraph("II. REGISTRO FÍSICO DE UNIDADES HABITACIONALES", st_sec), HRFlowable(width="100%", thickness=1, color=c_oro, spaceBefore=3, spaceAfter=6)])

    filas_tabla = [[Paragraph(h, st_th) for h in ["Grupo", "Unidad", "Propietario / Estatus / Tel.", "Friso", "Techo / Cubierta", "Baños", "Electricidad", "Patología", "% Obra"]]]
    estilos_tabla = [("BACKGROUND", (0, 0), (-1, 0), c_azul), ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#D5D8DC")), ("VALIGN", (0, 0), (-1, -1), "MIDDLE")]

    grupo_anterior = None
    for i, u in enumerate(sesion["unidades"], start=1):
        st_fri = st_tb_alerta if u.get("friso") in ["Pendiente", "Deteriorado"] else st_tb_ok
        st_tec = st_tb_alerta if any(k in u.get("techo", "").lower() for k in ["humedad", "filtracion", "filtraciones", "deteriorada", "sin cubierta"]) else st_tb_ok
        st_ban = st_tb_alerta if any(k in u.get("banos", "") for k in ["Sin", "proceso", "Fuera", "Otro"]) else st_tb_ok
        st_elec = st_tb_alerta if u.get("electricidad_unidad") == "Clandestina" else st_tb_ok
        st_pat = st_tb_ok if u.get("patologia", "Ninguna").strip().lower() in SIN_PATOLOGIA else st_tb_alerta

        telefono = u.get("telefono", "").strip()
        linea_tel = f"<br/><font color='#5B5346' size='6'>Tel: {telefono}</font>" if telefono else ""
        prop_str = f"{u.get('propietario', 'S/I')}<br/><font color='#5B5346' size='6'><i>({u.get('estatus', 'Habitado')})</i></font>{linea_tel}"

        if grupo_anterior and u["grupo"] != grupo_anterior:
            estilos_tabla.append(("LINEABOVE", (0, i), (-1, i), 1.5, c_azul))
        grupo_anterior = u["grupo"]

        avance = u.get("avance_obra", "").strip() if isinstance(u.get("avance_obra"), str) else u.get("avance_obra")
        texto_avance = f"{avance}%" if avance not in (None, "") else "-"
        st_avance = st_tb_ok if str(avance) in ("100",) else (st_tb_alerta if str(avance) in ("0", "") else st_tb)

        filas_tabla.append([
            Paragraph(u["grupo"], st_tb), Paragraph(u["unidad"], st_tb), Paragraph(prop_str, st_prop),
            Paragraph(u.get("friso", "-"), st_fri), Paragraph(u.get("techo", "-"), st_tec), Paragraph(u.get("banos", "-"), st_ban),
            Paragraph(u.get("electricidad_unidad", "Reglamentaria"), st_elec), Paragraph(u.get("patologia", "Ninguna"), st_pat),
            Paragraph(texto_avance, st_avance),
        ])

    t_unidades = Table(filas_tabla, colWidths=[1.9 * cm, 1.5 * cm, 3.1 * cm, 1.7 * cm, 2.9 * cm, 2.9 * cm, 1.7 * cm, 2.1 * cm, 1.6 * cm])
    t_unidades.setStyle(TableStyle(estilos_tabla))
    elementos.extend([t_unidades, Spacer(1, 14)])

    tot, c_pat, c_friso, c_techo, c_banos, c_elec, p_pat, p_friso, p_techo, p_banos, p_elec = calcular_estadisticas(sesion["unidades"])
    t_resumen = Table([
        [Paragraph(h, st_th) for h in ["Indicador", "Afectados", "Porcentaje"]],
        [Paragraph("Patologías Registradas", st_tb), Paragraph(f"{c_pat} / {tot}", st_tb), Paragraph(f"{p_pat:.1f}%", st_tb)],
        [Paragraph("Friso Pendiente / Deteriorado", st_tb), Paragraph(f"{c_friso} / {tot}", st_tb), Paragraph(f"{p_friso:.1f}%", st_tb)],
        [Paragraph("Techo o Entrepiso Afectado", st_tb), Paragraph(f"{c_techo} / {tot}", st_tb), Paragraph(f"{p_techo:.1f}%", st_tb)],
        [Paragraph("Baños con Deficiencias", st_tb), Paragraph(f"{c_banos} / {tot}", st_tb), Paragraph(f"{p_banos:.1f}%", st_tb)],
        [Paragraph("Conexión Eléctrica Clandestina", st_tb), Paragraph(f"{c_elec} / {tot}", st_tb), Paragraph(f"{p_elec:.1f}%", st_tb)],
    ], colWidths=[9.6 * cm, 4.5 * cm, 4.5 * cm])
    t_resumen.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), c_azul), ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#D5D8DC")), ("ALIGN", (1, 0), (-1, -1), "CENTER")]))

    elementos.append(KeepTogether([Paragraph("III. RESUMEN ESTADÍSTICO DE PATOLOGÍAS Y FALLAS", st_sec), HRFlowable(width="100%", thickness=1, color=c_oro, spaceBefore=3, spaceAfter=6), t_resumen]))

    observaciones = (sesion.get("observaciones_generales") or "").strip()
    if observaciones:
        elementos.extend([
            Spacer(1, 14),
            Paragraph("OBSERVACIONES GENERALES", st_sec),
            HRFlowable(width="100%", thickness=1, color=c_oro, spaceBefore=3, spaceAfter=6),
            Paragraph(observaciones.replace("\n", "<br/>"), st_valor),
        ])

    fotos_disponibles = [u for u in sesion["unidades"] if u.get("foto") and os.path.isfile(u.get("foto"))]
    if fotos_disponibles:
        elementos.extend([
            Spacer(1, 16),
            Paragraph("IV. REGISTRO FOTOGRÁFICO", st_sec),
            HRFlowable(width="100%", thickness=1, color=c_oro, spaceBefore=3, spaceAfter=10),
        ])
        st_pie_foto = ParagraphStyle("PieFoto", parent=styles["Normal"], fontName="Times-Bold", fontSize=8, textColor=c_azul, alignment=1)
        ANCHO_GALERIA = 5.6 * cm
        ALTO_GALERIA = 5.6 * cm
        celdas_galeria = []
        for u in fotos_disponibles:
            try:
                im = PILImage.open(u["foto"])
                w, h = im.size
                ancho = ANCHO_GALERIA
                alto = ancho * h / w
                if alto > ALTO_GALERIA:
                    alto = ALTO_GALERIA
                    ancho = alto * w / h
                img_flowable = Image(u["foto"], width=ancho, height=alto)
            except Exception:
                img_flowable = Paragraph("(no se pudo cargar la imagen)", st_tb)
            etiqueta = Paragraph(f"{u['grupo']} — {u['unidad']}", st_pie_foto)
            celdas_galeria.append([img_flowable, etiqueta])

        filas_galeria = []
        for i in range(0, len(celdas_galeria), 3):
            grupo_fila = celdas_galeria[i:i + 3]
            fila_img = [c[0] for c in grupo_fila] + [""] * (3 - len(grupo_fila))
            fila_txt = [c[1] for c in grupo_fila] + [""] * (3 - len(grupo_fila))
            filas_galeria.append(fila_img)
            filas_galeria.append(fila_txt)

        t_galeria = Table(filas_galeria, colWidths=[6.0 * cm, 6.0 * cm, 6.0 * cm])
        t_galeria.setStyle(TableStyle([
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        elementos.append(t_galeria)

    doc.build(elementos, onFirstPage=dibujar_fondo, onLaterPages=dibujar_fondo)
    return archivo_salida


def guardar_todo(sesion, carpeta):
    guardar_progreso(sesion, carpeta)
    ruta = generar_pdf(sesion, carpeta)
    return ruta
