import os
import re
import uuid
from flask import Flask, render_template, request, redirect, url_for, session, send_file

import logic

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "cambia-esta-clave-en-produccion")
app.config["MAX_CONTENT_LENGTH"] = 25 * 1024 * 1024  # 25 MB por solicitud

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
CARPETA = logic.carpeta_guardado(DATA_DIR)
FOTOS_DIR = os.path.join(DATA_DIR, "fotos")
os.makedirs(FOTOS_DIR, exist_ok=True)

EXTENSIONES_PERMITIDAS = {".jpg", ".jpeg", ".png", ".webp"}


def guardar_foto(archivo, prefijo):
    if not archivo or not archivo.filename:
        return None
    ext = os.path.splitext(archivo.filename)[1].lower()
    if ext not in EXTENSIONES_PERMITIDAS:
        ext = ".jpg"
    slug = re.sub(r"[^A-Za-z0-9_-]", "_", prefijo)[:60]
    nombre = f"{slug}_{uuid.uuid4().hex[:8]}{ext}"
    ruta = os.path.join(FOTOS_DIR, nombre)
    archivo.save(ruta)
    return ruta


def cargar_sesion_actual():
    urbanismo = session.get("urbanismo")
    if not urbanismo:
        return None
    return logic.cargar_progreso(urbanismo, CARPETA)


@app.route("/", methods=["GET", "POST"])
def welcome():
    if request.method == "POST":
        nombre = request.form.get("urbanismo", "").strip().upper()
        if not nombre:
            return render_template("welcome.html", error="Escribe el nombre del urbanismo.")
        session["urbanismo"] = nombre
        progreso = logic.cargar_progreso(nombre, CARPETA)
        if progreso:
            return redirect(url_for("cola"))
        return redirect(url_for("datos_generales"))
    return render_template("welcome.html")


@app.route("/datos_generales", methods=["GET", "POST"])
def datos_generales():
    if "urbanismo" not in session:
        return redirect(url_for("welcome"))

    if request.method == "POST":
        f = request.form
        tipo = f.get("tipo")
        plan = []
        try:
            if tipo == "Edificios":
                t = int(f.get("torres") or 0)
                p = int(f.get("pisos") or 0)
                a = int(f.get("aptos") or 0)
                if t <= 0 or p <= 0 or a <= 0:
                    raise ValueError
                for tt in range(1, t + 1):
                    for pp in range(p):
                        pref = "PB" if pp == 0 else str(pp)
                        for aa in range(1, a + 1):
                            plan.append({"grupo": f"Torre {tt}", "unidad_sugerida": f"{pref}-{'0' + str(aa) if aa < 10 else aa}"})
            else:
                c = int(f.get("calles") or 0)
                h = int(f.get("casas") or 0)
                if c <= 0 or h <= 0:
                    raise ValueError
                for cc in range(1, c + 1):
                    for hh in range(1, h + 1):
                        plan.append({"grupo": f"Calle {cc}", "unidad_sugerida": f"Casa {hh}"})
        except ValueError:
            return render_template("datos_generales.html", logic=logic, error="Revisa las cantidades numéricas.")

        sesion = {
            "urbanismo": session["urbanismo"],
            "fecha_inspeccion": f.get("fecha_inspeccion") or "",
            "ubicacion": f.get("ubicacion", ""),
            "parroquia": f.get("parroquia"),
            "tenencia": f.get("tenencia"),
            "riesgos": f.get("riesgos") or "Ninguno",
            "aceras": f.get("aceras"),
            "aguas_blancas": f.get("aguas_blancas"),
            "aguas_servidas": f.get("aguas_servidas"),
            "saneamiento": f.get("saneamiento"),
            "electricidad": f.get("electricidad"),
            "tipo": tipo,
            "plan_unidades": plan,
            "unidades": [],
        }
        logic.guardar_todo(sesion, CARPETA)
        return redirect(url_for("cola"))

    return render_template("datos_generales.html", logic=logic, error=None)


@app.route("/cola")
def cola():
    sesion = cargar_sesion_actual()
    if not sesion:
        return redirect(url_for("welcome"))

    plan = sesion.get("plan_unidades", [])
    hechas = len(sesion.get("unidades", []))

    if hechas >= len(plan):
        ruta = logic.guardar_todo(sesion, CARPETA)
        return render_template("finalizado.html", nombre_archivo=os.path.basename(ruta))

    siguiente = plan[hechas]
    return render_template("cola.html", siguiente=siguiente, hechas=hechas, total=len(plan))


