from fastapi import FastAPI, UploadFile, File
from ultralytics import YOLO # type: ignore
import uvicorn
import shutil
import os

app = FastAPI()

# Load model (CHANGE PATH if needed)
model = YOLO(r"weights/best.pt")


UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


@app.post("/detect")
async def detect(file: UploadFile = File(...)):
    file_path = os.path.join(UPLOAD_DIR, file.filename) #type: ignore

    # Save uploaded file
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # Run detection
    results = model(file_path, conf=0.2)

    detected = []

    for box in results[0].boxes:
        cls = int(box.cls[0])

        if cls == 0:
            detected.append("Headphones")
        elif cls == 1:
            detected.append("Earbuds")

    return {
        "status": "success",
        "detections": detected if detected else ["No Detection"]
    }


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)