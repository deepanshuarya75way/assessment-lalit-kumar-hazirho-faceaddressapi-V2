from datetime import datetime, timezone
import json
import logging
import os
import shutil
from typing import Any, Dict, Optional
import uuid

from geopy.distance import geodesic


REJECTION_LOG_PATH: str = os.path.join("logs", "geofence_rejections.jsonl")
REJECTED_PHOTOS_DIR: str = os.path.join("logs", "rejected_photos")

os.makedirs(os.path.dirname(REJECTION_LOG_PATH), exist_ok=True)
os.makedirs(REJECTED_PHOTOS_DIR, exist_ok=True)

audit_logger = logging.getLogger("geofence_audit")
audit_logger.setLevel(logging.WARNING)

if not audit_logger.handlers:
    file_handler = logging.FileHandler(REJECTION_LOG_PATH, encoding="utf-8")
    file_handler.setFormatter(logging.Formatter("%(message)s"))
    audit_logger.addHandler(file_handler)


def save_rejected_photo(
    employee_id: str,
    temp_photo_path: Optional[str],
    original_filename: Optional[str] = None,
) -> Optional[str]:
    """Copies the temporary uploaded photo into logs/rejected_photos/ before cleanup."""
    if not temp_photo_path or not os.path.exists(temp_photo_path):
        return None

    ext = os.path.splitext(original_filename or temp_photo_path)[1] or ".jpg"
    timestamp_slug = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    unique_filename = f"{employee_id}_{timestamp_slug}_{uuid.uuid4().hex[:6]}{ext}"
    destination_path = os.path.join(REJECTED_PHOTOS_DIR, unique_filename)

    shutil.copy2(temp_photo_path, destination_path)
    return destination_path


def log_out_of_bounds_attempt(
    employee_id: str,
    target_lat: float,
    target_lon: float,
    employee_lat: float,
    employee_lon: float,
    distance_meters: float,
    discrepancy_meters: float,
    max_allowed_meters: float,
    photo_filename: Optional[str] = None,
    saved_photo_path: Optional[str] = None,
) -> Dict[str, Any]:
    event_timestamp = datetime.now(timezone.utc).isoformat()

    audit_record: Dict[str, Any] = {
        "review": "NOT_REVIEWED",
        "event": "GEOFENCE_CHECKIN_REJECTED",
        "timestamp_utc": event_timestamp,
        "employee_id": employee_id,
        "photo_filename": photo_filename,
        "saved_photo_path": saved_photo_path,
        "designated_coordinates": {
            "latitude": target_lat,
            "longitude": target_lon,
        },
        "employee_coordinates": {
            "latitude": employee_lat,
            "longitude": employee_lon,
        },
        "distance_meters": distance_meters,
        "max_allowed_meters": max_allowed_meters,
        "distance_discrepancy_meters": discrepancy_meters,
    }

    audit_logger.warning(json.dumps(audit_record))
    return audit_record


def evaluate_geofence_checkin(
    employee_id: str,
    target_lat: float,
    target_lon: float,
    employee_lat: float,
    employee_lon: float,
    max_distance_meters: float,
    photo_filename: Optional[str] = None,
    temp_photo_path: Optional[str] = None,
) -> Dict[str, Any]:
    if max_distance_meters <= 0:
        raise ValueError("max_distance_meters must be greater than 0.")

    raw_distance = geodesic(
        (target_lat, target_lon),
        (employee_lat, employee_lon),
    ).meters

    distance_meters = round(raw_distance, 2)
    discrepancy_meters = round(max(0.0, distance_meters - max_distance_meters), 2)
    is_within_range = distance_meters <= max_distance_meters
    checked_at = datetime.now(timezone.utc).isoformat()

    if not is_within_range:
        saved_photo_path = save_rejected_photo(
            employee_id=employee_id,
            temp_photo_path=temp_photo_path,
            original_filename=photo_filename,
        )
        audit_record = log_out_of_bounds_attempt(
            employee_id=employee_id,
            target_lat=target_lat,
            target_lon=target_lon,
            employee_lat=employee_lat,
            employee_lon=employee_lon,
            distance_meters=distance_meters,
            discrepancy_meters=discrepancy_meters,
            max_allowed_meters=max_distance_meters,
            photo_filename=photo_filename,
            saved_photo_path=saved_photo_path,
        )
        return {
            "is_valid": False,
            "validation_status": "REJECTED_OUT_OF_BOUNDS",
            "timestamp_utc": audit_record["timestamp_utc"],
            "distance_meters": distance_meters,
            "max_allowed_meters": max_distance_meters,
            "distance_discrepancy_meters": discrepancy_meters,
            "review_logged": True,
            "saved_photo_path": saved_photo_path,
            "message": (
                f"Check-in rejected: {distance_meters}m from target "
                f"(exceeds {max_distance_meters}m limit by {discrepancy_meters}m). "
                "Incident and photo logged for review."
            ),
        }

    return {
        "is_valid": True,
        "validation_status": "APPROVED",
        "timestamp_utc": checked_at,
        "distance_meters": distance_meters,
        "max_allowed_meters": max_distance_meters,
        "distance_discrepancy_meters": 0.0,
        "review_logged": False,
        "saved_photo_path": None,
        "message": f"Check-in approved within {max_distance_meters}m geofence.",
    }