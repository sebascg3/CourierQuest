import Puntaje


class Marcador:
    """
    Clase que gestiona la lista de puntajes del juego.
    Permite agregar, ordenar, mostrar y guardar puntajes en un archivo JSON.
    """

    def __init__(self):
        # Lista de objetos Puntaje
        self.puntajes = []

    def agregar_puntaje(self, puntaje: Puntaje):
        """
        Agrega un puntaje a la lista, la ordena y la guarda en archivo.
        """
        self.puntajes.append(puntaje)
        self.ordenar_puntajes()
        self.guardar_puntajes_json()

    def guardar_puntajes_json(self):
        """
        Guarda todos los puntajes actuales en un archivo JSON.
        Si existen puntajes previos, los conserva y agrega los nuevos.
        """
        import os
        import json
        ruta = os.path.join('data', 'puntajes.json')
        os.makedirs('data', exist_ok=True)
        # Leer puntajes previos si existen
        if os.path.exists(ruta):
            with open(ruta, 'r', encoding='utf-8') as f:
                try:
                    prev = json.load(f)
                except Exception:
                    prev = []
        else:
            prev = []
        # Agrega todos los puntajes actuales al historial
        nuevos = [{'nombre': p.nombre, 'score': p.score} for p in self.puntajes]
        lista_final = prev + nuevos
        with open(ruta, 'w', encoding='utf-8') as f:
            json.dump(lista_final, f, ensure_ascii=False, indent=2)

    def ordenar_puntajes(self):
        """
        Ordena la lista de puntajes de mayor a menor.
        """
        self.puntajes.sort(key=lambda p: p.score, reverse=True)

    def mostrar_puntajes(self):
        """
        Imprime en consola todos los puntajes actuales.
        """
        for puntaje in self.puntajes:
            print(f"{puntaje.nombre}: {puntaje.score}")

    def guardar_puntaje_final(self, nombre, ingresos, reputacion):
        """
        Guarda el puntaje final al acabar el juego.
        Puntaje = ingresos * reputacion
        """
        score = ingresos * reputacion
        nuevo_puntaje = Puntaje.Puntaje(score, nombre)
        self.agregar_puntaje(nuevo_puntaje)
        # Aquí podrías guardar en archivo si lo deseas
        return nuevo_puntaje