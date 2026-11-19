import os

from rapidocr_onnxruntime import RapidOCR


class RapidOCREngine:
    def __init__(self):
        """Initializes the CPU/ONNX execution providers for text parsing."""
        self.engine = RapidOCR()

    def extract_text(self, image_path: str) -> str:

        try:
            if not os.path.exists(image_path):
                raise FileNotFoundError(
                    f"Target image resource not located at: {image_path}"
                )

            # RapidOCR output format: (results, elapsed_time)
            # results layout: [[box_coordinates, text_string, confidence_score], ...]
            ocr_result, _ = self.engine(image_path)

            if not ocr_result:
                return ""

            # Isolate and extract text rows chronologically
            clean_strings = [
                str(block[1]).strip() for block in ocr_result if len(block) > 1
            ]

            # Combine individual rows into a unified searchable text layout
            return "\n".join(clean_strings).strip()

        except Exception as e:
            print(f"RapidOCR Subsystem Processing Error: {str(e)}")
            raise e