@app.route("/detalle", methods=["GET", "POST"])
def detalle():
    sesion = cargar_sesion_actual()
    if not sesion:
        return redirect(url_for("welcome"))

    plan = sesion["plan_unidades"]
    hechas = len(sesion["unidades"])
    if hechas >= len(plan):
        return redirect(url_for("cola"))
    item = plan[hechas]

    if request.method == "POST":
        f = request.form
        ruta_foto = guardar_foto(request.files.get("foto"), f"{sesion['urbanismo']}_{item['grupo']}_{item['unidad_sugerida']}")
        unidad = {
            "grupo": item["grupo"],
            "unidad": f.get("unidad") or item["unidad_sugerida"],
            "estatus": f.get("estatus"),
            "propietario": (f.get("propietario") or "Sin Identificar").title(),
            "telefono": f.get("telefono", "").strip(),
            "friso": f.get("friso"),
            "techo": f.get("techo"),
            "banos": f.get("banos") or "Ninguno",
            "electricidad_unidad": f.get("electricidad_unidad"),
            "patologia": f.get("patologia") or "Ninguna",
            "foto": ruta_foto,
        }
        sesion["unidades"].append(unidad)
        logic.guardar_todo(sesion, CARPETA)
        return redirect(url_for("cola"))

    opc_techo = logic.OPC_TECHO_CASAS if sesion["tipo"] == "Casas" else logic.OPC_TECHO_EDIFICIOS
    return render_template("detalle.html", item=item, logic=logic, opc_techo=opc_techo)


@app.route("/lote", methods=["GET", "POST"])
def lote():
    sesion = cargar_sesion_actual()
    if not sesion:
        return redirect(url_for("welcome"))

    plan = sesion["plan_unidades"]
    hechas = len(sesion["unidades"])
    pendientes = plan[hechas:]
    opc_techo = logic.OPC_TECHO_CASAS if sesion["tipo"] == "Casas" else logic.OPC_TECHO_EDIFICIOS

    if request.method == "POST":
        f = request.form
        try:
            cantidad = int(f.get("cantidad") or 0)
        except ValueError:
            cantidad = 0
        if cantidad <= 0 or cantidad > len(pendientes):
            return render_template("lote.html", pendientes=pendientes, logic=logic, opc_techo=opc_techo,
                                    error=f"Escribe un número entre 1 y {len(pendientes)}.")
        seleccionados = pendientes[:cantidad]
        return render_template(
            "lote_propietarios.html",
            seleccionados=seleccionados,
            logic=logic,
            friso=f.get("friso"), techo=f.get("techo"), banos=f.get("banos"),
            electricidad=f.get("electricidad"), patologia=f.get("patologia") or "Ninguna",
        )

    return render_template("lote.html", pendientes=pendientes, logic=logic, opc_techo=opc_techo, error=None)


@app.route("/lote_guardar", methods=["POST"])
def lote_guardar():
    sesion = cargar_sesion_actual()
    if not sesion:
        return redirect(url_for("welcome"))

    f = request.form
    friso = f.get("friso")
    techo = f.get("techo")
    banos = f.get("banos")
    electricidad = f.get("electricidad")
    patologia = f.get("patologia") or "Ninguna"

    grupos = f.getlist("grupo")
    unidades_sug = f.getlist("unidad_sugerida")
    propietarios = f.getlist("propietario")
    telefonos = f.getlist("telefono")
    estatuses = f.getlist("estatus")
    fotos = request.files.getlist("foto")

    for i in range(len(grupos)):
        foto_archivo = fotos[i] if i < len(fotos) else None
        ruta_foto = guardar_foto(foto_archivo, f"{sesion['urbanismo']}_{grupos[i]}_{unidades_sug[i]}")
        sesion["unidades"].append({
            "grupo": grupos[i],
            "unidad": unidades_sug[i],
            "estatus": estatuses[i],
            "propietario": (propietarios[i].strip() or "Sin Identificar").title(),
            "telefono": telefonos[i].strip(),
            "friso": friso,
            "techo": techo,
            "banos": banos,
            "electricidad_unidad": electricidad,
            "patologia": patologia,
            "foto": ruta_foto,
        })

    logic.guardar_todo(sesion, CARPETA)
    return redirect(url_for("cola"))


@app.route("/descargar/<nombre_archivo>")
def descargar(nombre_archivo):
    ruta = os.path.join(CARPETA, nombre_archivo)
    return send_file(ruta, as_attachment=True)


@app.route("/nuevo")
def nuevo():
    session.pop("urbanismo", None)
    return redirect(url_for("welcome"))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)
