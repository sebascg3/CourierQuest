class Puntaje:
    def __init__(self, score: int, nombre: str):
        self.score = score
        self.nombre = nombre

    def calcular_score_final(self, suma_pagos, pay_mult, bonus_tiempo=0, penalizaciones=0):
        score_base = suma_pagos * pay_mult
        self.score = score_base + bonus_tiempo - penalizaciones
        return self.score
#el suma pagos seria ingresos de repartidor

    def __repr__(self):
        return f"{self.nombre}: {self.score}"
