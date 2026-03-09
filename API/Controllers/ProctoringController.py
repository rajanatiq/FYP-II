# lib imports 
import numpy as np
import cv2
from datetime import datetime
from fastapi import UploadFile
from sqlalchemy.orm import Session
import time
import os
from pathlib import Path
from deepface import DeepFace
import shutil
from Controllers.UserController import UserController
root_dir = Path(__file__).resolve().parent.parent # Points to API Folder 

# import Models
from Models import (ProctoringEvent,CameraMonitoring, ScreenMonitoring, StudentExamLog, ExamAttempt)

# tarined models for prediction
from ML.FaceCount.faceCount import FaceCounter
from ML.pose_estimation_yaw_pitch.Training.predict_pose import PoseEstimation
from ML.PoseEstimationPivot.PoseEstimation import PoseEstimationClass
from ML.faceCount import FaceCounter

counter = FaceCounter()
predict = PoseEstimation()
pictures_base_folder = str(root_dir / 'Assets/Images/CameraMonitoring') # Points to Camera Monitoring folder
class ProctoringController:
    
    @staticmethod
    async def FaceProctoring(file: UploadFile, attempt_id: int, identity_no: int,  db: Session):
        '''This method checks the face proctoring, saving the image on the server and add's the entry in the database in the student exam log table. '''
        
        print(f'attempt id: {attempt_id}')
        examAttempt = db.query(ExamAttempt).filter(ExamAttempt.ID == attempt_id).first()
        if examAttempt: 
            proct = ProctoringController()
            content = await file.read()
            
            np_array = np.frombuffer(content, np.uint8)
            image = cv2.imdecode(np_array, cv2.IMREAD_COLOR)
            
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
                    
                    for i in result:
                        print(f'Confidence: {i["face_confidence"]}') # type:ignore
                    
            except Exception as e:  
                    face_count = 0  
            # face_count = counter.faceCount(image=image)

            
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
                    
                    if identity_verified == True:
                        pose = PoseEstimationClass.process_face(image)
                        new_record.position = str(pose)
                        new_record.isPresent = True
                        position = pose
                        
                    elif identity_verified == False:
                        new_record.position = "identity mismatched"
                        new_record.isPresent = False
                        position = "Identity Mismatched. Unauthorized Person Detected!"
                    # return {"pose": pose}
                    
                serverImagePath = proct.saveImageOnServer(content, attempt_id)
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

    def saveImageOnServer(self, image, attempt_id):
        '''Helper function to save the image on the server, by creating unique file name.'''
        image_path = os.path.join(pictures_base_folder, str(attempt_id))
        
        if not os.path.exists(image_path):
            os.mkdir(image_path)
        
        filename = ProctoringController.getTimeStamp() + ".jpg"
        print(filename)
        image_path = os.path.join(image_path, filename)
        
        ProctoringController.saveFileOnServer(image, image_path)
        # with open(image_path, "wb") as f:
        #     f.write(image)
        return os.path.join(str(attempt_id), filename)
    
    
    @staticmethod
    async def VoiceProctoring(file: UploadFile):
        '''Takes the audio and process and then save on the server. '''
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

            if str(new_event.EventType) == 'Camera':
                new_proctoring = CameraMonitoring(
                    EventID = new_event.ID,
                    IsStudentPresent = 1,
                    description = "Multiple faces detected in the camera during exam", 
                    ImageEvidence = ""
                )

                return await ProctoringController.add_proctoring_image(file, new_proctoring, db)
            elif str(new_event.EventType) == 'Screen':
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