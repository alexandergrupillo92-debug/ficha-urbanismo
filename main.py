"""
Ficha de Inspección de Urbanismos - App Android (Kivy)
Convierte el flujo de consola original a pantallas táctiles.
Toda la lógica de PDF/estadísticas vive en logic.py sin cambios.
"""
import os

from kivy.app import App
from kivy.core.window import Window
from kivy.uix.screenmanager import Screen, ScreenManager, SlideTransition
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.spinner import Spinner
from kivy.uix.button import Button
from kivy.uix.popup import Popup
from kivy.metrics import dp

import logic

try:
    from android.permissions import request_permissions, Permission
    request_permissions([Permission.WRITE_EXTERNAL_STORAGE, Permission.READ_EXTERNAL_STORAGE])
except Exception:
    pass


def carpeta_actual():
    preferida = None
    try:
        app = App.get_running_app()
        preferida = app.user_data_dir
    except Exception:
        pass
    return logic.carpeta_guardado(preferida)


def mostrar_aviso(titulo, mensaje):
    Popup(title=titulo, content=Label(text=mensaje), size_hint=(0.85, 0.4)).open()


class FormRow(BoxLayout):
    """Fila de formulario: etiqueta + widget de entrada."""
    def __init__(self, etiqueta, widget, **kwargs):
        super().__init__(orientation="vertical", size_hint_y=None, height=dp(72), spacing=dp(2), **kwargs)
        self.add_widget(Label(text=etiqueta, size_hint_y=None, height=dp(22), halign="left", valign="middle", font_size="13sp"))
        self.widget = widget
        self.add_widget(widget)

    @property
    def value(self):
        if isinstance(self.widget, Spinner):
            return self.widget.text
        return self.widget.text.strip()


class WelcomeScreen(Screen):
    def build(self):
        self.clear_widgets()
        root = BoxLayout(orientation="vertical", padding=dp(20), spacing=dp(14))
        root.add_widget(Label(text="Ficha de Inspección\nde Urbanismo", font_size="22sp", size_hint_y=None, height=dp(80), halign="center"))
        self.input_urb = TextInput(hint_text="Nombre del Urbanismo", multiline=False, size_hint_y=None, height=dp(48))
        root.add_widget(self.input_urb)
        btn = Button(text="Comenzar / Continuar", size_hint_y=None, height=dp(52))
        btn.bind(on_release=self.continuar)
        root.add_widget(btn)
        root.add_widget(Label())
        self.add_widget(root)

    def on_pre_enter(self):
        self.build()

    def continuar(self, *_):
        nombre = self.input_urb.text.strip().upper()
        if not nombre:
            mostrar_aviso("Falta información", "Escribe el nombre del urbanismo.")
            return
        app = App.get_running_app()
        carpeta = carpeta_actual()
        progreso = logic.cargar_progreso(nombre, carpeta)
        if progreso:
            app.sesion = progreso
            app.carpeta = carpeta
            self.manager.current = "cola"
        else:
            app.sesion = {"urbanismo": nombre}
            app.carpeta = carpeta
            self.manager.get_screen("datos_generales").preparar()
            self.manager.current = "datos_generales"


