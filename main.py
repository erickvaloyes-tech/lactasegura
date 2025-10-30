
# main.py - LactaSegura (Kivy) - Online-capable version
# Requires: kivy, requests (optional for online features), kivy_garden.graph, plyer
import webbrowser, os, json, threading, socket
from datetime import datetime, timedelta
import kivy
kivy.require('2.3.0')

try:
    from kivy_garden.graph import Graph, MeshLinePlot, SmoothLinePlot
except ImportError as e:
    print(f"Error importando gráficos: {e}")
    class Graph:
        def __init__(self, **kwargs): pass
    class MeshLinePlot: pass
    class SmoothLinePlot: pass

from kivy.utils import get_color_from_hex
try:
    from plyer import notification
except ImportError:
    # Fallback para cuando plyer no está disponible
    class notification:
        @staticmethod
        def notify(title="", message="", app_icon=None, timeout=10):
            print(f"Notificación: {title} - {message}")
from functools import partial
try:
    import requests
    _HAS_REQUESTS = True
except Exception:
    requests = None
    _HAS_REQUESTS = False
from kivy.app import App
from kivy.lang import Builder
from kivy.uix.screenmanager import ScreenManager, Screen, SlideTransition
from kivy.properties import StringProperty, ListProperty, BooleanProperty
from kivy.clock import mainthread
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.boxlayout import BoxLayout
from kivy.graphics import Color, Rectangle
from kivy.metrics import dp

# --- Article metadata (include trustworthy references and DOIs) ---
ARTICLES = [
    {
        "id": "art1",
        "title": "Assistência da enfermagem à desnutrição infantil na primeira infância: revisão integrativa (Brasil, 2022)",
        "authors": "Jussiely Bezerra; Lívia Carla Silva Barbosa; Luciana Cristina da Silva; Lilian de Lucena Oliveira; Alessandra Victoria da Silva Santos; Gabriele Barros da Silva",
        "source": "RSD Journal (PDF copy)",
        "url": "https://rsdjournal.org/rsd/article/download/38510/31880/420385",
        "summary": "Revisión integrativa (20 artículos, 2015-2022) que evidencia el rol de la enfermería en la detección temprana de la desnutrición infantil, educación alimentaria, acompañamiento familiar y vigilancia del crecimiento. Recomendaciones: medición sistemática, educación a cuidadores y estrategias comunitarias."
    },
    {
        "id": "art2",
        "title": "Facilitators and barriers of wet nursing: a qualitative study with implications for emergencies (Australia, 2025)",
        "authors": "Khadija Abdelrahmman; Bindi Borg; Karleen Gribble; Seema Mihrshahi",
        "source": "Frontiers in Nutrition (2025). DOI: 10.3389/fnut.2025.1456675",
        "url": "https://www.frontiersin.org/articles/10.3389/fnut.2025.1456675/full",
        "summary": "Estudio cualitativo que explora facilitadores y barreras de la lactancia cruzada (wet nursing) en emergencias. Identifica barreras culturales, religiosas y estructurales, y la falta de protocolos formales; sugiere capacitación profesional y protocolos para implementación segura."
    }
]
# --- Screens ---
class SplashScreen(Screen):
    pass

class MainMenu(Screen):
    online = BooleanProperty(False)
    sync_status = StringProperty("")
    
    def on_enter(self):
        # Verificar estado de conexión al entrar
        self.check_connection()
        # Programar verificación periódica
        from kivy.clock import Clock
        Clock.schedule_interval(lambda dt: self.check_connection(), 30)  # cada 30 segundos
        
    def on_leave(self):
        from kivy.clock import Clock
        Clock.unschedule(self.check_connection)
    
    def check_connection(self, *args):
        app = App.get_running_app()
        self.online = app.is_online()
        if self.online:
            self.sync_status = "En línea"
        else:
            self.sync_status = "Sin conexión"
    
    # Métodos accesibles desde KV para navegar desde el menú
    def abrir_pantalla(self, name):
        try:
            App.get_running_app().root.current = name
        except Exception as e:
            print(f"No se pudo cambiar a la pantalla {name}: {e}")

    def abrir_madres(self):
        self.abrir_pantalla('madres')

    def abrir_enfermeros(self):
        self.abrir_pantalla('enfermeros')

    def abrir_articulos(self):
        self.abrir_pantalla('articulos')

    def abrir_imc(self):
        self.abrir_pantalla('imc')

    def abrir_registro(self):
        self.abrir_pantalla('registro')

    def abrir_acerca(self):
        self.abrir_pantalla('acerca')

class GuiaMadres(Screen):
    pass

