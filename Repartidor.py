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
        self.inventario.agregar_pedido(pedido)
        self.peso_total += pedido.peso

    def pickup(self, pedido: Pedido, tiempo: datetime = None):
        tiempo = tiempo or datetime.now() 
        if self.inventario.agregar_pedido(pedido):
            pedido.tiempo_recogido = tiempo
            return True
        return False

    def dropoff(self, pedido_id: str, tiempo_entrega_contador: float):
        pedido = self.inventario.buscar_pedido(pedido_id)
        if not pedido:
            return [] 
        mensajes_feedback = []
        lavanda = arcade.color.BRIGHT_LAVENDER
        azul = arcade.color.AERO_BLUE
        oro = arcade.color.GOLD

        delta_segundos = tiempo_entrega_contador - pedido.deadline_contador
        
        if delta_segundos < 0: 
            self.racha_entregas_sin_penalizacion = 0
            
            retraso = abs(delta_segundos) 
            penalizacion = 0
            if retraso <= 30: penalizacion = -2
            elif retraso <= 120: penalizacion = -5
            else: penalizacion = -10

            if self.reputacion >= 85 and not self.primera_tardanza_del_dia_usada:
                penalizacion /= 2
                self.primera_tardanza_del_dia_usada = True
                mensajes_feedback.append( ("1ra Tarde: Penalización Reducida", oro) )
            
            self.reputacion += penalizacion
            mensajes_feedback.append( (f"Entrega Tardía: {int(penalizacion)} Rep.", azul) )

        else:  
            tiempo_total_asignado = (15 * 60) - pedido.deadline_contador 
            tiempo_usado = (15 * 60) - tiempo_entrega_contador 
            
            bonificacion = 0
            if tiempo_usado <= tiempo_total_asignado * 0.8:
                bonificacion = 5
                mensajes_feedback.append( (f"¡Entrega Temprana! +{bonificacion} Rep.", lavanda) )
            else:
                bonificacion = 3
                mensajes_feedback.append( (f"Entrega a Tiempo: +{bonificacion} Rep.", lavanda) )
            
            self.reputacion += bonificacion
            self.racha_entregas_sin_penalizacion += 1
            
            if self.racha_entregas_sin_penalizacion >= 3:
                self.reputacion += 2
                self.racha_entregas_sin_penalizacion = 0
                mensajes_feedback.append( ("¡Racha de 3! +2 Rep. Extra", oro) )
        pago = pedido.pago
        if self.reputacion >= 90:
            bonus = pago * 0.05
            pago += bonus
            mensajes_feedback.append( (f"Bonus de Pago: +${bonus:.2f}", oro) )
        self.ingresos += pago
        self.inventario.quitar_pedido(pedido_id)
        self.reputacion = min(self.reputacion, 100)
        
        if self.reputacion < 20:
            self.estado = "Derrota"
            mensajes_feedback.append( ("¡REPUTACIÓN MUY BAJA! - DERROTA", azul) )
        
        return mensajes_feedback

    def actualizar_resistencia(self, delta_time, esta_moviendo, peso_total, condicion_clima, intensidad_clima):
        self.resistencia_obj.actualizar(delta_time, esta_moviendo, peso_total, condicion_clima, intensidad_clima)
    
    def get_resistencia_actual(self):
        return self.resistencia_obj.get_resistencia_actual()
    
    def puede_moverse(self):
        return self.resistencia_obj.puede_moverse()

    #def descansar(self, segundos: float, en_punto_descanso=False):
        #recuperacion = 5 * segundos
        #if en_punto_descanso:
            #recuperacion = 10 * segundos
        #self.resistencia_obj.resistencia_actual = min(100, self.resistencia_obj.resistencia_actual + recuperacion)

    def calcular_velocidad(self, clima_mult: Clima, superficie: float):
        clima_mult_val = getattr(clima_mult, "obtenerMultiplicadorVelocidad", lambda: 1.0)()
        Mpeso = max(0.8, 1 - 0.03 * self.peso_total)
        Mrep = 1.03 if self.reputacion >= 90 else 1.0
        Mres = self.resistencia_obj.get_multiplicador_velocidad() 

        return self.velocidad_base * clima_mult_val * Mpeso * Mrep * Mres * superficie


    def mover(self, coord: Coordenada):
        if not self.puede_moverse():
            return  # No mueve si exhausted
        self.coordenada.x += coord.x
        self.coordenada.y += coord.y
        self.center_x = self.coordenada.x * 30
        self.center_y = self.coordenada.y * 30
