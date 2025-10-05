import arcade
from datetime import datetime
import Pedido
from Inventario import Inventario
import Clima
import Coordenada
from Resistencia import Resistencia


class Repartidor(arcade.Sprite):
    """
    Clase que representa al repartidor/jugador principal.
    Gestiona inventario, reputación, ingresos, resistencia y lógica de pedidos.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.nombre = "Repartidor"
        self.reputacion = 70
        self.ingresos = 0
        self.inventario = Inventario()
        self.coordenada = Coordenada.Coordenada(0, 0)
        self.peso_total = 0
        self.velocidad_base = 0
        self.resistencia_obj = Resistencia()
        self.estado = "Jugando"
        self.tiempo_actual = datetime.now()
        self.reputacion = 70
        self.tiempos_recogida = {}
        self.racha_entregas_sin_penalizacion = 0
        self.primera_tardanza_del_dia_usada = False

    def aceptar_pedido(self, pedido: Pedido):
        """
        Agrega un pedido al inventario y suma su peso.
        """
        self.inventario.agregar_pedido(pedido)
        self.peso_total += pedido.peso

    def pickup(self, pedido: Pedido, tiempo_actual_contador: float):
        """
        Recoge un pedido y registra el tiempo de recogida.
        """
        if self.inventario.agregar_pedido(pedido):
            pedido.tiempo_recogido_contador = tiempo_actual_contador
            return True
        return False

    def dropoff(self, pedido_id: str, tiempo_entrega_contador: float):
        """
        Entrega un pedido, calcula penalizaciones o bonificaciones y actualiza reputación e ingresos.
        Devuelve mensajes de feedback para el jugador.
        """
        pedido = self.inventario.buscar_pedido(pedido_id)
        if not pedido:
            return []
        mensajes_feedback = []
        lavanda = arcade.color.BRIGHT_LAVENDER
        azul = arcade.color.AERO_BLUE
        oro = arcade.color.GOLD

        delta_segundos = tiempo_entrega_contador - pedido.deadline_contador

        if delta_segundos < 0:
            # Entrega tardía: penalización a la reputación
            self.racha_entregas_sin_penalizacion = 0

            retraso = abs(delta_segundos)
            penalizacion = 0
            if retraso <= 30:
                penalizacion = -2
            elif retraso <= 120:
                penalizacion = -5
            else:
                penalizacion = -10

            # Primera tardanza del día: penalización reducida
            if self.reputacion >= 85 and not self.primera_tardanza_del_dia_usada:
                penalizacion /= 2
                self.primera_tardanza_del_dia_usada = True
                mensajes_feedback.append(("1ra Tarde: Penalización Reducida", oro))

            self.reputacion += penalizacion
            mensajes_feedback.append((f"Entrega Tardía: {int(penalizacion)} Rep.", azul))

        else:
            # Entrega a tiempo o temprana: bonificación a la reputación
            tiempo_total_asignado = pedido.tiempo_recogido_contador - pedido.deadline_contador
            tiempo_usado = pedido.tiempo_recogido_contador - tiempo_entrega_contador

            bonificacion = 0
            if tiempo_usado <= tiempo_total_asignado * 0.8:
                bonificacion = 5
                mensajes_feedback.append((f"¡Entrega Temprana! +{bonificacion} Rep.", lavanda))
            else:
                bonificacion = 3
                mensajes_feedback.append((f"Entrega a Tiempo: +{bonificacion} Rep.", lavanda))

            self.reputacion += bonificacion
            self.racha_entregas_sin_penalizacion += 1

            # Bonificación por racha de entregas sin penalización
            if self.racha_entregas_sin_penalizacion >= 3:
                self.reputacion += 2
                self.racha_entregas_sin_penalizacion = 0
                mensajes_feedback.append(("¡Racha de 3! +2 Rep. Extra", oro))

        pago = pedido.pago
        # Bonus de pago por reputación alta
        if self.reputacion >= 90:
            bonus = pago * 0.05
            pago += bonus
            mensajes_feedback.append((f"Bonus de Pago: +${bonus:.2f}", oro))
        self.ingresos += pago
        self.inventario.quitar_pedido(pedido_id)
        self.reputacion = min(self.reputacion, 100)

        # Derrota si la reputación es muy baja
        if self.reputacion < 20:
            self.estado = "Derrota"
            mensajes_feedback.append(("REPUTACIÓN MUY BAJA - DERROTA", azul))

        return mensajes_feedback

    def cancelar_pedido(self, pedido_id: str):
        """
        Cancela un pedido, penaliza la reputación y verifica derrota.
        """
        pedido = self.inventario.buscar_pedido(pedido_id)
        if pedido:
            self.reputacion -= 4
            self.inventario.quitar_pedido(pedido_id)

            if self.reputacion < 20:
                self.estado = "Derrota"

            return True

        return False

    def actualizar_resistencia(self, delta_time, esta_moviendo, peso_total, condicion_clima, intensidad_clima):
        """
        Actualiza la resistencia del repartidor según el estado y condiciones.
        """
        self.resistencia_obj.actualizar(
            delta_time, esta_moviendo, peso_total, condicion_clima, intensidad_clima
        )

    def get_resistencia_actual(self):
        """
        Devuelve la resistencia actual.
        """
        return self.resistencia_obj.get_resistencia_actual()

    def puede_moverse(self):
        """
        Indica si el repartidor puede moverse (no está agotado).
        """
        return self.resistencia_obj.puede_moverse()

    def calcular_velocidad(self, clima_mult: Clima, superficie: float):
        """
        Calcula la velocidad del repartidor considerando clima, peso, reputación y resistencia.
        """
        clima_mult_val = getattr(
            clima_mult, "obtenerMultiplicadorVelocidad", lambda: 1.0
        )()
        Mpeso = max(0.8, 1 - 0.03 * self.peso_total)
        Mrep = 1.03 if self.reputacion >= 90 else 1.0
        Mres = self.resistencia_obj.get_multiplicador_velocidad()

        return self.velocidad_base * clima_mult_val * Mpeso * Mrep * Mres * superficie

    def mover(self, coord: Coordenada):
        """
        Mueve al repartidor en el mapa si tiene suficiente resistencia.
        """
        if not self.puede_moverse():
            return  # No mueve si exhausted
        self.coordenada.x += coord.x
        self.coordenada.y += coord.y
        self.center_x = self.coordenada.x * 30
        self.center_y = self.coordenada.y * 30

    def pedidos_ids(self):
        """
        Retorna lista de IDs de pedidos en el inventario del repartidor.
        """
        ids = []
        # Accede al inventario del repartidor y recorre la lista doblemente enlazada
        nodo = self.inventario.inicio
        while nodo:
            ids.append(nodo.pedido.id)
            nodo = nodo.siguiente
        return ids
