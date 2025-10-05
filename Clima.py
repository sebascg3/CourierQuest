class Clima:
    """
    Clase que representa el clima actual en el juego.
    Almacena la condición, intensidad, duración y el multiplicador de velocidad.
    """

    def __init__(self, condicion: str, intensidad: float, duracion: int, multiplicadorVelocidad: float):
        """
        Inicializa el clima con condición, intensidad, duración y multiplicador de velocidad.
        """
        self.condicion = condicion
        self.intensidad = intensidad
        self.duracion = duracion
        self.tiempoRestante = duracion
        self.multiplicadorVelocidad = multiplicadorVelocidad

    def __str__(self):
        """
        Devuelve una representación legible del clima.
        """
        return (f"Clima(condicion={self.condicion}, intensidad={self.intensidad}, "
                f"duracion={self.duracion}, tiempoRestante={self.tiempoRestante})")

    def actualizar(self, delta_time: float) -> bool:
        """
        Actualiza el tiempo restante del clima.
        Retorna True si el clima ha terminado.
        """
        self.tiempoRestante -= delta_time
        return self.tiempoRestante <= 0

    def reiniciar(self, condicion: str, intensidad: float, duracion: int, multiplicadorVelocidad: float):
        """
        Reinicia el clima con nuevos valores.
        """
        self.condicion = condicion
        self.intensidad = intensidad
        self.duracion = duracion
        self.tiempoRestante = duracion
        self.multiplicadorVelocidad = multiplicadorVelocidad