class GuiaEnfermeros(Screen):
    pass

class Articulos(Screen):
    articles = ListProperty(ARTICLES)
    
    def on_enter(self):
        self.populate_articles()
        
    def populate_articles(self):
        grid = self.ids.art_grid
        grid.clear_widgets()
        for article in self.articles:
            btn = Button(
                text=article["title"],
                size_hint_y=None,
                height='48dp',
                background_normal="",
                background_color=(1, 0.78, 0.82, 1)
            )
            btn.bind(on_release=lambda btn, art=article: 
                App.get_running_app().abrir_resumen(
                    art["title"],
                    f"{art['authors']}\n\nFuente: {art['source']}\n\n{art['summary']}",
                    art["url"]
                )
            )
            grid.add_widget(btn)

class ResumenArticulo(Screen):
    title = StringProperty("")
    content = StringProperty("")
    content_link = StringProperty("")

class HistorialIMC(Screen):
    def on_enter(self):
        self.cargar_historial()
        self.actualizar_graficos()
        
    def actualizar_graficos(self):
        try:
            # Crear gráfico de IMC vs tiempo
            graph_imc = Graph(
                xlabel='Fecha',
                ylabel='IMC',
                x_ticks_minor=5,
                x_ticks_major=10,
                y_ticks_major=1,
                y_grid=True,
                x_grid=True,
                padding=5,
                x_grid_label=True,
                y_grid_label=True,
                xmin=0,
                xmax=10,
                ymin=10,
                ymax=20
            )
            
            # Crear gráfico de peso vs edad
            graph_peso = Graph(
                xlabel='Edad (meses)',
                ylabel='Peso (kg)',
                x_ticks_minor=1,
                x_ticks_major=6,
                y_ticks_major=2,
                y_grid=True,
                x_grid=True,
                padding=5,
                x_grid_label=True,
                y_grid_label=True,
                xmin=0,
                xmax=36,
                ymin=0,
                ymax=20
            )
            
            # Cargar datos históricos
            if os.path.exists(CalculadoraIMC.imc_history_file):
                with open(CalculadoraIMC.imc_history_file, "r", encoding="utf-8") as f:
                    historial = json.load(f)
                    
                # Preparar datos para los gráficos
                plot_imc = SmoothLinePlot(color=get_color_from_hex('#FF5722'))
                plot_peso = SmoothLinePlot(color=get_color_from_hex('#2196F3'))
                
                puntos_imc = []
                puntos_peso = []
                
                for i, calculo in enumerate(historial):
                    imc = float(calculo['imc'])
                    peso = float(calculo['peso_kg'])
                    edad = float(calculo['edad_meses'])
                    
                    puntos_imc.append((i, imc))
                    puntos_peso.append((edad, peso))
                
                plot_imc.points = puntos_imc
                plot_peso.points = puntos_peso
                
                # Añadir plots a los gráficos
                graph_imc.add_plot(plot_imc)
                graph_peso.add_plot(plot_peso)
                
                # Añadir gráficos al layout
                graficos_layout = self.ids.graficos_layout
                graficos_layout.clear_widgets()
                graficos_layout.add_widget(graph_imc)
                graficos_layout.add_widget(graph_peso)
                
        except Exception as e:
            print(f"Error al actualizar gráficos: {e}")
        
    def cargar_historial(self):
        try:
            grid = self.ids.historial_grid
            grid.clear_widgets()
            if os.path.exists(CalculadoraIMC.imc_history_file):
                with open(CalculadoraIMC.imc_history_file, "r", encoding="utf-8") as f:
                    historial = json.load(f)
                    
                for calculo in reversed(historial):  # Mostrar más recientes primero
                    from datetime import datetime
                    fecha = datetime.fromisoformat(calculo["fecha"]).strftime("%d/%m/%Y %H:%M")
                    texto = (f"Fecha: {fecha}\n"
                            f"Peso: {calculo['peso_kg']} kg, "
                            f"Talla: {calculo['talla_cm']} cm, "
                            f"Edad: {calculo['edad_meses']} meses\n"
                            f"IMC: {calculo['imc']}")
                    
                    item = BoxLayout(orientation='vertical', 
                                   size_hint_y=None, 
                                   height='100dp',
                                   padding=['10dp', '5dp'],
                                   spacing='5dp')
                    
                    item.canvas.before.add(Color(0.95, 0.95, 0.95, 1))
                    item.canvas.before.add(Rectangle(pos=item.pos, size=item.size))
                    
                    lbl = Label(text=texto,
                              color=(0, 0, 0, 1),
                              text_size=(grid.width - dp(20), None),
                              size_hint_y=None,
                              height='100dp')
                    item.add_widget(lbl)
                    grid.add_widget(item)
                    
                    def _update_text_size(lbl, width):
                        lbl.text_size = (width - dp(20), None)
                    
                    grid.bind(width=lambda inst, val: _update_text_size(lbl, val))
        except Exception as e:
            print("Error al cargar historial:", e)
    
    def exportar_historial(self):
        try:
            if os.path.exists(CalculadoraIMC.imc_history_file):
                with open(CalculadoraIMC.imc_history_file, "r", encoding="utf-8") as f:
                    historial = json.load(f)
                
                # Crear archivo CSV
                csv_file = "historial_imc.csv"
                import csv
                with open(csv_file, "w", newline="", encoding="utf-8") as f:
                    writer = csv.writer(f)
                    writer.writerow(["Fecha", "Peso (kg)", "Talla (cm)", "Edad (meses)", "IMC", "Interpretación"])
                    for calculo in historial:
                        writer.writerow([
                            calculo["fecha"],
                            calculo["peso_kg"],
                            calculo["talla_cm"],
                            calculo["edad_meses"],
                            calculo["imc"],
                            calculo["interpretacion"].replace("\n", " ")
                        ])
                self.ids.status_label.text = f"Historial exportado a {csv_file}"
        except Exception as e:
            self.ids.status_label.text = f"Error al exportar: {str(e)}"

