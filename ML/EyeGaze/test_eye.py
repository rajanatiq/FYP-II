import cv2
import numpy as np
import mediapipe as mp
from fastapi import FastAPI, UploadFile, File
import uvicorn


# ======================
# MEDIAPIPE INIT
# ======================
mp_face_mesh = mp.solutions.face_mesh

face_mesh = mp_face_mesh.FaceMesh(
    static_image_mode=True,
    max_num_faces=1,
    refine_landmarks=True,
    min_detection_confidence=0.5
)


# ======================
# LOGIC
# ======================
class EyeTracking:

    @staticmethod
    def pt(lm, i, w, h):
        return np.array([int(lm[i].x * w), int(lm[i].y * h)])

    @staticmethod
    def detect(image):

        rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        res = face_mesh.process(rgb)

        if not res.multi_face_landmarks:
            return "NO FACE"

        h, w, _ = image.shape
        lm = res.multi_face_landmarks[0].landmark

        left = EyeTracking.pt(lm, 33, w, h)
        right = EyeTracking.pt(lm, 133, w, h)
        top = EyeTracking.pt(lm, 159, w, h)
        bottom = EyeTracking.pt(lm, 145, w, h)
        iris = EyeTracking.pt(lm, 468, w, h)

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


# ======================
# FASTAPI
# ======================
app = FastAPI()


@app.post("/test-eye")
async def test_eye(file: UploadFile = File(...)):

    content = await file.read()
    np_arr = np.frombuffer(content, np.uint8)
    img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

    if img is None:
        return {"success": False, "msg": "invalid image"}

    return {
        "success": True,
        "eye_position": EyeTracking.detect(img)
    }


# ======================
# RUN
# ======================
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8002)