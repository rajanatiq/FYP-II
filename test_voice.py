"""
Standalone test server for voice verification + transcription.
Run: python test_voice_server.py

BEFORE RUNNING:
    pip install pyannote.audio
    set HF_TOKEN=your_huggingface_token   (free token from huggingface.co)

ENDPOINTS:
    POST http://localhost:8001/test-voice
        Original endpoint — single score, no diarization.
        Form-data: audio (File), identity_no (Text)

    POST http://localhost:8001/test-voice-diarize
        New endpoint — diarization-aware.
        Single speaker  → standard ECAPA verify, plain transcript on mismatch.
        Multiple speakers → labeled transcript, student-only ECAPA score.
        Form-data: audio (File), identity_no (Text)
"""

import sys
import os
import numpy as np
import librosa

API_DIR = os.path.join(os.path.dirname(__file__), "FYP-II(Backend)", "FYP-II", "API")
sys.path.insert(0, API_DIR)

# voice_verification sets HF_HUB_OFFLINE=1 on import — clear it so pyannote can download
import API.voice_verification  # noqa: F401 — triggers model + embedding load
os.environ.pop("HF_HUB_OFFLINE", None)

from API.voice_verification import (
    verify_student_voice,
    transcribe_audio,
    get_embedding_from_waveform,
    cosine_similarity,
    enrolled_embeddings,
    stt_model,
    MATCH_THRESHOLD,
)

import re
import uvicorn
from fastapi import FastAPI, UploadFile, File, Form

DIARIZATION_AVAILABLE = True
print("[DIARIZATION] Using ECAPA-based speaker diarization (no pyannote needed).")

_nli_model = None
try:
    from sentence_transformers import CrossEncoder as _CrossEncoder
    _nli_model = _CrossEncoder("cross-encoder/nli-deberta-v3-base")
    print("[NLI] Transcript analysis model loaded.")
except Exception as _nli_e:
    print(f"[NLI] NLI model not available: {_nli_e}")

app = FastAPI(title="Voice Test Server")


# ---------------------------------------------------------------------------
# ECAPA sliding-window diarization (no pyannote, uses already-loaded model)
# ---------------------------------------------------------------------------

def _diarize_by_identity(audio_path: str, identity_no: str,
                         window_sec: float = 3.0, stride_sec: float = 1.5) -> tuple:
    """
    Classifies each window directly against the enrolled student embedding.
    Returns:
        segments  : [(start_sec, end_sec, "STUDENT"|"OTHER"), ...]
        best_score: float  — highest per-window similarity to enrolled student
    """
    enrolled = enrolled_embeddings.get(identity_no)
    waveform, sr = librosa.load(audio_path, sr=16000, mono=True)
    total_sec = len(waveform) / sr
    window = int(window_sec * sr)
    stride = int(stride_sec * sr)

    if enrolled is None or len(waveform) < window:
        return [(0.0, round(total_sec, 2), "STUDENT")], 0.0

    window_labels = []
    pos = 0
    while pos + window <= len(waveform):
        chunk = waveform[pos: pos + window]
        emb = get_embedding_from_waveform(chunk)
        sim = cosine_similarity(enrolled, emb)
        start = round(pos / sr, 2)
        end = round((pos + window) / sr, 2)
        label = "STUDENT" if sim >= MATCH_THRESHOLD * 0.85 else "OTHER"
        print(f"[DIAR-DEBUG] {start}s-{end}s  sim={sim:.4f}  → {label}")
        window_labels.append((start, end, label, sim))
        pos += stride

    best_score = max(w[3] for w in window_labels)

    # Merge consecutive windows with the same label
    # Boundary = midpoint between previous window's end and current window's start
    segments = []
    seg_start = window_labels[0][0]
    cur_label = window_labels[0][2]
    for i in range(1, len(window_labels)):
        if window_labels[i][2] != cur_label:
            boundary = round((window_labels[i - 1][1] + window_labels[i][0]) / 2, 2)
            segments.append((seg_start, boundary, cur_label))
            seg_start = boundary
            cur_label = window_labels[i][2]
    segments.append((seg_start, round(total_sec, 2), cur_label))
    return segments, round(best_score, 4)


