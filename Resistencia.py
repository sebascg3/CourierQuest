class Resistencia:
    """
    Clase que gestiona la resistencia del repartidor.
    Controla el gasto y la recuperación de energía según movimiento, peso y clima.
    """

    def __init__(self):
        self.resistencia_actual = 100.0
        self.recuperacion_por_segundo_normal = 2.0  # Recuperación pasiva cuando no se mueve y no agotado
        self.recuperacion_por_segundo_agotado = 0.5  # Recuperación muy lenta cuando agotado (hasta 30%)
        self.recuperacion_minima_para_mover = 30.0  # Umbral para salir del agotamiento
        self.agotado = False

    def actualizar(self, delta_time, esta_moviendo, peso_total, condicion_clima, intensidad_clima):
        """
        Actualiza la resistencia según el estado del jugador y las condiciones.
        """
        # Si está agotado, solo recupera lentamente hasta el 30%
        if self.agotado:
            recuperacion = self.recuperacion_por_segundo_agotado * delta_time
            self.resistencia_actual += recuperacion
            self.resistencia_actual = min(self.resistencia_actual, 100.0)
            if self.resistencia_actual >= self.recuperacion_minima_para_mover:
                self.agotado = False
            return

        # Si no está agotado, procede normalmente
        if esta_moviendo:
            gasto_base = 1.0 * delta_time
            gasto_peso = 0.2 * (peso_total / 10.0) * delta_time
            gasto_clima = 0.0
            if condicion_clima == "lluvia":
                gasto_clima = 0.3 * intensidad_clima * delta_time
            elif condicion_clima == "viento":
                gasto_clima = 0.4 * intensidad_clima * delta_time
            elif condicion_clima == "tormenta":
                gasto_clima = 0.6 * intensidad_clima * delta_time
            elif condicion_clima == "calor":
                gasto_clima = 0.2 * intensidad_clima * delta_time
            gasto_total = gasto_base + gasto_peso + gasto_clima
            self.resistencia_actual -= gasto_total
            self.resistencia_actual = max(self.resistencia_actual, 0.0)
        else:
            recuperacion = self.recuperacion_por_segundo_normal * delta_time
            self.resistencia_actual += recuperacion
            self.resistencia_actual = min(self.resistencia_actual, 100.0)

        if self.resistencia_actual <= 0:
            self.resistencia_actual = 0.0
            self.agotado = True

    def puede_moverse(self):
        """
        Indica si el repartidor puede moverse (no está agotado).
        """
        return not self.agotado

    def get_multiplicador_velocidad(self):
        """
        Devuelve el multiplicador de velocidad según el nivel de resistencia.
        """
        if self.agotado:
            return 0.0
        if self.resistencia_actual < 50:
            return 0.8
        return 1.0

    def get_resistencia_actual(self):
        """
        Devuelve la resistencia actual.
        """
        return self.resistencia_actual

    def set_resistencia(self, valor):
        """
        Establece la resistencia actual y actualiza el estado de agotamiento.
        """
        self.resistencia_actual = float(valor)
        self.agotado = self.resistencia_actual <= 0
