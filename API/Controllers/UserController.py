import cv2
from sqlalchemy.orm import Session
from API.Models import (Users, Student, Teacher)
from fastapi import UploadFile, File
import numpy as np
import os
import shutil
from deepface import DeepFace
from sklearn.metrics.pairwise import cosine_similarity
class UserController:

    @staticmethod
    def get_all_users(db: Session):
        result = db.query(Users).all()  
        users = [Users.to_dict(data) for data in result]
        return users

    # @staticmethod
    # def checkLogin(file: UploadFile, id: int, db: Session):
    #     # import time
        # try:
        #     # time.sleep(5)
        #     user = db.query(Users.ID, Users.Role, Users.Name).filter(
        #         Users.identity_no == id
        #     ).first()
    
        #     if user is None:
        #         return {"error": "No User Found"}
        #     else:
        #         userId, role, name = user
    
        #         id = 0
        #         if role.lower() == "teacher":
        #             getID = db.query(Teacher.ID).filter(
        #                 Teacher.userID == userId
        #             ).first()
        #             id = getID[0]
        #         elif role.lower() == "student":
        #             getID = db.query(Student.StudentID).filter(
        #                 Student.userID == userId
        #             ).first()
        #             id = getID[0]
    
        #         return {
        #             "success": True,
        #             "id": id,
        #             "userID": userId,
        #             "role": role,
        #             "name": name
        #             }
        # except Exception as e:
        #     print("database error")
        #     return {"error": f"Database error: {str(e)}"}, 500

    @staticmethod
    def verifyPerson(id: str, image_array: np.ndarray ):
        from pathlib import Path
        DIR = Path(__file__).resolve().parent.parent.parent
        TEMP_IMAGE = "temp.jpg"
        EMBEDDINGS_DIR = str(DIR /"StoredEmbeddings")
        THRESHOLD = 0.65
       
        try:
            result = DeepFace.represent(
                        img_path=image_array,
                        model_name="Facenet",
                        enforce_detection=True
                    )

            live_embedding = result[0]["embedding"] # type: ignore
        except Exception as e:
            return False
        
        embedding_path = os.path.join(EMBEDDINGS_DIR, f"{id}.npy")
        print(f"embedding path: {embedding_path}")
        if not os.path.exists(embedding_path):
            return False
        # Load saved embedding
        saved_embedding = np.load(embedding_path)

        # Compare embeddings
        similarity = cosine_similarity(
            [live_embedding], # type: ignore
            [saved_embedding] # type: ignore
        )[0][0]
        print(similarity)
        if similarity > THRESHOLD:
            return True
        else:
            return False


    @staticmethod
    async def checkLogin(file: UploadFile, identity_no: str, db: Session):
        from pathlib import Path
        DIR = Path(__file__).resolve().parent.parent.parent
        TEMP_IMAGE = "temp.jpg"
        EMBEDDINGS_DIR = str(DIR /"StoredEmbeddings")
        THRESHOLD = 0.65
        content = await file.read()
       
        try:
            # time.sleep(5)
            user = db.query(Users.ID, Users.Role, Users.Name).filter(
                Users.identity_no == identity_no
            ).first()
    
            if user is None:
                print(f"No User Found. id: {identity_no}")
                return {"status": "error", "detail": "No User Found"}
            else:
                userId, role, name = user
                
                with open(TEMP_IMAGE, "wb") as buffer:
                    # shutil.copyfileobj(file.file, buffer)
                    buffer.write(content)

                # Generate embedding from live image
                try:
                    result = DeepFace.represent(
                        img_path=TEMP_IMAGE,
                        model_name="Facenet",
                        enforce_detection=True
                    )

                    live_embedding = result[0]["embedding"] # type: ignore
                    # print(len(result))

                except Exception as e:
                    print("Face not detected.")
                    return {"status": "error", "detail": "Face not detected"}

                # Build path of saved embedding
                embedding_path = os.path.join(EMBEDDINGS_DIR, f"{identity_no}.npy")

                # Check file exists
                if not os.path.exists(embedding_path):
                    print("Embedding not found for this ID")
                    return {"status": "error", "detail": "Embedding not found for this ID"}

                # Load saved embedding
                saved_embedding = np.load(embedding_path)

                # Compare embeddings
                similarity = cosine_similarity(
                    [live_embedding], # type: ignore
                    [saved_embedding] # type: ignore
                )[0][0]
                
                if similarity > THRESHOLD:
                    
                    id = 0 # Holds Teacher, Student or Admin ID.
                    
                    if role.lower() == "teacher":
                        getID = db.query(Teacher.ID).filter(
                            Teacher.userID == userId
                        ).first()
                        id = getID[0] # type: ignore
                    elif role.lower() == "student":
                        getID = db.query(Student.StudentID).filter(
                            Student.userID == userId
                        ).first()
                        id = getID[0] # type: ignore
        
                    print("User Found.")
                    return {
                        "status": "success",
                        "id": id,
                        "userID": userId,
                        "role": role,
                        "name": name
                        }
                    
                else:
                    print("Face not match")
                    return {"status": "error", "detail": "Face not matched"}
                
        except Exception as e:
            print("database error")
            return {"status": "error", "detail": f"Database error: {str(e)}"}
        # Save uploaded image
    
    @staticmethod
    def bytes_to_numpy(image_bytes: bytes) -> np.ndarray:
        nparr = np.frombuffer(image_bytes, np.uint8)
        image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        return image # type: ignore