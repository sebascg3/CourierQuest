class Resistencia:
    def __init__(self):
        self.resistencia_actual = 100.0
        self.recuperacion_por_segundo_normal = 2.0  # Recuperación pasiva cuando no se mueve y no agotado
        self.recuperacion_por_segundo_agotado = 0.5  # Recuperación muy lenta cuando agotado (hasta 30%)
        self.recuperacion_minima_para_mover = 30.0  # Umbral para salir del agotamiento (no bloquea movimiento antes de 0)
        self.agotado = False

    def actualizar(self, delta_time, esta_moviendo, peso_total, condicion_clima, intensidad_clima):
        # Si está agotado, forzar descanso: no gastar, solo recuperar lento hasta 30%
        if self.agotado:
            recuperacion = self.recuperacion_por_segundo_agotado * delta_time
            self.resistencia_actual += recuperacion
            self.resistencia_actual = min(self.resistencia_actual, 100.0)
            # Verificar si ya recuperó lo suficiente para desagotarse (solo al 30%)
            if self.resistencia_actual >= self.recuperacion_minima_para_mover:
                self.agotado = False
            return  # No hace nada más si agotado (no gasta, no mueve)

        # Si no está agotado, proceder normal (se mueve libremente hasta llegar a 0)
        if esta_moviendo:
            # Gasto base por movimiento
            gasto_base = 1.0 * delta_time            # Aumenta con peso (más peso, más gasto)
            gasto_peso = 0.2 * (peso_total / 10.0) * delta_time  # Asume peso max ~10 para escalar
            # Aumenta con clima adverso
            gasto_clima = 0.0
            if condicion_clima == "lluvia":
                gasto_clima = 0.3 * intensidad_clima * delta_time
            elif condicion_clima == "viento":
                gasto_clima = 0.4 * intensidad_clima * delta_time
            elif condicion_clima == "tormenta":
                gasto_clima = 0.6 * intensidad_clima * delta_time
            elif condicion_clima == "calor":
                gasto_clima = 0.2 * intensidad_clima * delta_time
            # Gasto total
            gasto_total = gasto_base + gasto_peso + gasto_clima
            self.resistencia_actual -= gasto_total
            self.resistencia_actual = max(self.resistencia_actual, 0.0)
        else:
            # Recuperación pasiva normal (lenta, solo cuando no se mueve)
            recuperacion = self.recuperacion_por_segundo_normal * delta_time
            self.resistencia_actual += recuperacion
            self.resistencia_actual = min(self.resistencia_actual, 100.0)

        # Verificar si llegó exactamente a 0 y setear agotado
        if self.resistencia_actual <= 0:
            self.resistencia_actual = 0.0
            self.agotado = True

    def puede_moverse(self):
        # Solo bloquea si agotado (se mueve libremente hasta 0, y después de recuperar al 30%)
        return not self.agotado

    def get_multiplicador_velocidad(self):
        if self.agotado:
            return 0.0
        elif self.resistencia_actual < 50:
            return 0.8  # Cansado: 80% velocidad (pero sigue moviéndose)
        else:
            return 1.0  # Normal

    def get_resistencia_actual(self):
        return self.resistencia_actual

    def set_resistencia(self, valor):
        self.resistencia_actual = float(valor)
        self.agotado = self.resistencia_actual <= 0
