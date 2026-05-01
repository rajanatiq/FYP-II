# lib imports
import io
import re
import numpy as np
import cv2
import librosa
import soundfile as sf
from datetime import datetime
from fastapi import UploadFile
from sqlalchemy.orm import Session
import time
import os
from pathlib import Path
from deepface import DeepFace
from retinaface import RetinaFace
from Controllers.UserController import UserController

root_dir = Path(__file__).resolve().parent.parent  # Points to API Folder

# import Models
from Models import (ProctoringEvent, CameraMonitoring, ScreenMonitoring, StudentExamLog, ExamAttempt, StudentDESCExamAudioChunk, StudentMCQExamAudioChunk)

# tarined models for prediction
from ML.FaceCount.faceCount import FaceCounter
from ML.pose_estimation_yaw_pitch.Training.predict_pose import PoseEstimation
from ML.PoseEstimationPivot.PoseEstimation import PoseEstimationClass
from ML.faceCount import FaceCounter

from API.voice_verification import (
    verify_student_voice, transcribe_audio,
    get_embedding_from_waveform, cosine_similarity,
    enrolled_embeddings, stt_model, MATCH_THRESHOLD,
)

# voice_verification sets HF_HUB_OFFLINE=1 — clear it so pyannote can load cached models
os.environ.pop("HF_HUB_OFFLINE", None)
DIARIZATION_AVAILABLE = False
_diarization_pipeline = None
try:
    from pyannote.audio import Pipeline as _PyannotePipeline
    _HF_TOKEN = os.environ.get("HF_TOKEN", "")
    _diarization_pipeline = _PyannotePipeline.from_pretrained(
        "pyannote/speaker-diarization-3.1",
        use_auth_token=_HF_TOKEN if _HF_TOKEN else None,
    )
    DIARIZATION_AVAILABLE = True
    print("[DIARIZATION] Speaker diarization pipeline loaded.")
except Exception as _diar_e:
    print(f"[DIARIZATION] pyannote not available — diarization disabled: {_diar_e}")

_nli_model = None
try:
    from sentence_transformers import CrossEncoder as _CrossEncoder
    _nli_model = _CrossEncoder("cross-encoder/nli-deberta-v3-base")
    print("[NLI] Transcript analysis model loaded.")
except Exception as _nli_e:
    print(f"[NLI] NLI model not available — content analysis disabled: {_nli_e}")

counter = FaceCounter()
predict = PoseEstimation()

retina_face_model = RetinaFace.build_model()  # Building Retina Face Model Once.

pictures_base_folder = str(root_dir / 'Assets/Images/CameraMonitoring')  # Points to Camera Monitoring folder
audios_base_folder = str(root_dir / 'Assets/Audio/VoiceMonitoring')  # Points to Voice Monitoring folder


