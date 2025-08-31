class Puntaje:
    def __init__(self, score: int, nombre: str):
        self.score = score
        self.nombre = nombre

    def __repr__(self):
        return f"{self.nombre}: {self.score}"
