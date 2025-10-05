from Pedido import Pedido


class NodoPedido:
    """
    Nodo de la lista doblemente enlazada para pedidos.
    """

    def __init__(self, pedido: Pedido):
        self.pedido = pedido
        self.siguiente = None
        self.anterior = None


class Inventario:
    """
    Inventario implementado como lista doblemente enlazada.
    Permite agregar, quitar, buscar y ordenar pedidos.
    """

    def __init__(self):
        self.inicio = None
        self.fin = None
        self.peso_maximo = 10
        self._peso_total = 0
        self._cantidad = 0

    def agregar_pedido(self, pedido: Pedido):
        """
        Agrega un pedido al inventario si no supera el peso máximo.
        """
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
        """
        Quita un pedido del inventario por su ID.
        """
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
        """
        Busca un pedido por su ID.
        """
        actual = self.inicio
        while actual:
            if actual.pedido.id == pedido_id:
                return actual.pedido
            actual = actual.siguiente
        return None

    def peso_total(self):
        """
        Devuelve el peso total de los pedidos en el inventario.
        """
        return self._peso_total

    def cantidad(self):
        """
        Devuelve la cantidad de pedidos en el inventario.
        """
        return self._cantidad

    def recorrer_adelante(self):
        """
        Generador para recorrer los pedidos desde el inicio hacia el final.
        """
        actual = self.inicio
        while actual:
            yield actual.pedido
            actual = actual.siguiente

    def recorrer_atras(self):
        """
        Generador para recorrer los pedidos desde el final hacia el inicio.
        """
        actual = self.fin
        while actual:
            yield actual.pedido
            actual = actual.anterior

    def acomodar_prioridad(self):
        """
        Devuelve una lista de pedidos ordenados por prioridad descendente.
        """
        pedidos = list(self.recorrer_adelante())
        return sorted(pedidos, key=lambda p: p.prioridad, reverse=True)

    def acomodar_deadline(self):
        """
        Devuelve una lista de pedidos ordenados por deadline ascendente.
        """
        pedidos = list(self.recorrer_adelante())
        return sorted(pedidos, key=lambda p: p.deadline)

    def vaciar(self):
        """
        Vacía el inventario de pedidos.
        """
        self.inicio = None
        self.fin = None
        self._cantidad = 0
        self._peso_total = 0.0

