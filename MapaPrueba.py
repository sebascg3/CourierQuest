import requests
import arcade
import random
from Repartidor import Repartidor 

CELL_SIZE = 50
BASE_URL = "https://tigerds-api.kindflower-ccaf48b6.eastus.azurecontainerapps.io"

# Obtener datos de la ciudad
city_data = requests.get(f"{BASE_URL}/city/map").json()
data = city_data.get("data", {})

tiles = data.get("tiles", [])
height = data.get("height", 0)
width = data.get("width", 0)

mapa = tiles
ROWS = len(mapa)
COLS = len(mapa[0])

class MapaWindow(arcade.Window):
    def __init__(self):
        self.active_direction = None  # Dirección activa
        self.window_width = 800
        self.window_height = 600
        super().__init__(self.window_width, self.window_height, "Mapa con Repartidor")
        arcade.set_background_color(arcade.color.WHITE)

        self.scale_x = self.window_width / (width * CELL_SIZE) if width > 0 else 1
        self.scale_y = self.window_height / (height * CELL_SIZE) if height > 0 else 1

        self.player_list = arcade.SpriteList()
        self.player_sprite = Repartidor("assets/repartidor.png", scale=0.8)

        # Texturas para tiles
        self.tex_parque = arcade.load_texture("assets/Parque.png")
        self.tex_edificio = arcade.load_texture("assets/Edificio.png")

        # Elegir posición inicial válida
        while True:
            start_row = random.randint(0, ROWS - 1)
            start_col = random.randint(0, COLS - 1)
            if mapa[start_row][start_col] != "B": 
                self.player_sprite.row = start_row
                self.player_sprite.col = start_col
                # Posición actual en píxeles
                self.player_sprite.center_x = (start_col * CELL_SIZE + CELL_SIZE // 2) * self.scale_x
                self.player_sprite.center_y = (height * CELL_SIZE - (start_row * CELL_SIZE + CELL_SIZE // 2)) * self.scale_y
                break

        # Destino objetivo en píxeles
        self.target_x = self.player_sprite.center_x
        self.target_y = self.player_sprite.center_y
        self.target_row = self.player_sprite.row
        self.target_col = self.player_sprite.col
        self.moving = False
        self.move_speed = 10  # píxeles por frame
        self.player_list.append(self.player_sprite)

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
                    # Otros tipos siguen con color sólido
                    color = arcade.color.GRAY if tipo == "C" else arcade.color.BLACK
                    arcade.draw_rect_filled(rect, color)

                # Borde de la celda
                arcade.draw_rect_outline(rect, arcade.color.BLACK, 1)

        self.player_list.draw()

    def on_key_press(self, key, modifiers):
        # Registrar dirección activa
        if key in (arcade.key.UP, arcade.key.DOWN, arcade.key.LEFT, arcade.key.RIGHT):
            self.active_direction = key
        self.try_move()

    def on_key_release(self, key, modifiers):
        # Borrar dirección activa si se suelta
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

    def on_update(self, delta_time):
        if self.moving:
            dx = self.target_x - self.player_sprite.center_x
            dy = self.target_y - self.player_sprite.center_y
            dist = (dx ** 2 + dy ** 2) ** 0.5
            if dist < self.move_speed:
                # Llega al destino
                self.player_sprite.center_x = self.target_x
                self.player_sprite.center_y = self.target_y
                self.player_sprite.row = self.target_row
                self.player_sprite.col = self.target_col
                self.moving = False
                # Si hay dirección activa, intentar mover de nuevo
                self.try_move()
            else:
                # Movimiento suave
                self.player_sprite.center_x += self.move_speed * dx / dist
                self.player_sprite.center_y += self.move_speed * dy / dist
        

if __name__ == "__main__":
    MapaWindow()
    arcade.run()