def _build_labeled_transcript(audio_path: str, diar_segments: list,
                               identity_no: str, best_score: float = 0.0):
    """
    Returns (labeled_transcript: str, score: float, is_match: bool)
    diar_segments labels are already "STUDENT" or "OTHER" from _diarize_by_identity.
    """
    waveform, sr = librosa.load(audio_path, sr=16000, mono=True)
    is_match = best_score >= MATCH_THRESHOLD

    whisper_result = stt_model.transcribe(waveform, verbose=None, language="en", word_timestamps=True)
    whisper_segments = whisper_result.get("segments", [])

    def label_for_time(t: float) -> str:
        for s, e, lbl in diar_segments:
            if s <= t <= e:
                return lbl
        return "OTHER"

    # collect all words with their timestamps
    all_words = []
    for seg in whisper_segments:
        for w in seg.get("words", []):
            all_words.append({
                "word": w["word"],
                "start": w["start"],
                "end": w["end"],
                "label": label_for_time((w["start"] + w["end"]) / 2),
            })

    # group consecutive words with same label
    parts = []
    if all_words:
        cur_label = all_words[0]["label"]
        cur_start = all_words[0]["start"]
        cur_words = [all_words[0]["word"]]
        cur_end = all_words[0]["end"]

        for w in all_words[1:]:
            if w["label"] == cur_label:
                cur_words.append(w["word"])
                cur_end = w["end"]
            else:
                display = "Student" if cur_label == "STUDENT" else "Other"
                parts.append(f"{display} ({cur_start:.1f}s-{cur_end:.1f}s):{' '.join(cur_words)}")
                cur_label = w["label"]
                cur_start = w["start"]
                cur_words = [w["word"]]
                cur_end = w["end"]

        display = "Student" if cur_label == "STUDENT" else "Other"
        parts.append(f"{display} ({cur_start:.1f}s-{cur_end:.1f}s):{' '.join(cur_words)}")

    return " | ".join(parts), best_score, is_match


# ---------------------------------------------------------------------------
# Original endpoint — untouched logic
# ---------------------------------------------------------------------------

@app.post("/test-voice")
async def test_voice(
    audio: UploadFile = File(...),
    identity_no: str = Form(...),
):
    audio_bytes = await audio.read()

    print(f"\n{'='*50}")
    print(f"  Audio File  : {audio.filename}")
    print(f"  Identity No : {identity_no}")
    print(f"{'='*50}")

    print("\n[STEP 1] Running voice verification...")
    verification = verify_student_voice(identity_no, audio_bytes)

    if not verification.get("success"):
        error_msg = verification.get("error")
        print(f"[ERROR] Verification failed: {error_msg}")
        return {"success": False, "error": error_msg}

    if verification.get("no_speech"):
        print("[VERIFICATION] No speech detected — treating as silent, match assumed")
        ver_result = {"no_speech": True, "is_match": True, "score": 0}
    else:
        score = verification.get("score", 0)
        is_match = verification.get("is_match", False)
        status = "MATCH" if is_match else "NO MATCH"
        print(f"[VERIFICATION] Result : {status}")
        print(f"[VERIFICATION] Score  : {score}  (threshold = 0.75)")
        ver_result = {"no_speech": False, "is_match": is_match, "score": score}

    print("\n[STEP 2] Extracting transcript with Whisper...")
    transcript = None
    transcript_error = None

    suffix = os.path.splitext(audio.filename or "")[-1] or ".wav"
    tmp_path = os.path.join(os.path.dirname(__file__), f"_temp_audio{suffix}")

    with open(tmp_path, "wb") as f:
        f.write(audio_bytes)

    try:
        transcript = transcribe_audio(tmp_path)
        print(f'[TRANSCRIPT] "{transcript}"')
    except Exception as e:
        transcript_error = str(e)
        print(f"[TRANSCRIPT ERROR] {transcript_error}")
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

    print(f"\n{'='*50}\n")

    return {
        "identity_no": identity_no,
        "verification": ver_result,
        "transcript": transcript,
        "transcript_error": transcript_error,
    }