class CalculadoraIMC(Screen):
    peso = StringProperty("3.0")
    talla = StringProperty("50.0")
    edad = StringProperty("0")
    resultado = StringProperty("")
    interpretacion = StringProperty("Mueva los controles deslizantes para ajustar los valores")
    imc_history_file = "lactasegura_imc_history.json"
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Asegurar que tenemos valores iniciales válidos
        self.peso = "3.0"
        self.talla = "50.0"
        self.edad = "0"
    
    def on_enter(self):
        # Asegurar valores válidos al entrar a la pantalla
        if not self.peso or float(self.peso) < 0.5:
            self.peso = "3.0"
        if not self.talla or float(self.talla) < 30:
            self.talla = "50.0"
        if not self.edad or not self.edad.isdigit():
            self.edad = "0"
        self.actualizar_calculo()
    
    def on_peso(self, instance, value):
        if not value:  # Si está vacío, usar valor predeterminado
            self.peso = "3.0"
            return
        try:
            peso = float(value)
            if 0.5 <= peso <= 30:
                self.actualizar_calculo()
            else:
                self.peso = "3.0"  # Restablecer a valor predeterminado si está fuera de rango
        except ValueError:
            self.peso = "3.0"  # Restablecer si no es un número válido
                
    def on_talla(self, instance, value):
        if not value:
            self.talla = "50.0"
            return
        try:
            talla = float(value)
            if 30 <= talla <= 120:
                self.actualizar_calculo()
            else:
                self.talla = "50.0"
        except ValueError:
            self.talla = "50.0"
                
    def on_edad(self, instance, value):
        if not value:
            self.edad = "0"
            return
        try:
            edad = float(value)
            if 0 <= edad <= 36:
                self.actualizar_calculo()
            else:
                self.edad = "0"
        except ValueError:
            self.edad = "0"
                
    def actualizar_calculo(self, *args):
        # Verificar que tenemos todos los valores necesarios
        if not self.peso or not self.talla or not self.edad:
            self.interpretacion = "Por favor, ajuste los valores usando los controles deslizantes"
            self.resultado = ""
            return

        try:
            # Convertir valores asegurando que son números válidos
            peso = float(self.peso.replace(',', '.'))
            talla_cm = float(self.talla.replace(',', '.'))
            edad_meses = float(self.edad.replace(',', '.'))
            
            # Validar rangos con mensajes específicos
            if not (0.5 <= peso <= 30):
                self.interpretacion = "[color=ff0000]El peso debe estar entre 0.5 y 30 kg[/color]"
                self.resultado = ""
                return
            
            if not (30 <= talla_cm <= 120):
                self.interpretacion = "[color=ff0000]La talla debe estar entre 30 y 120 cm[/color]"
                self.resultado = ""
                return
            
            if not (0 <= edad_meses <= 36):
                self.interpretacion = "[color=ff0000]La edad debe estar entre 0 y 36 meses[/color]"
                self.resultado = ""
                return
            
            # Calcular IMC
            talla_m = talla_cm / 100.0
            imc = peso / (talla_m ** 2)
            self.resultado = f"{imc:.1f}"
            
            # Interpretación según la edad
            if edad_meses <= 24:
                rango_bajo = 13
                rango_normal = 14
                rango_alto = 17
            else:
                rango_bajo = 14
                rango_normal = 15
                rango_alto = 18
            
            # Preparar texto de interpretación con colores
            if imc < rango_bajo:
                estado = "[color=ff0000]ATENCIÓN: Posible bajo peso severo[/color]"
                recomendacion = "[b]Consulte URGENTEMENTE a un profesional de la salud.[/b]"
            elif imc < rango_normal:
                estado = "[color=ffa500]Alerta: Bajo peso[/color]"
                recomendacion = "[b]Se recomienda consultar a un pediatra para evaluación.[/b]"
            elif imc < rango_alto:
                estado = "[color=008000]IMC dentro de rangos esperados para la edad[/color]"
                recomendacion = "[b]Continúe con los controles regulares.[/b]"
            else:
                estado = "[color=ffa500]IMC por encima del rango esperado[/color]"
                recomendacion = "[b]Consulte con su pediatra en el próximo control.[/b]"
            
            self.interpretacion = f"{estado}\n\n{recomendacion}\n\nIMC calculado: {imc:.1f}\nPeso: {peso:.1f} kg\nTalla: {talla_cm:.1f} cm\nEdad: {int(edad_meses)} meses\n\n[i]Recordatorio: Este cálculo es solo orientativo.\nSiempre siga las recomendaciones de su profesional de salud.[/i]"
            
            # Guardar automáticamente en el historial
            self.guardar_calculo(imc, self.interpretacion)
            
        except ValueError as e:
            print(f"Error en cálculo: {e}")
            self.resultado = ""
            self.interpretacion = "[color=ff0000]Error en el cálculo. Verifique los valores ingresados.[/color]"

    def on_enter(self):
        # Limpiar campos al entrar
        self.peso = ""
        self.talla = ""
        self.edad = ""
        self.resultado = ""
        self.interpretacion = "Ingrese los datos del bebé para calcular su IMC"
        
    def guardar_calculo(self, imc, interpretacion):
        """Guarda el cálculo en el historial"""
        try:
            from datetime import datetime
            # Cargar historial existente
            if os.path.exists(self.imc_history_file):
                with open(self.imc_history_file, "r", encoding="utf-8") as f:
                    historial = json.load(f)
            else:
                historial = []
            
            # Añadir nuevo cálculo
            calculo = {
                "fecha": datetime.now().isoformat(),
                "peso_kg": self.peso,
                "talla_cm": self.talla,
                "edad_meses": self.edad,
                "imc": imc,
                "interpretacion": interpretacion
            }
            historial.append(calculo)
            
            # Guardar historial actualizado
            with open(self.imc_history_file, "w", encoding="utf-8") as f:
                json.dump(historial, f, ensure_ascii=False, indent=2)
            
            # Mostrar mensaje en la interpretación
            self.interpretacion += "\n\nCálculo guardado en el historial."
        except Exception as e:
            print("Error al guardar el cálculo:", e)
    
    def validar_entrada(self, texto, tipo):
        """Valida la entrada mientras el usuario escribe"""
        try:
            if not texto:
                return True
            # Permitir comas y puntos para decimales
            texto = texto.replace(',', '.')
            valor = float(texto)
            
            if tipo == 'peso':
                # Rango razonable para bebés: 0.5 kg a 30 kg
                return 0.5 <= valor <= 30
            elif tipo == 'talla':
                # Rango razonable para bebés: 30 cm a 120 cm
                return 30 <= valor <= 120
            elif tipo == 'edad':
                # Rango razonable: 0 a 36 meses
                return 0 <= valor <= 36
            return True
        except ValueError:
            return False

    def format_decimal(self, texto):
        """Formatea números decimales para mostrar siempre un decimal"""
        try:
            valor = float(texto.replace(',', '.'))
            return f"{valor:.1f}"
        except ValueError:
            return texto

    def calcular(self):
        """Método mantenido para compatibilidad con el botón existente"""
        self.actualizar_calculo()
