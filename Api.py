import requests

BASE_URL = "https://tigerds-api.kindflower-ccaf48b6.eastus.azurecontainerapps.io"


def main():
    """
    Consulta y muestra información de la API de CourierQuest:
    - Estado de salud del backend.
    - Mapa de la ciudad y su leyenda.
    - Lista de trabajos/pedidos disponibles.
    - Información y transición del clima.
    Imprime los resultados en consola.
    """
    # Health check
    health_data = requests.get(f"{BASE_URL}/healthz").json()
    health = health_data.get("ok", False)  # Devuelve True/False

    # City map
    city_data = requests.get(f"{BASE_URL}/city/map").json()
    data = city_data.get("data", {})

    city_name = data.get("city_name", "")
    tiles = data.get("tiles", [])
    height = data.get("height", 0)
    width = data.get("width", 0)
    legend = data.get("legend", {})
    goal = data.get("goal", {})
    max_time = data.get("max_time", 0)

    # Legend details
    street = legend.get("C", {})
    building = legend.get("B", {})
    parks = legend.get("P", {})

    # Jobs (pedidos)
    jobs_data = requests.get(f"{BASE_URL}/city/jobs").json()
    jobs = jobs_data.get("data", [])

    # Weather (clima)
    weather_data = requests.get(f"{BASE_URL}/city/weather?city=TigerCity&mode=seed").json()
    weather_info = weather_data.get("data", {})

    initial_weather = weather_info.get("initial", {})
    conditions = weather_info.get("conditions", [])
    transition = weather_info.get("transition", {})

    # ------------------------
    # Mostrar resultados
    # ------------------------
    print("✅ Health:", health)
    print("🌆 City:", city_name)
    print("Width:", width, "Height:", height)
    print("Goal:", goal, "Max time:", max_time)

    print("\n📖 Legend details:")
    print("Street:", street)
    print("Building:", building)
    print("Parks:", parks)

    print("\n💼 Jobs:")
    for job in jobs:
        print(
            f"- {job['id']} | Pickup: {job['pickup']} -> Dropoff: {job['dropoff']} | "
            f"Payout: {job['payout']} | Deadline: {job['deadline']}"
        )

    print("\n🌤 Weather:")
    print("Initial:", initial_weather)
    print("Conditions:", conditions)
    print("Transition:", transition)


if __name__ == "__main__":
    main()
