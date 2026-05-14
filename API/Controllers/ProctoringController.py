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
from API.Controllers.UserController import UserController
from datetime import datetime
import asyncio
import mediapipe as mp
from ultralytics import YOLO #type: ignore
from concurrent.futures import ProcessPoolExecutor

process_executor = ProcessPoolExecutor(max_workers=6)

root_dir = Path(__file__).resolve().parent.parent  # Points to API Folder

yolo_model_path = str(root_dir.parent / "ML/ObjectDetection/yolov8n.pt")

object_detection_model = YOLO(yolo_model_path)

# import Models
from API.Models import (ProctoringEvent, CameraMonitoring, ScreenMonitoring, StudentExamLog, ExamAttempt, StudentDESCExamAudioChunk, StudentMCQExamAudioChunk, DetectedObjects)

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

print("[DIARIZATION] Using ECAPA-based speaker diarization (no pyannote needed).")

_nli_model = None
try:
    # offline mode on karo taake sentence_transformers internet check na kare
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    os.environ["HF_DATASETS_OFFLINE"] = "1"
    from sentence_transformers import CrossEncoder as _CrossEncoder
    _nli_model = _CrossEncoder("cross-encoder/nli-deberta-v3-base")
    print("[NLI] Transcript analysis model loaded.")
except Exception as _nli_e:
    print(f"[NLI] NLI model not available — content analysis disabled: {_nli_e}")

counter = FaceCounter()
predict = PoseEstimation()

retina_face_model = RetinaFace.build_model()  # Building Retina Face Model Once.

pictures_base_folder = str(root_dir / 'Assets/Images/CameraMonitoring')  # Points to Camera Monitoring folder
back_camera_base_folder = str(root_dir / 'Assets/Images/BackCamera')  # Points to Back Camera folder
audios_base_folder = str(root_dir / 'Assets/Audio/VoiceMonitoring')  # Points to Voice Monitoring folder


mp_face_mesh = mp.solutions.face_mesh # type: ignore

face_mesh = mp_face_mesh.FaceMesh(
    static_image_mode=True,
    max_num_faces=1,
    refine_landmarks=True,
    min_detection_confidence=0.5
)
cheating_objects = ["cell phone", "book", "laptop", "tv", "remote"]