class DatosGeneralesScreen(Screen):
    def preparar(self):
        self.clear_widgets()
        scroll = ScrollView()
        grid = GridLayout(cols=1, spacing=dp(8), padding=dp(16), size_hint_y=None)
        grid.bind(minimum_height=grid.setter("height"))

        self.rows = {}

        def add_text(clave, etiqueta, hint=""):
            ti = TextInput(hint_text=hint, multiline=False, size_hint_y=None, height=dp(44))
            row = FormRow(etiqueta, ti)
            self.rows[clave] = row
            grid.add_widget(row)

        def add_spinner(clave, etiqueta, opciones):
            sp = Spinner(text=opciones[0], values=opciones, size_hint_y=None, height=dp(44))
            row = FormRow(etiqueta, sp)
            self.rows[clave] = row
            grid.add_widget(row)

        add_text("fecha_inspeccion", "Fecha de inspección")
        add_text("ubicacion", "Ubicación / Sector")
        add_spinner("parroquia", "Parroquia", logic.OPC_PARROQUIA)
        add_spinner("tenencia", "Tenencia de la tierra", logic.OPC_TENENCIA)
        add_text("riesgos", "Riesgos geológicos (Ninguno si no aplica)")
        add_spinner("aceras", "Aceras y brocales", logic.OPC_ACERAS)
        add_spinner("aguas_blancas", "Aguas blancas", logic.OPC_AGUAS_BLANCAS)
        add_spinner("aguas_servidas", "Aguas servidas", logic.OPC_AGUAS_SERVIDAS)
        add_spinner("saneamiento", "Sistema de saneamiento", logic.OPC_SANEAMIENTO)
        add_spinner("electricidad", "Sistema eléctrico general", logic.OPC_ELECTRICIDAD)
        add_spinner("tipo", "Tipología del urbanismo", logic.OPC_TIPO)

        add_text("torres", "Torres (solo si Edificios)")
        add_text("pisos", "Pisos incl. PB (solo si Edificios)")
        add_text("aptos", "Aptos por nivel (solo si Edificios)")
        add_text("calles", "Calles (solo si Casas)")
        add_text("casas", "Casas por calle (solo si Casas)")

        btn = Button(text="Generar plan y comenzar registro", size_hint_y=None, height=dp(52))
        btn.bind(on_release=self.generar_plan)
        grid.add_widget(btn)

        scroll.add_widget(grid)
        self.add_widget(scroll)

    def generar_plan(self, *_):
        r = self.rows
        try:
            tipo = r["tipo"].value
            plan = []
            if tipo == "Edificios":
                t = int(r["torres"].value or 0)
                p = int(r["pisos"].value or 0)
                a = int(r["aptos"].value or 0)
                if t <= 0 or p <= 0 or a <= 0:
                    raise ValueError
                for tt in range(1, t + 1):
                    for pp in range(p):
                        pref = "PB" if pp == 0 else str(pp)
                        for aa in range(1, a + 1):
                            plan.append({"grupo": f"Torre {tt}", "unidad_sugerida": f"{pref}-{'0' + str(aa) if aa < 10 else aa}"})
            else:
                c = int(r["calles"].value or 0)
                h = int(r["casas"].value or 0)
                if c <= 0 or h <= 0:
                    raise ValueError
                for cc in range(1, c + 1):
                    for hh in range(1, h + 1):
                        plan.append({"grupo": f"Calle {cc}", "unidad_sugerida": f"Casa {hh}"})
        except ValueError:
            mostrar_aviso("Datos incompletos", "Revisa las cantidades numéricas de torres/pisos/aptos o calles/casas.")
            return

        app = App.get_running_app()
        app.sesion.update({
            "fecha_inspeccion": r["fecha_inspeccion"].value or "",
            "ubicacion": r["ubicacion"].value,
            "parroquia": r["parroquia"].value,
            "tenencia": r["tenencia"].value,
            "riesgos": r["riesgos"].value or "Ninguno",
            "aceras": r["aceras"].value,
            "aguas_blancas": r["aguas_blancas"].value,
            "aguas_servidas": r["aguas_servidas"].value,
            "saneamiento": r["saneamiento"].value,
            "electricidad": r["electricidad"].value,
            "tipo": tipo,
            "plan_unidades": plan,
            "unidades": [],
        })
        logic.guardar_todo(app.sesion, app.carpeta)
        self.manager.current = "cola"


class ColaScreen(Screen):
    def on_pre_enter(self):
        self.clear_widgets()
        app = App.get_running_app()
        plan = app.sesion.get("plan_unidades", [])
        hechas = len(app.sesion.get("unidades", []))
        root = BoxLayout(orientation="vertical", padding=dp(20), spacing=dp(14))

        if hechas >= len(plan):
            root.add_widget(Label(text="¡Levantamiento completo!", font_size="20sp"))
            ruta = logic.guardar_todo(app.sesion, app.carpeta)
            root.add_widget(Label(text=f"PDF guardado en:\n{ruta}", font_size="13sp"))
            btn_fin = Button(text="Volver al inicio", size_hint_y=None, height=dp(50))
            btn_fin.bind(on_release=lambda *_: setattr(self.manager, "current", "welcome"))
            root.add_widget(btn_fin)
            self.add_widget(root)
            return

        siguiente = plan[hechas]
        root.add_widget(Label(text=f"Progreso: {hechas} / {len(plan)} unidades", font_size="16sp", size_hint_y=None, height=dp(30)))
        root.add_widget(Label(text=f"Siguiente:\n{siguiente['grupo']} - {siguiente['unidad_sugerida']}", font_size="18sp"))

        b1 = Button(text="Inspección detallada (1 unidad)", size_hint_y=None, height=dp(52))
        b1.bind(on_release=lambda *_: self.ir_detalle())
        b2 = Button(text="Carga rápida por lote", size_hint_y=None, height=dp(52))
        b2.bind(on_release=lambda *_: self.ir_lote())
        b3 = Button(text="Guardar y salir", size_hint_y=None, height=dp(52))
        b3.bind(on_release=lambda *_: self.guardar_y_salir())

        root.add_widget(b1)
        root.add_widget(b2)
        root.add_widget(b3)
        self.add_widget(root)

    def ir_detalle(self):
        self.manager.get_screen("detalle").preparar()
        self.manager.current = "detalle"

    def ir_lote(self):
        self.manager.get_screen("lote").preparar()
        self.manager.current = "lote"

    def guardar_y_salir(self):
        app = App.get_running_app()
        logic.guardar_todo(app.sesion, app.carpeta)
        self.manager.current = "welcome"


