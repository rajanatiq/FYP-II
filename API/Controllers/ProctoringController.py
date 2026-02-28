from datetime import datetime
from fastapi import UploadFile
from sqlalchemy.orm import Session
import time
from pathlib import Path

root_dir = Path(__file__).resolve().parent.parent

# import Models
from Models import (ProctoringEvent,CameraMonitoring, ScreenMonitoring)

# lib imports 
import numpy as np
import cv2

# tarined models for prediction
from ML.FaceCount.faceCount import FaceCounter
from ML.pose_estimation_yaw_pitch.Training.predict_pose import PoseEstimation
from ML.PoseEstimationPivot.PoseEstimation import PoseEstimationClass
from ML.faceCount import FaceCounter

counter = FaceCounter()
predict = PoseEstimation()

class ProctoringController:
    
    @staticmethod
    async def FaceProctoring(file: UploadFile):
        content = await file.read()
        np_array = np.frombuffer(content, np.uint8)
        image = cv2.imdecode(np_array, cv2.IMREAD_COLOR)

        face_count = counter.faceCount(image=image)

        if face_count > 1:
            return {"pose": "Multiple faces detected"}
        elif face_count == 0:
            print("No face deteced.")
            return {"pose": "No face detected"}
        else:
            pose = PoseEstimationClass.process_face(image)
            print(f"pose= {pose}")
            return {"pose": pose}

    @staticmethod
    async def VoiceProctoring(file: UploadFile):
        audio_bytes = await file.read()
        if audio_bytes is not None:
            timeStamp = ProctoringController.getTimeStamp()
            dir_path = str(root_dir / f"Assets/Audio/VoiceMonitoring/{timeStamp}.m4a")
            ProctoringController.saveFileOnServer(audio_bytes, dir_path)
        return
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

            if new_event.EventType == 'Camera':
                new_proctoring = CameraMonitoring(
                    EventID = new_event.ID,
                    IsStudentPresent = 1,
                    description = "Multiple faces detected in the camera during exam", 
                    ImageEvidence = ""
                )

                return await ProctoringController.add_proctoring_image(file, new_proctoring, db)
            elif new_event.EventType == 'Screen':
                new_proctoring = ScreenMonitoring(
                    EventID = new_event.ID,
                    ActionType = "Close App", 
                    EvidanceImage = ""
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
    async def add_screen_image(file: UploadFile, new_pro: ScreenMonitoring, db: Session):
        import os
        
        folder = "Assets/Images/ScreenMonitoring"
        if not os.path.exists(folder):
            os.makedirs(folder)
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
    def get_student_cheating_count(std_id: int, db: Session):
        try:
            count = db.query(ProctoringEvent).filter(ProctoringEvent.S_ID == std_id).count()
            return {
                "student_id": std_id,
                "total_violations": count
            }
        except Exception as e:
            return {"error": f"Error: {str(e)}"}, 500

    @staticmethod
    def saveFileOnServer(data: bytes, path: str):
        with open(path, "wb") as f:
            f.write(data)
        return
    @staticmethod
    def getTimeStamp():
        current_timestamp = time.time()
        local_time = time.localtime(current_timestamp)
        readable_time = time.strftime("%Y-%m-%d %H_%M_%S", local_time)
        return readable_time