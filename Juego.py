import requests
import arcade
import random
import pyglet
from datetime import datetime
import Inventario
from Pedido import Pedido
from Repartidor import Repartidor
from Clima import Clima
from MarkovClima import MarkovClima
from Resistencia import Resistencia
import math
from datetime import datetime, timezone
import os
import json
import pickle
import heapq

CELL_SIZE = 50
BASE_URL = "https://tigerds-api.kindflower-ccaf48b6.eastus.azurecontainerapps.io"

# --- función para cargar backup si falla el API ---
def cargar_backup():
    ruta = os.path.join("data", "backup.json")
    if os.path.exists(ruta):
        with open(ruta, "r", encoding="utf-8") as f:
            return json.load(f)
    return None

# --- city/map ---
try:
    city_data = requests.get(f"{BASE_URL}/city/map", timeout=5).json()
except Exception as e:
    print(f"[WARN] city/map API failed: {e}")
    backup = cargar_backup()
    if backup and "city_map" in backup:
        city_data = backup["city_map"]
    else:
        raise RuntimeError("No se pudo obtener city/map ni backup.json")

data = city_data.get("data", {})
tiles = data.get("tiles", [])
height = data.get("height", 0)
width = data.get("width", 0)
mapa = tiles
ROWS = len(mapa)
COLS = len(mapa[0])

TIEMPO_PARA_RECOGER = 30

SURFACE_WEIGHTS = {
    "C": 1.0,   # Calle / camino
    "P": 0.5,  # Parque (más lento)
    "B": 0.0,   # Edificio (intransitable, ya se bloquea antes)
}


# --- Clima y Markov ---
try:
    weather_data = requests.get(f"{BASE_URL}/city/weather?city=TigerCity&mode=seed", timeout=5).json()
except Exception as e:
    print(f"[WARN] weather API failed: {e}")
    backup = cargar_backup()
    if backup and "weather" in backup:
        weather_data = backup["weather"]
    else:
        raise RuntimeError("No se pudo obtener weather ni backup.json")

weather_info = weather_data.get("data", {})
initial_weather = weather_info.get("initial", {})

conditions = weather_info.get("conditions", [])
transition = weather_info.get("transition", {})

# Normaliza nombres de condiciones
cond_names = [c["condition"] if isinstance(c, dict) and "condition" in c 
              else c for c in conditions]

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

BACKUP_DATA = {
    "city_map": city_data,
    "weather": weather_data,
    "jobs": None
}

def save_backup():
    """Guarda BACKUP_DATA en data/backup.json."""
    try:
        os.makedirs("data", exist_ok = True)
        ruta = os.path.join("data", "backup.json")
        with open(ruta, "w", encoding = "utf-8") as f:
            json.dump(BACKUP_DATA, f, ensure_ascii = False, indent = 2)
    except Exception as e:
        print(f"[WARN] No se pudo escribir backup.json: {e}")

