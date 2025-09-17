import requests
import arcade
import random

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

        # Escalado para ajustar mapa al tamaño de ventana
        self.scale_x = self.window_width / (width * CELL_SIZE) if width > 0 else 1
        self.scale_y = self.window_height / (height * CELL_SIZE) if height > 0 else 1

        # Repartidor en coordenadas aleatorias libres
        while True:
            self.player_row = random.randint(0, ROWS - 1)
            self.player_col = random.randint(0, COLS - 1)
            if mapa[self.player_row][self.player_col] != "B":  # no iniciar en muro
                break

    def on_draw(self): 
        self.clear() # Dibujar el mapa 
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
                else: color = arcade.color.BLACK 
                rect = arcade.Rect.from_kwargs( x=x, y=y, width=CELL_SIZE * self.scale_x, height=CELL_SIZE * self.scale_y ) 
                arcade.draw_rect_filled(rect, color) 
                arcade.draw_rect_outline(rect, arcade.color.BLACK, 1)

        # Dibujar repartidor como círculo azul
        px = (self.player_col * CELL_SIZE + CELL_SIZE // 2) * self.scale_x
        py = (height * CELL_SIZE - (self.player_row * CELL_SIZE + CELL_SIZE // 2)) * self.scale_y
        arcade.draw_circle_filled(px, py, 15, arcade.color.BLUE)

    def on_key_press(self, key, modifiers):
        # Movimiento del jugador
        if key == arcade.key.UP and self.player_row > 0 and mapa[self.player_row-1][self.player_col] != "B":
            self.player_row -= 1
        elif key == arcade.key.DOWN and self.player_row < ROWS - 1 and mapa[self.player_row+1][self.player_col] != "B":
            self.player_row += 1
        elif key == arcade.key.LEFT and self.player_col > 0 and mapa[self.player_row][self.player_col-1] != "B":
            self.player_col -= 1
        elif key == arcade.key.RIGHT and self.player_col < COLS - 1 and mapa[self.player_row][self.player_col+1] != "B":
            self.player_col += 1

if __name__ == "__main__":
    MapaWindow()
    arcade.run()
