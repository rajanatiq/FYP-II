import sys
import os
import io
import types
import numpy as np
import librosa
# Deep learning tensors ke liye — SpeechBrain model PyTorch pe run karta hai
import torch
import whisper

# k2 ek optional SpeechBrain dependency hai jo humne install nahi ki
# agar k2 pehle se sys.modules mein nahi hai (matlab import nahi hua)
if "k2" not in sys.modules:
    # ek khali/fake k2 module bana do taake SpeechBrain import karte waqt error na aaye
    sys.modules["k2"] = types.ModuleType("k2")

# SpeechBrain ke kuch andar ke modules exist nahi karte install mein
# lekin SpeechBrain unhe dhundta hai — agar nahi mile to crash ho jata hai
# isliye inhe bhi fake/dummy se replace kar dete hain taake crash na ho


# SpeechBrain se ECAPA-TDNN speaker recognition model ka inference class import karo
from speechbrain.inference.speaker import SpeakerRecognition

# voice_samples folder ka full path banao — yahan student ki enrolled WAV files hoti hain
VOICE_SAMPLES_DIR = os.path.join(os.path.dirname(__file__), "voice_samples")
# pretrained ECAPA model folder ka path — pehle se download kiya hua model yahan hota hai
MODEL_DIR = os.path.join(os.path.dirname(__file__), "pretrained_models/spkrec-ecapa-voxceleb")

# cosine similarity ka minimum score jo "same person" maana jaye — 0.75 matlab 75% match chahiye
MATCH_THRESHOLD = 0.75

# SpeakerRecognition model ek baar server start hone par load karo
# source: model ka naam (reference ke liye) — asli model local savedir se load hoga
# savedir: locally download/cached model ka folder
verification_model = SpeakerRecognition.from_hparams(
    source="speechbrain/spkrec-ecapa-voxceleb",
    savedir=MODEL_DIR
)

# enrolled_embeddings ek dictionary hai — key: student identity_no, value: unki voice embedding (numpy array)
enrolled_embeddings = {}

def load_all_embeddings():
    # voice_samples folder mein saari files ki list lo
    all_files = os.listdir(VOICE_SAMPLES_DIR)

    # sirf .npy wali files chahiye — normal loop se filter karo
    npy_files = []
    for f in all_files:
        if f.endswith(".npy"):
            npy_files.append(f)

    # [4043.py, 2022-arid-4097.py]
    # har .npy file ke liye loop chalao
    for f in npy_files:
        # filename se extension hata ke student ID lo, jaise "2021-CS-001.npy" → "2021-CS-001"
        #  split text(f) phly split kry ga ["4043",".npy"] and [0] phla part uthaye ga
        student_id = os.path.splitext(f)[0]
        # us file ka full path banao
        path = os.path.join(VOICE_SAMPLES_DIR, f)
        # numpy array load karo aur dictionary mein student ID ke saath store karo
        enrolled_embeddings[student_id] = np.load(path)  # yahan se load ho gi embedding
       # enroled_embeddiings {"4043":"4043.npy"}

    # kitni embeddings load huin wo print karo — debugging ke liye
    print(f"Loaded {len(enrolled_embeddings)} voice embeddings.")

# server start hone par turant sab embeddings memory mein load karo
load_all_embeddings()

# Whisper STT model ek baar load karo — "base" size model use ho raha hai (fast + accurate balance)
stt_model = whisper.load_model("base")


def transcribe_audio(file_path):
    # librosa se audio load karo — ffmpeg ki zaroorat nahi, 16kHz mono format mein
    # _ matlab second return value (sample rate) humein chahiye nahi, isliye ignore kar diya
    audio, _ = librosa.load(file_path, sr=16000, mono=True)
    # Whisper ko numpy array do aur transcription (text) hasil karo
    result = stt_model.transcribe(audio)
    # result dictionary se sirf text field lo aur extra spaces hata ke return karo
    return result["text"].strip() # return transcript


