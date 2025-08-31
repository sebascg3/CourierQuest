from Pedido import Pedido

######metodos para ordenar por prioridad y por deadline
class Inventario:
    def __init__(self):
        self.pedidos = []  

    def agregar_pedido(self, pedido: Pedido):
        self.pedidos.append(pedido)

    def quitar_pedido(self, pedido_num: str):
        self.pedidos = [p for p in self.pedidos if p.num != pedido_num]

    def buscar_pedido(self, pedido_id: str):
        return next((p for p in self.pedidos if p.id == pedido_id), None)

    def peso_total(self):
        return sum(p.weight for p in self.pedidos)
