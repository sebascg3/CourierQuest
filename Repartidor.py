import arcade
from datetime import datetime
import Pedido
import Inventario
#####coordenadas en clase, metodo mover
class Repartidor(arcade.Sprite):

    def __init__(self, imagen: str, escala: float = 1.0, v0: float = 3.0):
        super().__init__(imagen, escala)

        self.nombre="Repartidor"
        self.resistencia = 100         
        self.reputacion = 70           
        self.ingresos = 0              
        self.inventario = Inventario() 
        self.peso_total = 0            
        self.velocidad_base = v0       

        self.estadoFisico = "Normal"
        self.estado="Jugando"        
        self.tiempo_actual = datetime.now()
        self.x = 0
        self.y = 0

    def aceptar_pedido(self, pedido: Pedido):
        self.inventario.agregar_pedido(pedido)
        self.peso_total += pedido.weight

    def entregar_pedido(self, pedido_id: str, tiempo_entrega: datetime):
        pedido = self.inventario.buscar_pedido(pedido_id)
        if not pedido:
            return False

        self.inventario.quitar_pedido(pedido_id)
        self.peso_total -= pedido.weight

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
         #falta acá que se termine el juego pq está derrotado

        return True

    def actualizar_resistencia(self, clima: str):
        gasto = 0.5
        if self.peso_total > 3:
            gasto += 0.2 * (self.peso_total - 3)

        if clima in ("lluvia", "viento"):
            gasto += 0.1
        elif clima == "tormenta":
            gasto += 0.3
        elif clima == "calor":
            gasto += 0.2

        self.resistencia -= gasto
        self.resistencia = max(self.resistencia, 0)

        if self.resistencia <= 0:
            self.estadoFisico = "Exhausto"
        else:
            self.estadoFisico = "Normal"

    def descansar(self, segundos: float, en_punto_descanso=False):
        recuperacion = 5 * segundos
        if en_punto_descanso:
            recuperacion = 10 * segundos

        self.resistencia = min(100, self.resistencia + recuperacion)

    def calcular_velocidad(self, clima_mult: float, superficie: float):
        Mpeso = max(0.8, 1 - 0.03 * self.peso_total)
        Mrep = 1.03 if self.reputacion >= 90 else 1.0
        Mres = 1.0 if self.estadoFisico == "Normal" else (0.8 if self.estadoFisico == "Cansado" else 0.0)

        return self.velocidad_base * clima_mult * Mpeso * Mrep * Mres * superficie
