import arcade
import requests

WINDOW_WIDTH = 1280
WINDOW_HEIGHT = 720
WINDOW_TITLE = "Courier Quest"

TILE_SIZE = 32  # Tamaño de cada tile

# Colores para cada tipo de tile (ajusta según los símbolos que devuelve la API)
TILE_COLORS = {
    "R": arcade.color.GRAY,         # Road
    "B": arcade.color.DARK_BROWN,   # Building
    "P": arcade.color.GREEN,        # Park
    "W": arcade.color.BLUE,         # Water
    # Agrega más símbolos según lo que devuelva la API
}

class DeliveryGame(arcade.Window):
    def __init__(self):
        super().__init__(WINDOW_WIDTH, WINDOW_HEIGHT, WINDOW_TITLE)
        self.background_color = arcade.color.AMAZON
        self.scene = arcade.Scene()

    def setup(self):
        """Carga el mapa desde la API y lo convierte en sprites"""
        url = "https://tigerds-api.kindflower-ccaf48b6.eastus.azurecontainerapps.io/city/map"
        try:
            response = requests.get(url)
            response.raise_for_status()
            self.city_data = response.json()["data"]
        except Exception as e:
            print(f"Error al obtener el mapa: {e}")
            self.city_data = {"tiles": [], "height": 0}

        tiles = self.city_data.get("tiles", [])
        height = self.city_data.get("height", 0)

        for row_idx, row in enumerate(tiles):
            for col_idx, symbol in enumerate(row):
                x = col_idx * TILE_SIZE + TILE_SIZE // 2
                y = (height - row_idx - 1) * TILE_SIZE + TILE_SIZE // 2

                color = TILE_COLORS.get(symbol, arcade.color.BLUE_GREEN)
                sprite = arcade.SpriteSolidColor(TILE_SIZE, TILE_SIZE, color)
                sprite.center_x, sprite.center_y = x, y
                self.scene.add_sprite("map", sprite)

    def on_draw(self):
        """Dibuja la escena en cada frame"""
        self.clear()
        self.scene.draw()

if __name__ == "__main__":
    game = DeliveryGame()
    game.setup() 
    arcade.run()
