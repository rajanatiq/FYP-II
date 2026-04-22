import os
import io
import torch
import whisper
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

# Load whisper once at startup
stt_model = whisper.load_model("base")

def transcribe_audio(file_path: str) -> str:
    result = stt_model.transcribe(file_path)
    return result["text"].strip()

def extract_speech_segments(audio_bytes: bytes):
    """
    Puri audio se sirf speech wale parts nikalta hai silence hata ke.
    Returns: (speech_waveform, has_speech)
    """
    waveform, _ = librosa.load(io.BytesIO(audio_bytes), sr=16000, mono=True)

    # Non-silent intervals nikalo — top_db=25 matlab 25dB se kam = silence
    intervals = librosa.effects.split(waveform, top_db=25)

    if len(intervals) == 0:
        return None, False

    # Sab speech intervals ko ek saath jodo
    speech = np.concatenate([waveform[start:end] for start, end in intervals])

    # 0.5 second se kam speech = practically silence, skip karo
    if len(speech) < 8000:  # 8000 samples = 0.5 sec at 16kHz
        return None, False

    return speech, True

def get_embedding_from_waveform(waveform: np.ndarray) -> np.ndarray:
    waveform_tensor = torch.tensor(waveform).unsqueeze(0)
    with torch.no_grad():
        embedding = verification_model.encode_batch(waveform_tensor) #type: ignore
    return embedding.squeeze().numpy()

def cosine_similarity(v1: np.ndarray, v2: np.ndarray) -> float:
    return float(np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2)))

def verify_student_voice(identity_no: str, audio_bytes: bytes) -> dict:
    try:
        if identity_no not in enrolled_embeddings:
            return {"success": False, "error": f"No voice enrolled for {identity_no}"}

        speech_waveform, has_speech = extract_speech_segments(audio_bytes)

        if not has_speech:
            return {"success": True, "no_speech": True, "is_match": True, "score": 0}

        stored_embedding = enrolled_embeddings[identity_no]
        live_embedding = get_embedding_from_waveform(speech_waveform)

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
