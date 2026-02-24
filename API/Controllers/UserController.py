from sqlalchemy.orm import Session
from Models import (Users, Student, Teacher)
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
    def checkLogin(file: UploadFile, id: int, db: Session):
        from pathlib import Path
        DIR = Path(__file__).resolve().parent.parent.parent
        TEMP_IMAGE = "temp.jpg"
        EMBEDDINGS_DIR = str(DIR /"StoredEmbeddings")
        THRESHOLD = 0.65

        try:
            # time.sleep(5)
            user = db.query(Users.ID, Users.Role, Users.Name).filter(
                Users.identity_no == id
            ).first()
    
            if user is None:
                return {"status": "error", "details": "No User Found"}
            else:
                userId, role, name = user
                with open(TEMP_IMAGE, "wb") as buffer:
                    shutil.copyfileobj(file.file, buffer)

                # Generate embedding from live image
                try:
                    result = DeepFace.represent(
                        img_path=TEMP_IMAGE,
                        model_name="Facenet",
                        enforce_detection=True
                    )

                    live_embedding = result[0]["embedding"]

                except Exception as e:
                    return {"status": "error", "detail": "Face not detected"}

                # Build path of saved embedding
                embedding_path = os.path.join(EMBEDDINGS_DIR, f"{id}.npy")

                # Check file exists
                if not os.path.exists(embedding_path):
                    return {"status": "error", "detail": "Embedding not found for this ID"}

                # Load saved embedding
                saved_embedding = np.load(embedding_path)

                # Compare embeddings
                similarity = cosine_similarity(
                    [live_embedding],
                    [saved_embedding]
                )[0][0]
                print(similarity)
                if similarity > THRESHOLD:
                    id = 0
                    if role.lower() == "teacher":
                        getID = db.query(Teacher.ID).filter(
                            Teacher.userID == userId
                        ).first()
                        id = getID[0]
                    elif role.lower() == "student":
                        getID = db.query(Student.StudentID).filter(
                            Student.userID == userId
                        ).first()
                        id = getID[0]
        
                    return {
                        "status": "success",
                        "id": id,
                        "userID": userId,
                        "role": role,
                        "name": name
                        }
                else:
                    return {"status": "error", "detail": "Face not matched"}
                
        except Exception as e:
            print("database error")
            return {"status": "error", "detail": f"Database error: {str(e)}"}
        # Save uploaded image