def extract_speech_segments(audio_bytes):
    # audio bytes ko librosa se load karo — 16kHz mono numpy array milega
    waveform, _ = librosa.load(io.BytesIO(audio_bytes), sr=16000, mono=True)

    # Non-silent intervals nikalo — top_db=25 matlab jo parts 25dB se zyada quiet hain wo silence hain
    # intervals ek list hai jisme [start, end] sample positions hain
    intervals = librosa.effects.split(waveform, top_db=25)

    # agar koi bhi non-silent interval nahi mila — matlab poori audio silence hai
    if len(intervals) == 0:
        return None, False

    # sab speech intervals ko ek list mein jama karo, phir ek saath jodo
    speech_parts = []
    for start, end in intervals:
        # waveform ka sirf yeh hissa lo (start se end tak)
        part = waveform[start:end]
        speech_parts.append(part)

    # sab parts ko ek single array mein jodo
    speech = np.concatenate(speech_parts)

    # 8000 samples = 0.5 second at 16kHz — itni kam speech practically silence hai, skip karo
    if len(speech) < 8000:
        return None, False

    # speech waveform aur True (speech mili hai) return karo
    return speech, True


def get_embedding_from_waveform(waveform):
#Audio
#samples(numpy)
# ↓  torch.tensor()
# PyTorch
# tensor
# ↓  unsqueeze(0)
# Tray
# mein
# rakha
# tensor[[...]]
# ↓  encode_batch()
# ECAPA
# fingerprint[[[0.31, -0.12, ...]]]
# ↓  squeeze()
# Clean
# fingerprint[0.31, -0.12, ...]
# ↓.numpy()
# Numpy
# array — return ✓
    # numpy array ko PyTorch tensor mein convert karo
    waveform_tensor = torch.tensor(waveform)

    # batch dimension add karo — model ko input shape [1, samples] chahiye hoti hai
    waveform_tensor = waveform_tensor.unsqueeze(0)

    # torch.no_grad() se gradient calculation band karo — inference mein gradients ki zaroorat nahi, memory bachti hai
    with torch.no_grad():
        # ECAPA model se voice embedding nikalo — ye ek high-dimensional vector hai jo voice ka "fingerprint" hai
        embedding = verification_model.encode_batch(waveform_tensor) #type: ignore

    # batch dimension hata do (squeeze)
    embedding = embedding.squeeze()

    # PyTorch tensor ko numpy array mein convert karke return karo
    embedding = embedding.numpy()

    return embedding


def cosine_similarity(v1, v2):
    # Step 1: dono vectors ka dot product nikalo — kitne same direction mein hain
    dot_product = np.dot(v1, v2)

    # Step 2: pehle vector ki length (magnitude) nikalo
    norm_v1 = np.linalg.norm(v1)

    # Step 3: doosre vector ki length nikalo
    norm_v2 = np.linalg.norm(v2)

    # Step 4: dot product ko dono lengths ke product se divide karo
    # result: 0 to 1 — 1 matlab bilkul same awaaz, 0 matlab bilkul alag
    similarity = dot_product / (norm_v1 * norm_v2)

    return float(similarity)


def verify_student_voice(identity_no, audio_bytes):
    try:
        # check karo ke is student ki enrolled voice exist karti hai ya nahi
        if identity_no not in enrolled_embeddings:
            # agar nahi hai to error return karo
            return {"success": False, "error": f"No voice enrolled for {identity_no}"}

        # audio se speech segments nikalo aur check karo ke speech hai bhi ya nahi
        speech_waveform, has_speech = extract_speech_segments(audio_bytes)
        # speech_waveform yahan hamary pass silence khtm kr ke combined audio hai
        # agar audio mein koi speech nahi thi (silence ya noise only)
        if not has_speech:
            # silence ko suspicious nahi maante — is_match=True return karo taake false alarm na ho
            return {"success": True, "no_speech": True,  "score": 0}

        # enrolled student ki stored embedding dictionary se nikalo
        stored_embedding = enrolled_embeddings[identity_no]

        # live audio ka embedding nikalo — ECAPA model use hoga
        live_embedding = get_embedding_from_waveform(speech_waveform)

        # stored aur live embedding ke beech cosine similarity nikalo
        score = cosine_similarity(stored_embedding, live_embedding)

        # score MATCH_THRESHOLD (0.75) se zyada ya barabar hai to same person maana jaye
        is_match = score >= MATCH_THRESHOLD

        # score ko 4 decimal places tak round karo
        rounded_score = round(score, 4)

        # result dictionary return karo
        result = {
            "success": True,
            "student_id": identity_no,  # kaun sa student verify hua
            "is_match": is_match,       # True/False — same person hai ya nahi
            "score": rounded_score      # similarity score
        }
        return result

    except Exception as e:
        # koi bhi unexpected error aaye to uski details return karo
        return {"success": False, "error": str(e)}