class RegistroLocal(Screen):
    records_file = "lactasegura_records.json"
    records = ListProperty([])
    filtered_records = ListProperty([])
    
    def on_pre_enter(self, *args):
        self.load_records()
        self.filtered_records = self.records.copy()
        
    def buscar_registros(self, texto_busqueda):
        if not texto_busqueda:
            self.filtered_records = self.records.copy()
        else:
            self.filtered_records = [
                r for r in self.records
                if texto_busqueda.lower() in r['nombre'].lower() or
                   texto_busqueda in r['fecha'] or
                   texto_busqueda in r['edad_meses'] or
                   texto_busqueda in r['peso_kg']
            ]
        self.actualizar_vista_registros()
        
    def filtrar_por_edad(self, min_edad, max_edad):
        try:
            min_edad = float(min_edad) if min_edad else 0
            max_edad = float(max_edad) if max_edad else 999
            self.filtered_records = [
                r for r in self.records
                if min_edad <= float(r['edad_meses']) <= max_edad
            ]
            self.actualizar_vista_registros()
        except ValueError:
            print("Error: Ingrese valores numéricos válidos para el rango de edad")
            
    def ordenar_registros(self, criterio):
        if criterio == 'fecha':
            self.filtered_records.sort(key=lambda x: x['fecha'], reverse=True)
        elif criterio == 'nombre':
            self.filtered_records.sort(key=lambda x: x['nombre'].lower())
        elif criterio == 'edad':
            self.filtered_records.sort(key=lambda x: float(x['edad_meses']))
        elif criterio == 'peso':
            self.filtered_records.sort(key=lambda x: float(x['peso_kg']))
        self.actualizar_vista_registros()
    
    def on_pre_enter(self, *args):
        self.load_records()
        
    def load_records(self):
        if os.path.exists(self.records_file):
            try:
                with open(self.records_file, "r", encoding="utf-8") as f:
                    self.records = json.load(f)
            except Exception:
                self.records = []
        else:
            self.records = []
    
    def exportar_registros(self):
        try:
            if self.records:
                # Crear archivo Excel
                csv_file = "registros_lactasegura.csv"
                import csv
                with open(csv_file, "w", newline="", encoding="utf-8") as f:
                    writer = csv.writer(f)
                    writer.writerow(["ID", "Fecha", "Nombre", "Edad (meses)", "Peso (kg)", "Observación"])
                    for record in self.records:
                        writer.writerow([
                            record["id"],
                            record["fecha"],
                            record["nombre"],
                            record["edad_meses"],
                            record["peso_kg"],
                            record["observacion"]
                        ])
                self.ids.status_label.text = f"Registros exportados a {csv_file}"
            else:
                self.ids.status_label.text = "No hay registros para exportar"
        except Exception as e:
            self.ids.status_label.text = f"Error al exportar: {str(e)}"
    
    def editar_registro(self, rec_id, nombre, edad, peso, observacion):
        try:
            # Encontrar y actualizar el registro
            for record in self.records:
                if record["id"] == rec_id:
                    record["nombre"] = nombre
                    record["edad_meses"] = edad
                    record["peso_kg"] = peso
                    record["observacion"] = observacion
                    break
            
            # Guardar cambios
            with open(self.records_file, "w", encoding="utf-8") as f:
                json.dump(self.records, f, ensure_ascii=False, indent=2)
            
            # Recargar registros
            self.load_records()
            self.ids.status_label.text = "Registro actualizado"
        except Exception as e:
            self.ids.status_label.text = f"Error al editar: {str(e)}"
        
        # Mostrar los registros en la interfaz
        records_grid = self.ids.content_grid
        # Limpiar widgets existentes y mantener inputs/buttons (pero no re-ponerlos aún)
        children_to_keep = [c for c in records_grid.children if isinstance(c, (Button, TextInput))]
        records_grid.clear_widgets()

        # Preparar lista para labels y deshacer bindings previos si existen
        if not hasattr(self, '_record_labels'):
            self._record_labels = []
        else:
            # vaciar lista de labels anteriores
            self._record_labels.clear()

        # Si teníamos un binding previo al ancho, quitarlo para evitar múltiples binds
        if hasattr(self, '_width_bind'):
            try:
                records_grid.unbind(width=self._width_bind)
            except Exception:
                pass
            del self._width_bind

        # Primero agregar las etiquetas de los registros (de modo que queden debajo de los inputs/buttons)
        for record in self.records:
            record_text = f"[{record['fecha']}] {record['nombre']}\nEdad: {record['edad_meses']} meses, Peso: {record['peso_kg']} kg\nObs: {record['observacion']}"
            lbl = Label(
                text=record_text,
                size_hint_y=None,
                height='80dp',
                text_size=(records_grid.width - 20, None),
                halign='left'
            )
            self._record_labels.append(lbl)
            records_grid.add_widget(lbl)

        # Hacer un único bind para actualizar text_size de todas las labels cuando cambie el ancho
        def _sync_text_size(grid, value):
            for label in self._record_labels:
                try:
                    label.text_size = (grid.width - 20, None)
                except Exception:
                    pass

        self._width_bind = _sync_text_size
        records_grid.bind(width=self._width_bind)

        # Finalmente, re-agregar los inputs/buttons para que queden encima y sigan siendo interactivos
        for child in reversed(children_to_keep):
            records_grid.add_widget(child)

    def on_touch_down(self, touch):
        # Registro simple para depurar la recepción de toques en esta pantalla
        try:
            print(f"[RegistroLocal] on_touch_down at {touch.pos}")
        except Exception:
            pass
        return super().on_touch_down(touch)

    def on_pre_leave(self, *args):
        # Limpiar bindings para evitar fugas y datos obsoletos
        try:
            if hasattr(self, '_width_bind'):
                self.ids.content_grid.unbind(width=self._width_bind)
                del self._width_bind
        except Exception:
            pass
    def save_record(self, nombre, edad, peso, observacion):
        rec = {
            "id": str(len(self.records)+1),
            "fecha": __import__('datetime').datetime.now().isoformat(),
            "nombre": nombre,
            "edad_meses": edad,
            "peso_kg": peso,
            "observacion": observacion
        }
        self.records.append(rec)
        with open(self.records_file, "w", encoding="utf-8") as f:
            json.dump(self.records, f, ensure_ascii=False, indent=2)
        self.load_records()
    def delete_record(self, rec_id):
        self.records = [r for r in self.records if r["id"] != rec_id]
        with open(self.records_file, "w", encoding="utf-8") as f:
            json.dump(self.records, f, ensure_ascii=False, indent=2)
        self.load_records()

