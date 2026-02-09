import cv2
import mediapipe as mp
import os
import csv
import math
from pathlib import Path

DIR = Path(__file__).resolve().parent

# Initialize MediaPipe FaceMesh
mp_face = mp.solutions.face_mesh.FaceMesh(static_image_mode=True)

# Important landmark indexes
NOSE = 1
LEFT_EYE = 33
RIGHT_EYE = 263
CHIN = 199

image_count = 0

DATASET_PATH = str(DIR.parent.parent / "DataSet")
CSV_FILE = str(DIR / "face_pose_data.csv")

def get_distance(p1, p2):
    return math.sqrt(
        (p1[0] - p2[0]) ** 2 +
        (p1[1] - p2[1]) ** 2 +
        (p1[2] - p2[2]) ** 2
    )

# Create CSV file
with open(CSV_FILE, "w", newline="") as file:
    writer = csv.writer(file)
    writer.writerow(["yaw", "pitch", "label"])

    for label in os.listdir(DATASET_PATH):
        label_folder = os.path.join(DATASET_PATH, label)

        if not os.path.isdir(label_folder):
            continue
        
        for image_name in os.listdir(label_folder):
            image_path = os.path.join(label_folder, image_name)
            image = cv2.imread(image_path)

            if image is None:
                continue

            rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            result = mp_face.process(rgb_image)

            if result.multi_face_landmarks is None:
                continue
            

            landmarks = result.multi_face_landmarks[0].landmark

            # Read landmark points
            nose = [landmarks[NOSE].x, landmarks[NOSE].y, landmarks[NOSE].z]
            left_eye = [landmarks[LEFT_EYE].x, landmarks[LEFT_EYE].y, landmarks[LEFT_EYE].z]
            right_eye = [landmarks[RIGHT_EYE].x, landmarks[RIGHT_EYE].y, landmarks[RIGHT_EYE].z]
            chin = [landmarks[CHIN].x, landmarks[CHIN].y, landmarks[CHIN].z]

            # Normalization (scale by face width)
            face_width = get_distance(left_eye, right_eye)
            if face_width == 0:
                continue

            nose = [x / face_width for x in nose]
            left_eye = [x / face_width for x in left_eye]
            right_eye = [x / face_width for x in right_eye]
            chin = [x / face_width for x in chin]

            # Calculate yaw and pitch
            yaw = get_distance(nose, right_eye) - get_distance(nose, left_eye)

            eye_center = [
                (left_eye[0] + right_eye[0]) / 2,
                (left_eye[1] + right_eye[1]) / 2,
                (left_eye[2] + right_eye[2]) / 2
            ]

            pitch = get_distance(nose, chin) - get_distance(nose, eye_center)

            writer.writerow([yaw, pitch, label])
            image_count = image_count + 1

print(f"Step 1 complete: CSV file created having {image_count} images data" )
