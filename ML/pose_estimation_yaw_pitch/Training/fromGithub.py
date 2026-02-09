import cv2
import mediapipe as mp
import numpy as np
import pandas as pd
import os
from pathlib import Path

# Get directory of this script
DIR = Path(__file__).resolve().parent

# Initialize Mediapipe FaceMesh
mp_face_mesh = mp.solutions.face_mesh
face_mesh = mp_face_mesh.FaceMesh(
    static_image_mode=True,
    max_num_faces=1,
    min_detection_confidence=0.3  # lower to detect more faces
)

# Base dataset folder (adjust if needed)
base_folder_path = DIR.parent.parent / "Data Set"

# Labels / subfolders (adjust capitalization to match your folders)
labels = ['Left', 'Right', 'UP', 'Front']

# Lists for DataFrame
image_paths = []
rolls = []
pitches = []
yaws = []
image_labels = []

def calculate_pose_angles(image_path):
    """Calculates roll, pitch, yaw from face landmarks."""
    image = cv2.imread(str(image_path))
    if image is None:
        print("Could not read image:", image_path)
        return None, None, None

    # Optional: resize to improve detection
    # image = cv2.resize(image, (640, 480))

    image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    results = face_mesh.process(image_rgb)

    if results.multi_face_landmarks:
        for face_landmarks in results.multi_face_landmarks:
            landmarks = []
            h, w, _ = image.shape
            for landmark in face_landmarks.landmark:
                x, y, z = int(landmark.x * w), int(landmark.y * h), landmark.z
                landmarks.append((x, y, z))

            nose_tip = landmarks[1]
            chin = landmarks[152]
            left_eye = landmarks[33]
            right_eye = landmarks[263]

            roll = np.arctan2(right_eye[1] - left_eye[1], right_eye[0] - left_eye[0])
            pitch = np.arctan2(chin[1] - nose_tip[1], chin[2] - nose_tip[2])
            yaw = np.arctan2(nose_tip[0] - chin[0], nose_tip[2] - chin[2])

            return np.degrees(roll), np.degrees(pitch), np.degrees(yaw)

    # Face not detected
    return None, None, None

# Process each label folder
for label in labels:
    folder_path = base_folder_path / label
    if not folder_path.exists():
        print(f"Folder not found: {folder_path}, skipping...")
        continue

    # Case-insensitive image extensions
    image_files = [f for f in os.listdir(folder_path) if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
    print(f"Found {len(image_files)} images in {label}")

    for image_file in image_files:
        image_path = folder_path / image_file
        roll, pitch, yaw = calculate_pose_angles(image_path)

        if roll is not None and pitch is not None and yaw is not None:
            # Save full path
            image_paths.append(str(image_path))
            rolls.append(roll)
            pitches.append(pitch)
            yaws.append(yaw)
            image_labels.append(label)
        else:
            print("Face not detected in:", image_file)

# Create DataFrame
df = pd.DataFrame({
    'Image Path': image_paths,
    'Roll': rolls,
    'Pitch': pitches,
    'Yaw': yaws,
    'Label': image_labels
})

# Ensure CSV folder exists
csv_folder = DIR / "csv files"
csv_folder.mkdir(parents=True, exist_ok=True)

# Save to CSV
csv_file_path = csv_folder / "head_pose.csv"
df.to_csv(csv_file_path, index=False)

print(f"CSV file saved to: {csv_file_path}")
print(df.head())
print(f"Total images processed (with detected face): {len(image_paths)}")
