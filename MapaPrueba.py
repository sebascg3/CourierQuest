
import requests
import arcade
import random
from datetime import datetime
from Pedido import Pedido
from Repartidor import Repartidor
from Clima import Clima
from MarkovClima import MarkovClima

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

    def draw_clima_info(self):
        # Texto del clima
        texto = f"Clima: {self.clima.condicion}\n"
        texto += f"Intensidad: {self.clima.intensidad:.2f}\n"
        texto += f"Tiempo restante: {int(self.clima.tiempoRestante)}s"
        ancho = 180
        alto = 70
        x = 0
        y = 0
        arcade.draw_lbwh_rectangle_filled(x, y, ancho, alto, arcade.color.LIGHT_GRAY)
        arcade.draw_lbwh_rectangle_outline(x, y, ancho, alto, arcade.color.DARK_GRAY, 2)
        arcade.draw_text(
            texto,
            x + 10, y + alto,
            arcade.color.BLACK, 13,
            anchor_x="left", anchor_y="top",
            multiline=True,
            width=ancho-20
        )


    def cambiar_clima(self):
        nueva_cond = self.markov.calcularSiguiente(self.clima.condicion)
        nueva_intensidad = self.markov.sortearIntensidad()
        nueva_duracion = self.markov.sortearDuracion()
        nuevo_mult = self.markov.obtenerMultiplicador(nueva_cond)
        self.iniciar_transicion_clima(nueva_cond, nueva_intensidad, nueva_duracion, nuevo_mult)




    def __init__(self):
        self.active_direction = None
        self.window_width = 800
        self.window_height = 600
        super().__init__(self.window_width, self.window_height, "Mapa con Repartidor")
        arcade.set_background_color(arcade.color.WHITE)
        self.scale_x = self.window_width / (width * CELL_SIZE) if width > 0 else 1
        self.scale_y = self.window_height / (height * CELL_SIZE) if height > 0 else 1
        self.player_list = arcade.SpriteList()
        self.player_sprite = Repartidor("assets/repartidor.png", scale=0.8)
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



    def draw_popup_pedido(self):
     if self.mostrar_pedido and self.pedido_actual:
        ancho, alto = 400, 150
        x = self.window_width // 2 - ancho // 2
        y = self.window_height // 2 - alto // 2

        arcade.draw_lbwh_rectangle_filled(x, y, ancho, alto, arcade.color.BLACK)
        arcade.draw_lbwh_rectangle_outline(x, y, ancho, alto, arcade.color.BLACK, 2)

        arcade.draw_text(#cambiar esto para que no quede pegado
            f"Nuevo pedido: {self.pedido_actual.id}\n"
            f"Peso: {self.pedido_actual.peso}\n"
            f"Pago: ${self.pedido_actual.pago}",
            x + 20, y + alto - 20,
            arcade.color.WHITE, 14,
            anchor_x="left", anchor_y="top"
        )
        arcade.draw_text(
            "[A]ceptar   [R]echazar",
            x + 120, y + 55,
            arcade.color.WHITE, 14
        )




    def on_draw(self):
        self.clear()
        for row in range(ROWS):
            for col in range(COLS):
                x = (col * CELL_SIZE + CELL_SIZE // 2) * self.scale_x
                y = (height * CELL_SIZE - (row * CELL_SIZE + CELL_SIZE // 2)) * self.scale_y
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
        texto = ""
        pedidos = []
        nodo = self.player_sprite.inventario.inicio
        while nodo:
            pedidos.append(nodo.pedido.id)
            nodo = nodo.siguiente
        texto = f"Pedidos: {', '.join(pedidos) if pedidos else 'Ninguno'}\n"
        texto += f"Peso: {self.player_sprite.peso_total:.1f}/{self.player_sprite.inventario.peso_maximo}\n"
        texto += f"Ingresos: ${self.player_sprite.ingresos:.2f}\n"
        texto += f"Reputación: {self.player_sprite.reputacion}"
        arcade.draw_text(
            texto,
            x=10, 
            y=self.window_height - 10, 
            color=arcade.color.BLACK,
            font_size=12,
            anchor_y="top",
            multiline=True,
            width=200 
        )
        minutes = int(self.total_time) // 60
        seconds = int(self.total_time) % 60
        time_text = f"{minutes:02d}:{seconds:02d}"
        arcade.draw_text(
            time_text,
            x=self.window_width - 10,
            y=self.window_height - 10,
            color=arcade.color.RED,
            font_size=20,
            anchor_x="right",
            anchor_y="top"
        )
        self.draw_popup_pedido()
        self.draw_clima_info()

    def on_key_press(self, key, modifiers):
        if key in (arcade.key.UP, arcade.key.DOWN, arcade.key.LEFT, arcade.key.RIGHT):
            self.active_direction = key
        self.try_move()

    def on_key_release(self, key, modifiers):
       if self.mostrar_pedido and self.pedido_actual:
           if key == arcade.key.A: 
               pedido = self.pedido_actual
               #Para saber cuando acepta
               print(f"Pedido {pedido.id} aceptado")
               self.pedidos_activos[pedido.id] = pedido 
               pickup_x, pickup_y = self.celda_a_pixeles(*pedido.coord_recoger)
               dropoff_x, dropoff_y = self.celda_a_pixeles(*pedido.coord_entregar)
               self.crear_pedido(pickup_x, pickup_y, dropoff_x, dropoff_y, pedido.id)

               self.mostrar_pedido = False
               self.pedido_actual = None

           elif key == arcade.key.R:  
                #Parafijarnos los que rechaza
                print(f"Pedido {self.pedido_actual.id} rechazado")
                self.mostrar_pedido = False
                self.pedido_actual = None

       if self.active_direction == key:
            self.active_direction = None

    def try_move(self):
        if self.moving or self.active_direction is None:
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
