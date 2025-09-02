from Pedido import Pedido

class NodoPedido:
    def __init__(self, pedido: Pedido):
        self.pedido = pedido
        self.siguiente = None
        self.anterior = None


class Inventario:
    def __init__(self, peso_maximo=5):
        self.inicio = None
        self.fin = None
        self.peso_maximo = peso_maximo
        self._peso_total = 0
        self._cantidad = 0

    def agregar_pedido(self, pedido: Pedido):
        if self._peso_total + pedido.peso > self.peso_maximo:
            return False  
        nodo = NodoPedido(pedido)
        if not self.inicio:
            self.inicio = self.fin = nodo
        else:
            self.fin.siguiente = nodo
            nodo.anterior = self.fin
            self.fin = nodo
        self._peso_total += pedido.peso
        self._cantidad += 1
        return True

    def quitar_pedido(self, pedido_id: str):
        actual = self.inicio
        while actual:
            if actual.pedido.id == pedido_id:
                if actual.anterior:
                    actual.anterior.siguiente = actual.siguiente
                else:
                    self.inicio = actual.siguiente
                if actual.siguiente:
                    actual.siguiente.anterior = actual.anterior
                else:
                    self.fin = actual.anterior
                self._peso_total -= actual.pedido.peso
                self._cantidad -= 1
                return True
            actual = actual.siguiente
        return False

    def buscar_pedido(self, pedido_id: str):
        actual = self.inicio
        while actual:
            if actual.pedido.id == pedido_id:
                return actual.pedido
            actual = actual.siguiente
        return None

    def peso_total(self):
        return self._peso_total

    def cantidad(self):
        return self._cantidad



    def acomodar_prioridad(self):######
        pedidos = list(self.recorrer_adelante())
        return sorted(pedidos, key=lambda p: p.prioridad, reverse=True)

    def acomodar_deadline(self):#####
        pedidos = list(self.recorrer_adelante())
        return sorted(pedidos, key=lambda p: p.deadline)

