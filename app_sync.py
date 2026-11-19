import os
import shutil
import tempfile
from typing import Optional
from fastapi import FastAPI, File, HTTPException, UploadFile, status

from src.face_engine import DeepFaceRecognitionEngine
from src.geocoder import geocode_text_block
from src.ocr_engine_rapid import RapidOCREngine

app = FastAPI(title="Vision & Spatial Processing API")

ocr_service = RapidOCREngine()
face_service = DeepFaceRecognitionEngine()

ALLOWED_MEDIA_TYPES = {"image/jpeg", "image/jpg", "image/png"}


def validate_image_type(content_type: Optional[str]) -> None:
    if not content_type:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing Content-Type header.",
        )
    if content_type not in ALLOWED_MEDIA_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Input media must be JPEG, JPG, or PNG formats.",
        )


def save_upload_file_safely(upload_file: UploadFile) -> str:
    ext = os.path.splitext(upload_file.filename)[1] if upload_file.filename else ".png"
    fd, temp_path = tempfile.mkstemp(suffix=ext, prefix="api_vision_")
    with os.fdopen(fd, "wb") as buffer:
        shutil.copyfileobj(upload_file.file, buffer)
    return temp_path


# ADDRESS PROCESSING
@app.post("/v1/address/process", status_code=status.HTTP_200_OK)
def process_address_image(file: UploadFile = File(...)):
    validate_image_type(file.content_type)
    temp_file_path = save_upload_file_safely(file)

    try:
        extracted_text = ocr_service.extract_text(temp_file_path)
        if not extracted_text or not extracted_text.strip():
            return {
                "ocr_status": "NO_TEXT_FOUND",
                "extracted_text": "",
                "geocoding_results": None,
            }
        spatial_payload = geocode_text_block(extracted_text)
        return {
            "ocr_status": "SUCCESS",
            "extracted_text": extracted_text,
            "geocoding_results": spatial_payload,
        }
    finally:
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)


# FACE ENCODING
@app.post("/v1/face/encoding", status_code=status.HTTP_200_OK)
def generate_face_embedding(file: UploadFile = File(...)):
    validate_image_type(file.content_type)
    temp_file_path = save_upload_file_safely(file)

    try:
        vector_list = face_service.create_encoding(temp_file_path)
        return {
            "status": "SUCCESS",
            "dimension_length": len(vector_list),
            "face_encoding": vector_list,
        }
    finally:
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)


# FACE VERIFICATION
@app.post("/v1/face/verify", status_code=status.HTTP_200_OK)
def verify_two_faces(
    file_a: UploadFile = File(...),
    file_b: UploadFile = File(...),
):
    validate_image_type(file_a.content_type)
    validate_image_type(file_b.content_type)

    path_a = save_upload_file_safely(file_a)
    path_b = save_upload_file_safely(file_b)

    try:
        verification_result = face_service.verify_two_images(path_a, path_b)

        if isinstance(verification_result, dict) and "error" in verification_result:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=verification_result["error"],
            )
        return verification_result
    finally:
        if os.path.exists(path_a):
            os.remove(path_a)
        if os.path.exists(path_b):
            os.remove(path_b)
