import os
import numpy as np
import torch
import torchaudio
import librosa
import soundfile as sf

os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
os.environ["HF_HUB_OFFLINE"] = "1"

from speechbrain.pretrained import SpeakerRecognition

ENROLLMENT_FOLDER = r"D:\FYP-II(Backend)\FYP-II\EnrollmentAudios"
EMBEDDINGS_DIR = os.path.join(os.path.dirname(__file__), "voice_samples")
MODEL_DIR = os.path.join(os.path.dirname(__file__), "pretrained_models/spkrec-ecapa-voxceleb")
os.makedirs(EMBEDDINGS_DIR, exist_ok=True)

model = SpeakerRecognition.from_hparams(
    source="speechbrain/spkrec-ecapa-voxceleb",
    savedir=MODEL_DIR
)

def get_embedding(audio_path: str) -> np.ndarray:
    waveform, sr = librosa.load(audio_path, sr=16000, mono=True)
    waveform_tensor = torch.tensor(waveform).unsqueeze(0)
    with torch.no_grad():
        embedding = model.encode_batch(waveform_tensor)
    return embedding.squeeze().numpy()

def enroll_all():
    student_folders = [f for f in os.listdir(ENROLLMENT_FOLDER)
                       if os.path.isdir(os.path.join(ENROLLMENT_FOLDER, f))]

    if not student_folders:
        print("Koi student folder nahi mila.")
        return

    print(f"{len(student_folders)} students mile — processing...\n")
    success, failed = 0, []

    for student_id in student_folders:
        folder_path = os.path.join(ENROLLMENT_FOLDER, student_id)
        audio_files = [f for f in os.listdir(folder_path)
                       if f.lower().endswith((".ogg", ".wav", ".mp3"))]

        if not audio_files:
            print(f"❌ Student {student_id} — koi audio nahi mili")
            failed.append(student_id)
            continue

        try:
            # Extract embedding from each audio and average them
            embeddings = []
            for audio_file in audio_files:
                audio_path = os.path.join(folder_path, audio_file)
                emb = get_embedding(audio_path)
                embeddings.append(emb)

            # Average all embeddings → one final embedding per student
            final_embedding = np.mean(embeddings, axis=0)

            # Save as .npy
            save_path = os.path.join(EMBEDDINGS_DIR, f"{student_id}.npy")
            np.save(save_path, final_embedding)

            print(f"✅ Student {student_id} enrolled ({len(audio_files)} audios averaged)")
            success += 1

        except Exception as e:
            print(f"❌ Student {student_id} failed: {e}")
            failed.append(student_id)

    print(f"\nDone — {success} enrolled, {len(failed)} failed")
    if failed:
        print(f"Failed IDs: {failed}")

if __name__ == "__main__":
    enroll_all()
