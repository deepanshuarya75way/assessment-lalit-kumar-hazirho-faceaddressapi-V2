# import os
import sys

# sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))
from src.face_engine import DeepFaceRecognitionEngine

engine = DeepFaceRecognitionEngine()

# this is tester for the ocr engine

first_arg = ""
second_arg = ""
if len(sys.argv) > 2:
    first_arg = sys.argv[1]
    second_arg = sys.argv[2]
else:
    print("Not enough arguments provided!")

result = engine.verify_two_images(first_arg, second_arg)
print(result)
