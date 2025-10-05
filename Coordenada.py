class Coordenada:
    """
    Clase que representa una coordenada (x, y) en el mapa.
    """

    def __init__(self, x: int, y: int):
        """
        Inicializa la coordenada con valores x e y.
        """
        self.x = x
        self.y = y

    def __repr__(self):
        """
        Devuelve una representación legible de la coordenada.
        """
        return f"Coordenada(x={self.x}, y={self.y})"