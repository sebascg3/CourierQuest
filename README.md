# CourierQuest

## Descripción General

**Courier Quest** juego de simulación de repartidor en 2D desarrollado en Python con la librería Arcade. El jugador asume el rol de un mensajero en una ciudad con el objetivo de recoger y entregar paquetes antes de que se acabe el tiempo para llegar a una meta mínima de ingresos.

## Características Principales

* **Movimiento en Cuadrícula:** Desplazamiento por una ciudad 2D con diferentes tipos de superficie que afectan la velocidad.
* **Gestión de Tiempo:** 15 minutos para cumplir la meta de ingresos.
* **Sistema de Reputación:** La puntualidad es clave. Una alta reputación otorga bonus, mientras que una baja reputación puede llevar a la derrota.
* **Clima Dinámico:** Condiciones climáticas que cambian durante el juego y afectan la jugabilidad.
* **Gestión de Inventario y Pedidos:** Acepta, rechaza, recoge y entrega pedidos, cada uno con peso, pago y deadline.
* **Sistema de Guardado y Carga:** Permite guardar y cargar el progreso de la partida
* **Tabla de Puntuaciones:** Guarda los mejores puntajes obtenidos al finalizar una partida.

## Estructuras de Datos Utilizadas


### 1. Lista Enlazada Doble (Implementada Manualmente)
* **Uso:** Se utiliza para gestionar el **inventario** (en la clase `Inventario`).
Estructura para un inventario donde los pedidos se pueden recorrer hacia adelante y hacia atrás para seleccionar o cancelar un pedido.
* **Complejidad:**
    * **Agregar Pedido (`agregar_pedido`):** $O(1)$, ya que se añade al final de la lista.
    * **Quitar/Buscar Pedido (`quitar_pedido`, `buscar_pedido`):** $O(n)$, donde `n` es el número de pedidos en el inventario, ya que se debe recorrer la lista para encontrar el elemento.

### 2. Diccionario (Hash Map)
* **Uso Principal:** Se usa como una "base de datos" maestra de todos los pedidos cargados al inicio (`self.pedidos_dict`).
Proporciona un acceso rápido a los datos de cualquier pedido usando su ID como clave. Esto es rápido para reconstruir el inventario al cargar una partida o para obtener los detalles de un paquete al colisionar con su punto de recogida.
* **Complejidad:**
    * **Búsqueda por ID:** $O(1)$ .

Para gestionar los pedidos aceptados pero aún no recogidos (`self.pedidos_activos`), permitiendo una rápida verificación de si un pedido expiró.
* **Operaciones y Complejidad:**
    * **Inserción, Eliminación y Búsqueda:** $O(1)$.

### 3. Lista  (Python `list`)
* **Uso 1:** Para gestionar la cola de **pedidos pendientes** para mostrar al jugador (`self.pedidos_pendientes`).
Es una estructura simple y adecuada para una cola de elementos. La eliminación de un elemento (`.remove()`) es $O(n)$

* **Uso 2:** Para la **tabla de puntuaciones** (`self.popup_puntajes`).
Para cargar y ordenar los puntajes desde el json 


### 4. Matriz (Lista de Listas)
* **Uso:** Para representar el **mapa del juego** (`mapa`).
Es la representación más natural para una cuadrícula 2D, permitiendo un acceso directo a las propiedades de cualquier celda como terreno y obstáculos.
* **Complejidad:**
    * **Acceso a una Celda (`mapa[fila][col]`):** $O(1)$.

## Complejidad Algorítmica (Big O)

* **Bucle Principal (`on_update`):**Las operaciones que se realizan en cada actualización, como la verificación de colisiones, el movimiento del jugador y la actualización de los temporizadores de los pedidos, dependen del número de pedidos activos y sprites en pantalla. Las operaciones de búsqueda y actualización en diccionarios son $O(1)$, y los recorridos sobre listas pequeñas (menos de 5 elementos) también son $O(1)$. 
