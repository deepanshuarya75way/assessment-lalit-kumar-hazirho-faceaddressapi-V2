import requests


def geocode(address: str, api_key: str) -> dict:
    geoapify_url = "https://api.geoapify.com/v1/geocode/search"

    params = {
        "text": address,
        "filter": "countrycode:in",  #API only looks inside India
        "apiKey": api_key
    }

    resp = requests.get(geoapify_url, params=params).json()

    try:
        # Pulls the very first match from the features array
        first_match = resp["features"][0]
        lon, lat = first_match["geometry"]["coordinates"]
        return {"latitude": lat, "longitude": lon}
    except (KeyError, IndexError):
        return {"error": "No coordinates found or bad API response"}
