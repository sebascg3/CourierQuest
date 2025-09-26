
class Clima:
    def __init__(self, condicion: str, intensidad: float, duracion: int, multiplicadorVelocidad: float):
        self.condicion = condicion
        self.intensidad = intensidad
        self.duracion = duracion
        self.tiempoRestante = duracion
        self.multiplicadorVelocidad = multiplicadorVelocidad

    def __str__(self):
        return (f"Clima(condicion={self.condicion}, intensidad={self.intensidad}, "
                f"duracion={self.duracion}, tiempoRestante={self.tiempoRestante})")

    def actualizar(self, delta_time: float) -> bool:
        self.tiempoRestante -= delta_time
        return self.tiempoRestante <= 0

    def reiniciar(self, condicion: str, intensidad: float, duracion: int, multiplicadorVelocidad: float):
        self.condicion = condicion
        self.intensidad = intensidad
        self.duracion = duracion
        self.tiempoRestante = duracion
        self.multiplicadorVelocidad = multiplicadorVelocidad