class DetalleUnidadScreen(Screen):
    def preparar(self):
        self.clear_widgets()
        app = App.get_running_app()
        plan = app.sesion["plan_unidades"]
        hechas = len(app.sesion["unidades"])
        item = plan[hechas]
        tipo = app.sesion["tipo"]

        scroll = ScrollView()
        grid = GridLayout(cols=1, spacing=dp(8), padding=dp(16), size_hint_y=None)
        grid.bind(minimum_height=grid.setter("height"))

        grid.add_widget(Label(text=f"{item['grupo']} — sugerido: {item['unidad_sugerida']}", size_hint_y=None, height=dp(30), font_size="15sp"))

        self.rows = {}

        def add_text(clave, etiqueta, defecto=""):
            ti = TextInput(text=defecto, multiline=False, size_hint_y=None, height=dp(44))
            row = FormRow(etiqueta, ti)
            self.rows[clave] = row
            grid.add_widget(row)

        def add_spinner(clave, etiqueta, opciones):
            sp = Spinner(text=opciones[0], values=opciones, size_hint_y=None, height=dp(44))
            row = FormRow(etiqueta, sp)
            self.rows[clave] = row
            grid.add_widget(row)

        add_text("unidad", "Identificador de unidad", item["unidad_sugerida"])
        add_spinner("estatus", "Estatus de ocupación", logic.OPC_ESTATUS)
        add_text("propietario", "Nombre del propietario", "Sin Identificar")
        add_spinner("friso", "Friso", logic.OPC_FRISO)
        add_spinner("techo", "Techo / Cubierta", logic.OPC_TECHO_CASAS if tipo == "Casas" else logic.OPC_TECHO_EDIFICIOS)
        add_text("banos", "Baños (cantidad y condición)", "1, Completo")
        add_spinner("electricidad_unidad", "Electricidad en la vivienda", logic.OPC_ELECTRICIDAD)
        add_text("patologia", "Patología (Ninguna, Grietas, Fisuras, Humedad, Filtraciones)", "Ninguna")

        btn = Button(text="Guardar unidad", size_hint_y=None, height=dp(52))
        btn.bind(on_release=lambda *_: self.guardar(item))
        grid.add_widget(btn)

        scroll.add_widget(grid)
        self.add_widget(scroll)

    def guardar(self, item):
        r = self.rows
        app = App.get_running_app()
        unidad = {
            "grupo": item["grupo"],
            "unidad": r["unidad"].value or item["unidad_sugerida"],
            "estatus": r["estatus"].value,
            "propietario": (r["propietario"].value or "Sin Identificar").title(),
            "friso": r["friso"].value,
            "techo": r["techo"].value,
            "banos": r["banos"].value or "Ninguno",
            "electricidad_unidad": r["electricidad_unidad"].value,
            "patologia": r["patologia"].value or "Ninguna",
        }
        app.sesion["unidades"].append(unidad)
        logic.guardar_todo(app.sesion, app.carpeta)
        self.manager.current = "cola"