class ProctoringController:

    # ═══════════════════════════ IMAGE / CAMERA ═══════════════════════════

    @staticmethod
    def bytes_to_numpy(image_bytes: bytes) -> np.ndarray:
        nparr = np.frombuffer(image_bytes, np.uint8)
        image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        return image # type: ignore
    
    @staticmethod
    async def FaceProctoring(file: UploadFile, attempt_id: int, identity_no: str, db: Session):
        '''This method checks the face proctoring, saving the image on the server and add's the entry in the database in the student exam log table. '''

        
        print(f'attempt id: {attempt_id}')
        examAttempt = db.query(ExamAttempt).filter(ExamAttempt.ID == attempt_id).first()
        if examAttempt:
            
            image_bytes = await file.read()
            image_array = ProctoringController.bytes_to_numpy(image_bytes)

            # face_count = ProctoringController.count_face_deep_face(content=content)
            # face_count = counter.faceCount(image=image)

            face_count = ProctoringController.count_face(image_array)

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
                    identity_verified = UserController.verifyPerson(identity_no, image_array)
                    
                    print(f"identity = {identity_verified}")
                    
                    if identity_verified == True:
                        pose = str(PoseEstimationClass.process_face_pose(image_array))
                        
                        new_record.eye_gaze = ProctoringController.EyeGazeMovement(image_array)
                            
                        new_record.position = pose
                        new_record.isPresent = True 
                        position = pose

                    elif identity_verified == False:
                        new_record.position = "identity mismatched"
                        new_record.isPresent = False
                        position = "Identity Mismatched. Unauthorized Person Detected!"
                    # return {"pose": pose}

                serverImagePath = ProctoringController.saveImageOnServer(pictures_base_folder,image_bytes, attempt_id, time)
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
    def saveImageOnServer(baseFolder, image_bytes, attempt_id, time):
        '''Helper function to save the image on the server, by creating unique file name.'''
        # image_path = os.path.join(pictures_base_folder, str(attempt_id))
        image_path = os.path.join(baseFolder, str(attempt_id))

        if not os.path.exists(image_path):
            os.mkdir(image_path)

        filename = time + ".jpg"
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
    #   3. _diarize_by_identity() — ECAPA sliding-window: labels each window "STUDENT" or "OTHER"
    #       ↓
    #   4a. Only STUDENT detected → verify_student_voice() — ECAPA match + no_speech check
    #   4b. OTHER detected        → _build_labeled_transcript() — label each word "Student"/"Other"
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
    async def VoiceProctoringDiarize(file: UploadFile, attempt_id: int, identity_no: str, question_id: int, exam_type: str, start_time: str, end_time: str, db: Session):
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
        # Handles: .wav, .ogg, .mp3, .mp4, .m4a, .flac, etc.
        # File is always saved as .wav — original format is not kept.
        wav_bytes = ProctoringController._to_wav_bytes(audio_bytes)

        # STEP 3: Save WAV file to server disk
        # Saved at (full path) : API/Assets/Audio/VoiceMonitoring/{attempt_id}/q{question_id}_{timestamp}.wav
        # relative_path (for DB): {attempt_id}/q{question_id}_{timestamp}.wav
        # Example              : 5/q3_20260430143022.wav
        relative_path = ProctoringController.saveAudioOnServer(wav_bytes, attempt_id, question_id, "wav")
        # full_path is needed by Whisper and ECAPA (they read from disk, not from bytes)
        full_path = os.path.join(audios_base_folder, relative_path)
        print(f'[DIARIZE] Audio saved: {relative_path}')

        # STEP 3: Parse frontend timestamp. Fallback to server time if invalid/missing.
        try:
            chunk_timestamp = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
        except Exception:
            chunk_timestamp = datetime.now()

            
        # STEP 4: Inner helper — saves a suspicious audio record to the DB.
        # MCQ  exam → StudentMCQExamAudioChunk  (chunk_url = relative_path, transcript = Whisper text)
        # DESC exam → StudentDESCExamAudioChunk (chunk_url = relative_path, no transcript column)
        # timestamp = frontend recorded_at (when AudioRecord.stop() was called on device)
        # def _save_to_db(transcript=None):
        #     try:
        #         if exam_type.lower() == 'mcq':
        #             record = StudentMCQExamAudioChunk(
        #                 attemptID=attempt_id,
        #                 question_id=question_id,
        #                 chunk_url=relative_path,   # e.g. "5/q3_20260430143022.wav"
        #                 transcript=transcript,
        #                 timestamp=chunk_timestamp,
        #             )
        #         else:
        #             record = StudentDESCExamAudioChunk(
        #                 attemptID=attempt_id,
        #                 question_id=question_id,
        #                 chunk_url=relative_path,
        #                 timestamp=chunk_timestamp,
        #             )
        #         db.add(record)
        #         db.commit()
        #         return None  # None means no error
        #     except Exception as e:
        #         db.rollback()
        #         return str(e)  # Returns error string if DB fails

        # STEP 4: ECAPA sliding-window diarization — classifies each window as STUDENT or OTHER
        try:
            diar_segments, best_score = ProctoringController._diarize_by_identity(full_path, identity_no)
            unique_labels = {s[2] for s in diar_segments}
            
            print('printing unique labels................')
            for i in unique_labels:
                print(i)
                
            has_other = "OTHER" in unique_labels
            is_match = best_score >= MATCH_THRESHOLD
            print(f'[DIARIZE] attempt={attempt_id}, other_speaker={has_other}, score={best_score}')

            print(f'has_other = {has_other}')
            
            # STEP 5A: Only student detected — standard verify (handles no_speech + score)
            if not has_other:
                verification = verify_student_voice(identity_no, wav_bytes)
                if verification.get("no_speech"):
                    
                    # db, examtype, attemptid, questionid, path, transcript, student voice matched ?, other person present? , iscontentsuspicious, starttime, endtime
                    
                    ProctoringController.save_audio_to_db(db, exam_type, attempt_id, question_id, relative_path, "", True, False, True, start_time , end_time)
                    
                    
                    # ave_audio_to_db(db: Session, exam_type: str, attempt_id: int, question_id: int, relative_path: str, labeled_transcript: str, is_match: bool, other_person: bool, is_content_suspicious:bool, start_time: str, end_time: str):
                        
                        
                    return {'status': 'silence', 'speakers': 1}
                is_match = verification.get("is_match", False)
                score = verification.get("score", 0)
                
                transcript = transcribe_audio(full_path)
                print(transcript)
                if not is_match:
                    # err = _save_to_db(transcript)
                    # if err:
                    
                    #     return {'error': f'database error: {err}'}
                    print('single user but not matched')
                    ProctoringController.save_audio_to_db(db, exam_type, attempt_id, question_id, relative_path, transcript, is_match, True, True, start_time , end_time)
                    
                    return {'status': 'suspicious', 'speakers': 1, 'score': score, 'transcript': transcript}
                ProctoringController.save_audio_to_db(db, exam_type, attempt_id, question_id, relative_path, transcript, is_match, False, False, start_time , end_time)
                
                return {'status': 'match', 'speakers': 1, 'score': score}

            # STEP 5B: OTHER speaker detected — labeled transcript + NLI
            # is_match = True if STUDENT appears in any segment (mixed), False if completely absent.
            labeled_transcript, score, _ = ProctoringController._build_labeled_transcript(
                full_path, diar_segments, identity_no, best_score
            )
            is_match = "STUDENT" in unique_labels

            # Completely OTHER — student absent, skip NLI
            if not is_match:
                ProctoringController.save_audio_to_db(db, exam_type, attempt_id, question_id, relative_path, labeled_transcript, False, True, False, start_time, end_time)
                return {
                    'status': 'suspicious',
                    'is_match': False,
                    'speakers': len(unique_labels),
                    'score': score,
                    'transcript': labeled_transcript,
                    'other_suspicious': False,
                    'nli_score': 0.0,
                }

            # Mixed (STUDENT + OTHER) — run NLI on other person's text
            other_texts = re.findall(r'Other \([\d.]+s-[\d.]+s\):([^|]+)', labeled_transcript)
            other_combined = " ".join(t.strip() for t in other_texts)
            is_content_suspicious, nli_score = ProctoringController._is_transcript_suspicious(other_combined)

            ProctoringController.save_audio_to_db(db, exam_type, attempt_id, question_id, relative_path, labeled_transcript, is_match, True, is_content_suspicious, start_time, end_time)

            print('last matched')

            return {
                'status': 'suspicious',
                'is_match': is_match,
                'speakers': len(unique_labels),
                'score': score,
                'transcript': labeled_transcript,
                'other_suspicious': is_content_suspicious,
                'nli_score': nli_score,
            }

        except Exception as e:
            return {'error': str(e)}
    
    
    # @staticmethod
    # async def VoiceProctoringDiarize(file: UploadFile, attempt_id: int, identity_no: str, question_id: int, exam_type: str, start_time: str, end_time: str, db: Session):
    #     '''
    #     Diarization-aware voice monitoring.
    #     Single speaker  → standard ECAPA verify, plain transcript on mismatch.
    #     Multiple speakers → labeled transcript (Student/Other), student-only ECAPA score.
    #     Suspicious audio always saved to DB.
    #     '''
        
    #     print(f'identity no: {identity_no}, attempt id: {attempt_id}, question id: {question_id}, exam type: {exam_type}, start time: {start_time}, end time: {end_time}')
        
        
    #     # STEP 1: Read uploaded audio bytes from the request
    #     audio_bytes = await file.read()
    #     if not audio_bytes:
    #         return {'error': 'no audio received'}

    #     # STEP 2: Convert incoming audio to WAV (16kHz mono) regardless of original format.
    #     # Handles: .wav, .ogg, .mp3, .mp4, .m4a, .flac, etc.
    #     # File is always saved as .wav — original format is not kept.
    #     wav_bytes = ProctoringController._to_wav_bytes(audio_bytes)

    #     # STEP 3: Save WAV file to server disk
    #     # Saved at (full path) : API/Assets/Audio/VoiceMonitoring/{attempt_id}/q{question_id}_{timestamp}.wav
    #     # relative_path (for DB): {attempt_id}/q{question_id}_{timestamp}.wav
    #     # Example              : 5/q3_20260430143022.wav
    #     relative_path = ProctoringController.saveAudioOnServer(wav_bytes, attempt_id, question_id, "wav")
    #     # full_path is needed by Whisper and ECAPA (they read from disk, not from bytes)
    #     full_path = os.path.join(audios_base_folder, relative_path)
    #     print(f'[DIARIZE] Audio saved: {relative_path}')

    #     # STEP 3: Parse frontend timestamp. Fallback to server time if invalid/missing.
    #     try:
    #         chunk_timestamp = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
    #     except Exception:
    #         chunk_timestamp = datetime.now()

            
    #     # STEP 4: Inner helper — saves a suspicious audio record to the DB.
    #     # MCQ  exam → StudentMCQExamAudioChunk  (chunk_url = relative_path, transcript = Whisper text)
    #     # DESC exam → StudentDESCExamAudioChunk (chunk_url = relative_path, no transcript column)
    #     # timestamp = frontend recorded_at (when AudioRecord.stop() was called on device)
    #     # def _save_to_db(transcript=None):
    #     #     try:
    #     #         if exam_type.lower() == 'mcq':
    #     #             record = StudentMCQExamAudioChunk(
    #     #                 attemptID=attempt_id,
    #     #                 question_id=question_id,
    #     #                 chunk_url=relative_path,   # e.g. "5/q3_20260430143022.wav"
    #     #                 transcript=transcript,
    #     #                 timestamp=chunk_timestamp,
    #     #             )
    #     #         else:
    #     #             record = StudentDESCExamAudioChunk(
    #     #                 attemptID=attempt_id,
    #     #                 question_id=question_id,
    #     #                 chunk_url=relative_path,
    #     #                 timestamp=chunk_timestamp,
    #     #             )
    #     #         db.add(record)
    #     #         db.commit()
    #     #         return None  # None means no error
    #     #     except Exception as e:
    #     #         db.rollback()
    #     #         return str(e)  # Returns error string if DB fails

    #     # STEP 4: ECAPA sliding-window diarization — classifies each window as STUDENT or OTHER
    #     try:
    #         diar_segments, best_score = ProctoringController._diarize_by_identity(full_path, identity_no)
    #         unique_labels = {s[2] for s in diar_segments}
            
    #         print('printing unique labels................')
    #         for i in unique_labels:
    #             print(i)
                
    #         has_other = "OTHER" in unique_labels
    #         is_match = best_score >= MATCH_THRESHOLD
    #         print(f'[DIARIZE] attempt={attempt_id}, other_speaker={has_other}, score={best_score}')

    #         print(f'has_other = {has_other}')
            
    #         # STEP 5A: Only student detected — standard verify (handles no_speech + score)
    #         if not has_other:
    #             verification = verify_student_voice(identity_no, wav_bytes)
    #             if verification.get("no_speech"):
                    
    #                 # db, examtype, attemptid, questionid, path, transcript, student voice matched ?, other person present? , iscontentsuspicious, starttime, endtime
                    
    #                 ProctoringController.save_audio_to_db(db, exam_type, attempt_id, question_id, relative_path, "", True, False, True, start_time , end_time)
                    
                    
    #                 # ave_audio_to_db(db: Session, exam_type: str, attempt_id: int, question_id: int, relative_path: str, labeled_transcript: str, is_match: bool, other_person: bool, is_content_suspicious:bool, start_time: str, end_time: str):
                        
                        
    #                 return {'status': 'silence', 'speakers': 1}
    #             is_match = verification.get("is_match", False)
    #             score = verification.get("score", 0)
                
    #             transcript = transcribe_audio(full_path)
    #             print(transcript)
    #             if not is_match:
    #                 # err = _save_to_db(transcript)
    #                 # if err:
                    
    #                 #     return {'error': f'database error: {err}'}
    #                 print('single user but not matched')
    #                 ProctoringController.save_audio_to_db(db, exam_type, attempt_id, question_id, relative_path, transcript, is_match, True, True, start_time , end_time)
                    
    #                 return {'status': 'suspicious', 'speakers': 1, 'score': score, 'transcript': transcript}
    #             ProctoringController.save_audio_to_db(db, exam_type, attempt_id, question_id, relative_path, transcript, is_match, False, False, start_time , end_time)
                
    #             return {'status': 'match', 'speakers': 1, 'score': score}

    #         # STEP 5B: OTHER speaker detected — labeled transcript + NLI
    #         labeled_transcript, score, is_match = ProctoringController._build_labeled_transcript(
    #             full_path, diar_segments, identity_no, best_score
    #         )
    #         other_texts = re.findall(r'Other \([\d.]+s-[\d.]+s\):([^|]+)', labeled_transcript)
    #         other_combined = " ".join(t.strip() for t in other_texts)
    #         is_content_suspicious, nli_score = ProctoringController._is_transcript_suspicious(other_combined)
    #         # err = _save_to_db(labeled_transcript)
    #         # if err:
    #         #     return {'error': f'database error: {err}'}
            
    #         ProctoringController.save_audio_to_db(db, exam_type, attempt_id, question_id, relative_path, labeled_transcript, is_match, True if len(unique_labels) > 1 else False , is_content_suspicious, start_time , end_time)
            
    #         print('last matched')
            
    #         return {
    #             'status': 'suspicious',
    #             'is_match': is_match,
    #             'speakers': len(unique_labels),
    #             'score': score,
    #             'transcript': labeled_transcript,
    #             'other_suspicious': is_content_suspicious,
    #             'nli_score': nli_score,
    #         }

    #     except Exception as e:
    #         return {'error': str(e)}

    @staticmethod
    def save_audio_to_db(db: Session, exam_type: str, attempt_id: int, question_id: int, relative_path: str, labeled_transcript: str, is_match: bool, other_person: bool, is_content_suspicious:bool, start_time: str, end_time: str):
        try:
            if exam_type.lower() == 'mcq':
                
                suspicious = True if is_content_suspicious else True if not is_match else False
                
                new_record = StudentMCQExamAudioChunk(
                    attemptID = attempt_id,
                    question_id = question_id,
                    chunk_url = relative_path,
                    transcript = labeled_transcript,
                    student_present = 1 if is_match else 0,
                    other_person = 1 if other_person else 0,
                    other_suspicous = 1 if is_content_suspicious else 0,
                    start_time = datetime.fromisoformat(start_time),
                    end_time = datetime.fromisoformat(end_time),
                    is_suspicious = suspicious
                )
                
                db.add(new_record)
                db.commit()
                db.refresh(new_record)
            
            elif exam_type.lower() == 'desc':
                suspicious = True if is_content_suspicious else True if not is_match else False
                
                new_record = StudentDESCExamAudioChunk(
                    attemptID = attempt_id,
                    question_id = question_id,
                    chunk_url = relative_path,
                    transcript = labeled_transcript,
                    student_present = 1 if is_match else 0,
                    other_person = 1 if other_person else 0,
                    other_suspicous = 1 if is_content_suspicious else 0,
                    start_time = datetime.fromisoformat(start_time),
                    end_time = datetime.fromisoformat(end_time),
                    is_suspicious = suspicious
                )
                
                db.add(new_record)
                db.commit()
                db.refresh(new_record)
                print(f'record added in db with id {new_record.ID}')

        except Exception as e:
            print(f"ERROR: {e}")
            db.rollback()
    @staticmethod
    def _diarize_by_identity(audio_path, identity_no,
                             window_sec=3.0, stride_sec=1.5):

        # voice_verification.py ki dictionary se is student ki enrolled embedding lo
        enrolled = enrolled_embeddings.get(identity_no)

        # audio file disk se load karo — 16kHz mono numpy array milega
        # sr = sample rate (16000 matlab 1 second mein 16000 samples)
        waveform, sr = librosa.load(audio_path, sr=16000, mono=True)

        # poori audio ki length seconds mein nikalo
        # jaise 48000 samples / 16000 = 3.0 seconds
        total_sec = len(waveform) / sr

        # window ka size samples mein convert karo
        # 3.0 sec * 16000 = 48000 samples — ek baar mein itni audio analyze hogi
        window = int(window_sec * sr)

        # stride ka size samples mein convert karo
        # 1.5 sec * 16000 = 24000 samples — har baar window itna aage khiskega
        stride = int(stride_sec * sr)


        print(f'inside diarize by identity enrolled:')
        # agar student ki koi enrolled voice nahi hai
        # ya audio itni choti hai ke ek bhi window fit nahi hota
        if enrolled is None or len(waveform) < window:
            # poori audio ko STUDENT maano aur score 0 return karo
            return [(0.0, round(total_sec, 2), "STUDENT")], 0.0

        # har window ka result yahan store hoga — (start, end, label, score)
        window_labels = []

        # audio ke start se shuru karo
        pos = 0

        # jab tak window audio ke andar fit hota rahe
        while pos + window <= len(waveform):

            # audio ka yeh hissa nikalo (pos se pos+window tak)
            chunk = waveform[pos: pos + window]

            # is chunk ka ECAPA fingerprint (embedding) nikalo
            emb = get_embedding_from_waveform(chunk)

            # enrolled student ki embedding se compare karo — similarity score nikalo
            sim = cosine_similarity(enrolled, emb)

            # is window ka start time seconds mein
            start = round(pos / sr, 2)

            # is window ka end time seconds mein
            end = round((pos + window) / sr, 2)

            # agar similarity MATCH_THRESHOLD ka 85% ya zyada hai to STUDENT, warna OTHER
            # 0.85 isliye use kiya — thoda lenient threshold, partial match bhi STUDENT maana jaye
            if sim >= MATCH_THRESHOLD * 0.85:
                label = "STUDENT"
            else:
                label = "OTHER"
            
            # debugging ke liye print karo — kaunsa window, kitna score, kya label mila
            print(f"[DIAR-DEBUG] {start}s-{end}s  sim={sim:.4f}  → {label}")

            # is window ka result list mein save karo
            window_labels.append((start, end, label, sim))

            # window ko stride jitna aage khisao — next chunk pe jao
            pos += stride

        # sab windows mein se sabse zyada similarity score nikalo
        # w[3] matlab tuple ka 4th element jo similarity score hai
        best_score = max(w[3] for w in window_labels)

        # ab consecutive windows ko merge karo — same label wale windows ek segment ban jayenge
        segments = []

        # pehle window se shuru karo
        seg_start = window_labels[0][0]  # pehle window ka start time
        cur_label = window_labels[0][2]  # pehle window ka label (STUDENT ya OTHER)

        # index 1 se shuru karo kyunke index 0 upar handle kar liya
        for i in range(1, len(window_labels)):

            # agar is window ka label pichle window se alag hai — matlab speaker badal gaya
            if window_labels[i][2] != cur_label:
                # boundary = pichle window ke end aur is window ke start ka darmiyaan wala point
                boundary = round((window_labels[i - 1][1] + window_labels[i][0]) / 2, 2)

                # pichla segment complete hua — list mein save karo
                segments.append((seg_start, boundary, cur_label))

                # naya segment yahan se shuru hoga
                seg_start = boundary
                cur_label = window_labels[i][2]

        # loop khatam hone ke baad last segment bhi save karo — audio ke end tak
        segments.append((seg_start, round(total_sec, 2), cur_label))

        # segments list aur best score return karo
        return segments, round(best_score, 4)

    # NLI model ko ye 4 sentences diye jaate hain check karne ke liye
    # ke "Other" speaker ka transcript cheating suggest karta hai ya nahi
    _NLI_HYPOTHESES = [
        "The speaker is telling someone to select a specific answer option.",
        # kisi ko specific option chunne bol raha hai
        "The speaker is giving the correct answer to someone.",  # kisi ko sahi jawab bata raha hai
        "Someone is directing another person to choose a particular option.",  # kisi ko option select karwa raha hai
        "The speaker is helping someone answer an exam question.",  # exam question mein help kar raha hai
    ]
    @staticmethod
    def _is_transcript_suspicious(transcript: str):
        if not transcript or len(transcript.strip()) < 5:
            return False, 0.0
        if _nli_model is None:
            return False, 0.0
        pairs = [(transcript, h) for h in ProctoringController._NLI_HYPOTHESES]
        all_scores = _nli_model.predict(pairs) # type: ignore
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
    def _build_labeled_transcript(audio_path: str, diar_segments: list, identity_no: str, best_score: float = 0.0):
        # diar_segments already carry "STUDENT"/"OTHER" labels from _diarize_by_identity.
        # Runs Whisper with word timestamps and maps each word to its speaker label.
        # Returns: (labeled_transcript_string, best_score, is_match)
        waveform, sr = librosa.load(audio_path, sr=16000, mono=True)
        is_match = best_score >= MATCH_THRESHOLD

        whisper_result = stt_model.transcribe(waveform, verbose=False, language="en", word_timestamps=True)
        whisper_segments = whisper_result.get("segments", [])

        def label_for_time(t: float) -> str:
            for s, e, lbl in diar_segments:
                if s <= t <= e:
                    return lbl
            return "OTHER"

        all_words = []
        for seg in whisper_segments:
            for w in seg.get("words", []): #type: ignore
                all_words.append({
                    "word": w["word"],
                    "start": w["start"],
                    "end": w["end"],
                    "label": label_for_time((w["start"] + w["end"]) / 2),
                })

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
        # This ensures ECAPA and Whisper both receive a consistent WAV format.
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

    @staticmethod
    async def VoiceProctoring(file: UploadFile, attempt_id: int, identity_no: str, question_id: int, exam_type: str, db: Session):
        '''Saves audio, runs speaker verification. If mismatch, transcribe and store in DB.'''
    
        audio_bytes = await file.read()
        if not audio_bytes:
            return {'error': 'no audio received'}
    
        ext = file.filename.split(".")[-1] if file.filename else "wav"
    
        relative_path = ProctoringController.saveAudioOnServer(audio_bytes, attempt_id, question_id, ext)
    
        full_path = os.path.join(audios_base_folder, relative_path)
        print(f'Audio saved: {relative_path}')
    
        if exam_type.lower() == 'mcq':
            verification = verify_student_voice(identity_no, audio_bytes)
    
            if verification.get("no_speech"):
                print("No speech detected — skipping")
                return {'status': 'silence'}
    
            is_match = verification.get("is_match", False)
            score = verification.get("score", 0)
            print(f'Voice match: {is_match}, score: {score}')
    
            new_record = StudentMCQExamAudioChunk(
                        attemptID=attempt_id,
                        question_id=question_id,
                        chunk_url=relative_path
                    )
    
            if not is_match:
                transcript = transcribe_audio(full_path)
                new_record.transcript = transcript
    
            try:
                db.add(new_record)
                db.commit()
            except Exception as e:
                db.rollback()
                return {'error': f'database error {e}'}
    
                return {'status': 'suspicious', 'score': score, 'transcript': transcript}
    
            return {'status': 'match', 'score': score}
    
        return {'audio_path': relative_path}

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

    @staticmethod
    def pt(lm, i, w, h):
        return np.array([int(lm[i].x * w), int(lm[i].y * h)])

    @staticmethod
    def EyeGazeMovement(image):
        rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        res = face_mesh.process(rgb)

        if not res.multi_face_landmarks:
            return "NO FACE"

        h, w, _ = image.shape
        lm = res.multi_face_landmarks[0].landmark

        left = ProctoringController.pt(lm, 33, w, h)
        right = ProctoringController.pt(lm, 133, w, h)
        top = ProctoringController.pt(lm, 159, w, h)
        bottom = ProctoringController.pt(lm, 145, w, h)
        iris = ProctoringController.pt(lm, 468, w, h)

        x = (iris[0] - left[0]) / (right[0] - left[0] + 1)
        y = (iris[1] - top[1]) / (bottom[1] - top[1] + 1)

        if x < 0.38:
            return "LEFT"
        elif x > 0.62:
            return "RIGHT"
        elif y < 0.38:
            return "UP"
        elif y > 0.62:
            return "DOWN"
        return "CENTER"
    
    # @staticmethod
    # async def FaceProctoringParallel(file: UploadFile, attempt_id: int, identity_no: str, db: Session):
    #     '''This method checks the face proctoring, saving the image on the server and add's the entry in the database in the student exam log table. '''

    #     try:
    #         examAttempt = db.query(ExamAttempt).filter(ExamAttempt.ID == attempt_id).first()

    #         if examAttempt:
                
    #             image_bytes = await file.read()
                
    #             if not image_bytes:

    #                 new_record = StudentExamLog(
    #                     attempt_id = attempt_id,
    #                     TIMESTAMP = datetime.now(),
    #                     position = 'unknow',
    #                     isPresent = 0,
    #                     image_path = None, 
    #                     eye_gaze = None
    #                 )
    #                 db.add(new_record)
    #                 db.commit()
    #                 return {'error': 'no image found'}
                    
    #             image_array = ProctoringController.bytes_to_numpy(image_bytes)

    #             face_count = ProctoringController.count_face(image_array)

    #             serverImagePath = ProctoringController.saveImageOnServer(image_bytes, attempt_id)
    #             new_record = StudentExamLog()
    #             new_record.attempt_id = attempt_id
    #             new_record.TIMESTAMP = datetime.now()

    #             position = "unknown"
                
    #             try:
                    
    #                 if face_count > 1:
    #                     new_record.isPresent = True
    #                     new_record.position = "multiple face detected"
    #                     position = "Multiple faces detected"
                    
    #                 elif face_count == 0:
    #                     new_record.isPresent = False
    #                     new_record.position = "none"
    #                     position = "no face detected"
                        
    #                 else:
    #                     identity_verified, pose, eye_gaze = await asyncio.gather(
    #                         asyncio.to_thread( UserController.verifyPerson, identity_no, image_array),
    #                         asyncio.to_thread( PoseEstimationClass.process_face_pose, image_array), 
    #                         asyncio.to_thread( ProctoringController.EyeGazeMovement, image_array)
    #                     )
    #                     new_record.eye_gaze = eye_gaze
                        
    #                     if identity_verified == True:
    #                         new_record.position = str(pose)
    #                         new_record.isPresent = True 
    #                         position = pose

    #                     elif identity_verified == False:
    #                         new_record.position = "identity mismatched"
    #                         new_record.isPresent = False
    #                         position = "Identity Mismatched. Unauthorized Person Detected!"
                        
                    
    #                 new_record.TIMESTAMP = datetime.now()
    #                 new_record.image_path = serverImagePath
    #                 # print(f"file path = {serverImagePath}, time: {new_record.TIMESTAMP}")
    #                 db.add(new_record)
    #                 db.commit()

    #                 return {'pose': position}
                
    #             except Exception as e:
    #                 db.rollback()
    #                 print(f'ERROR: {e}')
    #                 return {'fail': f"data base error {e}"}

    #         else:
    #             return {'fail': 'no student record found. '}
            
    #     except Exception as e:
    #         db.rollback()
    #         return {'fail': 'ERROR'}
        
        
    @staticmethod
    async def detect_objects(file: UploadFile, attempt_id: int, time: str, db: Session):

        try:
            contents = await file.read()

            image_array = ProctoringController.bytes_to_numpy(contents)

            server_path = await asyncio.to_thread(
                        ProctoringController.saveImageOnServer, back_camera_base_folder , contents, attempt_id, time
                    )
            print(f'image save at {server_path}')

            results = object_detection_model(image_array)

            detected_flag = False
            detected_objects = []

            for r in results:
                for box in r.boxes:
                    cls_id = int(box.cls[0])
                    label = object_detection_model.names[cls_id]

                    if label in cheating_objects:
                        detected_flag = True

                        if label not in detected_objects:
                            detected_objects.append(label)


            if detected_objects:
                print("No cheating objects detected.")

                objects = ""
                for obj in detected_objects:
                    objects += obj + ","
                    print(f"Detected cheating object: {obj}")
                try:
                    new_record = DetectedObjects(
                        attemptID = attempt_id,
                        objects = objects,
                        timestamp = datetime.now(),
                        image_path = server_path
                    )
                    db.add(new_record)
                    db.commit()
                except Exception as e:
                    db.rollback()
                    print(f"DB ERROR: {e}")
                    return {'fail': f'database error: {e}'}

            return {
                "cheating_detected": detected_flag,
                "detected_objects": detected_objects
            }
        except Exception as e:
            return {'fail': f'database error: {e}'}
    
    
    
    @staticmethod
    async def FaceProctoringParallel(file: UploadFile, attempt_id: int, identity_no: str, time: str, db: Session):
        '''This method checks the face proctoring, saving the image on the server and adds the entry in the database in the student exam log table.'''
        try:
            examAttempt = db.query(ExamAttempt).filter(ExamAttempt.ID == attempt_id).first()
            
            if not examAttempt:
                return {'fail': 'no student record found.'}

            image_bytes = await file.read()
            
            if not image_bytes:
                new_record = StudentExamLog(
                    attempt_id=attempt_id,
                    TIMESTAMP=datetime.now(),
                    position='unknown',
                    isPresent=0,
                    image_path=None,
                    eye_gaze=None
                )
                db.add(new_record)
                db.commit()
                return {'error': 'no image found'}

            loop = asyncio.get_event_loop()
            
            # Numpy conversion
            image_array = await asyncio.to_thread(ProctoringController.bytes_to_numpy, image_bytes)

            # Face count pehle check karo
            face_count = await loop.run_in_executor(
                process_executor,
                ProctoringController.count_face,
                image_array
            )

            position = "unknown"
            is_present = False
            eye_gaze = None
            server_path = None

            if face_count > 1:
                # Multiple faces - sirf image save karo, ML skip karo
                server_path = await asyncio.to_thread(
                    ProctoringController.saveImageOnServer,pictures_base_folder , image_bytes, attempt_id, time
                )
                is_present = True
                position = "Multiple faces detected"

            elif face_count == 0:
                # No face - sirf image save karo, ML skip karo
                server_path = await asyncio.to_thread(
                    ProctoringController.saveImageOnServer, pictures_base_folder, image_bytes, attempt_id, time
                )
                is_present = False
                position = "no face detected"

            else:
                # Ek face mila - image save + teeno ML parallel chalao
                try:
                    server_path, (identity_verified, pose, eye_gaze) = await asyncio.gather(
                        asyncio.to_thread(ProctoringController.saveImageOnServer, pictures_base_folder, image_bytes, attempt_id, time),
                        asyncio.gather(
                            loop.run_in_executor(process_executor, UserController.verifyPerson, identity_no, image_array),
                            loop.run_in_executor(process_executor, PoseEstimationClass.process_face_pose, image_array),
                            loop.run_in_executor(process_executor, ProctoringController.EyeGazeMovement, image_array)
                        )
                    )

                    if identity_verified:
                        position = str(pose)
                        is_present = True
                    else:
                        position = "identity mismatched"
                        is_present = False

                except Exception as e:
                    db.rollback()
                    print(f'ML Processing ERROR: {e}')
                    return {'fail': f'ML processing error: {e}'}

            # Ek baar DB mein save karo - sab data ready hai
            try:
                new_record = StudentExamLog(
                    attempt_id=attempt_id,
                    TIMESTAMP=datetime.now(),
                    position=position,
                    isPresent=is_present,
                    image_path=server_path,
                    eye_gaze=eye_gaze
                )
                db.add(new_record)
                db.commit()
            except Exception as e:
                db.rollback()
                print(f'DB ERROR: {e}')
                return {'fail': f'database error: {e}'}

            return {'pose': position}

        except Exception as e:
            db.rollback()
            print(f'ERROR: {e}')
            return {'fail': f'ERROR: {e}'}
