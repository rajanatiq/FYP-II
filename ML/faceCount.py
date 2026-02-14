import mediapipe as mp
import cv2

class FaceCounter:
    def __init__(self):
        mp_face = mp.solutions.face_detection
        self.face_detection = mp_face.FaceDetection(model_selection = 1, min_detection_confidence = 0.6)

    def faceCount(self, image):
        img = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        results = self.face_detection.process(img)

        if results.detections:
            return len(results.detections)
        else:
            return 0