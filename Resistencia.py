class Resistencia:
    def __init__(self, max_resistencia=100.0):
        self.max_resistencia = max_resistencia
        self.resistencia_actual = max_resistencia
        self.exhausto = False  # True si <=0, bloquea movimiento hasta >=30

    def actualizar(self, delta_time, esta_moviendo, peso_total, condicion_clima, intensidad_clima):
        if self.exhausto:
            # Recuperación cuando exhausted (lenta hasta 30%)
            recuperacion = 10 * delta_time  # 10 puntos por segundo cuando no se mueve
            self.resistencia_actual = min(self.resistencia_actual + recuperacion, self.max_resistencia)
            if self.resistencia_actual >= 30:
                self.exhausto = False
            return self.resistencia_actual

        if not esta_moviendo:
            # Recuperación pasiva normal (lenta)
            recuperacion = 3 * delta_time  # 3 puntos por segundo cuando parado
            self.resistencia_actual = min(self.resistencia_actual + recuperacion, self.max_resistencia)
            return self.resistencia_actual

        # Drenaje solo si se mueve
        drenaje_base = 2 * delta_time  # Base por movimiento
        drenaje_peso = 0
        if peso_total > 3:
            drenaje_peso = (peso_total - 3) * 1 * delta_time  # Más peso = más drenaje

        drenaje_clima = 0
        if condicion_clima != "clear":
            drenaje_clima = intensidad_clima * 2 * delta_time  # Clima adverso drena más

        drenaje_total = drenaje_base + drenaje_peso + drenaje_clima
        self.resistencia_actual = max(0, self.resistencia_actual - drenaje_total)

        if self.resistencia_actual <= 0:
            self.exhausto = True

        return self.resistencia_actual

    def puede_moverse(self):
        return not self.exhausto

    def get_multiplicador_velocidad(self):
        if self.exhausto:
            return 0.0
        elif self.resistencia_actual < 50:
            return 0.8  # Cansado: 80% velocidad
        else:
            return 1.0  # Normal
