import random

class MarkovClima:
    def __init__(self, condiciones: list[str], matrizTransicion: list[list[float]]):
        """
        Inicializa el modelo de Markov con las condiciones y la matriz de transición.
        """
        self.condiciones = condiciones
        self.matriz = matrizTransicion

    def calcularSiguiente(self, actual: str) -> str:
        """
        Dado el clima actual, elige el siguiente usando la matriz de transición.
        Si la condición no existe, usa la primera condición como fallback.
        """
        try:
            idx = self.condiciones.index(actual)
        except ValueError:
            idx = 0
        probs = self.matriz[idx]
        if not any(probs):
            # Si la fila está vacía, fallback a la primera condición
            return self.condiciones[0]
        siguiente = random.choices(self.condiciones, weights=probs, k=1)[0]
        return siguiente
    
    def sortearIntensidad(self) -> float:
        """
        Devuelve una intensidad aleatoria entre 0 y 1.
        """
        return round(random.uniform(0.2, 1.0), 2)

    def sortearDuracion(self) -> int:
        """
        Devuelve la duración de la ráfaga en segundos (normal: 45-60s).
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
