from fastapi import UploadFile
from fastapi.responses import JSONResponse

from sqlalchemy.orm import Session
import numpy as np
import cv2
# from Ai_Models.pose_estimation_yaw_pitch.predict_pose import predict_pose
from ML.pose_estimation_yaw_pitch.Training.predict_pose import PoseEstimation


class AIModelsController:
    @staticmethod
    def predict_pose_from_bytes(image_bytes: bytes) -> str:
        """
        Converts image bytes to OpenCV image and calls
        the existing prediction function.
        """
        # Convert bytes to numpy array
        np_arr = np.frombuffer(image_bytes, np.uint8)
        image = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

        if image is None:
            raise ValueError("Invalid image")

        # Call the prediction function from your separate file
        pose = PoseEstimation.predict_pose(image)  # image instead of path
        return pose