class Acerca(Screen):
    def on_enter(self):
        self.actualizar_estado_sync()
        
    def actualizar_estado_sync(self):
        app = App.get_running_app()
        if hasattr(app, 'cloud_sync'):
            self.ids.sync_status.text = app.cloud_sync.sync_status
            
    def iniciar_sesion(self, username, password):
        app = App.get_running_app()
        if app.cloud_sync.authenticate(username, password):
            self.ids.sync_status.text = "Autenticado correctamente"
            app.notification_manager.send_notification(
                "LactaSegura",
                "Sesión iniciada correctamente"
            )
        else:
            self.ids.sync_status.text = "Error de autenticación"
            
    def sincronizar(self):
        app = App.get_running_app()
        if app.cloud_sync.sync_data():
            app.notification_manager.send_notification(
                "LactaSegura",
                "Datos sincronizados correctamente"
            )
        self.actualizar_estado_sync()
        
    def restaurar(self):
        app = App.get_running_app()
        if app.cloud_sync.restore_data():
            app.notification_manager.send_notification(
                "LactaSegura",
                "Datos restaurados correctamente"
            )
            self.actualizar_estado_sync()

class NotificationManager:
    @staticmethod
    def send_notification(title, message):
        try:
            notification.notify(
                title=title,
                message=message,
                app_icon=None,
                timeout=10
            )
        except Exception as e:
            print(f"Error al enviar notificación: {e}")

    @staticmethod
    def schedule_reminder(fecha_control):
        try:
            notification.notify(
                title="Recordatorio de Control",
                message=f"Tienes un control programado para {fecha_control}",
                app_icon=None,
                timeout=10
            )
        except Exception as e:
            print(f"Error al programar recordatorio: {e}")

