import requests

BASE_URL = "https://tigerds-api.kindflower-ccaf48b6.eastus.azurecontainerapps.io"

# Obtener el mapa de la ciudad
map_response = requests.get(f"{BASE_URL}/city")
map_data = map_response.json()["data"]

getHealth = requests.get(f"{BASE_URL}/healthz")
getCityName = requests.get(f"{BASE_URL}/city/map/city_name")
getWidth = requests.get(f"{BASE_URL}/city/map/width")
getHeight = requests.get(f"{BASE_URL}/city/map/height")
getLegend = requests.get(f"{BASE_URL}/city/map/legend")
getTiles = requests.get(f"{BASE_URL}/city/map/tiles")
getGoal = requests.get(f"{BASE_URL}/city/map/goal")
getMaxTime = requests.get(f"{BASE_URL}/city/map/max_time")
getStreet = requests.get(f"{BASE_URL}/city/map/legend/C")
getBuilding = requests.get(f"{BASE_URL}/city/map/legend/B")
getParks = requests.get(f"{BASE_URL}/city/map/legend/P")
getJobs = requests.get(f"{BASE_URL}/city/jobs/data")
getWeather = requests.get(f"{BASE_URL}/city/weather?city=TigerCity&mode=seed")
getWeatherConditions = (f"{getWeather}/conditions")
getWeatherTransition = (f"{getWeather}/transition")