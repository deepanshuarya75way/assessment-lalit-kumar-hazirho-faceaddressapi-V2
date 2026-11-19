
import time

from geopy.exc import GeocoderServiceError, GeocoderTimedOut
from geopy.geocoders import Nominatim

geocoding_agent = Nominatim(user_agent="lalitutwal")

def geocode_geopy(address_text: str) -> dict:
    query_string: str = address_text.strip()
    if not query_string:
        raise ValueError("Empty text block.")

    # written in the documentation of the nominatim
    time.sleep(1)

    try:
        the_result = geocoding_agent.geocode(query_string)
    except (GeocoderTimedOut, GeocoderServiceError) as e:
        print(f"Geocoding error: {e}")
        return {
            "status": f"ERROR: {type(e).__name__}",
            "latitude": None,
            "longitude": None,
            "formatted_address": None,
        }

    if not the_result:
        return {
            "status": "ZERO_RESULTS",
            "latitude": None,
            "longitude": None,
            "formatted_address": None,
        }

    the_result = the_result.raw
    return {
        "status": "OK",
        "latitude": the_result["lat"],
        "longitude": the_result["lon"],
        "formatted_address": the_result["display_name"],
    }


if __name__ == "__main__":
    result = geocode_geopy("Rashtrapati Bhawan, President's Estate, New Delhi, Delhi")
    print(result)
