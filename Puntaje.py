class Puntaje:
    """
    Clase que representa el puntaje de un jugador.
    Permite calcular el puntaje final y mostrarlo de forma legible.
    """

    def __init__(self, score: int, nombre: str):
        """
        Inicializa el puntaje con un valor y el nombre del jugador.
        """
        self.score = score
        self.nombre = nombre

    def calcular_score_final(self, suma_pagos, pay_mult, bonus_tiempo=0, penalizaciones=0):
        """
        Calcula el puntaje final del jugador.

        """
        score_base = suma_pagos * pay_mult
        self.score = score_base + bonus_tiempo - penalizaciones
        return self.score

    def __repr__(self):
        """
        Representación legible del puntaje.
        """
        return f"{self.nombre}: {self.score}"
