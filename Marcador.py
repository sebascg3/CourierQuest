import Puntaje

class Marcador:
    def __init__(self):
        self.puntajes = []

    def agregar_puntaje(self, puntaje: Puntaje):
        self.puntajes.append(puntaje)

    def ordenar_puntajes(self):
        self.puntajes.sort(key=lambda p: p.score, reverse=True)

    def mostrar_puntajes(self):
        for puntaje in self.puntajes:
            print(f"{puntaje.nombre}: {puntaje.score}")

    #faltan los metodos para guardar puntajes y cargarlos