class CloudSync:
    def __init__(self):
        self.sync_status = StringProperty("No sincronizado")
        self.last_sync = None
        self.auth_token = None
        self._sync_file = "sync_status.json"
        
    def authenticate(self, username, password):
        try:
            # Simulación de autenticación
            if username and password:
                self.auth_token = "token_simulado"
                return True
            return False
        except Exception as e:
            print(f"Error de autenticación: {e}")
            return False
            
    def sync_data(self):
        try:
            if not self.auth_token:
                raise Exception("No autenticado")
                
            # Recopilar datos para sincronizar
            data = {
                "imc_history": self._read_file(CalculadoraIMC.imc_history_file),
                "records": self._read_file(RegistroLocal.records_file)
            }
            
            # Simular envío a la nube
            self._save_backup(data)
            
            self.last_sync = datetime.now()
            self.sync_status = f"Última sincronización: {self.last_sync.strftime('%d/%m/%Y %H:%M')}"
            return True
            
        except Exception as e:
            self.sync_status = f"Error de sincronización: {str(e)}"
            return False
            
    def restore_data(self):
        try:
            # Cargar respaldo
            backup = self._read_file("backup.json")
            if not backup:
                raise Exception("No hay respaldo disponible")
                
            # Restaurar datos
            self._write_file(CalculadoraIMC.imc_history_file, backup.get("imc_history", []))
            self._write_file(RegistroLocal.records_file, backup.get("records", []))
            
            return True
        except Exception as e:
            print(f"Error al restaurar datos: {e}")
            return False
            
    def _read_file(self, filename):
        try:
            if os.path.exists(filename):
                with open(filename, "r", encoding="utf-8") as f:
                    return json.load(f)
            return None
        except Exception:
            return None
            
    def _write_file(self, filename, data):
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            
    def _save_backup(self, data):
        self._write_file("backup.json", data)

