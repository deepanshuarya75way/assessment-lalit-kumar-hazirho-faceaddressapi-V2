import os
import tempfile
from typing import Optional

import dotenv
from fastapi import (
    FastAPI,
    File,
    HTTPException,
    UploadFile,
    status,
)
from fastapi.concurrency import run_in_threadpool

from src.face_engine import DeepFaceRecognitionEngine

#from src.geocoder import geocode_text_block
#from src.geocoder_geopy import geocode_geopy
# https://apidocs.geoapify.com/ -- this site for api docs and getting an api key
from src.geocoder_geoapify import geocode
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


async def save_upload_file(upload_file: UploadFile) -> str:
    def write_file() -> str:
        ext = os.path.splitext(upload_file.filename or "")[1] or ".png"

        fd, path = tempfile.mkstemp(suffix=ext)

        with os.fdopen(fd, "wb") as file:
            file.write(upload_file.file.read())

        return path

    return await run_in_threadpool(write_file)


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
            api_key=apikey
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
