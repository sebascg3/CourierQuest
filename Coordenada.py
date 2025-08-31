class Coordenada:
    def __init__(self, x: int, y: int):
        self.x = x
        self.y = y

    def __repr__(self):
        return f"Coordenada(x={self.x}, y={self.y})"