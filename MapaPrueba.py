import requests
import arcade
import random
from datetime import datetime
from Pedido import Pedido
from Repartidor import Repartidor
from Clima import Clima
from MarkovClima import MarkovClima
from Resistencia import Resistencia  

CELL_SIZE = 50
BASE_URL = "https://tigerds-api.kindflower-ccaf48b6.eastus.azurecontainerapps.io"

city_data = requests.get(f"{BASE_URL}/city/map").json()
data = city_data.get("data", {})

tiles = data.get("tiles", [])
height = data.get("height", 0)
width = data.get("width", 0)

mapa = tiles
ROWS = len(mapa)
COLS = len(mapa[0])


# --- Clima y Markov ---
weather_data = requests.get(f"{BASE_URL}/city/weather?city=TigerCity&mode=seed").json()
weather_info = weather_data.get("data", {})
initial_weather = weather_info.get("initial", {})

conditions = weather_info.get("conditions", [])
transition = weather_info.get("transition", {})

# Normaliza nombres de condiciones
cond_names = [c["condition"] if isinstance(c, dict) and "condition" in c else c for c in conditions]

# Convierte el diccionario de transición a matriz cuadrada NxN
matrizT = []
for fila in cond_names:
    fila_probs = []
    trans_row = transition.get(fila, {})
    for col in cond_names:
        prob = trans_row.get(col, 0.0)
        fila_probs.append(prob)
    matrizT.append(fila_probs)

markov = MarkovClima(cond_names, matrizT)

