import requests
import arcade



CELL_SIZE = 50  

BASE_URL = "https://tigerds-api.kindflower-ccaf48b6.eastus.azurecontainerapps.io"

city_data = requests.get(f"{BASE_URL}/city/map").json()
data = city_data.get("data", {})

city_name = data.get("city_name", "")
tiles = data.get("tiles", [])
height = data.get("height", 0)
width = data.get("width", 0)              #importacion de las cosas del API
legend = data.get("legend", {})
goal = data.get("goal", {})
max_time = data.get("max_time", 0)



mapa = tiles  # ESTO SE PUEDE CAMBIAR PONIENDO UNA MATRIZ PARA PROBAR

ROWS = len(mapa)  # Número de filas
COLS = len(mapa[0])  # Número de columnas

class MapaWindow(arcade.Window):
    def __init__(self):
        self.window_width = 800   # Ancho de la ventana
        self.window_height = 600   # Alto de la ventana

        super().__init__(self.window_width, self.window_height, "Mapa con Matriz (draw_rect_filled)") 
        arcade.set_background_color(arcade.color.WHITE)

        self.scale_x = self.window_width / (width * CELL_SIZE) if width > 0 else 1   
        self.scale_y = self.window_height / (height * CELL_SIZE) if height > 0 else 1   

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

                rect = arcade.Rect.from_kwargs(
                    x=x,
                    y=y,
                    width=CELL_SIZE * self.scale_x,
                    height=CELL_SIZE * self.scale_y
                )

                arcade.draw_rect_filled(rect, color)
                arcade.draw_rect_outline(rect, arcade.color.BLACK, 1)


if __name__ == "__main__":
    MapaWindow()
    arcade.run()