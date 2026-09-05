import json
import os
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.graphics.shapes import Circle, Drawing, Path, Rect, String
from reportlab.platypus import (
    HRFlowable, KeepTogether, Paragraph, SimpleDocTemplate,
    Spacer, Table, TableStyle,
)

# ============================================================
# OPCIONES
# ============================================================
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

# ============================================================
# UBICACIÓN DE GUARDADO
# ============================================================
CANDIDATOS_DESCARGA = [
    "/storage/emulated/0/Download",
    "/storage/emulated/0/Descargas",
    "/sdcard/Download",
    os.path.expanduser("~/storage/downloads"),
]


def carpeta_guardado(preferida=None):
    candidatos = ([preferida] if preferida else []) + CANDIDATOS_DESCARGA
    for ruta in candidatos:
        if ruta and os.path.isdir(ruta) and os.access(ruta, os.W_OK):
            return ruta
    return os.getcwd()


def ruta_progreso(nombre_urbanismo, carpeta):
    slug = nombre_urbanismo.replace(" ", "_")
    return os.path.join(carpeta, f".progreso_{slug}.json")


def ruta_pdf(nombre_urbanismo, carpeta):
    slug = nombre_urbanismo.replace(" ", "_")
    fecha_str = datetime.now().strftime("%Y%m%d")
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


# ============================================================
# GENERADOR PDF (idéntico al original)
# ============================================================
def crear_sello_vectorial():
    d = Drawing(70, 70)
    d.add(Circle(35, 35, 33, fillColor=colors.HexColor("#16294A"), strokeColor=colors.HexColor("#FFD700"), strokeWidth=2))
    p = Path(fillColor=None, strokeColor=colors.HexColor("#FFD700"), strokeWidth=2)
    p.moveTo(35, 52); p.lineTo(50, 40); p.lineTo(45, 40); p.lineTo(45, 25); p.lineTo(25, 25); p.lineTo(25, 40); p.lineTo(20, 40); p.closePath()
    d.add(Rect(31, 25, 8, 9, fillColor=colors.HexColor("#FFD700"), strokeColor=None))
    d.add(String(35, 56, "ALCALDÍA DE BRIÓN", textAnchor="middle", fontSize=3.8, fillColor=colors.white, fontName="Helvetica-Bold"))
    d.add(String(35, 17, "HÁBITAT Y VIVIENDA", textAnchor="middle", fontSize=3.8, fillColor=colors.HexColor("#FFD700"), fontName="Helvetica-Bold"))
    d.add(String(35, 11, "ESTADO MIRANDA", textAnchor="middle", fontSize=3.2, fillColor=colors.HexColor("#E5E7E9"), fontName="Helvetica"))
    return d


