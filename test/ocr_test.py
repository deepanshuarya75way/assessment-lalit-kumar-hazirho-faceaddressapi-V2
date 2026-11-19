import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from src.ocr_engine_rapid import RapidOCREngine

# this is tester for the ocr engine

engine = RapidOCREngine()
first_arg = ""
if len(sys.argv) > 1:
    first_arg = sys.argv[1]
else:
    print("No arguments provided!")

result = engine.extract_text(first_arg)
print(result)
