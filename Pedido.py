import Coordenada
class Pedido:
    def __init__(self, id, peso, deadline, pago, prioridad=0, coord_recoger=None, coord_entregar=None):
        self.id = id
        self.peso = peso
        self.deadline = deadline
        self.pago = pago
        self.prioridad = prioridad  
        self.coord_recoger = coord_recoger 
        self.coord_entregar = coord_entregar  



