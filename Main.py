from MapaPrueba import MapaWindow
from Repartidor import Repartidor
import arcade

class Juego(arcade.Window):
    def __init__(self):
        super().__init__(800, 600, "Courier Quest")
        self.mapa = MapaWindow()
        self.repartidor = Repartidor("assets/Repartidor2.png")

        def on_draw(self):
            arcade.start_render()
            self.mapa.draw()
            self.repartidor.draw()

if __name__ == "__main__":
    juego = Juego()
    arcade.run()