# ---------------------------------------------------------------------------
# New diarization-aware endpoint
# ---------------------------------------------------------------------------

@app.post("/test-voice-diarize")
async def test_voice_diarize(
    audio: UploadFile = File(...),
    identity_no: str = Form(...),
):
    if not DIARIZATION_AVAILABLE:
        return {
            "error": (
                "pyannote not available. "
                "Run: pip install pyannote.audio  "
                "and set HF_TOKEN env var (free at huggingface.co)."
            )
        }

    audio_bytes = await audio.read()

    print(f"\n{'='*50}")
    print(f"  [DIARIZE] Audio File  : {audio.filename}")
    print(f"  [DIARIZE] Identity No : {identity_no}")
    print(f"{'='*50}")

    suffix = os.path.splitext(audio.filename or "")[-1] or ".wav"
    tmp_path = os.path.join(os.path.dirname(__file__), f"_temp_diarize{suffix}")

    with open(tmp_path, "wb") as f:
        f.write(audio_bytes)

    try:
        # Step 1 — Identify student vs other windows directly
        print("\n[STEP 1] Running identity-based diarization...")
        diar_segments, best_score = _diarize_by_identity(tmp_path, identity_no)
        unique_labels = {s[2] for s in diar_segments}
        has_other = "OTHER" in unique_labels
        print(f"[DIARIZATION] Segments: {diar_segments}")
        print(f"[DIARIZATION] Other speaker present: {has_other}")

        is_match = best_score >= MATCH_THRESHOLD

        # ----------------------------------------------------------------
        # Case A: Only student detected — plain result
        # ----------------------------------------------------------------
        if not has_other:
            print(f"\n[STEP 2] Only student detected — score: {best_score}")
            transcript = None
            if not is_match:
                print("[STEP 3] Mismatch — transcribing full audio...")
                transcript = transcribe_audio(tmp_path)
                print(f'[TRANSCRIPT] "{transcript}"')

            return {
                "speakers": 1,
                "is_match": is_match,
                "score": best_score,
                "transcript": transcript,
            }

        # ----------------------------------------------------------------
        # Case B: Other speaker detected — labeled transcript
        # ----------------------------------------------------------------
        print("\n[STEP 2] Other speaker detected — building labeled transcript...")
        labeled_transcript, score, _ = _build_labeled_transcript(
            tmp_path, diar_segments, identity_no, best_score
        )
        print(f"[VERIFICATION] score: {score} — MISMATCH (other speaker detected)")
        print(f'[TRANSCRIPT] "{labeled_transcript}"')

        return {
            "speakers": len(unique_labels),
            "is_match": False,
            "score": score,
            "transcript": labeled_transcript,
        }

    except Exception as e:
        return {"error": str(e)}

    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


# ---------------------------------------------------------------------------
# NLI helper
# ---------------------------------------------------------------------------

_NLI_HYPOTHESES = [
    "The speaker is telling someone to select a specific answer option.",
    "The speaker is giving the correct answer to someone.",
    "Someone is directing another person to choose a particular option.",
    "The speaker is helping someone answer an exam question.",
]

def _is_transcript_suspicious(transcript: str):
    if not transcript or len(transcript.strip()) < 5:
        return False, 0.0, "none"
    if _nli_model is None:
        return False, 0.0, "none"
    pairs = [(transcript, h) for h in _NLI_HYPOTHESES]
    all_scores = _nli_model.predict(pairs)
    max_entailment = 0.0
    matches = 0
    for s in all_scores:
        probs = np.exp(s) / np.exp(s).sum()
        entailment_prob = float(probs[1])
        if entailment_prob > max_entailment:
            max_entailment = entailment_prob
        if entailment_prob > 0.5:
            matches += 1
    return matches >= 2, round(max_entailment, 4), "nli"


# ---------------------------------------------------------------------------
# NLI text-only endpoint — quick test without audio
# ---------------------------------------------------------------------------

