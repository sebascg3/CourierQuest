import requests
base_url = "https://tigerds-api.kindflower-ccaf48b6.eastus.azurecontainerapps.io"
def get_map_data():
    response = requests.get(f"{base_url}/city/map")
    if response.status_code == 200:
        return response.json()
    else:
        return {f"error": f"Failed to retrieve map data, {response.status_code}"}

print(get_map_data())