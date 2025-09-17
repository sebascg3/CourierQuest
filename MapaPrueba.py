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
        self.window_width = 800
        self.window_height = 600
        super().__init__(self.window_width, self.window_height, "Mapa con Repartidor")
        arcade.set_background_color(arcade.color.WHITE)

        self.scale_x = self.window_width / (width * CELL_SIZE) if width > 0 else 1
        self.scale_y = self.window_height / (height * CELL_SIZE) if height > 0 else 1

        self.player_list = arcade.SpriteList()
        self.player_sprite = Repartidor("assets/repartidor.png", scale=0.8)

        while True:
            start_row = random.randint(0, ROWS - 1)
            start_col = random.randint(0, COLS - 1)
            if mapa[start_row][start_col] != "B": 
                
                self.player_sprite.row = start_row
                self.player_sprite.col = start_col
                
                self.player_sprite.center_x = (start_col * CELL_SIZE + CELL_SIZE // 2) * self.scale_x
                self.player_sprite.center_y = (height * CELL_SIZE - (start_row * CELL_SIZE + CELL_SIZE // 2)) * self.scale_y
                break

        self.player_list.append(self.player_sprite)

    def on_draw(self):
        self.clear()
        
        for row in range(ROWS):
            for col in range(COLS):
                x = (col * CELL_SIZE + CELL_SIZE // 2) * self.scale_x
                y = (height * CELL_SIZE - (row * CELL_SIZE + CELL_SIZE // 2)) * self.scale_y
                tipo = mapa[row][col]
                if tipo == "P":
                    color = arcade.color.DARK_GREEN
                elif tipo == "C":
                    color = arcade.color.GRAY
                elif tipo == "B":
                    color = arcade.color.DARK_RED
                else:
                    color = arcade.color.BLACK
                rect = arcade.Rect.from_kwargs(x=x, y=y, width=CELL_SIZE * self.scale_x, height=CELL_SIZE * self.scale_y)
                arcade.draw_rect_filled(rect, color)
                arcade.draw_rect_outline(rect, arcade.color.BLACK, 1)

        self.player_list.draw()

    def on_key_press(self, key, modifiers):
        new_row = self.player_sprite.row
        new_col = self.player_sprite.col

        if key == arcade.key.UP:
            new_row -= 1
        elif key == arcade.key.DOWN:
            new_row += 1
        elif key == arcade.key.LEFT:
            new_col -= 1
        elif key == arcade.key.RIGHT:
            new_col += 1
            
        if (0 <= new_row < ROWS and
            0 <= new_col < COLS and
            mapa[new_row][new_col] != "B"):
            self.player_sprite.row = new_row
            self.player_sprite.col = new_col

            self.player_sprite.center_x = (new_col * CELL_SIZE + CELL_SIZE // 2) * self.scale_x
            self.player_sprite.center_y = (height * CELL_SIZE - (new_row * CELL_SIZE + CELL_SIZE // 2)) * self.scale_y
        

if __name__ == "__main__":
    MapaWindow()
    arcade.run()
