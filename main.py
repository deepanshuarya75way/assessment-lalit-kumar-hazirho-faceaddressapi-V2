import os
import tempfile
from typing import Optional

import dotenv
from fastapi import (
    FastAPI,
    File,
    Form,
    HTTPException,
    UploadFile,
    status,
)
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import JSONResponse

from src.face_engine import DeepFaceRecognitionEngine

#from src.geocoder import geocode_text_block
#from src.geocoder_geopy import geocode_geopy
# https://apidocs.geoapify.com/ -- this site for api docs and getting an api key
from src.geocoder_geoapify import geocode
from src.geofence import evaluate_geofence_checkin
from src.ocr_engine_rapid import RapidOCREngine

dotenv.load_dotenv()
apikey: str = str(os.environ.get("GEO_API_FY"))

app = FastAPI(title="Vision & Spatial Processing API")

ocr_service = RapidOCREngine()
face_service = DeepFaceRecognitionEngine()

ALLOWED_MEDIA_TYPES = {
    "image/jpeg",
    "image/jpg",
    "image/png",
}


def validate_image_type(content_type: Optional[str]) -> None:
    if content_type not in ALLOWED_MEDIA_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only JPEG and PNG images are supported.",
        )


def validate_coordinates(lat: float, lon: float, label: str) -> None:
    if not (-90.0 <= lat <= 90.0):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid {label} latitude: {lat}. Must be between -90 and 90.",
        )
    if not (-180.0 <= lon <= 180.0):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid {label} longitude: {lon}. Must be between -180 and 180.",
        )


async def save_upload_file(upload_file: UploadFile) -> str:
    def write_file() -> str:
        ext = os.path.splitext(upload_file.filename or "")[1] or ".png"

        fd, path = tempfile.mkstemp(suffix=ext)

        with os.fdopen(fd, "wb") as file:
            file.write(upload_file.file.read())

        return path

    return await run_in_threadpool(write_file)


#
#
#address processing
#
#

@app.post(
    "/v1/address/process",
    status_code=status.HTTP_200_OK,
)
async def process_address_image(
    file: UploadFile = File(...),
):
    validate_image_type(file.content_type)
    temp_path = await save_upload_file(file)

    try:
        text = await run_in_threadpool(
            ocr_service.extract_text,
            temp_path,
        )

        if not text.strip():
            return {
                "ocr_status": "NO_TEXT_FOUND",
                "extracted_text": "",
                "geocoding_results": None,
            }

        result = await run_in_threadpool(
            geocode,
            address=text,
            api_key=apikey,
        )

        return {
            "ocr_status": "SUCCESS",
            "extracted_text": text,
            "geocoding_results": result,
        }

    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        )

    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


#
#
#face encoding
#
#

@app.post(
    "/v1/face/encoding",
    status_code=status.HTTP_200_OK,
)
async def generate_face_embedding(
    file: UploadFile = File(...),
):
    validate_image_type(file.content_type)
    temp_path = await save_upload_file(file)

    try:
        encoding = await run_in_threadpool(
            face_service.create_encoding,
            temp_path,
        )

        return {
            "status": "SUCCESS",
            "dimension_length": len(encoding),
            "face_encoding": encoding,
        }

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        )

    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        )

    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


#
#
#face verification
#
#

@app.post(
    "/v1/face/verify",
    status_code=status.HTTP_200_OK,
)
async def verify_two_faces(
    file_a: UploadFile = File(...),
    file_b: UploadFile = File(...),
):
    validate_image_type(file_a.content_type)
    validate_image_type(file_b.content_type)

    path_a = await save_upload_file(file_a)
    path_b = await save_upload_file(file_b)

    try:
        result = await run_in_threadpool(
            face_service.verify_two_images,
            path_a,
            path_b,
        )

        if isinstance(result, dict) and "error" in result:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=result["error"],
            )

        return result

    except HTTPException:
        raise

    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        )

    finally:
        if os.path.exists(path_a):
            os.remove(path_a)

        if os.path.exists(path_b):
            os.remove(path_b)


#
#
#geofence validation
#
#

@app.post(
    "/v1/geofence/validate",
    status_code=status.HTTP_200_OK,
)
async def validate_employee_geofence(
    employee_id: str = Form(..., min_length=1),
    target_lat: float = Form(...),
    target_lon: float = Form(...),
    employee_lat: float = Form(...),
    employee_lon: float = Form(...),
    max_distance_meters: float = Form(..., gt=0),
    captured_photo: UploadFile = File(...),
):
    validate_image_type(captured_photo.content_type)
    validate_coordinates(target_lat, target_lon, "target")
    validate_coordinates(employee_lat, employee_lon, "employee")

    temp_path = await save_upload_file(captured_photo)
    clean_employee_id = employee_id.strip()

    try:
        result = await run_in_threadpool(
            evaluate_geofence_checkin,
            employee_id=clean_employee_id,
            target_lat=target_lat,
            target_lon=target_lon,
            employee_lat=employee_lat,
            employee_lon=employee_lon,
            max_distance_meters=max_distance_meters,
            photo_filename=captured_photo.filename,
            temp_photo_path=temp_path,
        )

        payload = {
            "employee_id": clean_employee_id,
            "photo_received": True,
            "coordinates": {
                "designated_address": {
                    "latitude": target_lat,
                    "longitude": target_lon,
                },
                "employee": {
                    "latitude": employee_lat,
                    "longitude": employee_lon,
                },
            },
            **result,
        }

        if not result["is_valid"]:
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content=payload,
            )

        return payload

    except HTTPException:
        raise

    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        )

    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)