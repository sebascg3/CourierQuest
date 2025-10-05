import Coordenada


class Pedido:
    """
    Clase que representa un pedido en el juego Courier Quest.
    Contiene información sobre el pedido, como peso, pago, prioridad y coordenadas.
    """

    def __init__(self, id, peso, deadline, pago, prioridad=0,
                 coord_recoger=None, coord_entregar=None, release_time=0.0):
        """
        Inicializa un nuevo pedido.
        """
        self.id = id
        self.peso = peso
        self.deadline = deadline
        self.deadline_contador = 0.0
        self.pago = pago
        self.prioridad = prioridad
        self.coord_recoger = coord_recoger
        self.coord_entregar = coord_entregar
        self.release_time = release_time
        self.tiempo_expiracion = 0.0




