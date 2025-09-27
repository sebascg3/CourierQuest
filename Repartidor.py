import arcade
from datetime import datetime
import Pedido
from Inventario import Inventario
import Clima
import Coordenada
from Resistencia import Resistencia

class Repartidor(arcade.Sprite):
    def __init__(self, *args, **kwargs): 
        super().__init__(*args, **kwargs)


        self.nombre = "Repartidor"
        self.resistencia_obj = Resistencia(100.0)
        self.reputacion = 70
        self.ingresos = 0
        self.inventario = Inventario()
        self.coordenada = Coordenada.Coordenada(0, 0)
        self.peso_total = 0
        self.velocidad_base = 0

        self.estadoFisico = "Normal"
        self.estado = "Jugando"
        self.tiempo_actual = datetime.now()

    def aceptar_pedido(self, pedido: Pedido):
        self.inventario.agregar_pedido(pedido)
        self.peso_total += pedido.peso

    def pickup(self, pedido: Pedido, tiempo: datetime = None):
       tiempo = tiempo or datetime.now() 
       if self.inventario.agregar_pedido(pedido):
         self.peso_total += pedido.peso
         pedido.tiempo_recogido = tiempo
         return True
       return False


    def dropoff(self, pedido_id: str, tiempo_entrega: datetime):
        pedido = self.inventario.buscar_pedido(pedido_id)
        if not pedido:
            return False

        self.inventario.quitar_pedido(pedido_id)
        self.peso_total -= pedido.peso

        deadline = datetime.fromisoformat(pedido.deadline)
        delta = (tiempo_entrega - deadline).total_seconds()

        if delta <= -0.2 * (deadline - self.tiempo_actual).total_seconds():
            self.reputacion += 5
        elif delta <= 0:
            self.reputacion += 3
        elif delta <= 30:
            self.reputacion -= 2
        elif delta <= 120:
            self.reputacion -= 5
        else:
            self.reputacion -= 10

        pago = pedido.pago
        if self.reputacion >= 90:
            pago *= 1.05
        self.ingresos += pago

        if self.reputacion < 20:
            self.estado = "Derrota"

        return True

    def actualizar_resistencia(self, delta_time, clima):
        # Llama a la nueva clase para actualizar
        self.resistencia_obj.actualizar(delta_time, self.moving if hasattr(self, 'moving') else False, self.peso_total, clima.condicion, clima.intensidad)

    def descansar(self, segundos: float, en_punto_descanso=False):
        recuperacion = 5 * segundos
        if en_punto_descanso:
            recuperacion = 10 * segundos
        self.resistencia_obj.resistencia_actual = min(100, self.resistencia_obj.resistencia_actual + recuperacion)

    def calcular_velocidad(self, clima_mult: Clima, superficie: float):
        clima_mult_val = getattr(clima_mult, "obtenerMultiplicadorVelocidad", lambda: 1.0)()
        Mpeso = max(0.8, 1 - 0.03 * self.peso_total)
        Mrep = 1.03 if self.reputacion >= 90 else 1.0
        Mres = self.resistencia_obj.get_multiplicador_velocidad()

        return self.velocidad_base * clima_mult_val * Mpeso * Mrep * Mres * superficie

    def get_resistencia_actual(self):
        return self.resistencia_obj.resistencia_actual
    def puede_moverse(self):
        return self.resistencia_obj.puede_moverse()
    def mover(self, coord: Coordenada):
        if not self.puede_moverse():
            return  # No mueve si exhausted
        self.coordenada.x += coord.x
        self.coordenada.y += coord.y
        self.center_x = self.coordenada.x * 30
        self.center_y = self.coordenada.y * 30
