import os
import io
import torch

# Compatibility fix for speechbrain + torch 2.2.2
if not hasattr(torch.amp, 'custom_fwd'):
    torch.amp.custom_fwd = torch.cuda.amp.custom_fwd
    torch.amp.custom_bwd = torch.cuda.amp.custom_bwd

import numpy as np
import librosa

os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
os.environ["HF_HUB_OFFLINE"] = "1"

from speechbrain.pretrained import SpeakerRecognition

VOICE_SAMPLES_DIR = os.path.join(os.path.dirname(__file__), "voice_samples")
MODEL_DIR = os.path.join(os.path.dirname(__file__), "pretrained_models/spkrec-ecapa-voxceleb")

MATCH_THRESHOLD = 0.75

# Load model once at startup
verification_model = SpeakerRecognition.from_hparams(
    source="speechbrain/spkrec-ecapa-voxceleb",
    savedir=MODEL_DIR
)

# Load all saved embeddings into memory at startup
enrolled_embeddings = {}

def load_all_embeddings():
    files = [f for f in os.listdir(VOICE_SAMPLES_DIR) if f.endswith(".npy")]
    for f in files:
        student_id = os.path.splitext(f)[0]
        path = os.path.join(VOICE_SAMPLES_DIR, f)
        enrolled_embeddings[student_id] = np.load(path)
    print(f"Loaded {len(enrolled_embeddings)} voice embeddings.")

load_all_embeddings()

def get_embedding_from_bytes(audio_bytes: bytes) -> np.ndarray:
    waveform, _ = librosa.load(io.BytesIO(audio_bytes), sr=16000, mono=True)
    waveform_tensor = torch.tensor(waveform).unsqueeze(0)
    with torch.no_grad():
        embedding = verification_model.encode_batch(waveform_tensor)
    return embedding.squeeze().numpy()

def cosine_similarity(v1: np.ndarray, v2: np.ndarray) -> float:
    return float(np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2)))

def verify_student_voice(identity_no: str, audio_bytes: bytes) -> dict:
    try:
        if identity_no not in enrolled_embeddings:
            return {"success": False, "error": f"No voice enrolled for {identity_no}"}

        stored_embedding = enrolled_embeddings[identity_no]
        live_embedding = get_embedding_from_bytes(audio_bytes)

        score = cosine_similarity(stored_embedding, live_embedding)
        is_match = score >= MATCH_THRESHOLD

        return {
            "success": True,
            "student_id": identity_no,
            "is_match": is_match,
            "score": round(score, 4)
        }
    except Exception as e:
        return {"success": False, "error": str(e)}
