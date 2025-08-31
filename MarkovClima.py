import random

class MarkovClima:
    def __init__(self, condiciones: list[str], matrizTransicion: list[list[float]]):
        """
        :param condiciones: lista de condiciones climáticas (ej. ["clear", "clouds", "rain", "storm"])
        :param matrizTransicion: matriz NxN con probabilidades (cada fila suma 1.0)
        """
        self.condiciones = condiciones
        self.matriz = matrizTransicion

    def calcularSiguiente(self, actual: str) -> str:
        """
        Dado el clima actual, elige el siguiente usando la matriz de transición.
        """
        idx = self.condiciones.index(actual)
        probs = self.matriz[idx]

        # sorteo ponderado según probabilidades
        siguiente = random.choices(self.condiciones, weights=probs, k=1)[0]
        return siguiente
    
    def sortearIntensidad(self) -> float:
        """
        Devuelve una intensidad aleatoria entre 0 y 1.
        """
        return round(random.uniform(0.2, 1.0), 2)

    def sortearDuracion(self) -> int:
        """
        Devuelve la duración de la ráfaga en segundos.
        """
        return random.randint(45, 60)
    
    def obtenerMultiplicador(self, condicion: str) -> float:
        """
        Devuelve el multiplicador base de velocidad según la condición.
        """
        mults = {
            "clear": 1.00,
            "clouds": 0.98,
            "rain_light": 0.90,
            "rain": 0.85,
            "storm": 0.75,
            "fog": 0.88,
            "wind": 0.92,
            "heat": 0.90,
            "cold": 0.92
        }
        return mults.get(condicion, 1.0)
