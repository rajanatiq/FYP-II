"""
Standalone test server for voice verification + transcription.
Run: python test_voice_server.py
Postman: POST http://localhost:8001/test-voice
  - Form-data key: "audio"       (type: File)  → .wav/.ogg/.mp3
  - Form-data key: "identity_no" (type: Text)  → e.g. 2022-arid-4079
"""

import sys
import os

API_DIR = os.path.join(os.path.dirname(__file__), "FYP-II(Backend)", "FYP-II", "API")
sys.path.insert(0, API_DIR)

import uvicorn
from fastapi import FastAPI, UploadFile, File, Form

from API.voice_verification import verify_student_voice, transcribe_audio

app = FastAPI(title="Voice Test Server")


@app.post("/test-voice")
async def test_voice(
    audio: UploadFile = File(...),
    identity_no: str = Form(...)
):
    audio_bytes = await audio.read()

    print(f"\n{'='*50}")
    print(f"  Audio File  : {audio.filename}")
    print(f"  Identity No : {identity_no}")
    print(f"{'='*50}")

    # --- Voice Verification ---
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

    # --- Transcription ---
    print("\n[STEP 2] Extracting transcript with Whisper...")
    transcript = None
    transcript_error = None

    suffix = os.path.splitext(audio.filename)[-1] or ".wav"
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


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)
