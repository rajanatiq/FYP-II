from PoseEstimation import PoseEstimationClass
from pathlib import Path

import cv2

DIR = Path(__file__).resolve().parent

image = cv2.imread(str(image_path))
if image is None:
    print("No image Found")
else:
    print("image found")

print(PoseEstimationClass.process_face(image))