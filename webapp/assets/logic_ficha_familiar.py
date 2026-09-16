# -*- coding: utf-8 -*-
"""
logic_ficha_familiar.py
------------------------
Genera la "Ficha Familiar de Hábitat y Vivienda" (.docx) ya llena con los
datos capturados en el formulario web. Mismo patrón que logic_informe.py:
una plantilla con tokens {{...}} que se reemplazan por texto.

No lleva fotos ni menús desplegables — todos los campos son de texto libre,
tal como el formato original en papel.

Requiere: ninguna librería externa además de la librería estándar.
"""

import os
import xml.sax.saxutils as saxutils
import zipfile

TEMPLATE_PATH = os.path.join(os.path.dirname(__file__), "assets", "ficha_familiar_template.docx")

# Columnas del núcleo familiar, en el mismo orden que las columnas de la
# tabla (después de la columna N°), y hasta 5 personas (5 filas impresas).
COLUMNAS_NUCLEO = [
    "NOMBRE", "CI", "FECHA", "EDAD", "PARENTESCO",
    "OCUPACION", "ESCOLARIDAD", "DISCAPACIDAD", "OBSERVACION",
]


def _esc(valor):
    if valor is None:
        valor = ""
    return saxutils.escape(str(valor))


def generar_ficha_familiar_docx(data, docx_path):
    """
    data: dict con las llaves del jefe(a) familiar:
        nombres, apellidos, cedula, fecha_nacimiento, telefono, correo,
        codigo, serial, direccion, estado, municipio, parroquia,
        grado_estudio, ocupacion_jefe, descripcion_caso

        y "nucleo": lista de hasta 5 dicts, cada uno con las llaves:
        nombre, ci, fecha, edad, parentesco, ocupacion, escolaridad,
        discapacidad, observacion
        (las filas que falten o vengan de más se ignoran; sobran filas en
        blanco en la ficha si el núcleo tiene menos de 5 personas)
    """
    if not os.path.exists(TEMPLATE_PATH):
        raise FileNotFoundError(
            f"No se encontró la plantilla en {TEMPLATE_PATH}. "
            "Verifica que assets/ficha_familiar_template.docx esté en el repo."
        )

    reemplazos = {
        "{{NOMBRES}}": _esc(data.get("nombres", "")),
        "{{APELLIDOS}}": _esc(data.get("apellidos", "")),
        "{{CEDULA}}": _esc(data.get("cedula", "")),
        "{{FECHA_NACIMIENTO}}": _esc(data.get("fecha_nacimiento", "")),
        "{{TELEFONO}}": _esc(data.get("telefono", "")),
        "{{CORREO}}": _esc(data.get("correo", "")),
        "{{CODIGO}}": _esc(data.get("codigo", "")),
        "{{SERIAL}}": _esc(data.get("serial", "")),
        "{{DIRECCION}}": _esc(data.get("direccion", "")),
        "{{ESTADO}}": _esc(data.get("estado", "")),
        "{{MUNICIPIO}}": _esc(data.get("municipio", "")),
        "{{PARROQUIA}}": _esc(data.get("parroquia", "")),
        "{{GRADO_ESTUDIO}}": _esc(data.get("grado_estudio", "")),
        "{{OCUPACION_JEFE}}": _esc(data.get("ocupacion_jefe", "")),
        "{{DESCRIPCION_CASO}}": _esc(data.get("descripcion_caso", "")),
    }

    nucleo = data.get("nucleo", [])
    for fila in range(1, 6):
        persona = nucleo[fila - 1] if fila - 1 < len(nucleo) else {}
        for col in COLUMNAS_NUCLEO:
            clave = {
                "NOMBRE": "nombre", "CI": "ci", "FECHA": "fecha", "EDAD": "edad",
                "PARENTESCO": "parentesco", "OCUPACION": "ocupacion",
                "ESCOLARIDAD": "escolaridad", "DISCAPACIDAD": "discapacidad",
                "OBSERVACION": "observacion",
            }[col]
            reemplazos[f"{{{{N{fila}_{col}}}}}"] = _esc(persona.get(clave, ""))

    with zipfile.ZipFile(TEMPLATE_PATH, "r") as zin:
        document_xml = zin.read("word/document.xml").decode("utf-8")
        for token, valor in reemplazos.items():
            document_xml = document_xml.replace(token, valor)

        os.makedirs(os.path.dirname(docx_path) or ".", exist_ok=True)
        with zipfile.ZipFile(docx_path, "w", zipfile.ZIP_DEFLATED) as zout:
            for item in zin.infolist():
                if item.filename == "word/document.xml":
                    zout.writestr(item, document_xml.encode("utf-8"))
                else:
                    zout.writestr(item, zin.read(item.filename))

    return docx_path


if __name__ == "__main__":
    data_prueba = {
        "nombres": "María Fernanda",
        "apellidos": "Rodríguez Salazar",
        "cedula": "18.234.567",
        "fecha_nacimiento": "12/04/1985",
        "telefono": "0414-1234567",
        "correo": "mfrodriguez@gmail.com",
        "codigo": "A-045",
        "serial": "778812",
        "direccion": "Sector Los Pinos, calle principal, casa N°12, Higuerote",
        "estado": "Miranda",
        "municipio": "Brión",
        "parroquia": "Higuerote",
        "grado_estudio": "Bachiller",
        "ocupacion_jefe": "Ama de casa",
        "descripcion_caso": "Familia en situación de riesgo por vivienda deteriorada.",
        "nucleo": [
            {"nombre": "María Fernanda Rodríguez", "ci": "18.234.567", "fecha": "12/04/1985",
             "edad": "41", "parentesco": "Jefe de familia", "ocupacion": "Ama de casa",
             "escolaridad": "-", "discapacidad": "Ninguna", "observacion": "-"},
            {"nombre": "Carlos Eduardo Pérez", "ci": "18.234.999", "fecha": "03/09/1983",
             "edad": "43", "parentesco": "Cónyuge", "ocupacion": "Obrero",
             "escolaridad": "-", "discapacidad": "Ninguna", "observacion": "-"},
            {"nombre": "Ana Sofía Pérez Rodríguez", "ci": "-", "fecha": "20/01/2015",
             "edad": "11", "parentesco": "Hija", "ocupacion": "Estudiante",
             "escolaridad": "6to grado", "discapacidad": "Ninguna", "observacion": "-"},
        ],
    }
    generar_ficha_familiar_docx(data_prueba, "ficha_familiar_prueba.docx")
    print("Generado: ficha_familiar_prueba.docx")