class LoteScreen(Screen):
    def preparar(self):
        self.clear_widgets()
        app = App.get_running_app()
        self.pendientes = app.sesion["plan_unidades"][len(app.sesion["unidades"]):]
        tipo = app.sesion["tipo"]

        scroll = ScrollView()
        grid = GridLayout(cols=1, spacing=dp(8), padding=dp(16), size_hint_y=None)
        grid.bind(minimum_height=grid.setter("height"))

        grid.add_widget(Label(
            text=f"Lote desde: {self.pendientes[0]['grupo']} - {self.pendientes[0]['unidad_sugerida']}\n"
                 f"Máximo disponible: {len(self.pendientes)}",
            size_hint_y=None, height=dp(50), font_size="14sp"))

        self.cantidad_input = TextInput(hint_text=f"Cantidad de unidades (máx {len(self.pendientes)})",
                                         multiline=False, input_filter="int", size_hint_y=None, height=dp(44))
        grid.add_widget(self.cantidad_input)

        self.rows = {}

        def add_spinner(clave, etiqueta, opciones):
            sp = Spinner(text=opciones[0], values=opciones, size_hint_y=None, height=dp(44))
            row = FormRow(etiqueta, sp)
            self.rows[clave] = row
            grid.add_widget(row)

        add_spinner("friso", "Friso común", logic.OPC_FRISO)
        add_spinner("techo", "Techo / Cubierta común", logic.OPC_TECHO_CASAS if tipo == "Casas" else logic.OPC_TECHO_EDIFICIOS)
        add_spinner("banos_cond", "Condición de baños común", logic.OPC_BANOS_COND)
        add_spinner("electricidad", "Electricidad común", logic.OPC_ELECTRICIDAD)

        self.patologia_input = TextInput(text="Ninguna", multiline=False, size_hint_y=None, height=dp(44))
        grid.add_widget(FormRow("Patología común (Ninguna, Grietas, Fisuras, Humedad, Filtraciones)", self.patologia_input))

        btn = Button(text="Continuar: registrar propietarios", size_hint_y=None, height=dp(52))
        btn.bind(on_release=self.pedir_propietarios)
        grid.add_widget(btn)

        scroll.add_widget(grid)
        self.add_widget(scroll)

    def pedir_propietarios(self, *_):
        try:
            cant = int(self.cantidad_input.text or 0)
        except ValueError:
            cant = 0
        if cant <= 0 or cant > len(self.pendientes):
            mostrar_aviso("Cantidad inválida", f"Escribe un número entre 1 y {len(self.pendientes)}.")
            return
        self.cantidad = cant
        self.clear_widgets()

        scroll = ScrollView()
        grid = GridLayout(cols=1, spacing=dp(8), padding=dp(16), size_hint_y=None)
        grid.bind(minimum_height=grid.setter("height"))
        grid.add_widget(Label(text="Propietario y estatus de cada unidad:", size_hint_y=None, height=dp(30)))

        self.filas_propietarios = []
        for i in range(cant):
            item = self.pendientes[i]
            grid.add_widget(Label(text=f"{item['grupo']} - {item['unidad_sugerida']}", size_hint_y=None, height=dp(26), font_size="13sp"))
            ti = TextInput(hint_text="Propietario (opcional)", multiline=False, size_hint_y=None, height=dp(42))
            sp = Spinner(text=logic.OPC_ESTATUS[0], values=logic.OPC_ESTATUS, size_hint_y=None, height=dp(42))
            grid.add_widget(ti)
            grid.add_widget(sp)
            self.filas_propietarios.append((item, ti, sp))

        btn = Button(text=f"Guardar {cant} unidades", size_hint_y=None, height=dp(52))
        btn.bind(on_release=self.guardar_lote)
        grid.add_widget(btn)

        scroll.add_widget(grid)
        self.add_widget(scroll)

    def guardar_lote(self, *_):
        app = App.get_running_app()
        r = self.rows
        friso = r["friso"].value
        techo = r["techo"].value
        banos = r["banos_cond"].value
        electricidad = r["electricidad"].value
        patologia = self.patologia_input.text.strip() or "Ninguna"

        for item, ti, sp in self.filas_propietarios:
            app.sesion["unidades"].append({
                "grupo": item["grupo"],
                "unidad": item["unidad_sugerida"],
                "estatus": sp.text,
                "propietario": (ti.text.strip() or "Sin Identificar").title(),
                "friso": friso,
                "techo": techo,
                "banos": banos,
                "electricidad_unidad": electricidad,
                "patologia": patologia,
            })
        logic.guardar_todo(app.sesion, app.carpeta)
        self.manager.current = "cola"


class FichaApp(App):
    def build(self):
        Window.clearcolor = (0.96, 0.96, 0.96, 1)
        self.sesion = {}
        self.carpeta = carpeta_actual()

        sm = ScreenManager(transition=SlideTransition())
        sm.add_widget(WelcomeScreen(name="welcome"))
        sm.add_widget(DatosGeneralesScreen(name="datos_generales"))
        sm.add_widget(ColaScreen(name="cola"))
        sm.add_widget(DetalleUnidadScreen(name="detalle"))
        sm.add_widget(LoteScreen(name="lote"))
        return sm


if __name__ == "__main__":
    FichaApp().run()
