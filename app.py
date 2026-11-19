
## just to test the api is fuctioning or not

import requests
import streamlit as st
from streamlit_js_eval import get_geolocation


API_URL = "http://127.0.0.1:8000/v1/geofence/validate"

st.set_page_config(page_title="Employee Geofence Check-In", layout="centered")
st.title("Employee Geofence Check-In")

# 1. Automatically fetch browser GPS coordinates
st.subheader("1. Live Browser Location")
location = get_geolocation()

employee_lat = None
employee_lon = None

if location and "coords" in location:
    employee_lat = location["coords"]["latitude"]
    employee_lon = location["coords"]["longitude"]
    accuracy = round(location["coords"].get("accuracy", 0), 1)
    st.success(
        f"Location detected: `{employee_lat:.6f}, {employee_lon:.6f}` (±{accuracy}m accuracy)"
    )
else:
    st.warning("Waiting for browser location permission... Please click 'Allow' in your browser.")

# 2. Target Building Coordinates & Dynamic Radius
st.subheader("2. Target Site & Geofence Radius")
col1, col2, col3 = st.columns(3)
target_lat = col1.number_input("Target Latitude", value=None, format="%.6f", placeholder="e.g., 29.149200")
target_lon = col2.number_input("Target Longitude", value=None, format="%.6f", placeholder="e.g., 75.721700")
max_distance_meters = col3.number_input(
    "Allowed Radius (m)", min_value=1.0, value=None, step=10.0, placeholder="e.g., 50 or 100"
)

# 3. Employee ID & Photo Capture
st.subheader("3. Employee Details & Photo")
employee_id = st.text_input("Employee ID", placeholder="e.g., EMP-1042")
captured_photo = st.camera_input("Take Check-In Photo")

# 4. Submit to FastAPI Backend
if st.button("Validate Check-In", type="primary", use_container_width=True):
    if not employee_id.strip():
        st.error("Please enter your Employee ID.")
    elif employee_lat is None or employee_lon is None:
        st.error("Browser location not available yet. Allow location access and retry.")
    elif target_lat is None or target_lon is None:
        st.error("Please enter the target latitude and longitude.")
    elif max_distance_meters is None:
        st.error("Please enter the allowed geofence radius in meters.")
    elif captured_photo is None:
        st.error("Please capture a photo first.")
    else:
        with st.spinner("Validating geofence..."):
            try:
                files = {
                    "captured_photo": (
                        captured_photo.name or "checkin.jpg",
                        captured_photo.getvalue(),
                        captured_photo.type or "image/jpeg",
                    )
                }
                data = {
                    "employee_id": employee_id.strip(),
                    "target_lat": str(target_lat),
                    "target_lon": str(target_lon),
                    "employee_lat": str(employee_lat),
                    "employee_lon": str(employee_lon),
                    "max_distance_meters": str(max_distance_meters),
                }

                response = requests.post(API_URL, data=data, files=files, timeout=15)
                result = response.json()

                if response.status_code == 200 and result.get("is_valid"):
                    st.success(f"APPROVED — {result.get('message')}")
                elif response.status_code == 403:
                    st.error(f"NOT APPROVED — {result.get('message')}")
                else:
                    st.warning(f"Unexpected response ({response.status_code}): {result}")

                with st.expander("Full API Response"):
                    st.json(result)

            except requests.exceptions.ConnectionError:
                st.error("Cannot reach FastAPI server. Make sure Uvicorn is running on port 8000.")
            except Exception as exc:
                st.error(f"Request failed: {exc}")