@app.post("/test-nli-text")
async def test_nli_text(text: str = Form(...)):
    """
    Quick NLI test — just send raw text, get back suspicious/clean result.
    Form-data: text (Text)
    """
    print(f"\n{'='*50}")
    print(f"  [NLI-TEXT] Input: {text}")
    print(f"{'='*50}")

    is_suspicious, nli_score, method = _is_transcript_suspicious(text)
    result = "SUSPICIOUS" if is_suspicious else "CLEAN"
    print(f"[NLI] Result: {result}  |  Score: {nli_score}  |  Method: {method}")

    return {
        "text": text,
        "is_suspicious": is_suspicious,
        "nli_score": nli_score,
        "detected_by": method,
        "result": result,
    }


# ---------------------------------------------------------------------------
# NLI audio endpoint — full pipeline: diarize → extract Other → NLI
# ---------------------------------------------------------------------------

@app.post("/test-nli")
async def test_nli(
    audio: UploadFile = File(...),
    identity_no: str = Form(...),
):
    """
    Full NLI pipeline test.
    Diarizes audio → extracts Other speaker text → runs NLI on it.
    Form-data: audio (File), identity_no (Text)
    """
    if _nli_model is None:
        return {"error": "NLI model not loaded"}

    audio_bytes = await audio.read()

    print(f"\n{'='*50}")
    print(f"  [NLI] Audio File  : {audio.filename}")
    print(f"  [NLI] Identity No : {identity_no}")
    print(f"{'='*50}")

    suffix = os.path.splitext(audio.filename or "")[-1] or ".wav"
    tmp_path = os.path.join(os.path.dirname(__file__), f"_temp_nli{suffix}")

    with open(tmp_path, "wb") as f:
        f.write(audio_bytes)

    try:
        # Step 1 — Diarize
        print("\n[STEP 1] Running diarization...")
        diar_segments, best_score = _diarize_by_identity(tmp_path, identity_no)
        unique_labels = {s[2] for s in diar_segments}
        has_other = "OTHER" in unique_labels
        is_match = best_score >= MATCH_THRESHOLD
        print(f"[DIARIZATION] Segments : {diar_segments}")
        print(f"[DIARIZATION] Other speaker present: {has_other}")

        # No OTHER detected — skip Whisper + NLI entirely
        if not has_other:
            print("\n[STEP 2] Only student detected — skipping transcription and NLI.")
            return {
                "speakers": 1,
                "is_match": is_match,
                "score": best_score,
                "transcript": None,
                "other_text": None,
                "other_suspicious": False,
                "nli_score": 0.0,
            }

        # Step 2 — OTHER detected — build labeled transcript
        print("\n[STEP 2] Other speaker detected — building labeled transcript...")
        labeled_transcript, score, is_match = _build_labeled_transcript(
            tmp_path, diar_segments, identity_no, best_score
        )
        print(f'[TRANSCRIPT] "{labeled_transcript}"')

        # Step 3 — Extract Other text and run NLI
        other_texts = re.findall(r'Other \([\d.]+s-[\d.]+s\):([^|]+)', labeled_transcript)
        other_combined = " ".join(t.strip() for t in other_texts)
        print(f'[NLI] Other speaker text: "{other_combined}"')

        if not other_combined:
            print("[NLI] No Other speaker text found — skipping NLI")
            return {
                "speakers": len(unique_labels),
                "is_match": is_match,
                "score": score,
                "transcript": labeled_transcript,
                "other_text": None,
                "other_suspicious": False,
                "nli_score": 0.0,
            }

        is_suspicious, nli_score, method = _is_transcript_suspicious(other_combined)
        result = "SUSPICIOUS" if is_suspicious else "CLEAN"
        print(f"[NLI] Result: {result}  |  Score: {nli_score}  |  Method: {method}")

        return {
            "speakers": len(unique_labels),
            "is_match": is_match,
            "score": score,
            "transcript": labeled_transcript,
            "other_text": other_combined,
            "other_suspicious": is_suspicious,
            "nli_score": nli_score,
            "detected_by": method,
        }

    except Exception as e:
        return {"error": str(e)}

    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)
