"""
main.py - Archivo principal para correr Courier Quest.
Vincula MapaWindow (que integra Repartidor y toda la lógica del juego)
con el framework de Arcade.
"""

import arcade
from Juego import MapaWindow  # Importa la ventana principal del juego

def main():
    """
    Función principal para inicializar y correr el juego.
    """
    # Crea e inicia la ventana del juego
    window = MapaWindow()

    # Configuraciones globales opcionales (e.g., FPS, tema)
    arcade.enable_timings(60)  # Limita a 60 FPS para performance
    arcade.set_background_color(arcade.color.WHITE)  # Fondo por defecto

    # Corre el loop principal de Arcade
    arcade.run()


if __name__ == "__main__":
    main()