class ProctoringController:

    # ═══════════════════════════ IMAGE / CAMERA ═══════════════════════════

    @staticmethod
    async def FaceProctoring(file: UploadFile, attempt_id: int, identity_no: str, db: Session):
        '''This method checks the face proctoring, saving the image on the server and add's the entry in the database in the student exam log table. '''

        print(f'attempt id: {attempt_id}')
        examAttempt = db.query(ExamAttempt).filter(ExamAttempt.ID == attempt_id).first()
        if examAttempt:
            content = await file.read()

            np_array = np.frombuffer(content, np.uint8)
            image = cv2.imdecode(np_array, cv2.IMREAD_COLOR)

            # face_count = ProctoringController.count_face_deep_face(content=content)
            # face_count = counter.faceCount(image=image)

            face_count = ProctoringController.count_face(image)

            new_record = StudentExamLog()
            new_record.attempt_id = attempt_id
            new_record.TIMESTAMP = datetime.now()

            position = "unknown"
            try:
                print(f"face count: {face_count}")
                if face_count > 1:
                    new_record.isPresent = True
                    new_record.position = "multiple face detected"
                    position = "Multiple faces detected"
                    # return {"pose": "Multiple faces detected"}

                elif face_count == 0:
                    new_record.isPresent = False
                    new_record.position = "none"
                    position = "no face detected"
                    # return {"pose": "No face detected"}

                else:
                    identity_verified = UserController.verifyPerson(identity_no)
                    print(f"identity = {identity_verified}")

                    if identity_verified == True:
                        pose = PoseEstimationClass.process_face_pose(image)
                        new_record.position = str(pose)
                        new_record.isPresent = True
                        position = pose

                    elif identity_verified == False:
                        new_record.position = "identity mismatched"
                        new_record.isPresent = False
                        position = "Identity Mismatched. Unauthorized Person Detected!"
                    # return {"pose": pose}

                serverImagePath = ProctoringController.saveImageOnServer(content, attempt_id)
                new_record.TIMESTAMP = datetime.now()
                new_record.image_path = serverImagePath
                # print(f"file path = {serverImagePath}, time: {new_record.TIMESTAMP}")
                db.add(new_record)
                db.commit()

                return {'pose': position}
            except Exception as e:
                db.rollback()
                return {'fail': f"data base error {e}"}
        else:
            return {'fail': 'no student record found. '}

    @staticmethod
    async def proctoring_event(file: UploadFile, EX_ID: int, S_ID: int, db: Session):
        try:
            new_event = ProctoringEvent(
                EX_ID=EX_ID,
                S_ID=S_ID,
                EventType="Camera",
                EventTime=datetime.utcnow()
            )
            db.add(new_event)
            db.commit()
            db.refresh(new_event)

            if str(new_event.EventType) == 'Camera':
                new_proctoring = CameraMonitoring(
                    EventID=new_event.ID,
                    IsStudentPresent=1,
                    description="Multiple faces detected in the camera during exam",
                    ImageEvidence=""
                )

                return await ProctoringController.add_proctoring_image(file, new_proctoring, db)
            elif str(new_event.EventType) == 'Screen':
                new_proctoring = ScreenMonitoring(
                    EventID=new_event.ID,
                    ActionType="Close App",
                    EvidanceImage=""
                )

                return await ProctoringController.add_proctoring_image(file, new_proctoring, db)

        except Exception as e:
            db.rollback()
            return {"error": f"Database error: {str(e)}"}, 500

    @staticmethod
    async def add_proctoring_image(file: UploadFile, new_pro: CameraMonitoring, db: Session):
        import os

        folder = "Assets/Images/CameraMonitoring"
        if not os.path.exists(folder):
            os.makedirs(folder)

        if not file.filename:
            return

        ext = file.filename.split('.')[-1]
        id = new_pro.ID

        new_filename = f"image_{id}.{ext}"
        file_path = os.path.join(folder, new_filename)

        # new_pro.ImageEvidence = new_filename

        # Save file manually
        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)
        try:
            db.add(new_pro)
            db.commit()
        except Exception as e:
            db.rollback()
            return {"error": f"Database error: {str(e)}"}, 500

        return {"message": "Image saved successfully", "file_path": file_path}

    @staticmethod
    async def add_screen_image(file: UploadFile, new_pro: ScreenMonitoring, db: Session):
        import os

        folder = "Assets/Images/ScreenMonitoring"
        if not os.path.exists(folder):
            os.makedirs(folder)
        if not file.filename:
            return
        ext = file.filename.split('.')[-1]
        id = new_pro.ID

        new_filename = f"image_{id}.{ext}"
        file_path = os.path.join(folder, new_filename)

        new_pro.ImageEvidence = new_filename

        # Save file manually
        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)
        try:
            db.add(new_pro)
            db.commit()
        except Exception as e:
            db.rollback()
            return {"error": f"Database error: {str(e)}"}, 500

        return {"message": "Image saved successfully", "file_path": file_path}

    @staticmethod
    def saveImageOnServer(image_bytes, attempt_id):
        '''Helper function to save the image on the server, by creating unique file name.'''
        image_path = os.path.join(pictures_base_folder, str(attempt_id))

        if not os.path.exists(image_path):
            os.mkdir(image_path)

        filename = ProctoringController.getTimeStamp() + ".jpg"
        print(filename)
        image_path = os.path.join(image_path, filename)

        ProctoringController.saveFileOnServer(image_bytes, image_path)
        # with open(image_path, "wb") as f:
        #     f.write(image)
        return os.path.join(str(attempt_id), filename)

    @staticmethod
    def count_face(cv2Image):
        '''This function uses retina face for counting numeber of faces in an image.'''

        faces = RetinaFace.detect_faces(cv2Image, model=retina_face_model)

        if faces:
            face_count = len(faces)
        else:
            face_count = 0

        return face_count

    # ═══════════════════════════ VOICE / AUDIO ════════════════════════════
    #
    # ENTRY POINT (Router):
    #   POST /voiceMonitoringDiarize  →  calls VoiceProctoringDiarize()   ← MAIN FUNCTION
    #   POST /verifyVoice             →  calls verifyVoice()               (one-off identity check only)
    #
    # CALL FLOW after a frontend audio chunk is sent:
    #   1. VoiceProctoringDiarize()   — receives the uploaded audio file
    #       ↓
    #   2. saveAudioOnServer()        — saves audio bytes to disk, returns relative_path
    #       ↓  saved at:
    #          Full  : API/Assets/Audio/VoiceMonitoring/{attempt_id}/q{question_id}_{YYYYMMDDHHMMSS}.{ext}
    #          Stored in DB (chunk_url): {attempt_id}/q{question_id}_{YYYYMMDDHHMMSS}.{ext}
    #          Example: 5/q3_20260430143022.wav
    #       ↓
    #   3a. If pyannote NOT installed → verify_student_voice() (simple ECAPA check, no diarization)
    #   3b. If pyannote IS installed  → _diarize_audio()  — detect how many speakers are in the audio
    #       ↓
    #   4a. Single speaker   → verify_student_voice()  — ECAPA embedding match against enrolled voice
    #   4b. Multiple speakers → _build_labeled_transcript() — label each speaker as "Student"/"Other"
    #       ↓
    #   5.  If voice mismatch (suspicious) → transcribe_audio() via Whisper → save record to DB
    #          MCQ exam  → StudentMCQExamAudioChunk  (stores path + transcript)
    #          DESC exam → StudentDESCExamAudioChunk (stores path only)

    @staticmethod
    async def verifyVoice(file: UploadFile, identity_no: str):
        # One-off voice identity check — used before exam starts to confirm student identity.
        # Accepts any audio format (wav, ogg, mp3, mp4, etc.) — converts to WAV before processing.
        try:
            audio_bytes = await file.read()
            wav_bytes = ProctoringController._to_wav_bytes(audio_bytes)
            result = verify_student_voice(identity_no, wav_bytes)
            return result
        except Exception as e:
            return {"success": False, "error": str(e)}

    # ─────────────────────────────────────────────────────────────────────
    # MAIN VOICE PROCTORING FUNCTION
    # Called by route: POST /voiceMonitoringDiarize
    # Parameters received from frontend:
    #   file        — audio chunk (.wav / .mp3) recorded during exam
    #   attempt_id  — which exam attempt this chunk belongs to
    #   identity_no — student's identity number (used to look up enrolled voice)
    #   question_id — which question was being answered when audio was recorded
    #   exam_type   — "mcq" or "desc" (determines which DB table to save suspicious audio)
    #   recorded_at — ISO timestamp from frontend: when AudioRecord.stop() was called on device
    #                 e.g. "2026-04-30T14:30:25.123Z"  stored in DB as the chunk's timestamp
    # ─────────────────────────────────────────────────────────────────────
    @staticmethod
    async def VoiceProctoringDiarize(file: UploadFile, attempt_id: int, identity_no: str, question_id: int, exam_type: str, recorded_at: str, db: Session):
        '''
        Diarization-aware voice monitoring.
        Single speaker  → standard ECAPA verify, plain transcript on mismatch.
        Multiple speakers → labeled transcript (Student/Other), student-only ECAPA score.
        Suspicious audio always saved to DB.
        '''
        # STEP 1: Read uploaded audio bytes from the request
        audio_bytes = await file.read()
        if not audio_bytes:
            return {'error': 'no audio received'}

        # STEP 2: Convert incoming audio to WAV (16kHz mono) regardless of original format.
        # This ensures pyannote, ECAPA, and Whisper all work consistently.
        # Handles: .wav, .ogg, .mp3, .mp4, .m4a, .flac, etc.
        # File is always saved as .wav — original format is not kept.
        wav_bytes = ProctoringController._to_wav_bytes(audio_bytes)

        # STEP 3: Save WAV file to server disk
        # Saved at (full path) : API/Assets/Audio/VoiceMonitoring/{attempt_id}/q{question_id}_{timestamp}.wav
        # relative_path (for DB): {attempt_id}/q{question_id}_{timestamp}.wav
        # Example              : 5/q3_20260430143022.wav
        relative_path = ProctoringController.saveAudioOnServer(wav_bytes, attempt_id, question_id, "wav")
        # full_path is needed by Whisper/pyannote (they read from disk, not from bytes)
        full_path = os.path.join(audios_base_folder, relative_path)
        print(f'[DIARIZE] Audio saved: {relative_path}')

        # STEP 3: Parse frontend timestamp. Fallback to server time if invalid/missing.
        try:
            chunk_timestamp = datetime.fromisoformat(recorded_at.replace("Z", "+00:00"))
        except Exception:
            chunk_timestamp = datetime.now()

        # STEP 4: Inner helper — saves a suspicious audio record to the DB.
        # MCQ  exam → StudentMCQExamAudioChunk  (chunk_url = relative_path, transcript = Whisper text)
        # DESC exam → StudentDESCExamAudioChunk (chunk_url = relative_path, no transcript column)
        # timestamp = frontend recorded_at (when AudioRecord.stop() was called on device)
        def _save_to_db(transcript=None):
            try:
                if exam_type.lower() == 'mcq':
                    record = StudentMCQExamAudioChunk(
                        attemptID=attempt_id,
                        question_id=question_id,
                        chunk_url=relative_path,   # e.g. "5/q3_20260430143022.wav"
                        transcript=transcript,
                        timestamp=chunk_timestamp,
                    )
                else:
                    record = StudentDESCExamAudioChunk(
                        attemptID=attempt_id,
                        question_id=question_id,
                        chunk_url=relative_path,
                        timestamp=chunk_timestamp,
                    )
                db.add(record)
                db.commit()
                return None  # None means no error
            except Exception as e:
                db.rollback()
                return str(e)  # Returns error string if DB fails

        # STEP 4A: pyannote not installed → skip diarization, do simple ECAPA verification only
        if not DIARIZATION_AVAILABLE:
            verification = verify_student_voice(identity_no, wav_bytes)
            if verification.get("no_speech"):
                return {'status': 'silence'}
            is_match = verification.get("is_match", False)
            score = verification.get("score", 0)
            if not is_match:
                # Voice mismatch → transcribe with Whisper, save to DB, return suspicious
                transcript = transcribe_audio(full_path)
                err = _save_to_db(transcript)
                if err:
                    return {'error': f'database error: {err}'}
                return {'status': 'suspicious', 'speakers': 1, 'score': score, 'transcript': transcript, 'diarization': False}
            return {'status': 'match', 'speakers': 1, 'score': score, 'diarization': False}

        # STEP 4B: pyannote IS available → diarize first to count speakers in the saved audio file
        try:
            diar_segments = ProctoringController._diarize_audio(full_path)
            # diar_segments = [(start_sec, end_sec, "SPEAKER_00"), ...]
            unique_speakers = {s[2] for s in diar_segments}
            num_speakers = len(unique_speakers)
            print(f'[DIARIZE] attempt={attempt_id}, speakers_detected={num_speakers}')

            # STEP 5A: Only one speaker detected — do normal ECAPA verification
            if num_speakers <= 1:
                verification = verify_student_voice(identity_no, wav_bytes)
                if verification.get("no_speech"):
                    return {'status': 'silence', 'speakers': 1}
                is_match = verification.get("is_match", False)
                score = verification.get("score", 0)
                if not is_match:
                    # Single speaker but voice doesn't match enrolled student → suspicious
                    transcript = transcribe_audio(full_path)
                    err = _save_to_db(transcript)
                    if err:
                        return {'error': f'database error: {err}'}
                    return {'status': 'suspicious', 'speakers': 1, 'score': score, 'transcript': transcript}
                return {'status': 'match', 'speakers': 1, 'score': score}

            # STEP 5B: Multiple speakers → label each segment "Student" or "Other"
            # _build_labeled_transcript() compares each speaker's ECAPA embedding to enrolled voice,
            # assigns the best-matching speaker as "Student", rest as "Other".
            # Returns labeled transcript like: "Student (0.0s-3.2s): Hello | Other (3.5s-5.1s): cheating"
            labeled_transcript, score, is_match = ProctoringController._build_labeled_transcript(
                full_path, diar_segments, identity_no
            )
            # Extract only "Other" speaker text and run NLI on it
            other_texts = re.findall(r'Other \([\d.]+s-[\d.]+s\): ([^|]+)', labeled_transcript)
            other_combined = " ".join(t.strip() for t in other_texts)
            is_content_suspicious, nli_score = ProctoringController._is_transcript_suspicious(other_combined)
            # Multiple speakers is always flagged as suspicious regardless of score
            err = _save_to_db(labeled_transcript)
            if err:
                return {'error': f'database error: {err}'}
            return {
                'status': 'match' if is_match else 'suspicious',
                'speakers': num_speakers,
                'score': score,
                'transcript': labeled_transcript,
                'other_suspicious': is_content_suspicious,
                'nli_score': nli_score,
            }

        except Exception as e:
            return {'error': str(e)}

    @staticmethod
    def _diarize_audio(audio_path: str) -> list:
        # Runs pyannote speaker diarization on the saved audio file (reads from disk).
        # Returns list of segments: [(start_sec, end_sec, speaker_label), ...]
        # Example: [(0.0, 2.5, 'SPEAKER_00'), (2.8, 5.1, 'SPEAKER_01')]
        result = _diarization_pipeline(audio_path)  # type: ignore
        return [
            (round(turn.start, 2), round(turn.end, 2), speaker)
            for turn, _, speaker in result.itertracks(yield_label=True)
        ]

    _NLI_HYPOTHESES = [
        "The speaker is telling someone to select a specific answer option.",
        "The speaker is giving the correct answer to someone.",
        "Someone is directing another person to choose a particular option.",
        "The speaker is helping someone answer an exam question.",
    ]

    @staticmethod
    def _is_transcript_suspicious(transcript: str):
        if not transcript or len(transcript.strip()) < 5:
            return False, 0.0
        if _nli_model is None:
            return False, 0.0
        pairs = [(transcript, h) for h in ProctoringController._NLI_HYPOTHESES]
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
        return matches >= 2, round(max_entailment, 4)

    @staticmethod
    def _build_labeled_transcript(audio_path: str, diar_segments: list, identity_no: str):
        # For each unique speaker, build one ECAPA embedding by concatenating their audio segments.
        # Compare every speaker's embedding against the enrolled student's embedding via cosine similarity.
        # The speaker with the highest score becomes "Student"; all others become "Other".
        # Then run Whisper on the full audio and map each Whisper segment → nearest diarization label.
        # Returns: (labeled_transcript_string, best_score, is_match)
        import librosa as _librosa
        waveform, sr = _librosa.load(audio_path, sr=16000, mono=True)
        unique_speakers = list({s[2] for s in diar_segments})

        # Build one embedding per unique speaker from their combined audio chunks
        speaker_embeddings = {}
        for spk in unique_speakers:
            chunks = [
                waveform[int(s * sr): int(e * sr)]
                for s, e, lbl in diar_segments if lbl == spk
            ]
            combined = np.concatenate(chunks)
            if len(combined) >= 8000:  # skip clips shorter than 0.5 sec (too short for ECAPA)
                speaker_embeddings[spk] = get_embedding_from_waveform(combined)

        # Find which speaker best matches the enrolled student's voice
        enrolled = enrolled_embeddings.get(identity_no)
        student_speaker = None
        best_score = 0.0
        if enrolled is not None:
            for spk, emb in speaker_embeddings.items():
                sc = cosine_similarity(enrolled, emb)
                if sc > best_score:
                    best_score = sc
                    student_speaker = spk

        is_match = best_score >= MATCH_THRESHOLD

        # Transcribe with Whisper and label each segment using the diarization speaker map
        whisper_result = stt_model.transcribe(waveform, verbose=False)
        whisper_segments = whisper_result.get("segments", [])

        def speaker_at(t: float) -> str:
            # Returns the pyannote speaker label active at time t
            for s, e, spk in diar_segments:
                if s <= t <= e:
                    return spk
            return "__unknown__"

        parts = []
        for ws in whisper_segments:
            mid = (ws["start"] + ws["end"]) / 2
            spk = speaker_at(mid)
            label = "Student" if spk == student_speaker else ("Other" if spk != "__unknown__" else "Unknown")
            parts.append(f"{label} ({ws['start']:.1f}s-{ws['end']:.1f}s): {ws['text'].strip()}")

        return " | ".join(parts), round(best_score, 4), is_match

    @staticmethod
    def saveAudioOnServer(audio_bytes, attempt_id, question_id, ext="wav"):
        '''
        Saves audio bytes to disk and returns the relative path (used as DB chunk_url).

        Folder structure:
          audios_base_folder = API/Assets/Audio/VoiceMonitoring/
          Per-attempt folder  = API/Assets/Audio/VoiceMonitoring/{attempt_id}/
          Filename            = q{question_id}_{YYYYMMDDHHMMSS}.{ext}

        Full path example  : API/Assets/Audio/VoiceMonitoring/5/q3_20260430143022.wav
        Returned (relative): 5/q3_20260430143022.wav   ← this is stored in DB column chunk_url
        '''
        # Create per-attempt folder if it doesn't exist
        audio_path = os.path.join(audios_base_folder, str(attempt_id))
        if not os.path.exists(audio_path):
            os.mkdir(audio_path)

        # Build unique filename: q{question_id}_{timestamp}.{ext}
        filename = f"q{question_id}_{ProctoringController.getTimeStamp()}.{ext}"
        audio_path = os.path.join(audio_path, filename)

        ProctoringController.saveFileOnServer(audio_bytes, audio_path)

        # Return only the relative part so the caller can store it in DB
        # and later reconstruct the full path as: audios_base_folder + "/" + relative_path
        return os.path.join(str(attempt_id), filename)

    # ═══════════════════════════ GENERAL ══════════════════════════════════

    @staticmethod
    def get_student_cheating_count(std_id: int, db: Session):
        '''Method to count the total cheating in the exam of a particular student in exam.'''
        try:
            count = db.query(ProctoringEvent).filter(ProctoringEvent.S_ID == std_id).count()
            return {
                "student_id": std_id,
                "total_violations": count
            }
        except Exception as e:
            return {"error": f"Error: {str(e)}"}, 500

    # ═══════════════════════════ SHARED HELPERS ═══════════════════════════

    @staticmethod
    def _to_wav_bytes(audio_bytes: bytes) -> bytes:
        # Convert any audio format (ogg, mp4, mp3, wav, etc.) to WAV (16kHz, mono).
        # Uses librosa to decode and soundfile to re-encode — no extra dependencies needed.
        # This ensures pyannote, ECAPA, and Whisper all receive a consistent WAV format.
        waveform, _ = librosa.load(io.BytesIO(audio_bytes), sr=16000, mono=True)
        buf = io.BytesIO()
        sf.write(buf, waveform, 16000, format='WAV', subtype='PCM_16')
        buf.seek(0)
        return buf.read()

    @staticmethod
    def saveFileOnServer(data: bytes, path: str):
        with open(path, "wb") as f:
            f.write(data)

        return

    @staticmethod
    def getTimeStamp():
        current_timestamp = time.time()
        local_time = time.localtime(current_timestamp)
        readable_time = time.strftime("%Y%m%d%H%M%S", local_time)
        return readable_time

    # ═══════════════════════════ UNUSED / OLD ═════════════════════════════

    @staticmethod
    def count_face_deep_face(content):
        TEMP_IMAGE = "temp.jpg"
        with open(TEMP_IMAGE, "wb") as buffer:
            buffer.write(content)
        try:
                result = DeepFace.represent(
                    img_path=TEMP_IMAGE,
                    model_name="Facenet",
                    detector_backend="retinaface",
                    enforce_detection=True
                )
                print(len(result))
                face_count = len(result)
                # for i in result:
                #     print(f'Confidence: {i["face_confidence"]}') # type:ignore

        except Exception as e:
                face_count = 0
        return face_count

    # @staticmethod
    # async def VoiceProctoring(file: UploadFile, attempt_id: int, identity_no: str, question_id: int, exam_type: str, db: Session):
    #     '''Saves audio, runs speaker verification. If mismatch, transcribe and store in DB.'''
    #
    #     audio_bytes = await file.read()
    #     if not audio_bytes:
    #         return {'error': 'no audio received'}
    #
    #     ext = file.filename.split(".")[-1] if file.filename else "wav"
    #
    #     relative_path = ProctoringController.saveAudioOnServer(audio_bytes, attempt_id, question_id, ext)
    #
    #     full_path = os.path.join(audios_base_folder, relative_path)
    #     print(f'Audio saved: {relative_path}')
    #
    #     if exam_type.lower() == 'mcq':
    #         verification = verify_student_voice(identity_no, audio_bytes)
    #
    #         if verification.get("no_speech"):
    #             print("No speech detected — skipping")
    #             return {'status': 'silence'}
    #
    #         is_match = verification.get("is_match", False)
    #         score = verification.get("score", 0)
    #         print(f'Voice match: {is_match}, score: {score}')
    #
    #         new_record = StudentMCQExamAudioChunk(
    #                     attemptID=attempt_id,
    #                     question_id=question_id,
    #                     chunk_url=relative_path
    #                 )
    #
    #         if not is_match:
    #             transcript = transcribe_audio(full_path)
    #             new_record.transcript = transcript
    #
    #         try:
    #             db.add(new_record)
    #             db.commit()
    #         except Exception as e:
    #             db.rollback()
    #             return {'error': f'database error {e}'}
    #
    #             return {'status': 'suspicious', 'score': score, 'transcript': transcript}
    #
    #         return {'status': 'match', 'score': score}
    #
    #     return {'audio_path': relative_path}

    # async def FaceProctoring(file: UploadFile, EX_ID: int, S_ID: int, db: Session):

    # MARK: Predict Pose using SVM ->
    # async def FaceProctoring(file: UploadFile):
    #     contents = await file.read()  # bytes
    #     np_array = np.frombuffer(contents, np.uint8)
    #     image = cv2.imdecode(np_array, cv2.IMREAD_COLOR)

    #     if image is None:
    #         return {"error": "can not decode image"}

    #     pose = predict.predict_pose(image)
    #     print(pose)

    #     return {"face pose": pose}
