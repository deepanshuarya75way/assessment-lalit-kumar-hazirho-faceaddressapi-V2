import os

import googlemaps
from dotenv import load_dotenv
from googlemaps import geocoding

load_dotenv()
api_key = os.getenv("MAPS_API_KEY")

if not api_key:
    raise ValueError("Missing MAPS_API_KEY")

# Properly initialize the client instance
gmaps = googlemaps.Client(key=api_key)


def geocode_text_block(address_text: str) -> dict:
    query_string = address_text.strip()
    if not query_string:
        raise ValueError("Empty text block.")

    # Call the geocode method directly via the client instance
    the_result = geocoding.geocode(gmaps, query_string)

    if not the_result:
        return {
            "status": "ZERO_RESULTS",
            "latitude": None,
            "longitude": None,
            "formatted_address": None,
        }

    primary_match = the_result[0]
    coordinates = primary_match["geometry"]["location"]

    return {
        "status": "OK",
        "latitude": float(coordinates["lat"]),
        "longitude": float(coordinates["lng"]),
        "formatted_address": str(primary_match.get("formatted_address", "")),
    }