class MapaWindow(arcade.Window):
    # --- Popup de cargar partida ---
    def mostrar_popup_cargar(self):
        """Activa el popup para seleccionar slot de carga si no hay otros popups activos."""
        if getattr(self, 'mostrar_popup_puntajes', False):
            return
        if getattr(self, 'nombre_popup_activo', False):
            return
        if getattr(self, 'popup_guardar_activo', False):
            return
        if getattr(self, 'popup_cargar_activo', False):
            return
        self.popup_cargar_activo = True
        self.slot_cargar_seleccionado = None

    def draw_popup_cargar(self):
        if not getattr(self, 'popup_cargar_activo', False):
            return
        ancho, alto = 520, 140
        x = self.window_width // 2 - ancho // 2
        y = self.window_height // 2 - alto // 2
        arcade.draw_lbwh_rectangle_filled(x, y, ancho, alto, arcade.color.DARK_SLATE_GRAY)
        arcade.draw_lbwh_rectangle_outline(x, y, ancho, alto, arcade.color.WHITE, 3)
        texto = "¿Cuál espacio deseas cargar?\nSelecciona 1, 2 o 3"
        arcade.draw_text(texto, x + 20, y + alto - 25, arcade.color.WHITE, 18, anchor_x="left", anchor_y="top", multiline=True, width=ancho-40)
        if self.slot_cargar_seleccionado is not None:
            arcade.draw_text(f"Seleccionado: Slot {self.slot_cargar_seleccionado}", x + 20, y + 20, arcade.color.YELLOW, 14)
        else:
            arcade.draw_text("Presiona ESC para cancelar", x + 20, y + 20, arcade.color.LIGHT_GRAY, 12)

    def cargar_de_slot(self, slot:int):
        """Placeholder de carga real. Aquí se implementaría la lógica de restaurar el estado."""
        print(f"[DEBUG] Cargando partida de slot {slot} (placeholder)")
        self.slot_cargar_seleccionado = slot
        self.popup_cargar_activo = False
    def cargar_y_mostrar_puntajes(self):
        import os, json
        ruta = os.path.join('data', 'puntajes.json')
        if os.path.exists(ruta):
            with open(ruta, 'r', encoding='utf-8') as f:
                try:
                    puntajes = json.load(f)
                except Exception:
                    puntajes = []
        else:
            puntajes = []
        # Ordena de mayor a menor
        puntajes.sort(key=lambda p: p['score'], reverse=True)
        self.popup_puntajes = puntajes
        self.mostrar_popup_puntajes = True
    
    # --- Popup de guardar partida ---
    def mostrar_popup_guardar(self):
        """Activa el popup para seleccionar slot de guardado si no hay otros popups activos."""
        if getattr(self, 'mostrar_popup_puntajes', False):
            return
        if getattr(self, 'nombre_popup_activo', False):
            return
        # Evita abrir si ya está activo
        if getattr(self, 'popup_guardar_activo', False):
            return
        self.popup_guardar_activo = True
        self.slot_seleccionado = None

    def draw_popup_guardar(self):
        if not getattr(self, 'popup_guardar_activo', False):
            return
        ancho, alto = 520, 140
        x = self.window_width // 2 - ancho // 2
        y = self.window_height // 2 - alto // 2
        arcade.draw_lbwh_rectangle_filled(x, y, ancho, alto, arcade.color.DARK_SLATE_GRAY)
        arcade.draw_lbwh_rectangle_outline(x, y, ancho, alto, arcade.color.WHITE, 3)
        texto = "En cual slot deseas guardar la partida?\nSelecciona 1, 2 o 3"
        arcade.draw_text(texto, x + 20, y + alto - 25, arcade.color.WHITE, 18, anchor_x="left", anchor_y="top", multiline=True, width=ancho-40)
        if self.slot_seleccionado is not None:
            arcade.draw_text(f"Seleccionado: Slot {self.slot_seleccionado}", x + 20, y + 20, arcade.color.YELLOW, 14)
        else:
            arcade.draw_text("Presiona ESC para cancelar", x + 20, y + 20, arcade.color.LIGHT_GRAY, 12)
    
    def guardar_en_slot(self, slot:int):
        """Guarda el estado actual del juego en binario usando pickle."""
        import pickle, os
        ruta = os.path.join('data', f'slot{slot}.bin')
        estado = {
            'total_time': self.total_time,
            'player': {
                'row': self.player_sprite.row,
                'col': self.player_sprite.col,
                'center_x': self.player_sprite.center_x,
                'center_y': self.player_sprite.center_y,
                'resistencia': self.player_sprite.get_resistencia_actual(),
                'nombre': getattr(self.player_sprite, 'nombre', ''),
                'ingresos': getattr(self.player_sprite, 'ingresos', 0),
                'reputacion': getattr(self.player_sprite, 'reputacion', 1),
                'peso_total': getattr(self.player_sprite, 'peso_total', 0),
                # Inventario: lista de IDs de pedidos
                'inventario': [nodo.pedido.id for nodo in self._iterar_inventario()],
            },
            'clima': {
                'condicion': self.clima.condicion,
                'intensidad': self.clima.intensidad,
                'tiempoRestante': self.clima.tiempoRestante,
                'multiplicadorVelocidad': self.clima.multiplicadorVelocidad,
            },
            'pedidos_activos': list(self.pedidos_activos.keys()),
            'pedidos_pendientes': [p.id for p in self.pedidos_pendientes],
            'pedido_actual': self.pedido_actual.id if self.pedido_actual else None,
            # Guardar pickups y dropoffs
            'pickups': [
                {'pedido_id': s.pedido_id, 'center_x': s.center_x, 'center_y': s.center_y}
                for s in self.pickup_list
            ],
            'dropoffs': [
                {'pedido_id': s.pedido_id, 'center_x': s.center_x, 'center_y': s.center_y}
                for s in self.dropoff_list
            ],
        }
        with open(ruta, 'wb') as f:
            pickle.dump(estado, f)
        print(f"Guardado en {ruta}")
        self.slot_seleccionado = slot
        self.popup_guardar_activo = False

    def _iterar_inventario(self):
        """Itera sobre el inventario del jugador y retorna nodos."""
        nodo = self.player_sprite.inventario.inicio
        while nodo:
            yield nodo
            nodo = nodo.siguiente

    def cargar_de_slot(self, slot:int):
        """Carga el estado guardado en binario y restaura los atributos principales."""
        import pickle, os
        ruta = os.path.join('data', f'slot{slot}.bin')
        if not os.path.exists(ruta):
            print(f"No existe guardado en {ruta}")
            self.popup_cargar_activo = False
            return
        with open(ruta, 'rb') as f:
            estado = pickle.load(f)
        # Restaurar atributos principales
        self.total_time = estado.get('total_time', self.total_time)
        player = estado.get('player', {})
        self.player_sprite.row = player.get('row', self.player_sprite.row)
        self.player_sprite.col = player.get('col', self.player_sprite.col)
        self.player_sprite.center_x = player.get('center_x', self.player_sprite.center_x)
        self.player_sprite.center_y = player.get('center_y', self.player_sprite.center_y)
        self.player_sprite.resistencia_obj.set_resistencia(player.get('resistencia', 100))
        self.player_sprite.nombre = player.get('nombre', getattr(self.player_sprite, 'nombre', ''))
        self.player_sprite.ingresos = player.get('ingresos', getattr(self.player_sprite, 'ingresos', 0))
        self.player_sprite.reputacion = player.get('reputacion', getattr(self.player_sprite, 'reputacion', 1))
        self.player_sprite.peso_total = player.get('peso_total', getattr(self.player_sprite, 'peso_total', 0))
        # Inventario: reconstruir desde IDs
        self._restaurar_inventario(player.get('inventario', []))
        clima = estado.get('clima', {})
        self.clima.condicion = clima.get('condicion', self.clima.condicion)
        self.clima.intensidad = clima.get('intensidad', self.clima.intensidad)
        self.clima.tiempoRestante = clima.get('tiempoRestante', self.clima.tiempoRestante)
        self.clima.multiplicadorVelocidad = clima.get('multiplicadorVelocidad', self.clima.multiplicadorVelocidad)
        # Pedidos activos/pendientes
        self.pedidos_activos = {pid: self.pedidos_dict[pid] for pid in estado.get('pedidos_activos', []) if pid in self.pedidos_dict}
        self.pedidos_pendientes = [self.pedidos_dict[pid] for pid in estado.get('pedidos_pendientes', []) if pid in self.pedidos_dict]
        pid_actual = estado.get('pedido_actual', None)
        self.pedido_actual = self.pedidos_dict[pid_actual] if pid_actual and pid_actual in self.pedidos_dict else None
        # Restaurar pickups y dropoffs
        self.pickup_list = arcade.SpriteList()
        for info in estado.get('pickups', []):
            s = arcade.Sprite("assets/pickup.png", scale=0.8)
            s.center_x = info['center_x']
            s.center_y = info['center_y']
            s.pedido_id = info['pedido_id']
            self.pickup_list.append(s)
        self.dropoff_list = arcade.SpriteList()
        for info in estado.get('dropoffs', []):
            s = arcade.Sprite("assets/dropoff.png", scale=0.8)
            s.center_x = info['center_x']
            s.center_y = info['center_y']
            s.pedido_id = info['pedido_id']
            self.dropoff_list.append(s)
        print(f"Cargado desde {ruta}")
        self.slot_cargar_seleccionado = slot
        self.popup_cargar_activo = False

    def _restaurar_inventario(self, lista_ids):
        """Reconstruye el inventario del jugador desde una lista de IDs."""
        inv = self.player_sprite.inventario
        inv.inicio = None
        inv.peso_total = 0
        for pid in lista_ids:
            pedido = self.pedidos_dict.get(pid)
            if pedido:
                inv.agregar_pedido(pedido)
    def draw_popup_puntajes(self):
        ancho, alto = 400, 350
        x = self.window_width // 2 - ancho // 2
        y = self.window_height // 2 - alto // 2
        arcade.draw_lbwh_rectangle_filled(x, y, ancho, alto, arcade.color.DARK_GREEN)
        arcade.draw_lbwh_rectangle_outline(x, y, ancho, alto, arcade.color.WHITE, 3)
        arcade.draw_text("Marcadores", x + 20, y + alto - 30, arcade.color.WHITE, 20, anchor_x="left", anchor_y="top")
        if hasattr(self, 'popup_puntajes') and self.popup_puntajes:
            for i, p in enumerate(self.popup_puntajes[:10]):
                nombre = p['nombre']
                score = p['score']
                arcade.draw_text(f"{i+1}. {nombre}: {score}", x + 30, y + alto - 60 - i*28, arcade.color.YELLOW, 16, anchor_x="left", anchor_y="top")
        else:
            arcade.draw_text("No hay puntajes guardados.", x + 30, y + alto - 60, arcade.color.LIGHT_GRAY, 16, anchor_x="left", anchor_y="top")
        arcade.draw_text("Presiona ESC para cerrar", x + 20, y + 20, arcade.color.LIGHT_GRAY, 12)
    def pedir_nombre_popup(self):
        self.nombre_popup_activo = True
        self.nombre_jugador = ""

    def draw_nombre_popup(self):
        ancho, alto = 350, 120
        x = self.window_width // 2 - ancho // 2
        y = self.window_height // 2 - alto // 2
        arcade.draw_lbwh_rectangle_filled(x, y, ancho, alto, arcade.color.DARK_BLUE)
        arcade.draw_lbwh_rectangle_outline(x, y, ancho, alto, arcade.color.WHITE, 3)
        arcade.draw_text("Ingresa tu nombre de jugador:", x + 20, y + alto - 30, arcade.color.WHITE, 18, anchor_x="left", anchor_y="top")
        arcade.draw_text(self.nombre_jugador + "_", x + 20, y + alto - 65, arcade.color.WHITE, 16, anchor_x="left", anchor_y="top")
        arcade.draw_text("Presiona Enter para continuar y suerte!", x + 20, y + 15, arcade.color.LIGHT_GRAY, 12)

    def guardar_puntaje_si_termina(self):
        """
        Guarda el puntaje final usando Marcador cuando el tiempo llega a cero.
        """
        if not hasattr(self, 'marcador'):
            from Marcador import Marcador
            self.marcador = Marcador()
        nombre = getattr(self.player_sprite, 'nombre', 'Jugador')
        ingresos = getattr(self.player_sprite, 'ingresos', 0)
        reputacion = getattr(self.player_sprite, 'reputacion', 1)
        puntaje = self.marcador.guardar_puntaje_final(nombre, ingresos, reputacion)
        print(f"Puntaje guardado: {puntaje}")
        
    def iniciar_transicion_clima(self, nueva_cond, nueva_intensidad, nueva_duracion, nuevo_mult):
        self.transicion_clima = {
            'activa': True,
            't': 0.0,
            'duracion': random.uniform(3, 5),
            'inicio': {
                'condicion': self.clima.condicion,
                'intensidad': self.clima.intensidad,
                'multiplicador': self.clima.multiplicadorVelocidad
            },
            'fin': {
                'condicion': nueva_cond,
                'intensidad': nueva_intensidad,
                'multiplicador': nuevo_mult,
                'duracion': nueva_duracion
            }
        }

    def cambiar_clima(self):
        nueva_cond = self.markov.calcularSiguiente(self.clima.condicion)
        nueva_intensidad = self.markov.sortearIntensidad()
        nueva_duracion = self.markov.sortearDuracion()
        nuevo_mult = self.markov.obtenerMultiplicador(nueva_cond)
        self.iniciar_transicion_clima(nueva_cond, nueva_intensidad, nueva_duracion, nuevo_mult)




    def __init__(self):
        self.nombre_popup_activo = False
        self.nombre_jugador = ""
        self.active_direction = None
        self.window_width = 800
        self.window_height = 600
        self.hud_height = 100
        super().__init__(self.window_width, self.window_height, "Mapa con Repartidor")
        self.pedir_nombre_popup()
        arcade.set_background_color(arcade.color.WHITE)
        # Estado popup cargar
        self.popup_cargar_activo = False
        self.slot_cargar_seleccionado = None
        # Estado popup guardar
        self.popup_guardar_activo = False
        self.slot_seleccionado = None 
        map_height = height * CELL_SIZE
        self.scale_x = self.window_width / (width * CELL_SIZE) if width > 0 else 1
        self.scale_y = (self.window_height - self.hud_height) / map_height if height > 0 else 1
        self.player_list = arcade.SpriteList()
        self.player_sprite = Repartidor("assets/repartidor.png", scale=0.8)
        #inicializa resistencia
        self.player_sprite.resistencia_obj = Resistencia()
        self.total_time = 15 * 60
        self.tex_parque = arcade.load_texture("assets/Parque.png")
        self.tex_edificio = arcade.load_texture("assets/Edificio.png")
        self.pedidos_dict = {} 
        self.pickup_list = arcade.SpriteList()
        self.dropoff_list = arcade.SpriteList()
        self.pedidos_pendientes = []
        self.pedidos_activos = {}
        self.pedido_actual = None
        self.mostrar_pedido = False
        self.tiempo_ultimo_popup = 0
        self.tiempo_global = 0  
        self.intervalo_popup = 30 

        # Estado de transición de clima
        self.transicion_clima = {'activa': False}

        # --- Clima dinámico ---
        condicion_inicial = initial_weather.get("condition", "clear")
        intensidad_inicial = initial_weather.get("intensity", 1.0)
        duracion_inicial = random.randint(45, 60)  # clima normal
        multiplicador = markov.obtenerMultiplicador(condicion_inicial)
        self.clima = Clima(condicion_inicial, intensidad_inicial, duracion_inicial, multiplicador)
        self.markov = markov

        self.cargar_pedidos()
        while True:
            start_row = random.randint(0, ROWS - 1)
            start_col = random.randint(0, COLS - 1)
            if mapa[start_row][start_col] != "B": 
                self.player_sprite.row = start_row
                self.player_sprite.col = start_col
                self.player_sprite.center_x = (start_col * CELL_SIZE + CELL_SIZE // 2) * self.scale_x
                self.player_sprite.center_y = (height * CELL_SIZE - (start_row * CELL_SIZE + CELL_SIZE // 2)) * self.scale_y
                break
        self.target_x = self.player_sprite.center_x
        self.target_y = self.player_sprite.center_y
        self.target_row = self.player_sprite.row
        self.target_col = self.player_sprite.col
        self.moving = False
        self.move_speed = 10
        self.player_list.append(self.player_sprite)

    def celda_a_pixeles(self, row, col):
        x = (col * CELL_SIZE + CELL_SIZE // 2) * self.scale_x
        y = (height * CELL_SIZE - (row * CELL_SIZE + CELL_SIZE // 2)) * self.scale_y
        return x, y


    def draw_hud(self):
        """Dibuja el HUD completo en la parte superior (100px de altura, fondo verde)."""
        hud_y = self.window_height - self.hud_height
        # Fondo y borde del HUD
        arcade.draw_lbwh_rectangle_filled(
            0, hud_y, self.window_width, self.hud_height,
            arcade.color.WHITE_SMOKE  # Fondo Harvard Crimson
        )
        arcade.draw_lbwh_rectangle_outline(
            0, hud_y, self.window_width, self.hud_height,
            arcade.color.BLACK, 3  # Borde grueso negro
        )
    
        # Preparar textos organizados
        pedidos = []
        nodo = self.player_sprite.inventario.inicio
        while nodo:
            pedidos.append(str(nodo.pedido.id))
            nodo = nodo.siguiente
        pedidos_text = f"Pedidos: {', '.join(pedidos) if pedidos else 'Ninguno'}"
        peso_text = f"Peso: {self.player_sprite.peso_total:.1f}/{self.player_sprite.inventario.peso_maximo}"
        ingresos_text = f"Ingresos: ${self.player_sprite.ingresos:.2f}"
        reputacion_text = f"Reputación: {self.player_sprite.reputacion}"
        clima_text = f"Clima: {self.clima.condicion}\nIntensidad: {self.clima.intensidad:.2f}\nTiempo restante: {int(self.clima.tiempoRestante)}s"
    
    # Posiciones en el HUD (izquierda para stats del jugador, derecha para timer y clima)
        hud_font_size = 12
        hud_padding = 10
    
    # Stats del jugador (izquierda)
        stats_y = hud_y + self.hud_height - hud_padding
        arcade.draw_text(pedidos_text, hud_padding, stats_y - 10, arcade.color.BLACK, hud_font_size, anchor_y="top")
        arcade.draw_text(peso_text, hud_padding, stats_y - 25, arcade.color.BLACK, hud_font_size, anchor_y="top")
        arcade.draw_text(ingresos_text, hud_padding, stats_y - 40, arcade.color.BLACK, hud_font_size, anchor_y="top")
        arcade.draw_text(reputacion_text, hud_padding, stats_y - 55, arcade.color.BLACK, hud_font_size, anchor_y="top")

        # Resistencia
        arcade.draw_text(reputacion_text, hud_padding, stats_y - 55, arcade.color.BLACK, hud_font_size, anchor_y="top")
        # Nueva: Texto de resistencia debajo de reputación
        resistencia_actual = self.player_sprite.get_resistencia_actual()
        resistencia_text = f"Resistencia:        {int(resistencia_actual)}  /100"
        arcade.draw_text(resistencia_text, hud_padding, stats_y - 70, arcade.color.BLACK, hud_font_size, anchor_y="top")
        # Barra visual de resistencia (fondo gris, relleno verde, ancho 100, alto 10)
        bar_x = hud_padding
        bar_y = stats_y - 85
        bar_width = 100
        bar_height = 10
        # Fondo de la barra
        arcade.draw_lbwh_rectangle_filled(bar_x, bar_y, bar_width, bar_height, arcade.color.GRAY)
        # Relleno proporcional (verde si >30, amarillo si 0-30, rojo si exhausted)
        fill_color = arcade.color.GREEN if resistencia_actual > 30 else (arcade.color.YELLOW if resistencia_actual > 10 else arcade.color.RED)
        fill_width = (resistencia_actual / 100.0) * bar_width
        arcade.draw_lbwh_rectangle_filled(bar_x, bar_y, fill_width, bar_height, fill_color)
        # Borde de la barra
        arcade.draw_lbwh_rectangle_outline(bar_x, bar_y, bar_width, bar_height, arcade.color.BLACK, 1)


    # Texto centrado arriba: '[P]' para ver puntuaciones
        # Cartel de puntuaciones (centrado arriba)
        cartel_y = hud_y + self.hud_height - hud_padding - 10
        arcade.draw_text(
            "[P] para ver puntuaciones!",
            self.window_width // 2, cartel_y,
            arcade.color.DARK_BLUE, hud_font_size + 2,
            anchor_x="center", anchor_y="top"
        )
        # Cartel de guardar (debajo)
        arcade.draw_text(
            "[G] para guardar partida!",
            self.window_width // 2, cartel_y - 22,
            arcade.color.DARK_GREEN, hud_font_size + 2,
            anchor_x="center", anchor_y="top"
        )
        # Cartel de cargar (debajo)
        arcade.draw_text(
            "[L] para cargar partida!",
            self.window_width // 2, cartel_y - 44,
            arcade.color.DARK_ORANGE, hud_font_size + 2,
            anchor_x="center", anchor_y="top"
        )
    
        # Timer (derecha superior)
        minutes = int(self.total_time) // 60
        seconds = int(self.total_time) % 60
        timer_text = f"Tiempo: {minutes:02d}:{seconds:02d}"
        timer_x = self.window_width - hud_padding - 80  # Ajuste para ancho del texto
        arcade.draw_text(timer_text, timer_x, stats_y, arcade.color.RED, hud_font_size + 5, anchor_x="center", anchor_y="top")
    
    # Clima (derecha inferior, multiline) - ajustado para no superponerse con timer
        clima_x = self.window_width - hud_padding - 70  # Ancho aproximado para multiline
        clima_y = hud_y + hud_padding
        arcade.draw_text(
            clima_text,
            clima_x, clima_y,
            arcade.color.BLACK, hud_font_size,
            anchor_x="center", anchor_y="bottom",
            multiline=True, width=140
        )


    def draw_popup_pedido(self):
        """Dibuja el popup centrado en el área del mapa (evita superposición con HUD)."""
        if self.mostrar_pedido and self.pedido_actual:
            ancho, alto = 400, 150
            # Centrar en el área del mapa (restar hud_height para evitar HUD)
            x = self.window_width // 2 - ancho // 2
            y = (self.window_height - self.hud_height) // 2 - alto // 2
            arcade.draw_lbwh_rectangle_filled(x, y, ancho, alto, arcade.color.BLACK)
            arcade.draw_lbwh_rectangle_outline(x, y, ancho, alto, arcade.color.WHITE, 2)
            info_text = f"Nuevo pedido: {self.pedido_actual.id}\nPeso: {self.pedido_actual.peso}\nPago: ${self.pedido_actual.pago}"
            arcade.draw_text(
                info_text,
                x + 20, y + alto - 20,
                arcade.color.WHITE, 14,
                anchor_x="left", anchor_y="top",
                multiline=True, width=ancho - 40
            )
            arcade.draw_text(
                "[A]ceptar   [R]echazar",
                x + 120, y + 55,
                arcade.color.WHITE, 14
            )




    def on_draw(self):
        self.clear()
        if getattr(self, 'mostrar_popup_puntajes', False):
            self.draw_popup_puntajes()
            return
        if getattr(self, 'popup_cargar_activo', False):
            self.draw_popup_cargar()
            return
        if getattr(self, 'popup_guardar_activo', False):
            # Dibuja detrás el mapa tenue? (Opcional: no lo implementamos ahora) Sólo popup.
            self.draw_popup_guardar()
            return
        if self.nombre_popup_activo:
            self.draw_nombre_popup()
            return
        self.draw_hud()
        for row in range(ROWS):
            for col in range(COLS):
                x = (col * CELL_SIZE + CELL_SIZE // 2) * self.scale_x
                y = ((height * CELL_SIZE - (row * CELL_SIZE + CELL_SIZE // 2)) * self.scale_y)
                tipo = mapa[row][col]
                rect = arcade.Rect.from_kwargs(x=x, y=y, width=CELL_SIZE * self.scale_x, height=CELL_SIZE * self.scale_y)
                if tipo == "P":
                    arcade.draw_texture_rect(self.tex_parque, rect)
                elif tipo == "B":
                    arcade.draw_texture_rect(self.tex_edificio, rect)
                else:
                    color = arcade.color.GRAY if tipo == "C" else arcade.color.BLACK
                    arcade.draw_rect_filled(rect, color)
                arcade.draw_rect_outline(rect, arcade.color.BLACK, 1)
        self.player_list.draw()
        self.pickup_list.draw()
        self.dropoff_list.draw()
        self.draw_popup_pedido()


    def on_key_press(self, key, modifiers):
        if getattr(self, 'mostrar_popup_puntajes', False):
            # No hacer nada mientras el popup está abierto
            return
        if getattr(self, 'popup_cargar_activo', False):
            # Mientras está el popup de cargar, sólo aceptamos 1/2/3 o ESC
            if key == arcade.key.ESCAPE:
                self.popup_cargar_activo = False
                return
            if key in (arcade.key.KEY_1, arcade.key.KEY_2, arcade.key.KEY_3):
                mapping = {
                    arcade.key.KEY_1: 1,
                    arcade.key.KEY_2: 2,
                    arcade.key.KEY_3: 3
                }
                slot = mapping.get(key)
                if slot:
                    self.cargar_de_slot(slot)
                return
            return
        if getattr(self, 'popup_guardar_activo', False):
            # Mientras está el popup de guardar, sólo aceptamos 1/2/3 o ESC
            if key == arcade.key.ESCAPE:
                self.popup_guardar_activo = False
                return
            if key in (arcade.key.KEY_1, arcade.key.KEY_2, arcade.key.KEY_3):
                # Arcade define KEY_1 etc. Convertimos a número
                mapping = {
                    arcade.key.KEY_1: 1,
                    arcade.key.KEY_2: 2,
                    arcade.key.KEY_3: 3
                }
                slot = mapping.get(key)
                if slot:
                    self.guardar_en_slot(slot)
                return
            return
        if self.nombre_popup_activo:
            if key == arcade.key.ENTER:
                self.nombre_popup_activo = False
                self.player_sprite.nombre = self.nombre_jugador if self.nombre_jugador else "Jugador"
            elif key == arcade.key.BACKSPACE:
                self.nombre_jugador = self.nombre_jugador[:-1]
            # Solo letras, números y espacio
            elif 32 <= key <= 126 and len(self.nombre_jugador) < 16:
                self.nombre_jugador += chr(key)
            return
        if key == arcade.key.P:
            self.cargar_y_mostrar_puntajes()
            return
        if key == arcade.key.L:
            self.mostrar_popup_cargar()
            return
        if key == arcade.key.G:
            self.mostrar_popup_guardar()
            return
        if key in (arcade.key.UP, arcade.key.DOWN, arcade.key.LEFT, arcade.key.RIGHT):
            self.active_direction = key
        self.try_move()
    def on_key_release(self, key, modifiers):
        # Cierra popup de puntajes con ESC
        if getattr(self, 'mostrar_popup_puntajes', False):
            if key == arcade.key.ESCAPE:
                self.mostrar_popup_puntajes = False
            return
        # Popup pedido
        if self.mostrar_pedido and self.pedido_actual:
            if key == arcade.key.A: 
                pedido = self.pedido_actual
                print(f"Pedido {pedido.id} aceptado")
                self.pedidos_activos[pedido.id] = pedido 
                pickup_x, pickup_y = self.celda_a_pixeles(*pedido.coord_recoger)
                dropoff_x, dropoff_y = self.celda_a_pixeles(*pedido.coord_entregar)
                self.crear_pedido(pickup_x, pickup_y, dropoff_x, dropoff_y, pedido.id)
                self.mostrar_pedido = False
                self.pedido_actual = None
            elif key == arcade.key.R:  
                print(f"Pedido {self.pedido_actual.id} rechazado")
                self.mostrar_pedido = False
                self.pedido_actual = None
        if self.active_direction == key:
            self.active_direction = None

    def try_move(self):
        if self.moving or self.active_direction is None or not self.player_sprite.puede_moverse():
            if not self.player_sprite.puede_moverse():
                print("¡Agotado! Recupera resistencia al 30% para moverte.")
            return
        new_row = self.player_sprite.row
        new_col = self.player_sprite.col
        if self.active_direction == arcade.key.UP:
            new_row -= 1
            if self.player_sprite.scale_x > 0:
                self.player_sprite.angle = 270
            else:
                self.player_sprite.angle = 90
        elif self.active_direction == arcade.key.DOWN:
            new_row += 1
            if self.player_sprite.scale_x > 0:
                self.player_sprite.angle = 90
            else:
                self.player_sprite.angle = 270
        elif self.active_direction == arcade.key.LEFT:
            new_col -= 1
            self.player_sprite.angle = 0
            self.player_sprite.scale_x = -abs(self.player_sprite.scale_x)
        elif self.active_direction == arcade.key.RIGHT:
            new_col += 1
            self.player_sprite.angle = 0
            self.player_sprite.scale_x = abs(self.player_sprite.scale_x)
        if (0 <= new_row < ROWS and
            0 <= new_col < COLS and
            mapa[new_row][new_col] != "B"):
            self.target_row = new_row
            self.target_col = new_col
            self.target_x = (new_col * CELL_SIZE + CELL_SIZE // 2) * self.scale_x
            self.target_y = (height * CELL_SIZE - (new_row * CELL_SIZE + CELL_SIZE // 2)) * self.scale_y
            self.moving = True

    def celda_a_pixeles(self, row, col):
        x = (col * CELL_SIZE + CELL_SIZE // 2) * self.scale_x
        y = (height * CELL_SIZE - (row * CELL_SIZE + CELL_SIZE // 2)) * self.scale_y
        return x, y
    
    def crear_pedido(self, pickup_x, pickup_y, dropoff_x, dropoff_y, pedido_id):
        pickup_sprite = arcade.Sprite("assets/pickup.png", scale=0.8)
        pickup_sprite.center_x = pickup_x
        pickup_sprite.center_y = pickup_y
        pickup_sprite.pedido_id = pedido_id
        self.pickup_list.append(pickup_sprite)
        dropoff_sprite = arcade.Sprite("assets/dropoff.png", scale=0.8)
        dropoff_sprite.center_x = dropoff_x
        dropoff_sprite.center_y = dropoff_y
        dropoff_sprite.pedido_id = pedido_id
        self.dropoff_list.append(dropoff_sprite)

    def cargar_pedidos(self):
        response = requests.get(f"{BASE_URL}/city/jobs").json()
        jobs = response.get("data", [])
        for p in jobs:
            pedido_obj = Pedido(
                id=p["id"],
                peso=p["weight"],
                deadline=p["deadline"],
                pago=p["payout"],
                prioridad=p.get("priority", 0),
                coord_recoger=p["pickup"],
                coord_entregar=p["dropoff"]
            )        
            self.pedidos_dict[pedido_obj.id] = pedido_obj
            self.pedidos_pendientes.append(pedido_obj)

    def on_update(self, delta_time):
        if self.total_time > 0:
            self.total_time -= delta_time
            if self.total_time <= 0:
                self.guardar_puntaje_si_termina()
                self.total_time = 0
                print("¡El tiempo se ha agotado! Fin del juego.")
                self.close()
        # --- Clima dinámico ---
        if self.transicion_clima.get('activa', False):
            t = self.transicion_clima['t'] + delta_time
            dur = self.transicion_clima['duracion']
            prog = min(t / dur, 1.0)
            ini = self.transicion_clima['inicio']
            fin = self.transicion_clima['fin']
            # Interpolación lineal
            intensidad = ini['intensidad'] + (fin['intensidad'] - ini['intensidad']) * prog
            mult = ini['multiplicador'] + (fin['multiplicador'] - ini['multiplicador']) * prog
            self.clima.condicion = fin['condicion'] if prog >= 1.0 else ini['condicion']
            self.clima.intensidad = intensidad
            self.clima.multiplicadorVelocidad = mult
            if prog >= 1.0:
                # Fin de transición: setea clima final completo
                self.clima.reiniciar(fin['condicion'], fin['intensidad'], fin['duracion'], fin['multiplicador'])
                self.transicion_clima['activa'] = False
            else:
                self.transicion_clima['t'] = t
        else:
            if self.clima.actualizar(delta_time):
                self.cambiar_clima()
            self.player_sprite.actualizar_resistencia(delta_time, self.moving, self.player_sprite.peso_total, self.clima.condicion, self.clima.intensidad)

        if not self.player_sprite.puede_moverse() and self.moving:
            self.moving = False
            self.player_sprite.center_x = self.target_x  # Detiene en la posición actual
            self.player_sprite.center_y = self.target_y
            self.player_sprite.row = self.target_row
            self.player_sprite.col = self.target_col
            print("¡Agotado! Descansando hasta recuperar 30% de resistencia.")



        if self.moving:
            dx = self.target_x - self.player_sprite.center_x
            dy = self.target_y - self.player_sprite.center_y
            dist = (dx ** 2 + dy ** 2) ** 0.5
            # Ajusta la velocidad base por el multiplicador del clima y la intensidad
            mult_base = self.clima.multiplicadorVelocidad
            intensidad = self.clima.intensidad
            if self.clima.condicion == "clear":
                mult_final = mult_base
            else:
                # A mayor intensidad, más lento (hasta 50% extra)
                mult_final = mult_base * (1 - intensidad * 0.5)
                mult_final = max(mult_final, 0.1)
            velocidad_actual = self.move_speed * mult_final
            if dist < velocidad_actual:
                self.player_sprite.center_x = self.target_x
                self.player_sprite.center_y = self.target_y
                self.player_sprite.row = self.target_row
                self.player_sprite.col = self.target_col
                self.moving = False
                self.try_move()
            else:
                self.player_sprite.center_x += velocidad_actual * dx / dist
                self.player_sprite.center_y += velocidad_actual * dy / dist
        pickups_hit = arcade.check_for_collision_with_list(self.player_sprite, self.pickup_list)
        for pickup in pickups_hit:
            pedido_obj = self.pedidos_dict[pickup.pedido_id]
            print(f"Se recolectó el pedido {pickup.pedido_id}")
            self.player_sprite.pickup(pedido_obj, datetime.now())
            pickup.remove_from_sprite_lists()
        dropoffs_hit = arcade.check_for_collision_with_list(self.player_sprite, self.dropoff_list)
        for dropoff in dropoffs_hit:
            pedido_obj = self.pedidos_dict.get(dropoff.pedido_id)
            if not pedido_obj:
                continue
            if self.player_sprite.inventario.buscar_pedido(pedido_obj.id):
                print(f"Se entregó el pedido {dropoff.pedido_id}")
                self.player_sprite.dropoff(pedido_obj.id, datetime.now())
                dropoff.remove_from_sprite_lists()
            else:
                print(f"No se puede entregar {dropoff.pedido_id}, no está en el inventario.")

        self.tiempo_global += delta_time
        if not self.mostrar_pedido and self.pedidos_pendientes:
            if self.tiempo_global - self.tiempo_ultimo_popup >= self.intervalo_popup:
                self.pedido_actual = self.pedidos_pendientes.pop(0)
                self.mostrar_pedido = True
                self.tiempo_ultimo_popup = self.tiempo_global


        


if __name__ == "__main__":
    MapaWindow()
    arcade.run()