class LactaSeguraApp(App):
    def build(self):
        self.title = "LactaSegura"
        self.notification_manager = NotificationManager()
        self.cloud_sync = CloudSync()
        sm = ScreenManager(transition=SlideTransition())
        sm.add_widget(SplashScreen(name="splash"))
        sm.add_widget(MainMenu(name="menu"))
        sm.add_widget(GuiaMadres(name="madres"))
        sm.add_widget(GuiaEnfermeros(name="enfermeros"))
        sm.add_widget(Articulos(name="articulos"))
        sm.add_widget(ResumenArticulo(name="resumen"))
        sm.add_widget(CalculadoraIMC(name="imc"))
        sm.add_widget(RegistroLocal(name="registro"))
        sm.add_widget(Acerca(name="acerca"))
        # Mostrar la pantalla de inicio (SplashScreen) al arrancar
        try:
            sm.current = 'splash'
        except Exception:
            pass
        # internal articles data (can be loaded from remote or cache)
        self.articles = ARTICLES.copy()
        self._articles_cache_file = "lactasegura_articles_cache.json"
        self._remote_config_file = "remote_config.json"
        return sm
        
    def on_stop(self):
        """Se llama cuando la aplicación se está cerrando"""
        cleanup_lock()  # Limpiar archivo de bloqueo
        return True

    def on_start(self):
        # Load articles (from cache or remote if available) when app starts
        try:
            self.load_articles()
        except Exception as e:
            print("Error loading articles on start:", e)

    # Network and sync helpers
    def is_online(self, timeout=2):
        # Try to detect connectivity. Prefer requests if available; otherwise use a socket probe.
        if _HAS_REQUESTS:
            try:
                requests.get("https://www.google.com/", timeout=timeout)
                return True
            except Exception:
                return False
        else:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(timeout)
                sock.connect(("8.8.8.8", 53))
                sock.close()
                return True
            except Exception:
                return False

    def load_remote_config(self):
        if os.path.exists(self._remote_config_file):
            try:
                with open(self._remote_config_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    def save_remote_config(self, cfg):
        try:
            with open(self._remote_config_file, "w", encoding="utf-8") as f:
                json.dump(cfg, f, ensure_ascii=False, indent=2)
            print("Remote config saved.")
        except Exception as e:
            print("Failed saving remote config:", e)

    def fetch_remote_articles(self, url, timeout=6):
        # Attempt to fetch a JSON array of articles from `url`.
        if not url:
            raise ValueError("No remote URL configured")
        if not _HAS_REQUESTS:
            raise RuntimeError("requests package not available")
        resp = requests.get(url, timeout=timeout)
        resp.raise_for_status()
        data = resp.json()
        if not isinstance(data, list):
            raise ValueError("Remote data is not a list of articles")
        return data

    def _write_articles_cache(self, articles):
        try:
            with open(self._articles_cache_file, "w", encoding="utf-8") as f:
                json.dump(articles, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print("Failed writing articles cache:", e)

    def _read_articles_cache(self):
        if os.path.exists(self._articles_cache_file):
            try:
                with open(self._articles_cache_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return None
        return None

    def load_articles(self, force_remote=False):
        # Loads articles into self.articles using this priority:
        # 1) if force_remote and online and remote configured -> fetch remote
        # 2) cached file
        # 3) bundled ARTICLES
        cfg = self.load_remote_config()
        remote_url = cfg.get("remote_articles_url") if isinstance(cfg, dict) else None

        # If forced remote fetch and we are online, do it in a background thread
        if force_remote and remote_url and self.is_online():
            def _bg():
                try:
                    new = self.fetch_remote_articles(remote_url)
                    self.articles = new
                    self._write_articles_cache(new)
                    print("Articles updated from remote.")
                    # Update UI
                    mainthread_update = getattr(self, '_update_articles_ui', None)
                    if mainthread_update:
                        mainthread_update()
                except Exception as e:
                    print("Failed fetching remote articles:", e)
            threading.Thread(target=_bg, daemon=True).start()
            return

        # Try cache first
        cached = self._read_articles_cache()
        if cached:
            self.articles = cached
        else:
            # fallback to bundled list
            self.articles = ARTICLES.copy()

        # If not forced but online and remote_url, attempt a background refresh
        if not force_remote and remote_url and self.is_online():
            def _bg2():
                try:
                    new = self.fetch_remote_articles(remote_url)
                    self.articles = new
                    self._write_articles_cache(new)
                    print("Articles refreshed from remote in background.")
                    mainthread_update = getattr(self, '_update_articles_ui', None)
                    if mainthread_update:
                        mainthread_update()
                except Exception as e:
                    print("Background fetch failed:", e)
            threading.Thread(target=_bg2, daemon=True).start()

        # Finally, push to UI now
        try:
            screen = self.root.get_screen('articulos')
            screen.articles = self.articles
            try:
                screen.populate_articles()
            except Exception:
                pass
        except Exception:
            pass

    def refresh_articles(self):
        # Public method to force a remote refresh (called from UI)
        cfg = self.load_remote_config()
        remote_url = cfg.get("remote_articles_url") if isinstance(cfg, dict) else None
        if not remote_url:
            print("No remote URL configured. Set one in Acerca to enable fetching.")
            return
        if not self.is_online():
            print("No internet connection detected.")
            return
        # Force remote fetch
        self.load_articles(force_remote=True)

    def save_remote_articles_url(self, url):
        cfg = self.load_remote_config() or {}
        cfg['remote_articles_url'] = url
        self.save_remote_config(cfg)
        # Trigger an immediate background refresh
        try:
            if self.is_online():
                self.load_articles(force_remote=True)
        except Exception:
            pass

    # Método genérico para cambiar pantallas, utilizable desde KV como app.abrir_pantalla('nombre')
    def abrir_pantalla(self, name):
        try:
            if not self.root:
                print(f"Advertencia: root aún no inicializado, no se puede abrir {name}")
                return
            if name in self.root.screen_names:
                self.root.current = name
            else:
                print(f"Pantalla '{name}' no encontrada entre: {self.root.screen_names}")
        except Exception as e:
            print(f"Error al cambiar a la pantalla {name}: {e}")

    def abrir_resumen(self, title, content, link=None):
        resumen = self.root.get_screen("resumen")
        resumen.title = title
        resumen.content = content
        if link:
            resumen.content_link = link
        else:
            resumen.content_link = "https://www.google.com"
        self.root.current = "resumen"

    def abrir_en_navegador(self, url):
        try:
            webbrowser.open(url)
        except Exception as e:
            print("No se pudo abrir el navegador:", e)

def check_single_instance():
    """Verifica si ya hay una instancia de la aplicación corriendo usando un archivo de bloqueo"""
    import os, sys, time
    lock_file = os.path.join(os.path.expanduser('~'), '.lactasegura.lock')
    
    try:
        # Si el archivo existe, verificar si el proceso sigue vivo
        if os.path.exists(lock_file):
            with open(lock_file, 'r') as f:
                old_pid = int(f.read().strip())
            
            # En Windows, intentar terminar el proceso anterior si existe
            if sys.platform == 'win32':
                import ctypes
                kernel32 = ctypes.windll.kernel32
                PROCESS_TERMINATE = 1
                handle = kernel32.OpenProcess(PROCESS_TERMINATE, False, old_pid)
                if handle:
                    kernel32.TerminateProcess(handle, -1)
                    kernel32.CloseHandle(handle)
            
            # Esperar un momento para asegurarse de que el proceso anterior se cerró
            time.sleep(1)
            
        # Crear nuevo archivo de bloqueo
        with open(lock_file, 'w') as f:
            f.write(str(os.getpid()))
        return True
        
    except Exception as e:
        print(f"Error al gestionar el archivo de bloqueo: {e}")
        return False

def cleanup_lock():
    """Limpia el archivo de bloqueo al cerrar la aplicación"""
    try:
        lock_file = os.path.join(os.path.expanduser('~'), '.lactasegura.lock')
        if os.path.exists(lock_file):
            os.remove(lock_file)
    except:
        pass

if __name__ == "__main__":
    import atexit
    atexit.register(cleanup_lock)  # Registrar limpieza al salir
    
    if not check_single_instance():
        print("No se pudo iniciar LactaSegura.")
        import sys
        sys.exit(1)
        
    try:
        LactaSeguraApp().run()
    except Exception:
        import traceback
        # Imprimir la traza en consola
        traceback.print_exc()
        # Intentar guardar la traza en un archivo para inspección
        try:
            with open("crash_log.txt", "w", encoding="utf-8") as f:
                traceback.print_exc(file=f)
            print("Se escribió crash_log.txt con la traza de error.")
        except Exception as e:
            print("No se pudo escribir crash_log.txt:", e)
        # Re-levantar la excepción después de registrar
        raise