class MapaWindow(arcade.Window):
    def __init__(self):
        self.hora_inicio_juego_utc = datetime.now(timezone.utc)
        self.meta_ingresos = 1500 
        self.meta_cumplida = False
        
        self.mostrar_config_bot_popup = True  
        self.config_bot_opciones = ["Jugar CON Bot", "Jugar SIN Bot"]
        self.config_bot_seleccion = 0  
        self.npc_habilitado = True  
        
        self.mostrar_meta_popup = False  
        self.mostrar_inventario_popup = False
        self.inventario_seleccion_idx = 0  
        self.pedido_activo_para_entrega = None
        self.lista_inventario_visible = [] 
        self.modo_orden = 'prioridad'
        self.notificaciones = []
        self.nombre_popup_activo = False
        self.nombre_jugador = ""
        self.active_direction = None
        self.window_width = 800
        self.window_height = 600
        self.hud_height = 100
        icon1 = pyglet.image.load("assets/repartidor.png")
        icon2 = pyglet.image.load("assets/repartidor.png")
        super().__init__(self.window_width, self.window_height, "Courier Quest",fixed_frame_cap=60, )
        self.set_icon(icon1, icon2) 
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
        # Inicialización para lógica de fin de juego
        self.game_over = False
        self.victoria = False
        self.end_message = ""
        self.end_stats = []
        self.pedidos_completados = 0
        self.undo_stack = []  # Stack de estados para deshacer (lista de dicts)
        self.undo_limit = 10  # Máximo N pasos a deshacer (ajustable)
        self.ultimo_movimiento_tiempo = 0  # Para guardar undo solo después de movimientos


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
        self.move_speed = 150
        self.player_list.append(self.player_sprite)

        # --- NUEVO: crear segundo jugador (NPC) estático ---
        self.npc_list = arcade.SpriteList()
        # Busca una celda libre distinta a la del jugador
        while True:
            npc_row = random.randint(0, ROWS - 1)
            npc_col = random.randint(0, COLS - 1)
            if mapa[npc_row][npc_col] != "B" and not (npc_row == self.player_sprite.row and npc_col == self.player_sprite.col):
                break
        self.npc_sprite = Repartidor("assets/repartidor.png", scale=0.8)  # usa mismo asset por simplicidad
        self.npc_sprite.resistencia_obj = Resistencia()
        # Inicializa coordenadas/estado del NPC
        self.npc_sprite.row = npc_row
        self.npc_sprite.col = npc_col
        self.npc_sprite.inventario = Inventario.Inventario()
        self.npc_sprite.center_x, self.npc_sprite.center_y = self.celda_a_pixeles(npc_row, npc_col)
        # Marca opcional para identificarlo
        self.npc_sprite.nombre = "NPC"
        self.npc_sprite.ingresos = 0
        self.npc_sprite.reputacion = 70  # Igual que el jugador inicial
        if not hasattr(self.npc_sprite, "peso_total"):
            self.npc_sprite.peso_total = 0
        # No mover ni actualizar: sprite estático
        self.npc_list.append(self.npc_sprite)

        # --- NUEVO: estado para popup de dificultad ---
        self.difficulty_popup_active = False
        self.difficulty_options = ["Fácil", "Normal", "Difícil"]
        self.difficulty_selected_idx = 1  # por defecto 'Normal'
        self.npc_difficulty = None
        self.npc_moving = False  # Para controlar si el NPC se está moviendo (para resistencia)
        self.npc_pedido_activo = None  # Pedido actual del NPC
        self.npc_action_timer = 0  # Temporizador para acciones periódicas
        # Ruta/objetivo del NPC para pathfinding
        self.npc_path = []
        self.npc_goal = None
        # Movimiento suave del NPC (igual a la velocidad del jugador)
        self.npc_move_speed = self.move_speed
        self.npc_target_row = npc_row
        self.npc_target_col = npc_col
        self.npc_target_x = self.npc_sprite.center_x
        self.npc_target_y = self.npc_sprite.center_y
        self.npc_smooth_moving = False
        self.npc_spriteRow = npc_row
        self.npc_spriteCol = npc_col

    def remover_npc(self):
        """Remueve el NPC del juego cuando se elige jugar sin bot"""
        if hasattr(self, 'npc_sprite') and self.npc_sprite:
            self.npc_sprite.remove_from_sprite_lists()
            self.npc_sprite = None
        
        # Limpiar variables del NPC
        self.npc_pedido_activo = None
        self.npc_path = []
        self.npc_goal = None
        self.npc_smooth_moving = False
        self.npc_moving = False

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

        ancho, alto = 400, 220
        x = self.window_width // 2 - ancho // 2
        y = self.window_height // 2 - alto // 2

        arcade.draw_lbwh_rectangle_filled(x, y, ancho, alto, arcade.color.DARK_SLATE_GRAY)
        arcade.draw_lbwh_rectangle_outline(x, y, ancho, alto, arcade.color.WHITE, 3)
        
        arcade.draw_text("Cargar Partida",
                         x + ancho / 2, y + alto - 45,
                         arcade.color.GOLD, 22, bold=True, anchor_x="center")

        arcade.draw_text("¿Qué slot deseas cargar?",
                         x + ancho / 2, y + alto - 90,
                         arcade.color.WHITE, 16, anchor_x="center")

        slot_button_width = 80
        slot_button_height = 50
        
        start_x_buttons = x + ancho / 2 - (slot_button_width * 1.5 + 20)

        for i in range(1, 4): 
            button_x = start_x_buttons + (i - 1) * (slot_button_width + 20)
            button_y = y + 70 
            arcade.draw_lbwh_rectangle_filled(button_x, button_y, slot_button_width, slot_button_height, arcade.color.DARK_BLUE)
            arcade.draw_lbwh_rectangle_outline(button_x, button_y, slot_button_width, slot_button_height, arcade.color.LIGHT_GRAY, 2)
            arcade.draw_text(str(i),
                             button_x + slot_button_width / 2, button_y + slot_button_height / 2,
                             arcade.color.WHITE, 20, bold=True, anchor_x="center", anchor_y="center")

        arcade.draw_text("Presiona [1], [2], [3] o [ESC] para cancelar",
                         x + ancho / 2, y + 25,
                         arcade.color.LIGHT_GRAY, 12, anchor_x="center")

    def cargar_de_slot(self, slot:int):
        """Placeholder de carga real. Aquí se implementaría la lógica de restaurar el estado."""
        print(f"[DEBUG] Cargando partida de slot {slot} (placeholder)")
        self.slot_cargar_seleccionado = slot
        self.popup_cargar_activo = False

    def cargar_y_mostrar_puntajes(self):
        ruta = os.path.join('data', 'puntajes.json')
        if os.path.exists(ruta):
            with open(ruta, 'r', encoding = 'utf-8') as f:
                try:
                    puntajes = json.load(f)
                except Exception:
                    puntajes = []
        else:
            puntajes = []
        # Ordena de mayor a menor
        puntajes.sort(key = lambda p: p['score'], reverse=True)
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

        ancho, alto = 400, 220
        x = self.window_width // 2 - ancho // 2
        y = self.window_height // 2 - alto // 2
        arcade.draw_lbwh_rectangle_filled(x, y, ancho, alto, arcade.color.DARK_BLUE_GRAY)
        arcade.draw_lbwh_rectangle_outline(x, y, ancho, alto, arcade.color.WHITE, 3)
        
        arcade.draw_text("Guardar Partida",
                         x + ancho / 2, y + alto - 45,
                         arcade.color.GOLD, 22, bold=True, anchor_x="center")

        arcade.draw_text("¿En qué slot deseas guardar?",
                         x + ancho / 2, y + alto - 90,
                         arcade.color.WHITE, 16, anchor_x="center")

        slot_button_width = 80
        slot_button_height = 50
        
        
        start_x_buttons = x + ancho / 2 - (slot_button_width * 1.5 + 20) 

        for i in range(1, 4): 
            button_x = start_x_buttons + (i - 1) * (slot_button_width + 20)
            button_y = y + 70 
            button_color = arcade.color.BLUE_BELL if self.slot_seleccionado == i else arcade.color.DARK_BLUE
            outline_color = arcade.color.YELLOW if self.slot_seleccionado == i else arcade.color.LIGHT_GRAY
            
            arcade.draw_lbwh_rectangle_filled(button_x, button_y, slot_button_width, slot_button_height, button_color)
            arcade.draw_lbwh_rectangle_outline(button_x, button_y, slot_button_width, slot_button_height, outline_color, 2)
            
            arcade.draw_text(str(i), 
                             button_x + slot_button_width / 2, button_y + slot_button_height / 2,
                             arcade.color.WHITE, 20, bold=True, anchor_x="center", anchor_y="center")

        arcade.draw_text("Presiona [ESC] para cancelar",
                         x + ancho / 2, y + 25,
                         arcade.color.LIGHT_GRAY, 12, anchor_x="center")
    
    def guardar_en_slot(self, slot:int):
        """Guarda el estado actual del juego en binario usando pickle."""
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
                # Inventario: lista de IDs de pedidos
                'inventario': [nodo.pedido.id for nodo in self._iterar_inventario()],
                'racha_entregas': getattr(self.player_sprite, 'racha_entregas_sin_penalizacion', 0),
                'primera_tardanza': getattr(self.player_sprite, 'primera_tardanza_del_dia_usada', False),
            },
            'clima': {
                'condicion': self.clima.condicion,
                'intensidad': self.clima.intensidad,
                'tiempoRestante': self.clima.tiempoRestante,
                'multiplicadorVelocidad': self.clima.multiplicadorVelocidad,
            },
            'pedidos_activos': list(self.pedidos_activos.keys()),
            'pedidos_pendientes': [p.id for p in self.pedidos_pendientes],
            'pedido_current': self.pedido_actual.id if self.pedido_actual else None,
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
        self.undo_stack.clear()

    def _iterar_inventario(self):
        """Itera sobre el inventario del jugador y retorna nodos."""
        nodo = self.player_sprite.inventario.inicio
        while nodo:
            yield nodo
            nodo = nodo.siguiente

    def cargar_de_slot(self, slot:int):
        """Carga el estado guardado en binario y restaura los atributos principales."""
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
        self.player_sprite.racha_entregas_sin_penalizacion = player.get('racha_entregas', 0)
        self.player_sprite.primera_tardanza_del_dia_usada = player.get('primera_tardanza', False)

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
        self.undo_stack.clear()  # Limpia undo al cargar (nuevo estado)

    def _restaurar_inventario(self, lista_ids):
        """Reconstruye el inventario del jugador desde una lista de IDs."""
        inv = self.player_sprite.inventario
        inv.inicio = None
        inv._peso_total = 0  # Asumiendo que _peso_total es el atributo interno; ajusta si es diferente
        for pid in lista_ids:
            pedido = self.pedidos_dict.get(pid)
            if pedido:
                inv.agregar_pedido(pedido)
        # Actualiza cantidad si es necesario (asumiendo que Inventario tiene _cantidad)
        inv._cantidad = len(lista_ids)  # Opcional, si usas un atributo _cantidad

    def guardar_estado_actual(self):
        """Guarda un snapshot liviano del estado actual para undo.
        Similar a guardar_en_slot, pero sin sprites pesados."""

        estado = {
            'total_time': getattr(self, 'total_time', 0),
            'tiempo_global': getattr(self, 'tiempo_global', 0),
            'player': {
                'row': self.player_sprite.row,
                'col': self.player_sprite.col,
                'center_x': self.player_sprite.center_x,
                'center_y': self.player_sprite.center_y,
                'resistencia': self.player_sprite.get_resistencia_actual(),
                'nombre': getattr(self.player_sprite, 'nombre', ''),
                'ingresos': getattr(self.player_sprite, 'ingresos', 0),
                'reputacion': getattr(self.player_sprite, 'reputacion', 1),
                'inventario': [nodo.pedido.id for nodo in self._iterar_inventario()],
                'racha_entregas': getattr(self.player_sprite, 'racha_entregas_sin_penalizacion', 0),
                'primera_tardanza': getattr(self.player_sprite, 'primera_tardanza_del_dia_usada', False),
            },
            'clima': {
                'condicion': self.clima.condicion,
                'intensidad': self.clima.intensidad,
                'tiempoRestante': self.clima.tiempoRestante,
                'multiplicadorVelocidad': self.clima.multiplicadorVelocidad,
            },
            'pedidos_activos': list(self.pedidos_activos.keys()),
            'pedidos_pendientes': [p.id for p in self.pedidos_pendientes],
            'pedido_current': self.pedido_actual.id if self.pedido_actual else None,
            'pedido_activo_entrega': self.pedido_activo_para_entrega.id if self.pedido_activo_para_entrega else None,
            'pedidos_completados': self.pedidos_completados,
            # No guardamos pickups/dropoffs completos (se recrean en restaurar)
        }

        # Serializar a bytes y apilar para undo
        snapshot = pickle.dumps(estado, protocol=pickle.HIGHEST_PROTOCOL)

        # Asegurar estructura de la pila de undo y el límite
        if not hasattr(self, 'undo_stack') or self.undo_stack is None:
            self.undo_stack = []
        if not hasattr(self, 'undo_limit') or not isinstance(self.undo_limit, int) or self.undo_limit <= 0:
            self.undo_limit = 20  # valor por defecto razonable

        self.undo_stack.append(snapshot)

        # Limitar a N elementos (elimina el más antiguo)
        if len(self.undo_stack) > self.undo_limit:
            self.undo_stack.pop(0)
    
    def deshacer_paso(self):
        """Restaura el estado anterior desde el stack de undo.
        Recrear pickups/dropoffs basados en pedidos."""
        if not self.undo_stack:
            self.agregar_notificacion("No hay pasos para deshacer.", arcade.color.BLACK_OLIVE)
            return

        try:
            # Obtener y deserializar último estado
            ultimo_snapshot = self.undo_stack.pop()
            estado = pickle.loads(ultimo_snapshot)

            # Restaurar atributos principales (similar a cargar_de_slot)
            self.total_time = estado.get('total_time', self.total_time)
            self.tiempo_global = estado.get('tiempo_global', self.tiempo_global)
            self.pedidos_completados = estado.get('pedidos_completados', 0)
            self.meta_cumplida = estado.get('meta_cumplida', False)
        
            player = estado.get('player', {})
            self.player_sprite.row = player.get('row', self.player_sprite.row)
            self.player_sprite.col = player.get('col', self.player_sprite.col)
            self.player_sprite.center_x = player.get('center_x', self.player_sprite.center_x)
            self.player_sprite.center_y = player.get('center_y', self.player_sprite.center_y)
            self.player_sprite.resistencia_obj.set_resistencia(player.get('resistencia', 100))
            self.player_sprite.nombre = player.get('nombre', getattr(self.player_sprite, 'nombre', ''))
            self.player_sprite.ingresos = player.get('ingresos', getattr(self.player_sprite, 'ingresos', 0))
            self.player_sprite.reputacion = player.get('reputacion', getattr(self.player_sprite, 'reputacion', 1))
            self.player_sprite.racha_entregas_sin_penalizacion = player.get('racha_entregas', 0)
            self.player_sprite.primera_tardanza_del_dia_usada = player.get('primera_tardanza', False)

            # Restaurar inventario
            self._restaurar_inventario(player.get('inventario', []))

            # Restaurar clima
            clima = estado.get('clima', {})
            self.clima.condicion = clima.get('condicion', self.clima.condicion)
            self.clima.intensidad = clima.get('intensidad', self.clima.intensidad)
            self.clima.tiempoRestante = clima.get('tiempoRestante', self.clima.tiempoRestante)
            self.clima.multiplicadorVelocidad = clima.get('multiplicadorVelocidad', self.clima.multiplicadorVelocidad)

            # Restaurar pedidos
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
        except Exception as e:
            print(f"[ERROR] Fallo en cargar_de_slot: {e}")
        finally:
            self.slot_cargar_seleccionado = slot # type: ignore
            self.popup_cargar_activo = False
            self.undo_stack.clear()  # Limpia undo al cargar (nuevo estado)

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

    def celda_a_pixeles(self, row, col):
        x = (col * CELL_SIZE + CELL_SIZE // 2) * self.scale_x
        y = (height * CELL_SIZE - (row * CELL_SIZE + CELL_SIZE // 2)) * self.scale_y
        return x, y

    def draw_hud(self):
        """Dibuja el HUD completo en la parte superior"""
        hud_y = self.window_height - self.hud_height
        
        arcade.draw_lbwh_rectangle_filled(
            0, hud_y, self.window_width, self.hud_height,
            arcade.color.WHITE_SMOKE  
        )
        arcade.draw_lbwh_rectangle_outline(
            0, hud_y, self.window_width, self.hud_height,
            arcade.color.BLACK, 3 
        )
    
        pedidos = []
        nodo = self.player_sprite.inventario.inicio
        while nodo:
            pedidos.append(str(nodo.pedido.id))
            nodo = nodo.siguiente
        pedidos_text = f"Pedidos: {', '.join(pedidos) if pedidos else 'Ninguno'}"
        peso_text = f"Peso: {self.player_sprite.inventario.peso_total():.1f}/{self.player_sprite.inventario.peso_maximo:.1f}"
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
        
        resistencia_actual = self.player_sprite.get_resistencia_actual()
        resistencia_text = f"Resistencia:        {int(resistencia_actual)}  /100"
        arcade.draw_text(resistencia_text, hud_padding, stats_y - 70, arcade.color.BLACK, hud_font_size, anchor_y="top")
        # Barra de resistencia
        bar_x = hud_padding
        bar_y = stats_y - 85
        bar_width = 100
        bar_height = 10
        arcade.draw_lbwh_rectangle_filled(bar_x, bar_y, bar_width, bar_height, arcade.color.GRAY)
        
        fill_color = arcade.color.GREEN if resistencia_actual > 30 else (arcade.color.YELLOW if resistencia_actual > 10 else arcade.color.RED)
        fill_width = (resistencia_actual / 100.0) * bar_width
        arcade.draw_lbwh_rectangle_filled(bar_x, bar_y, fill_width, bar_height, fill_color)
        arcade.draw_lbwh_rectangle_outline(bar_x, bar_y, bar_width, bar_height, arcade.color.BLACK, 1)


    # Carteles de controles (centro)
        cartel_y = hud_y + self.hud_height - hud_padding - 5
        arcade.draw_text(
            "[I] para abrir inventario y seleccionar!",
            self.window_width // 2, cartel_y-60,
            arcade.color.DARK_PINK, hud_font_size + 2,
            anchor_x="center", anchor_y="top"
        )
        arcade.draw_text(
            "[P] para ver puntuaciones!",
            self.window_width // 2, cartel_y,
            arcade.color.DARK_BLUE, hud_font_size + 2,
            anchor_x="center", anchor_y="top"
        )
        arcade.draw_text(
            "[G] para guardar partida!",
            self.window_width // 2, cartel_y - 22,
            arcade.color.DARK_GREEN, hud_font_size + 2,
            anchor_x="center", anchor_y="top"
        )
        arcade.draw_text(
            "[L] para cargar partida!",
            self.window_width // 2, cartel_y - 44,
            arcade.color.DARK_ORANGE, hud_font_size + 2,
            anchor_x="center", anchor_y="top"
        )
    
        #Timer
        minutes = int(self.total_time) // 60
        seconds = int(self.total_time) % 60
        timer_text = f"Tiempo: {minutes:02d}:{seconds:02d}"
        timer_x = self.window_width - hud_padding - 80  
        arcade.draw_text(timer_text, timer_x, stats_y, arcade.color.RED, hud_font_size + 5, anchor_x="center", anchor_y="top")
    
    #Clima
        clima_x = self.window_width - hud_padding - 70 
        clima_y = hud_y + hud_padding
        arcade.draw_text(
            clima_text,
            clima_x, clima_y,
            arcade.color.BLACK, hud_font_size,
            anchor_x = "center", anchor_y = "bottom",
            multiline = True, width=140
        )

    def draw_inventario_popup(self):
        """Dibuja el menú de selección de pedidos a partir de una lista temporal."""
        if not self.mostrar_inventario_popup:
            return

        ancho, alto = 500, 350
        x = self.window_width // 2 - ancho // 2
        y = self.window_height // 2 - alto // 2
        
        arcade.draw_lbwh_rectangle_filled(x, y, ancho, alto, arcade.color.DARK_SLATE_GRAY)
        arcade.draw_lbwh_rectangle_outline(x, y, ancho, alto, arcade.color.WHITE, 3)
        
        titulo = f"Inventario de Pedidos (Orden: {self.modo_orden.capitalize()})"
        arcade.draw_text(titulo, x + ancho / 2, y + alto - 30,
                         arcade.color.WHITE, 20, anchor_x="center")
        arcade.draw_text("[↑↓] Navegar  [ENTER] Seleccionar [C] Cancelar [I] Cerrar", x + ancho / 2, y + alto - 60,
                         arcade.color.LIGHT_GRAY, 12, anchor_x="center")
        arcade.draw_text("[D] Ordenar por Deadline  [Z] Ordenar por Prioridad", x + ancho / 2, y + 20,
                         arcade.color.CYAN, 12, anchor_x="center")

        if not self.lista_inventario_visible:
            arcade.draw_text("No tienes pedidos.", x + ancho/2, y + alto/2,
                             arcade.color.GRAY, 16, anchor_x="center")
            return

        for i, pedido in enumerate(self.lista_inventario_visible):
            deadline_str = pedido.deadline.strftime('%Y-%m-%d %H:%M')
            linea_texto = f"ID: {pedido.id} | Prioridad: {pedido.prioridad} | Deadline: {deadline_str}"
            color_texto = arcade.color.YELLOW if i == self.inventario_seleccion_idx else arcade.color.WHITE

            if i == self.inventario_seleccion_idx:
                arcade.draw_lbwh_rectangle_filled(x + 20, y + alto - 100 - i * 30 - 5, ancho - 40, 30, arcade.color.DARK_BLUE)
            
            arcade.draw_text(linea_texto, x + 30, y + alto - 100 - i * 30, color_texto, 14)


    def draw_popup_pedido(self):
        """Dibuja un popup de nuevo pedido mejorado, con más información y mejor diseño."""
        if self.mostrar_pedido and self.pedido_actual:
            ancho, alto = 450, 200
            x = self.window_width // 2 - ancho // 2
            y = (self.window_height - self.hud_height) // 2 - alto // 2
            
            arcade.draw_lbwh_rectangle_filled(x, y, ancho, alto, arcade.color.DARK_SLATE_GRAY)
            arcade.draw_lbwh_rectangle_outline(x, y, ancho, alto, arcade.color.WHITE, 3)
            
            arcade.draw_text(f"NUEVO PEDIDO: {self.pedido_actual.id}",
                             x + ancho / 2, y + alto - 35,
                             arcade.color.GOLD, 18, bold=True, anchor_x="center")

            deadline_contador = self.pedido_actual.deadline_contador
            minutos = int(deadline_contador) // 60
            segundos = int(deadline_contador) % 60
            deadline_texto = f"{minutos:02d}:{segundos:02d}"

            info_y = y + alto - 80
            arcade.draw_text(f"Peso:", x + 40, info_y, arcade.color.WHITE, 14)
            arcade.draw_text(f"{self.pedido_actual.peso} kg", x + 150, info_y, arcade.color.LIGHT_GRAY, 14)
            
            arcade.draw_text(f"Pago:", x + 40, info_y - 25, arcade.color.WHITE, 14)
            arcade.draw_text(f"${self.pedido_actual.pago:.2f}", x + 150, info_y - 25, arcade.color.GREEN_YELLOW, 14, bold=True)
            
            arcade.draw_text(f"Deadline:", x + 250, info_y, arcade.color.WHITE, 14)
            arcade.draw_text(deadline_texto, x + 350, info_y, arcade.color.ORANGE_RED, 14, bold=True)
            
            arcade.draw_text(f"Prioridad:", x + 250, info_y - 25, arcade.color.WHITE, 14)
            arcade.draw_text(f"{self.pedido_actual.prioridad}", x + 350, info_y - 25, arcade.color.LIGHT_GRAY, 14)

            arcade.draw_lbwh_rectangle_filled(x + 50, y + 20, 150, 40, arcade.color.DARK_GREEN)
            arcade.draw_text("[A] Aceptar", x + 125, y + 40, arcade.color.WHITE, 16, anchor_x="center")

            arcade.draw_lbwh_rectangle_filled(x + ancho - 200, y + 20, 150, 40, arcade.color.DARK_RED)
            arcade.draw_text("[R] Rechazar", x + ancho - 125, y + 40, arcade.color.WHITE, 16, anchor_x="center")

    def draw_config_bot_popup(self):
        """Dibuja el popup de configuración del bot"""
        ancho, alto = 500, 350
        x = self.width // 2 - ancho // 2
        y = self.height // 2 - alto // 2
        
        # Fondo del popup
        arcade.draw_lbwh_rectangle_filled(x, y, ancho, alto, arcade.color.DARK_SLATE_GRAY)
        arcade.draw_lbwh_rectangle_outline(x, y, ancho, alto, arcade.color.WHITE, 3)
        
        # Título
        arcade.draw_text(
            "Configuración del Juego",
            x + ancho // 2, y + alto - 50,
            arcade.color.WHITE, 24,
            anchor_x="center", anchor_y="center", bold=True
        )
        
        arcade.draw_text(
            "¿Quieres competir contra un bot?",
            x + ancho // 2, y + alto - 100,
            arcade.color.CYAN, 18,
            anchor_x="center", anchor_y="center"
        )
        
        # Opciones
        for i, opcion in enumerate(self.config_bot_opciones):
            option_y = y + alto // 2 - (i * 60) + 20
            color = arcade.color.YELLOW if i == self.config_bot_seleccion else arcade.color.WHITE
            
            # Indicador de selección
            if i == self.config_bot_seleccion:
                arcade.draw_text("►", x + 120, option_y, arcade.color.YELLOW, 20, anchor_x="center")
            
            # Texto de la opción
            arcade.draw_text(opcion, x + 180, option_y, color, 20, anchor_x="left")
        
        # Descripción de la opción seleccionada
        descripcion = ""
        if self.config_bot_seleccion == 0:
            descripcion = "El bot competirá contigo por los mismos paquetes.\nPodrás elegir la dificultad del bot."
        else:
            descripcion = "Jugarás solo contra el tiempo.\nSin competencia adicional."
            
        arcade.draw_text(
            descripcion,
            x + ancho // 2, y + 80,
            arcade.color.LIGHT_GRAY, 14,
            anchor_x="center", anchor_y="center",
            multiline=True, width=ancho-40
        )
        
        # Instrucciones
        arcade.draw_text(
            "Usa ↑↓ para navegar, ENTER para confirmar",
            x + ancho // 2, y + 30,
            arcade.color.LIGHT_GRAY, 12,
            anchor_x="center", anchor_y="center"
        )

    def draw_popup_meta(self):
        ancho, alto = 600, 400
        x = self.width // 2 - ancho // 2
        y = self.height // 2 - alto // 2
        
        arcade.draw_lbwh_rectangle_filled(x, y, ancho, alto, arcade.color.DARK_SLATE_GRAY)
        arcade.draw_lbwh_rectangle_outline(x, y, ancho, alto, arcade.color.WHITE, 3)
        
        arcade.draw_text(
            "Bienvenido a Courier Quest",
            x + ancho // 2, y + alto - 50,
            arcade.color.WHITE, 22,
            anchor_x="center", anchor_y="center", bold=True
        )

        arcade.draw_text(
            f"Tu meta es alcanzar ${self.meta_ingresos} antes de que se agote el tiempo.",
            x + ancho // 2, y + alto - 90,
            arcade.color.CYAN, 16,
            anchor_x="center", anchor_y="center"
        )
        
        arcade.draw_text(
            "Reglas Principales",
            x + ancho // 2, y + alto - 140,
            arcade.color.WHITE, 16,
            anchor_x="center", anchor_y="center", bold=True
        )

        reglas_text = (
            "- La Reputación es clave: entrégala a tiempo para aumentarla.\n"
            "- Las entregas tardías, expiraciones o cancelaciones la reducirán.\n"
            "- ¡Cuidado! Si tu reputación baja de 20, pierdes la partida.\n"
            "- Usa [I] para ver tu inventario y seleccionar pedidos.\n"
            "- Usa [G] para guardar tu partida"
        )
        arcade.draw_text(
            reglas_text,
            x + ancho // 2, y + alto // 2 - 30,
            arcade.color.WHITE, 14,
            anchor_x="center", anchor_y="center",
            align="center", multiline=True, width=ancho - 60
        )
        
        arcade.draw_text(
            "Presiona [Enter] para empezar",
            x + ancho // 2, y + 40,
            arcade.color.LIGHT_GREEN, 16,
            anchor_x="center", anchor_y="center", bold=True
        )

        
    def agregar_notificacion(self, texto, color=arcade.color.WHITE):
        notificacion = {
            "texto": texto,
            "color": color,
            "tiempo_vida": 4.0, 
            "y_offset": 0
        }
        for n in self.notificaciones:
            n["y_offset"] += 30
            
        self.notificaciones.insert(0, notificacion) 

    def actualizar_notificaciones(self, delta_time):
        for notificacion in self.notificaciones[:]:
            notificacion["tiempo_vida"] -= delta_time
            if notificacion["tiempo_vida"] <= 0:
                self.notificaciones.remove(notificacion)
    
    def draw_notificaciones(self):
        start_x = 20
        start_y = self.window_height - self.hud_height - 40 

        for notificacion in self.notificaciones:
            duracion_total = 4.0 
            porcentaje_vida = notificacion["tiempo_vida"] / duracion_total
            alpha = int(255 * porcentaje_vida)
            alpha = max(0, min(255, alpha))
            color = (*notificacion["color"][:3], alpha)

            arcade.draw_text(
                notificacion["texto"],
                start_x,
                start_y - notificacion["y_offset"],
                color,
                font_size=16,
                bold=True
            )

    def draw_difficulty_popup(self):
        """Dibuja el popup de selección de dificultad para el NPC."""
        if not getattr(self, 'difficulty_popup_active', False):
            return
        ancho, alto = 420, 200
        x = self.window_width // 2 - ancho // 2
        y = self.window_height // 2 - alto // 2

        arcade.draw_lbwh_rectangle_filled(x, y, ancho, alto, arcade.color.DARK_SLATE_GRAY)
        arcade.draw_lbwh_rectangle_outline(x, y, ancho, alto, arcade.color.WHITE, 3)
        arcade.draw_text("Selecciona dificultad del NPC",
                         x + ancho / 2, y + alto - 40,
                         arcade.color.GOLD, 18, anchor_x="center", bold=True)

        # Opciones
        for i, opt in enumerate(self.difficulty_options):
            oy = y + alto - 90 - i * 36
            bg = arcade.color.DARK_BLUE if i == self.difficulty_selected_idx else arcade.color.DARK_GRAY
            outline = arcade.color.YELLOW if i == self.difficulty_selected_idx else arcade.color.LIGHT_GRAY
            arcade.draw_lbwh_rectangle_filled(x + 40, oy, ancho - 80, 30, bg)
            arcade.draw_lbwh_rectangle_outline(x + 40, oy, ancho - 80, 30, outline, 2)
            arcade.draw_text(f"{i+1}. {opt}", x + 60, oy + 15, arcade.color.WHITE, 14, anchor_x="left", anchor_y="center")

        arcade.draw_text("←/→ o ↑/↓ para navegar, [1-3] seleccionar, Enter confirmar, ESC cancelar",
                         x + ancho / 2, y + 18, arcade.color.LIGHT_GRAY, 10, anchor_x="center")

    def on_draw(self):
        self.clear()
        
        # PRIMERO: Popup de configuración del bot
        if getattr(self, 'mostrar_config_bot_popup', False):
            self.draw_config_bot_popup()
            return
        
        if self.game_over:
            self._draw_end_screen()
            return
        if self.mostrar_meta_popup:
            self.draw_popup_meta()
            return 
        if getattr(self, 'mostrar_popup_puntajes', False):
            self.draw_popup_puntajes()
            return
        if getattr(self, 'popup_cargar_activo', False):
            self.draw_popup_cargar()
            return
        if getattr(self, 'popup_guardar_activo', False):
            self.draw_popup_guardar()
            return
        if self.nombre_popup_activo:
            self.draw_nombre_popup()
            return
        # --- NUEVO: mostrar popup dificultad si está activo (después del nombre) ---
        if getattr(self, 'difficulty_popup_active', False):
            self.draw_difficulty_popup()
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
        # --- NUEVO: dibujar NPC (segundo jugador) solo si está habilitado ---
        if getattr(self, 'npc_habilitado', True) and hasattr(self, 'npc_sprite') and self.npc_sprite:
            self.npc_list.draw()
            # Dibuja etiqueta encima del NPC
            try:
                for npc in self.npc_list:
                    arcade.draw_text(getattr(npc, "nombre", ""), npc.center_x, npc.center_y + 24,
                                     arcade.color.BLACK, 12, anchor_x="center")
            except Exception:
                pass

        self.player_list.draw()
        self.pickup_list.draw()
        sprite_activo = None
        escala_original = 0.8 
        if self.pedido_activo_para_entrega:
            for sprite in self.dropoff_list:
                if sprite.pedido_id == self.pedido_activo_para_entrega.id:
                    sprite_activo = sprite
                    break
        if sprite_activo:
            pulso = 1.2 + math.sin(self.tiempo_global * 5) * 0.2
            sprite_activo.scale = escala_original * pulso
        self.dropoff_list.draw()
        if sprite_activo:
            sprite_activo.scale = escala_original

        self.draw_popup_pedido()
        self.draw_notificaciones()
        if self.mostrar_inventario_popup:
            self.draw_inventario_popup()
            return


    def restart_game(self):
        """Reinicia el juego reseteando todas las variables de estado a sus valores iniciales."""
        print("--- Reiniciando el juego ---")

        self.game_over = False
        self.victoria = False
        self.meta_cumplida = False
        
        self.total_time = 15 * 60 
        self.tiempo_global = 0.0
        
        self.pedidos_dict = {}
        self.pedidos_pendientes = []
        self.pedidos_activos = {}
        self.pickup_list = arcade.SpriteList()
        self.dropoff_list = arcade.SpriteList()

        self.pedido_actual = None
        self.mostrar_pedido = False
        self.pedido_activo_para_entrega = None
        
        self.player_sprite.reputacion = 70
        self.player_sprite.ingresos = 0
        self.player_sprite.inventario.inicio = None  
        self.player_sprite.inventario._cantidad = 0
        self.player_sprite.inventario._peso_total = 0.0
        self.player_sprite.resistencia_obj.set_resistencia(100) 

        # Vuelve a cargar los 5 pedidos originales desde la API o backup
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
        self.moving = False
        self.undo_stack.clear()  # Limpia undo al reiniciar

    def _force_redraw(self):
        """Fuerza un redibujo inmediato para cerrar popups (llamado después de reinicio)."""
        arcade.schedule(lambda dt: None, 0.0) 


    def on_key_press(self, key, modifiers):
        # --- PRIORIDAD 1: manejar popup de configuración del bot PRIMERO ---
        if getattr(self, 'mostrar_config_bot_popup', False):
            # navegación
            if key in (arcade.key.UP, arcade.key.LEFT):
                self.config_bot_seleccion = (self.config_bot_seleccion - 1) % len(self.config_bot_opciones)
                return
            if key in (arcade.key.DOWN, arcade.key.RIGHT):
                self.config_bot_seleccion = (self.config_bot_seleccion + 1) % len(self.config_bot_opciones)
                return
            # confirmar
            if key == arcade.key.ENTER:
                self.npc_habilitado = (self.config_bot_seleccion == 0)  # 0 = CON Bot, 1 = SIN Bot
                self.mostrar_config_bot_popup = False
                
                if self.npc_habilitado:
                    # Si elige CON Bot, mostrar popup de dificultad
                    self.difficulty_popup_active = True
                else:
                    # Si elige SIN Bot, remover el NPC y mostrar popup de meta
                    self.remover_npc()
                    self.mostrar_meta_popup = True
                return
        
        # --- PRIORIDAD 2: manejar popup de dificultad segundo ---
        if getattr(self, 'difficulty_popup_active', False):
            # navegación
            if key in (arcade.key.UP, arcade.key.LEFT):
                self.difficulty_selected_idx = (self.difficulty_selected_idx - 1) % len(self.difficulty_options)
                return
            if key in (arcade.key.DOWN, arcade.key.RIGHT):
                self.difficulty_selected_idx = (self.difficulty_selected_idx + 1) % len(self.difficulty_options)
                return
            # selección directa
            if key == arcade.key.KEY_1:
                self.difficulty_selected_idx = 0
                return
            elif key == arcade.key.KEY_2:
                self.difficulty_selected_idx = 1
                return
            elif key == arcade.key.KEY_3:
                self.difficulty_selected_idx = 2
                return
            # confirmar
            if key == arcade.key.ENTER:
                self.npc_difficulty = self.difficulty_options[self.difficulty_selected_idx]
                self.difficulty_popup_active = False
                try:
                    self.npc_sprite.nombre = f"NPC ({self.npc_difficulty})"
                except Exception:
                    pass
                # Después de elegir dificultad, mostrar popup de meta
                self.mostrar_meta_popup = True
                return
            # cancelar
            if key == arcade.key.ESCAPE:
                self.difficulty_popup_active = False
                self.npc_difficulty = None
                self.agregar_notificacion("Selección de dificultad cancelada.", arcade.color.LIGHT_GRAY)
                return

        if self.mostrar_meta_popup and key == arcade.key.ENTER:
            self.mostrar_meta_popup = False
            # Después del popup de meta, ir al popup de nombre
            self.pedir_nombre_popup()
            return

        # Verificación de game_over (al inicio, para pausar todo y manejar reinicio)
        if self.game_over:
            if key == arcade.key.SPACE or key == arcade.key.ESCAPE:
                self.close()
            elif key == arcade.key.R:
                # Reiniciar juego 
                self.restart_game()
                self._force_redraw()
            return 
        # Manejo de popups
        elif self.nombre_popup_activo:
            if key == arcade.key.ENTER:
                if self.nombre_jugador.strip():
                    self.nombre_popup_activo = False
                    self.player_sprite.nombre = self.nombre_jugador.strip()
                    # Ya no activar popup de dificultad aquí - se hace antes en la configuración del bot
            elif key == arcade.key.BACKSPACE:
                self.nombre_jugador = self.nombre_jugador[:-1]
            elif 32 <= key <= 126 and len(self.nombre_jugador) < 16:
                self.nombre_jugador += chr(key)
            return
        elif self.popup_guardar_activo:
            if key == arcade.key.ESCAPE:
                self.popup_guardar_activo = False
            elif key == arcade.key.KEY_1: self.guardar_en_slot(1)
            elif key == arcade.key.KEY_2: self.guardar_en_slot(2)
            elif key == arcade.key.KEY_3: self.guardar_en_slot(3)
            return

        elif self.popup_cargar_activo:
            if key == arcade.key.ESCAPE:
                self.popup_cargar_activo = False
            elif key == arcade.key.KEY_1: self.cargar_de_slot(1)
            elif key == arcade.key.KEY_2: self.cargar_de_slot(2)
            elif key == arcade.key.KEY_3: self.cargar_de_slot(3)
            return

        if self.mostrar_inventario_popup:
            if key == arcade.key.I or key == arcade.key.ESCAPE:
                self.mostrar_inventario_popup = False
                return

            if self.player_sprite.inventario.cantidad() > 0:
                if key == arcade.key.UP:
                    self.inventario_seleccion_idx = (self.inventario_seleccion_idx - 1) % self.player_sprite.inventario.cantidad()
                
                elif key == arcade.key.DOWN:
                    self.inventario_seleccion_idx = (self.inventario_seleccion_idx + 1) % self.player_sprite.inventario.cantidad()
                
                elif key == arcade.key.D:
                    self.lista_inventario_visible = self.player_sprite.inventario.acomodar_deadline()
                    self.modo_orden = 'deadline'
                    self.inventario_seleccion_idx = 0 
                
                elif key == arcade.key.Z:
                    self.lista_inventario_visible = self.player_sprite.inventario.acomodar_prioridad()
                    self.modo_orden = 'prioridad'
                    self.inventario_seleccion_idx = 0 

                elif key == arcade.key.ENTER:
                    self.pedido_activo_para_entrega = self.lista_inventario_visible[self.inventario_seleccion_idx]
                    ######
                    print(f"Pedido seleccionado para entrega: {self.pedido_activo_para_entrega.id}")
                    self.mostrar_inventario_popup = False
                elif key == arcade.key.C:
                    pedido_a_cancelar = self.lista_inventario_visible[self.inventario_seleccion_idx]
                    
                    if self.player_sprite.cancelar_pedido(pedido_a_cancelar.id):
                    
                        self.agregar_notificacion(f"Pedido Cancelado: -4 Rep.", arcade.color.ORANGE_RED)
                        
                        for sprite in self.pickup_list:
                            if sprite.pedido_id == pedido_a_cancelar.id:
                                sprite.remove_from_sprite_lists()
                        for sprite in self.dropoff_list:
                            if sprite.pedido_id == pedido_a_cancelar.id:
                                sprite.remove_from_sprite_lists()
                        if self.pedido_activo_para_entrega and self.pedido_activo_para_entrega.id == pedido_a_cancelar.id:
                            self.pedido_activo_para_entrega = None
                        self.mostrar_inventario_popup = False
            return

        #Depuracion
        if key == arcade.key.V:
            print("[DEBUG] Forzando victoria...")
            self.player_sprite.ingresos = self.meta_ingresos + 1 
            self.meta_cumplida = True
            self.check_game_end()
            return
        elif key == arcade.key.D:
            print("[DEBUG] Forzando derrota...")
            self.total_time = 0  
            self.check_game_end()
            return

        if key == arcade.key.I:
            self.mostrar_inventario_popup = True
            self.inventario_seleccion_idx = 0 
            if self.modo_orden == 'prioridad':
                self.lista_inventario_visible = self.player_sprite.inventario.acomodar_prioridad()
            else:
                self.lista_inventario_visible = self.player_sprite.inventario.acomodar_deadline()
            return
        #Deshacer movimiento with 'U'
        if key == arcade.key.U:
            if self.game_over or self.nombre_popup_activo or self.popup_guardar_activo or self.popup_cargar_activo or self.mostrar_inventario_popup or self.mostrar_pedido or self.mostrar_meta_popup:
                return  
            self.deshacer_paso()
            return

        #Mostrar popup de puntajes
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
        if self.nombre_popup_activo or self.popup_guardar_activo or self.popup_cargar_activo or self.mostrar_inventario_popup:
            return
        # Cierra popup de puntajes con ESC
        if getattr(self, 'mostrar_popup_puntajes', False):
            if key == arcade.key.ESCAPE:
                self.mostrar_popup_puntajes = False
            return
        # Popup pedido
        if self.mostrar_pedido and self.pedido_actual:
            if key == arcade.key.A: 
                pedido = self.pedido_actual
                # Solo permitir aceptar si el pickup aún existe
                existe_pickup = any(s.pedido_id == pedido.id for s in self.pickup_list)
                if not existe_pickup:
                    print(f"Pedido {pedido.id} aceptado")
                    self.pedidos_activos[pedido.id] = pedido 
                    pedido.tiempo_expiracion = self.tiempo_global + TIEMPO_PARA_RECOGER
                   
                    pickup_x, pickup_y = self.celda_a_pixeles(*pedido.coord_recoger)
                    dropoff_x, dropoff_y = self.celda_a_pixeles(*pedido.coord_entregar)
                    self.crear_pedido(pickup_x, pickup_y, dropoff_x, dropoff_y, pedido.id)
                    self.mostrar_pedido = False
                    self.pedido_actual = None
                else:
                    self.agregar_notificacion("Pedido ya fue recogido por otro repartidor.", arcade.color.ORANGE_RED)
                    self.mostrar_pedido = False
                    self.pedido_actual = None
            elif key == arcade.key.R:  
                print(f"Pedido {self.pedido_actual.id} rechazado")
                self.mostrar_pedido = False
                self.pedido_actual = None
        if self.active_direction == key:
            self.active_direction = None

        #Manejo de movimiento
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
        """Convierte coordenadas de celda a coordenadas de píxeles"""
        x = (col * CELL_SIZE + CELL_SIZE // 2) * self.scale_x
        y = (height * CELL_SIZE - (row * CELL_SIZE + CELL_SIZE // 2)) * self.scale_y
        return x, y
    
    def pixeles_a_celda(self, x, y):
        """Convierte coordenadas de píxeles a coordenadas de celda"""
        col = int(x / self.scale_x / CELL_SIZE)
        row = int((height * CELL_SIZE - y / self.scale_y) / CELL_SIZE)
        return row, col
    
    def encontrar_celda_accesible_mas_cercana(self, row, col):
        """
        Encuentra la celda accesible (no edificio) más cercana a las coordenadas dadas.
        Si la celda original no es un edificio, devuelve las coordenadas originales.
        """
        if 0 <= row < ROWS and 0 <= col < COLS and mapa[row][col] != "B":
            return row, col
        
        max_radio = max(ROWS, COLS)
        
        for radio in range(1, max_radio):
            for dr in range(-radio, radio + 1):
                for dc in range(-radio, radio + 1):
                    if abs(dr) == radio or abs(dc) == radio:
                        nueva_row = row + dr
                        nueva_col = col + dc
                        
                        if (0 <= nueva_row < ROWS and 
                            0 <= nueva_col < COLS and 
                            mapa[nueva_row][nueva_col] != "B"):
                            return nueva_row, nueva_col
        
        return row, col
    
    def crear_pedido(self, pickup_x, pickup_y, dropoff_x, dropoff_y, pedido_id):
        """Crea sprites de pickup/dropoff. Si la celda original es un edificio,
        coloca el sprite en la celda accesible más cercana."""
        try:
            p_row, p_col = self.pixeles_a_celda(pickup_x, pickup_y)
            if 0 <= p_row < ROWS and 0 <= p_col < COLS and mapa[p_row][p_col] == "B":
                p_row, p_col = self.encontrar_celda_accesible_mas_cercana(p_row, p_col)
                pickup_x, pickup_y = self.celda_a_pixeles(p_row, p_col)
        except Exception:
            pass

        try:
            d_row, d_col = self.pixeles_a_celda(dropoff_x, dropoff_y)
            if 0 <= d_row < ROWS and 0 <= d_col < COLS and mapa[d_row][d_col] == "B":
                d_row, d_col = self.encontrar_celda_accesible_mas_cercana(d_row, d_col)
                dropoff_x, dropoff_y = self.celda_a_pixeles(d_row, d_col)
        except Exception:
            pass

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
        # --- intenta API, si falla usa backup ---
        try:
            response = requests.get(f"{BASE_URL}/city/jobs", timeout=5).json()
        except Exception as e:
            print(f"[WARN] jobs API failed: {e}")
            backup = cargar_backup()
            if backup and "jobs" in backup:
                response = backup["jobs"]
            else:
                raise RuntimeError("No se pudo obtener jobs ni backup.json")
        jobs = response.get("data", [])
        for p in jobs:
            deadline_api = datetime.fromisoformat(p["deadline"].replace('Z', '+00:00'))
            duracion_en_segundos = (deadline_api - self.hora_inicio_juego_utc).total_seconds()
            
            if duracion_en_segundos < 0:
                duracion_en_segundos = random.randint(180, 420)

            pedido_obj = Pedido(
                id=p["id"],
                peso=p["weight"],
                deadline=deadline_api,
                pago=p["payout"],
                prioridad=p.get("priority", 0),
                coord_recoger=p["pickup"],
                coord_entregar=p["dropoff"],
                release_time=p.get("release_time", 0)
            )
            tiempo_inicial_juego = 15 * 60
            pedido_obj.deadline_contador = tiempo_inicial_juego - duracion_en_segundos
                    
            self.pedidos_dict[pedido_obj.id] = pedido_obj
            self.pedidos_pendientes.append(pedido_obj)
        BACKUP_DATA["jobs"] = response
        save_backup()

    def on_update(self, delta_time):
        if self.game_over:
            return
        self.actualizar_notificaciones(delta_time)
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
            self.player_sprite.center_x = self.target_x 
            self.player_sprite.center_y = self.target_y
            self.player_sprite.row = self.target_row
            self.player_sprite.col = self.target_col
            print("¡Agotado! Descansando hasta recuperar 30% de resistencia.")

        # Manejo de movimiento suave
        if self.moving:
            dx = self.target_x - self.player_sprite.center_x
            dy = self.target_y - self.player_sprite.center_y
            dist = (dx ** 2 + dy ** 2) ** 0.5
        
            mult_clima = self.clima.multiplicadorVelocidad
            if self.clima.condicion != "clear":
                mult_clima *= (1 - self.clima.intensidad * 0.5)
            mult_clima = max(mult_clima, 0.1)

            # Reduccion por peso de velocidad
            peso_total = self.player_sprite.inventario.peso_total()
            peso_maximo = self.player_sprite.inventario.peso_maximo
            speed_reduction_factor = 0.8
            reduction = (peso_total / peso_maximo) * speed_reduction_factor if peso_maximo > 0 else 0
            mult_peso = max(1.0 - reduction, 0.2)

            mult_resistencia = self.player_sprite.resistencia_obj.get_multiplicador_velocidad()

            # Reduccion por superficie
            mult_surface_actual = self.obtener_multiplicador_superficie(self.player_sprite.row, self.player_sprite.col)
            mult_surface_dest = self.obtener_multiplicador_superficie(self.target_row, self.target_col)
            mult_surface = (mult_surface_actual + mult_surface_dest) / 2.0
            if mult_surface <= 0:
                mult_surface = 0.01

            velocidad_base = self.move_speed  
            velocidad_actual_por_frame = (
                velocidad_base *
                mult_clima *
                mult_peso *
                mult_resistencia *
                mult_surface *
                delta_time
            )

            if dist < velocidad_actual_por_frame:
                self.player_sprite.center_x = self.target_x
                self.player_sprite.center_y = self.target_y
                self.player_sprite.row = self.target_row
                self.player_sprite.col = self.target_col
                self.moving = False
                self.try_move()
            else:
                self.player_sprite.center_x += velocidad_actual_por_frame * dx / dist
                self.player_sprite.center_y += velocidad_actual_por_frame * dy / dist
    # --- Guardar undo después de un movimiento exitoso ---
        if not self.moving and self.tiempo_global > self.ultimo_movimiento_tiempo + 0.5:
            if self.active_direction is not None or self.player_sprite.row != self.target_row or self.player_sprite.col != self.target_col:
                self.guardar_estado_actual()
                self.ultimo_movimiento_tiempo = self.tiempo_global
        pickups_hit = arcade.check_for_collision_with_list(self.player_sprite, self.pickup_list)

        # Verificación adicional para pickups en edificios
        if not pickups_hit:
            for pickup in self.pickup_list:
                pickup_row, pickup_col = self.pixeles_a_celda(pickup.center_x, pickup.center_y)
                
                if (0 <= pickup_row < ROWS and 0 <= pickup_col < COLS and 
                    mapa[pickup_row][pickup_col] == "B"):
                    
                    celda_accesible_row, celda_accesible_col = self.encontrar_celda_accesible_mas_cercana(pickup_row, pickup_col)
                    
                    if (self.player_sprite.row == celda_accesible_row and 
                        self.player_sprite.col == celda_accesible_col):
                        pickups_hit.append(pickup)
        # Manejo de pickups y dropoffs
        if pickups_hit:
            for pickup in pickups_hit:
                pedido_obj = self.pedidos_dict[pickup.pedido_id]
                if self.player_sprite.pickup(pedido_obj, self.total_time):
                    self.agregar_notificacion(f"Recogido: {pedido_obj.id}", arcade.color.WHITE_SMOKE)
                    pickup.remove_from_sprite_lists()

                    if pedido_obj.id in self.pedidos_activos:
                        del self.pedidos_activos[pedido_obj.id]
                else:
                    self.agregar_notificacion("¡Inventario Lleno!", arcade.color.RED)
        else:
            dropoffs_hit = arcade.check_for_collision_with_list(self.player_sprite, self.dropoff_list)
            
            if not dropoffs_hit and self.pedido_activo_para_entrega:
                for dropoff in self.dropoff_list:
                    if dropoff.pedido_id == self.pedido_activo_para_entrega.id:
                        dropoff_row, dropoff_col = self.pixeles_a_celda(dropoff.center_x, dropoff.center_y)
                        
                        if (0 <= dropoff_row < ROWS and 0 <= dropoff_col < COLS and 
                            mapa[dropoff_row][dropoff_col] == "B"):

                            celda_accesible_row, celda_accesible_col = self.encontrar_celda_accesible_mas_cercana(dropoff_row, dropoff_col)
                            
                            if (self.player_sprite.row == celda_accesible_row and 
                                self.player_sprite.col == celda_accesible_col):
                                dropoffs_hit.append(dropoff)
                                break
            # Manejo de entregas
            for dropoff in dropoffs_hit:
                if self.pedido_activo_para_entrega and dropoff.pedido_id == self.pedido_activo_para_entrega.id:
                    
                    mensajes = self.player_sprite.dropoff(self.pedido_activo_para_entrega.id, self.total_time)
                    
                    if mensajes:
                        for texto, color in mensajes:
                            self.agregar_notificacion(texto, color)
                        self.pedidos_completados += 1
                    self.pedido_activo_para_entrega = None
                    dropoff.remove_from_sprite_lists()

        self.tiempo_global += delta_time
        
        if self.check_game_end():

            return
        # Verifica expiración de pedidos activos
        pedidos_expirados = []
        for pedido_id, pedido in self.pedidos_activos.items():
            if self.tiempo_global > pedido.tiempo_expiracion:
                print(f"¡El pedido {pedido.id} ha expirado!")
                self.player_sprite.reputacion -= 6
                self.agregar_notificacion(f"Pedido Expirado: -6 Rep.", arcade.color.RED)
                
                pedidos_expirados.append(pedido_id)
        for pedido_id in pedidos_expirados:
            del self.pedidos_activos[pedido_id]
            for sprite in self.pickup_list:
                if sprite.pedido_id == pedido_id:
                    sprite.remove_from_sprite_lists()
            for sprite in self.dropoff_list:
                if sprite.pedido_id == pedido_id:
                    sprite.remove_from_sprite_lists()
        # Logica para enciclar
        if not self.mostrar_pedido:
            pedido_encontrado_para_mostrar = None
            for pedido in self.pedidos_pendientes:
                if self.tiempo_global >= pedido.release_time:
                    pedido_encontrado_para_mostrar = pedido
                    break 

            if pedido_encontrado_para_mostrar:
                self.pedido_actual = pedido_encontrado_para_mostrar
                self.mostrar_pedido = True
                self.pedidos_pendientes.remove(pedido_encontrado_para_mostrar)
            elif not self.pedidos_pendientes:
                pedidos_reciclados = list(self.pedidos_dict.values())
                for i, pedido in enumerate(pedidos_reciclados):
                    pedido.release_time = self.tiempo_global + ( (i + 1) * 30 )
                    nueva_duracion_segundos = random.randint(180, 300) 
                    pedido.deadline_contador = self.total_time - nueva_duracion_segundos

                random.shuffle(pedidos_reciclados)
                self.pedidos_pendientes = pedidos_reciclados
        self.check_game_end()

        self.actualizar_npc(delta_time)
        self._actualizar_movimiento_npc(delta_time)

    def check_game_end(self):
        """Verifica si el juego terminó por victoria o derrota."""
        if self.game_over:
            return True
        # VICTORIA
        if self.player_sprite.ingresos >= self.meta_ingresos:
            self.victoria = True
            self.game_over = True
            self.end_message = "¡Victoria! Has alcanzado la meta de ingresos."
            self.end_stats = self._get_end_stats()
            self.guardar_puntaje_si_termina()
            return True
        # DERROTA
        mensaje_derrota = ""
        if self.total_time <= 0:
            mensaje_derrota = "¡Derrota! Se te ha agotado el tiempo."
        elif self.player_sprite.reputacion < 20:
            mensaje_derrota = "¡Derrota! Tu reputación ha bajado a menos de 20."

        if mensaje_derrota:
            self.victoria = False
            self.game_over = True
            self.end_message = mensaje_derrota
            self.end_stats = self._get_end_stats()
            self.guardar_puntaje_si_termina()
            return True

        return False
 
    def obtener_multiplicador_superficie(self, row, col):
        """Devuelve el multiplicador de velocidad según la superficie de la celda."""
        if 0 <= row < ROWS and 0 <= col < COLS:
            tipo = mapa[row][col]
            return SURFACE_WEIGHTS.get(tipo, 1.0)
        return 1.0
    
    def _get_end_stats(self):
        """Método auxiliar para calcular estadísticas de fin de juego."""
        return [
            f"Ingresos: ${self.player_sprite.ingresos:.2f}",
            f"Reputación: {self.player_sprite.reputacion}",
            f"Pedidos Completados: {self.pedidos_completados}",
            f"Tiempo Restante: {max(0, int(self.total_time)) // 60:02d}:{max(0, int(self.total_time)) % 60:02d}"
        ]
    
    def _draw_end_screen(self):
        """Muestra el popup de fin de juego con mensaje y estadísticas."""
    # Pausa el juego
        self.game_over = True
    # Obtener estadísticas
        ingresos = self.player_sprite.ingresos
        reputacion = self.player_sprite.reputacion
        tiempo_restante = max(0, int(self.total_time))
        pedidos = self.pedidos_completados

        color_fondo = arcade.color.DARK_GREEN if self.victoria else arcade.color.DARK_RED
        color_texto = arcade.color.WHITE
        color_titulo = arcade.color.YELLOW if self.victoria else arcade.color.ORANGE_RED
    # Dibujar popup
        ancho, alto = 500, 400
        x = self.window_width // 2 - ancho // 2
        y = self.window_height // 2 - alto // 2
    # Fondo semi-transparente
        arcade.draw_lbwh_rectangle_filled(0, self.window_width, 0, self.window_height, arcade.color.BLACK)
    # Rectángulo del popup
        arcade.draw_lbwh_rectangle_filled(x, y, ancho, alto, color_fondo)
        arcade.draw_lbwh_rectangle_outline(x, y, ancho, alto, arcade.color.WHITE, 3)
    # Título y mensaje
        arcade.draw_text("FIN DEL JUEGO", x + ancho // 2, y + alto - 40, color_titulo, 24, anchor_x="center", anchor_y="top")
        arcade.draw_text(self.end_message, x + ancho // 2, y + alto - 80, color_texto, 18, anchor_x="center", anchor_y="top", width=ancho - 40)
    # Estadísticas
        y_offset = y + alto - 120
        for stat in self.end_stats:
            arcade.draw_text(stat, x + ancho // 2, y_offset, color_texto, 16, anchor_x="center", anchor_y="top")
            y_offset -= 25
    # Instrucciones
        arcade.draw_text("Presiona [ESC] para cerrar o [R] para reiniciar", x + ancho // 2, y + 30, arcade.color.LIGHT_GRAY, 14, anchor_x="center", anchor_y="top")


    def actualizar_npc(self, delta_time):
        """Actualiza el NPC: movimiento, elección y acciones de pedido."""
        # No actualizar si no está habilitado o no existe
        if not getattr(self, 'npc_habilitado', True) or not hasattr(self, 'npc_sprite') or not self.npc_sprite:
            return
            
        # No recalcular mientras se anima un paso
        if getattr(self, "npc_smooth_moving", False):
            return
        if not self.npc_difficulty:
            # Asignar dificultad por defecto para evitar estado inerte
            self.npc_difficulty = "Fácil"
            print("[NPC DEBUG] Dificultad por defecto aplicada: Fácil")
        self._sync_npc_position()
        intervalo = 0.05 if self.npc_difficulty == "Fácil" else 0.1  # Intervalos más pequeños para movimiento fluido
        self.npc_action_timer += delta_time
        if self.npc_action_timer < intervalo:
            return
        self.npc_action_timer = 0
        try:
            self.npc_sprite.actualizar_resistencia(
                delta_time,
                self.npc_moving,
                getattr(self.npc_sprite, "peso_total", 0),
                self.clima.condicion,
                self.clima.intensidad
            )
            # Verificar si el pedido actual sigue siendo válido
            if self.npc_pedido_activo:
                # Si ya recogimos el pedido o ya no hay pickup, buscar nuevo objetivo
                tiene_pedido = self.npc_tiene_pedido(self.npc_sprite, self.npc_pedido_activo.id)
                existe_pickup = any(s.pedido_id == self.npc_pedido_activo.id for s in self.pickup_list)
                
                if not tiene_pedido and not existe_pickup:
                    self.npc_pedido_activo = None
                    self.npc_path = []
                    self.npc_goal = None
                    print(f"[NPC DEBUG] Pedido perdido, buscando nuevo objetivo.")

            if not self.npc_pedido_activo:
                pedido = self.elegir_pedido_npc()
                if pedido:
                    self.npc_pedido_activo = pedido
                    print(f"[NPC DEBUG] Pedido asignado {pedido.id}")
            
            # Check if NPC can move (resistance check like player)
            if not self.npc_sprite.puede_moverse():
                print(f"[NPC DEBUG] NPC exhausted, resting...")
                # Stop movement if exhausted
                if self.npc_smooth_moving:
                    self.npc_smooth_moving = False
                    self.npc_moving = False
                return
            
            nueva_pos = None
            if self.npc_difficulty == "Fácil":
                nueva_pos = self.movimiento_aleatorio_npc()
            elif self.npc_pedido_activo:  # Normal o Difícil con pedido
                tiene = self.npc_tiene_pedido(self.npc_sprite, self.npc_pedido_activo.id)
                
                # Buscar la posición REAL del sprite (pickup o dropoff)
                objetivo = None
                if tiene:
                    # Buscar dropoff
                    for dropoff in self.dropoff_list:
                        if dropoff.pedido_id == self.npc_pedido_activo.id:
                            drop_row, drop_col = self.pixeles_a_celda(dropoff.center_x, dropoff.center_y)
                            objetivo = (drop_row, drop_col)
                            break
                else:
                    # Buscar pickup
                    for pickup in self.pickup_list:
                        if pickup.pedido_id == self.npc_pedido_activo.id:
                            pick_row, pick_col = self.pixeles_a_celda(pickup.center_x, pickup.center_y)
                            objetivo = (pick_row, pick_col)
                            break
                
                # Si no encontramos el sprite, usar coordenadas del pedido como fallback
                if objetivo is None:
                    objetivo = tuple(self.npc_pedido_activo.coord_entregar if tiene else self.npc_pedido_activo.coord_recoger)
                    obj_r, obj_c = objetivo
                    if 0 <= obj_r < ROWS and 0 <= obj_c < COLS and mapa[obj_r][obj_c] == "B":
                        obj_r, obj_c = self.encontrar_celda_accesible_mas_cercana(obj_r, obj_c)
                        objetivo = (obj_r, obj_c)
                
                start = (self.npc_spriteRow, self.npc_spriteCol)
                
                if self.npc_difficulty == "Difícil":
                    
                    if self.npc_goal != objetivo or not self.npc_path:
                        self.npc_path = self.npc_build_path_a_star(start, objetivo)
                        self.npc_goal = objetivo
                        print(f"[NPC DEBUG] Nueva ruta A* desde {start} hacia {objetivo} pasos={len(self.npc_path)}")
                    if self.npc_path:
                        nueva_pos = self.npc_path.pop(0)
                        print(f"[NPC DEBUG] Siguiente paso A*: {nueva_pos}")
                    else:
                        nueva_pos = self.calcular_movimiento_npc(objetivo)
                        print(f"[NPC DEBUG] A* falló, usando movimiento simple hacia {objetivo}")
                else:  # Normal
                    nueva_pos = self.calcular_movimiento_npc(objetivo)
                    print(f"[NPC DEBUG] Movimiento simple desde {start} hacia {objetivo} -> {nueva_pos}")
            else:
                # Sin pedido: moverse aleatorio para no quedar estático
                nueva_pos = self.movimiento_aleatorio_npc()
            if nueva_pos and nueva_pos != (self.npc_spriteRow, self.npc_spriteCol):
                dr = nueva_pos[0] - self.npc_spriteRow
                dc = nueva_pos[1] - self.npc_spriteCol
                if dr == -1:
                    self.npc_sprite.angle = 270
                    self.npc_sprite.scale_x = abs(self.npc_sprite.scale_x)  # Mirar arriba, escala positiva
                elif dr == 1:
                    self.npc_sprite.angle = 90
                    self.npc_sprite.scale_x = abs(self.npc_sprite.scale_x)  # Mirar abajo, escala positiva
                elif dc == -1:
                    self.npc_sprite.angle = 0
                    self.npc_sprite.scale_x = -abs(self.npc_sprite.scale_x)  # Mirar izquierda
                elif dc == 1:
                    self.npc_sprite.angle = 0
                    self.npc_sprite.scale_x = abs(self.npc_sprite.scale_x)   # Mirar derecha
                # Iniciar movimiento suave al siguiente tile
                self.npc_target_row, self.npc_target_col = nueva_pos
                self.npc_target_x, self.npc_target_y = self.celda_a_pixeles(*nueva_pos)
                self.npc_smooth_moving = True
                self.npc_moving = True
            self.verificar_interacciones_npc()
        except Exception as e:
            print(f"[NPC WARN] Fallo actualizar_npc: {e}")
        finally:
            if not getattr(self, "npc_smooth_moving", False):
                self.npc_moving = False

    def _actualizar_movimiento_npc(self, delta_time):
        """
        Interpolación de posición del NPC usando exactamente la misma lógica que el jugador.
        """
        # No actualizar si no está habilitado o no existe
        if not getattr(self, 'npc_habilitado', True) or not hasattr(self, 'npc_sprite') or not self.npc_sprite:
            return
            
        if not self.npc_smooth_moving:
            return
    
        dx = self.npc_target_x - self.npc_sprite.center_x
        dy = self.npc_target_y - self.npc_sprite.center_y
        dist = (dx ** 2 + dy ** 2) ** 0.5
    
        # Multiplicador de clima (igual al jugador)
        mult_clima = self.clima.multiplicadorVelocidad
        if self.clima.condicion != "clear":
            mult_clima *= (1 - self.clima.intensidad * 0.5)
        mult_clima = max(mult_clima, 0.1)

        # Reducción por peso (igual al jugador)
        peso_total = self.npc_sprite.inventario.peso_total()
        peso_maximo = self.npc_sprite.inventario.peso_maximo
        speed_reduction_factor = 0.8
        reduction = (peso_total / peso_maximo) * speed_reduction_factor if peso_maximo > 0 else 0
        mult_peso = max(1.0 - reduction, 0.2)

        # Multiplicador de resistencia (igual al jugador)
        mult_resistencia = self.npc_sprite.resistencia_obj.get_multiplicador_velocidad()

        # Multiplicador de superficie (igual al jugador)
        mult_surface_actual = self.obtener_multiplicador_superficie(self.npc_sprite.row, self.npc_sprite.col)
        mult_surface_dest = self.obtener_multiplicador_superficie(self.npc_target_row, self.npc_target_col)
        mult_surface = (mult_surface_actual + mult_surface_dest) / 2.0
        if mult_surface <= 0:
            mult_surface = 0.01
    
        # Velocidad base igual al jugador
        velocidad_base = self.move_speed  # Misma velocidad que el jugador
        
        # Aplicar todos los multiplicadores exactamente como el jugador
        velocidad_actual_por_frame = (
            velocidad_base *
            mult_clima *
            mult_peso *
            mult_resistencia *
            mult_surface *
            delta_time
        )
    
        if dist < velocidad_actual_por_frame:  
            
            self.npc_sprite.center_x = self.npc_target_x
            self.npc_sprite.center_y = self.npc_target_y
            self.npc_spriteRow = self.npc_target_row
            self.npc_spriteCol = self.npc_target_col
            self.npc_sprite.row = self.npc_spriteRow
            self.npc_sprite.col = self.npc_spriteCol
            self.npc_smooth_moving = False
            self.npc_moving = False
            # Intentar interacción (pickup/dropoff) al llegar
            self.verificar_interacciones_npc()
        else:
            # Movimiento interpolado igual al jugador
            self.npc_sprite.center_x += velocidad_actual_por_frame * dx / dist
            self.npc_sprite.center_y += velocidad_actual_por_frame * dy / dist
    
        # Actualizar resistencia durante el movimiento (igual al jugador)
        self.npc_sprite.actualizar_resistencia(
            delta_time,
            True,  # está moviendo
            self.npc_sprite.inventario.peso_total(),
            self.clima.condicion,
            self.clima.intensidad
        )

    def elegir_pedido_npc(self):
        """
        Selecciona un pedido disponible según dificultad.
        Ahora solo busca entre los pedidos que YA fueron aceptados por el jugador
        (que tienen pickups en el mundo).
        """
        # Buscar pedidos que tienen pickup disponible (fueron aceptados por el jugador)
        disponibles = []
        for pickup in self.pickup_list:
            pedido_id = pickup.pedido_id
            if pedido_id in self.pedidos_dict:
                pedido = self.pedidos_dict[pedido_id]
                # Solo considerar si no está en el inventario de nadie
                if not self.npc_tiene_pedido(self.player_sprite, pedido_id) and not self.npc_tiene_pedido(self.npc_sprite, pedido_id):
                    disponibles.append(pedido)
        
        if not disponibles:
            return None
    
        if self.npc_difficulty == "Fácil":
            # Selección aleatoria
            return random.choice(disponibles)
    
        if self.npc_difficulty == "Normal":
            # Selección basada en pago y distancia Manhattan
            return max(
                disponibles,
                key=lambda p: (p.pago) / (self._distancia_manhattan((self.npc_spriteRow, self.npc_spriteCol), p.coord_recoger) + 1)
            )
    
        if self.npc_difficulty == "Difícil":
            # Selección basada en Dijkstra (ruta más corta)
            mejor_pedido = None
            mejor_costo = float("inf")
    
            for pedido in disponibles:
                # Buscar la posición real del sprite de pickup
                pickup_pos = None
                for pickup in self.pickup_list:
                    if pickup.pedido_id == pedido.id:
                        pickup_row, pickup_col = self.pixeles_a_celda(pickup.center_x, pickup.center_y)
                        pickup_pos = (pickup_row, pickup_col)
                        break
                
                if pickup_pos is None:
                    continue  # Skip si no encontramos el sprite
                
                # Calcular el costo de la ruta más corta hacia el pickup real
                costo_ruta = self._dijkstra_cost((self.npc_spriteRow, self.npc_spriteCol), pickup_pos)
                print(f"[NPC DEBUG] Dijkstra para pedido {pedido.id}: costo={costo_ruta}")
                
                if costo_ruta is not None:
                    # Evaluar el pedido basado en el pago y el costo de la ruta
                    costo_total = costo_ruta / (pedido.pago + 0.1)  # Simplificado
                    if costo_total < mejor_costo:
                        mejor_costo = costo_total
                        mejor_pedido = pedido
    
            print(f"[NPC DEBUG] Dijkstra eligió pedido: {mejor_pedido.id if mejor_pedido else 'None'}")
            return mejor_pedido
    
        return None
    
    
    def _dijkstra_cost(self, start, goal):
        """
        Calcula el costo de la ruta más corta desde 'start' hasta 'goal' usando Dijkstra.
        Retorna el costo total o None si no hay ruta.
        """
        import heapq
        
        print(f"[NPC DEBUG] Dijkstra: desde {start} hasta {goal}")
        
        # Validar entrada
        if start == goal:
            return 0.0
            
        if not (0 <= start[0] < ROWS and 0 <= start[1] < COLS):
            print(f"[NPC DEBUG] Dijkstra: start {start} fuera de límites")
            return None
            
        if not (0 <= goal[0] < ROWS and 0 <= goal[1] < COLS):
            print(f"[NPC DEBUG] Dijkstra: goal {goal} fuera de límites")
            return None
    
        # Inicializar estructuras de datos
        open_heap = []
        heapq.heappush(open_heap, (0, start))  # (costo acumulado, nodo actual)
        costos = {start: 0}
        visitados = set()
        max_iterations = ROWS * COLS * 2  # Evitar bucles infinitos
        iterations = 0
    
        while open_heap and iterations < max_iterations:
            iterations += 1
            costo_actual, nodo_actual = heapq.heappop(open_heap)
    
            if nodo_actual in visitados:
                continue
    
            # Si llegamos al objetivo, devolvemos el costo
            if nodo_actual == goal:
                print(f"[NPC DEBUG] Dijkstra: ruta encontrada, costo={costo_actual}, iteraciones={iterations}")
                return costo_actual
    
            visitados.add(nodo_actual)
    
            # Explorar vecinos
            for vecino in self._npc_neighbors(nodo_actual):
                if vecino in visitados:
                    continue
    
                # Calcular el costo para llegar al vecino
                costo_vecino = costo_actual + self._npc_cell_cost(vecino)
    
                if vecino not in costos or costo_vecino < costos[vecino]:
                    costos[vecino] = costo_vecino
                    heapq.heappush(open_heap, (costo_vecino, vecino))
    
        # Si no se encuentra una ruta, devolver None
        print(f"[NPC DEBUG] Dijkstra: sin ruta encontrada después de {iterations} iteraciones")
        return None

    def movimiento_aleatorio_npc(self):
        """
        Devuelve una celda vecina válida (no edificio) al azar para el NPC.
        Si no hay vecinos válidos, permanece en su celda actual.
        """
        cur = (self.npc_spriteRow, self.npc_spriteCol)
        vecinos = self._npc_neighbors(cur)
        if not vecinos:
            return cur
        return random.choice(vecinos)

    def calcular_movimiento_npc(self, objetivo_pos):
        """
        Movimiento simple hacia el objetivo (row,col) evitando edificios.
        Mejorado para evitar que se quede pegado.
        """
        cur_r, cur_c = self.npc_spriteRow, self.npc_spriteCol
        tgt_r, tgt_c = objetivo_pos
        # Ajustar si objetivo es edificio
        if 0 <= tgt_r < ROWS and 0 <= tgt_c < COLS and mapa[tgt_r][tgt_c] == "B":
            tgt_r, tgt_c = self.encontrar_celda_accesible_mas_cercana(tgt_r, tgt_c)
        objetivo = (tgt_r, tgt_c)
        if (cur_r, cur_c) == objetivo:
            return (cur_r, cur_c)
        
        # Calcular diferencias
        diff_r = tgt_r - cur_r
        diff_c = tgt_c - cur_c
        
        # Priorizar movimiento en la dirección con mayor diferencia
        candidatos = []
        if abs(diff_r) >= abs(diff_c):
            # Mover primero verticalmente
            if diff_r > 0:
                candidatos.append((cur_r + 1, cur_c))
            elif diff_r < 0:
                candidatos.append((cur_r - 1, cur_c))
            # Luego horizontalmente
            if diff_c > 0:
                candidatos.append((cur_r, cur_c + 1))
            elif diff_c < 0:
                candidatos.append((cur_r, cur_c - 1))
        else:
            # Mover primero horizontalmente
            if diff_c > 0:
                candidatos.append((cur_r, cur_c + 1))
            elif diff_c < 0:
                candidatos.append((cur_r, cur_c - 1))
            # Luego verticalmente
            if diff_r > 0:
                candidatos.append((cur_r + 1, cur_c))
            elif diff_r < 0:
                candidatos.append((cur_r - 1, cur_c))
        
        # Filtrar movimientos válidos
        for r, c in candidatos:
            if 0 <= r < ROWS and 0 <= c < COLS and mapa[r][c] != "B":
                return (r, c)
        
        # Si no puede moverse hacia el objetivo, buscar cualquier movimiento válido
        todos_candidatos = [
            (cur_r - 1, cur_c),
            (cur_r + 1, cur_c),
            (cur_r, cur_c - 1),
            (cur_r, cur_c + 1),
        ]
        validos = [(r, c) for r, c in todos_candidatos
                   if 0 <= r < ROWS and 0 <= c < COLS and mapa[r][c] != "B"]
        
        if validos:
            # Elegir el que reduce más la distancia Manhattan
            mejor = validos[0]
            mejor_dist = self._distancia_manhattan(mejor, objetivo)
            for v in validos[1:]:
                d = self._distancia_manhattan(v, objetivo)
                if d < mejor_dist:
                    mejor = v
                    mejor_dist = d
            return mejor
        
        return (cur_r, cur_c)

    def _distancia_manhattan(self, pos1, pos2):
        """Calcula la distancia Manhattan entre dos posiciones (fila, columna)."""
        return abs(pos1[0] - pos2[0]) + abs(pos1[1] - pos2[1])

    def npc_tiene_pedido(self, npc_sprite, pedido_id):
        """
        Verifica si el NPC tiene un pedido específico en su inventario.
        :param npc_sprite: El sprite del NPC.
        :param pedido_id: El ID del pedido a verificar.
        :return: True si el NPC tiene el pedido, False en caso contrario.
        """
        nodo = npc_sprite.inventario.inicio
        while nodo:
            if nodo.pedido.id == pedido_id:
                return True
            nodo = nodo.siguiente
        return False

    def verificar_interacciones_npc(self):
        """Pickups y dropoffs del NPC (versión consolidada)."""
        if not self.npc_pedido_activo:
            return
        pedido = self.npc_pedido_activo

        # Pickup - verificar si el NPC está en la misma posición que el sprite de pickup
        for pickup in list(self.pickup_list):
            if pickup.pedido_id == pedido.id:
                pickup_row, pickup_col = self.pixeles_a_celda(pickup.center_x, pickup.center_y)
                if (self.npc_spriteRow, self.npc_spriteCol) == (pickup_row, pickup_col):
                    print(f"[NPC DEBUG] Intentando recoger pedido {pedido.id}")
                    if self.npc_sprite.pickup(pedido, self.total_time):
                        pickup.remove_from_sprite_lists()
                        if pedido.id in self.pedidos_activos:
                            del self.pedidos_activos[pedido.id]
                        # Recalcular ruta ahora hacia el dropoff
                        self.npc_path = []
                        self.npc_goal = None
                        print(f"[NPC DEBUG] Pedido recogido {pedido.id}, recalculando hacia dropoff.")

        # Dropoff - verificar si el NPC está en la misma posición que el sprite de dropoff
        for dropoff in list(self.dropoff_list):
            if dropoff.pedido_id == pedido.id:
                dropoff_row, dropoff_col = self.pixeles_a_celda(dropoff.center_x, dropoff.center_y)
                if (self.npc_spriteRow, self.npc_spriteCol) == (dropoff_row, dropoff_col):
                    print(f"[NPC DEBUG] Intentando entregar pedido {pedido.id}")
                    mensajes = self.npc_sprite.dropoff(pedido.id, self.total_time)
                    if mensajes:
                        self.npc_pedido_activo = None
                        self.pedidos_completados += 1
                        # Limpiar ruta al completar
                        self.npc_path = []
                        self.npc_goal = None
                        print(f"[NPC DEBUG] Pedido entregado {pedido.id}.")
                    dropoff.remove_from_sprite_lists()

    def _sync_npc_position(self):
        """Mantiene sincronizadas las coordenadas auxiliares del NPC."""
        if hasattr(self, 'npc_sprite') and self.npc_sprite:
            if not hasattr(self, 'npc_spriteRow') or not hasattr(self, 'npc_spriteCol'):
                # Inicializar si no existen
                self.npc_spriteRow = getattr(self.npc_sprite, 'row', 0)
                self.npc_spriteCol = getattr(self.npc_sprite, 'col', 0)
            else:
                self.npc_spriteRow = self.npc_sprite.row
                self.npc_spriteCol = self.npc_sprite.col

    # --- A* para NPC ---
    def _npc_neighbors(self, pos):
        r, c = pos
        cand = [(r - 1, c), (r + 1, c), (r, c - 1), (r, c + 1)]
        return [(nr, nc) for nr, nc in cand
                if 0 <= nr < ROWS and 0 <= nc < COLS and mapa[nr][nc] != "B"]

    def _npc_cell_cost(self, pos):
        """Calcula el costo de moverse a una celda específica."""
        try:
            tipo_celda = mapa[pos[0]][pos[1]]
            surf_mult = SURFACE_WEIGHTS.get(tipo_celda, 1.0)
            
            if surf_mult > 0:
                surf_cost = 1.0 / surf_mult
            else:
                surf_cost = 10.0 
            
            clima_mult = max(self.clima.multiplicadorVelocidad, 0.1)
            if self.clima.condicion != "clear":
                clima_mult *= max(0.5, 1.0 - self.clima.intensidad * 0.3)
            
            clima_cost = 1.0 / clima_mult
            
            total_cost = surf_cost + clima_cost
            return total_cost
            
        except Exception as e:
            return 10.0  

    def npc_build_path_a_star(self, start, goal):
        """Devuelve lista de celdas desde el siguiente paso a goal (incluido). Vacía si no hay ruta."""
        if start == goal:
            return []
        h = lambda p: abs(p[0] - goal[0]) + abs(p[1] - goal[1])
        open_heap = []
        heapq.heappush(open_heap, (h(start), 0.0, start))
        came_from = {}
        g_score = {start: 0.0}
        closed = set()
        while open_heap:
            _, gcur, cur = heapq.heappop(open_heap)
            if cur in closed:
                continue
            if cur == goal:
                # reconstruir camino
                path = []
                p = cur
                while p in came_from:
                    path.append(p)
                    p = came_from[p]
                path.reverse()
                if path and path[0] == start:
                    path = path[1:]
                return path
            closed.add(cur)
            for nb in self._npc_neighbors(cur):
                tentative = gcur + self._npc_cell_cost(nb)
                if nb not in g_score or tentative < g_score[nb]:
                    g_score[nb] = tentative
                    came_from[nb] = cur
                    heapq.heappush(open_heap, (tentative + h(nb), tentative, nb))
        return []

    # --- Popup nombre (restaurado) ---
    def pedir_nombre_popup(self):
        self.nombre_popup_activo = True
        self.nombre_jugador = ""

    def draw_nombre_popup(self):
        ancho, alto = 450, 180
        x = self.window_width // 2 - ancho // 2
        y = self.window_height // 2 - alto // 2
        arcade.draw_lbwh_rectangle_filled(x, y, ancho, alto, arcade.color.DARK_SLATE_GRAY)
        arcade.draw_lbwh_rectangle_outline(x, y, ancho, alto, arcade.color.WHITE, 3)
        arcade.draw_text("Ingresa tu nombre", x + ancho / 2, y + alto - 40,
                         arcade.color.WHITE, 20, bold=True, anchor_x="center")
        input_box_x = x + 40
        input_box_y = y + alto - 95
        input_box_w = ancho - 80
        input_box_h = 40
        arcade.draw_lbwh_rectangle_filled(input_box_x, input_box_y, input_box_w, input_box_h, arcade.color.BLACK)
        arcade.draw_lbwh_rectangle_outline(input_box_x, input_box_y, input_box_w, input_box_h, arcade.color.WHITE, 1)
        cursor = "|" if math.sin(getattr(self, "tiempo_global", 0) * 10) > 0 else " "
        texto_a_mostrar = self.nombre_jugador + cursor
        arcade.draw_text(texto_a_mostrar, input_box_x + 10, input_box_y + input_box_h // 2,
                         arcade.color.WHITE, 18, anchor_x="left", anchor_y="center")
        arcade.draw_text("Presiona [Enter] para continuar",
                         x + ancho / 2, y + 25,
                         arcade.color.LIGHT_GREEN, 14, anchor_x="center")
        arcade.draw_lbwh_rectangle_filled(x, y, ancho, alto, arcade.color.DARK_SLATE_GRAY)
        arcade.draw_lbwh_rectangle_outline(x, y, ancho, alto, arcade.color.WHITE, 3)
        arcade.draw_text("Ingresa tu nombre", x + ancho / 2, y + alto - 40,
                         arcade.color.WHITE, 20, bold=True, anchor_x="center")
        input_box_x = x + 40
        input_box_y = y + alto - 95
        input_box_w = ancho - 80
        input_box_h = 40
        arcade.draw_lbwh_rectangle_filled(input_box_x, input_box_y, input_box_w, input_box_h, arcade.color.BLACK)
        arcade.draw_lbwh_rectangle_outline(input_box_x, input_box_y, input_box_w, input_box_h, arcade.color.WHITE, 1)
        cursor = "|" if math.sin(getattr(self, "tiempo_global", 0) * 10) > 0 else " "
        texto_a_mostrar = self.nombre_jugador + cursor
        arcade.draw_text(texto_a_mostrar, input_box_x + 10, input_box_y + input_box_h // 2,
                         arcade.color.WHITE, 18, anchor_x="left", anchor_y="center")
        arcade.draw_text("Presiona [Enter] para continuar",
                         x + ancho / 2, y + 25,
                         arcade.color.LIGHT_GREEN, 14, anchor_x="center")

