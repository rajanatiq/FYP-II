import os
import numpy as np
from deepface import DeepFace

DATASET_DIR = r"D:\FYP-II\EmbeddingsDataset"
EMBEDDINGS_DIR = r"D:\FYP-II\StoredEmbeddings"

os.makedirs(EMBEDDINGS_DIR, exist_ok=True)

def train_students():
    students = os.listdir(DATASET_DIR)

    for student_id in students:
        student_path = os.path.join(DATASET_DIR, student_id)

        if not os.path.isdir(student_path):
            continue

        print(f"\nTraining student: {student_id}")

        embeddings = []

        for image_name in os.listdir(student_path):
            image_path = os.path.join(student_path, image_name)

            try:
                result = DeepFace.represent(
                    img_path=image_path,
                    model_name="Facenet",
                    enforce_detection=True
                )

                embedding = result[0]["embedding"]
                embeddings.append(embedding)

                print(f"Processed: {image_name}")

            except Exception as e:
                print(f"Skipped {image_name} -> {e}")

        if len(embeddings) < 3:
            print("Not enough clear images, skipping student")
            continue

        avg_embedding = np.mean(embeddings, axis=0)

        save_path = os.path.join(
            EMBEDDINGS_DIR,
            f"{student_id}.npy"
        )

        np.save(save_path, avg_embedding)

        print(f"Embedding saved for student {student_id}")

    print("\nTraining completed.")

if __name__ == "__main__":
    train_students()