def generar_pdf(sesion, carpeta):
    archivo_salida = ruta_pdf(sesion["urbanismo"], carpeta)
    doc = SimpleDocTemplate(
        archivo_salida, pagesize=letter,
        leftMargin=1.2 * cm, rightMargin=1.2 * cm,
        topMargin=1.2 * cm, bottomMargin=1.2 * cm,
    )

    elementos = []
    styles = getSampleStyleSheet()

    c_azul = colors.HexColor("#16294A")
    c_oro = colors.HexColor("#D4AC0D")
    c_rojo = colors.HexColor("#C0392B")
    c_verde = colors.HexColor("#27AE60")

    st_inst = ParagraphStyle("Inst", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=9, leading=11, textColor=c_oro)
    st_tit = ParagraphStyle("Tit", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=13, leading=15, textColor=colors.white)
    st_sub = ParagraphStyle("Sub", parent=styles["Normal"], fontName="Helvetica", fontSize=8, textColor=colors.HexColor("#D5D8DC"))
    st_sec = ParagraphStyle("Sec", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=10, textColor=c_azul)
    st_etiqueta = ParagraphStyle("Etiq", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=8, textColor=colors.HexColor("#5B5346"))
    st_valor = ParagraphStyle("Val", parent=styles["Normal"], fontName="Helvetica", fontSize=8, textColor=colors.black)

    st_th = ParagraphStyle("TH", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=7, leading=8.5, textColor=c_oro, alignment=1)
    st_tb = ParagraphStyle("TB", parent=styles["Normal"], fontName="Helvetica", fontSize=7, leading=8.5)
    st_tb_alerta = ParagraphStyle("TBA", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=7, leading=8.5, textColor=c_rojo)
    st_tb_ok = ParagraphStyle("TBO", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=7, leading=8.5, textColor=c_verde)
    st_prop = ParagraphStyle("Prop", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=7, leading=8)

    t_header = Table([[crear_sello_vectorial(), [Paragraph("ALCALDÍA DEL MUNICIPIO AUTÓNOMO DE BRIÓN", st_inst), Spacer(1, 2), Paragraph("FICHA DE INSPECCIÓN Y ESTATUS FÍSICO DE URBANISMO", st_tit), Spacer(1, 2), Paragraph("DIRECCIÓN DE HÁBITAT Y VIVIENDA · ESTADO BOLIVARIANO DE MIRANDA", st_sub)]]], colWidths=[2.5 * cm, 16.1 * cm])
    t_header.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), c_azul), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("ALIGN", (0, 0), (0, 0), "CENTER"), ("PADDING", (0, 0), (-1, -1), 8)]))
    elementos.extend([t_header, Spacer(1, 14), Paragraph("I. DATOS GENERALES Y DIAGNÓSTICO DE SERVICIOS", st_sec), HRFlowable(width="100%", thickness=1, color=c_oro, spaceBefore=3, spaceAfter=6)])

    f_dato = lambda l, v: [Paragraph(l, st_etiqueta), Paragraph(str(v), st_valor)]
    t_gen = Table([
        f_dato("FECHA INSPECCIÓN:", sesion.get('fecha_inspeccion', "")), f_dato("URBANISMO:", sesion['urbanismo']), f_dato("UBICACIÓN:", sesion['ubicacion']),
        f_dato("PARROQUIA:", sesion['parroquia'] + ", Brión"), f_dato("TENENCIA TIERRA:", sesion['tenencia']), f_dato("RIESGOS:", sesion['riesgos']),
        f_dato("ACERAS/BROCALES:", sesion['aceras']), f_dato("AGUAS BLANCAS:", sesion['aguas_blancas']), f_dato("AGUAS SERVIDAS:", sesion['aguas_servidas']),
        f_dato("SANEAMIENTO:", sesion['saneamiento']), f_dato("RED ELÉCTRICA:", sesion['electricidad'])
    ], colWidths=[4.5 * cm, 14.1 * cm])
    t_gen.setStyle(TableStyle([("LINEBELOW", (0, 0), (-1, -1), 0.5, colors.HexColor("#E5E7E9")), ("PADDING", (0, 0), (-1, -1), 3)]))
    elementos.extend([t_gen, Spacer(1, 14), Paragraph("II. REGISTRO FÍSICO DE UNIDADES HABITACIONALES", st_sec), HRFlowable(width="100%", thickness=1, color=c_oro, spaceBefore=3, spaceAfter=6)])

    filas_tabla = [[Paragraph(h, st_th) for h in ["Grupo", "Unidad", "Propietario / Estatus", "Friso", "Techo / Cubierta", "Baños", "Electricidad", "Patología"]]]
    estilos_tabla = [("BACKGROUND", (0, 0), (-1, 0), c_azul), ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#D5D8DC")), ("VALIGN", (0, 0), (-1, -1), "MIDDLE")]

    grupo_anterior = None
    for i, u in enumerate(sesion["unidades"], start=1):
        st_fri = st_tb_alerta if u.get("friso") in ["Pendiente", "Deteriorado"] else st_tb_ok
        st_tec = st_tb_alerta if any(k in u.get("techo", "").lower() for k in ["humedad", "filtracion", "filtraciones", "deteriorada", "sin cubierta"]) else st_tb_ok
        st_ban = st_tb_alerta if any(k in u.get("banos", "") for k in ["Sin", "proceso", "Fuera", "Otro"]) else st_tb_ok
        st_elec = st_tb_alerta if u.get("electricidad_unidad") == "Clandestina" else st_tb_ok
        st_pat = st_tb_ok if u.get("patologia", "Ninguna").strip().lower() in SIN_PATOLOGIA else st_tb_alerta

        prop_str = f"{u.get('propietario', 'S/I')}<br/><font color='#5B5346' size='6'><i>({u.get('estatus', 'Habitado')})</i></font>"

        if grupo_anterior and u["grupo"] != grupo_anterior:
            estilos_tabla.append(("LINEABOVE", (0, i), (-1, i), 1.5, c_azul))
        grupo_anterior = u["grupo"]

        filas_tabla.append([
            Paragraph(u["grupo"], st_tb), Paragraph(u["unidad"], st_tb), Paragraph(prop_str, st_prop),
            Paragraph(u.get("friso", "-"), st_fri), Paragraph(u.get("techo", "-"), st_tec), Paragraph(u.get("banos", "-"), st_ban),
            Paragraph(u.get("electricidad_unidad", "Reglamentaria"), st_elec), Paragraph(u.get("patologia", "Ninguna"), st_pat),
        ])

    t_unidades = Table(filas_tabla, colWidths=[2.0 * cm, 1.8 * cm, 3.0 * cm, 1.8 * cm, 2.8 * cm, 3.0 * cm, 1.8 * cm, 2.4 * cm])
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
    doc.build(elementos)
    return archivo_salida


def guardar_todo(sesion, carpeta):
    guardar_progreso(sesion, carpeta)
    ruta = generar_pdf(sesion, carpeta)
    return ruta
