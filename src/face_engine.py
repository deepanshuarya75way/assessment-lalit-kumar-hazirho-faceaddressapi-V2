import os

import numpy as np
from deepface import DeepFace


class DeepFaceRecognitionEngine:
    def __init__(self):
        print("[INFO] Initializing DeepFace Engine with Facenet512 + OpenCV...")
        self.cosine_threshold = 0.40

    def create_encoding(self, image_path: str) -> list:
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"File missing: {image_path}")

        print(f"[INFO] Creating encoding for {image_path}...")
        try:
            embedding_objs: list[dict[str, any]] = DeepFace.represent(  # type: ignore
                img_path=image_path,
                model_name="Facenet512",
                detector_backend="retinaface",
                enforce_detection=True,
            )
            return embedding_objs[0]["embedding"]
        except Exception as e:
            raise ValueError(
                f"No face isolated within target space or processing error: {str(e)}"
            )

    def verify_two_encodings(self, encoding_1: list, encoding_2: list) -> dict:
        """
        Core math engine. Compares two pre-computed vector lists directly using Cosine Distance.
        """
        try:
            u = np.array(encoding_1)
            v = np.array(encoding_2)

            # Cosine distance calculation
            distance = 1.0 - (np.dot(u, v) / (np.linalg.norm(u) * np.linalg.norm(v)))
            verified = bool(distance <= self.cosine_threshold)

            return {
                "same_person": verified,
                "distance_score": round(float(distance), 4),
                "tolerance_threshold": self.cosine_threshold,
                "metric_used": "cosine",
            }
        except Exception as e:
            return {"error": f"Vector verification calculation failure: {str(e)}"}

    def verify_two_images(self, image_path_1: str, image_path_2: str) -> dict:

        try:
            print("[INFO] Extracting embeddings from image paths...")
            encoding_1 = self.create_encoding(image_path_1)
            encoding_2 = self.create_encoding(image_path_2)

            print("[INFO] Executing vector-to-vector verification...")
            return self.verify_two_encodings(encoding_1, encoding_2)
        except Exception as e:
            return {"error": f"Biometric calculation failure: {str(e)}"}
