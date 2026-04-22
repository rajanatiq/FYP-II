import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi.staticfiles import StaticFiles

# Get the path to the 'API' folder (one level up from main.py)
root_path = Path(__file__).resolve().parent.parent
sys.path.append(str(root_path))

# from Fast_API.Routers import voice_route
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from db import SessionLocal
from Routers import student_route, user_route, admin_route, proctoring_route, exam_route, teacher_route
import Models


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        print("SUCCESS: Successfully connected to database 'Exam Proctoring'.\n")
        db.close()
    except Exception as e:
        print(f"\nERROR: Connection failed.\nDetails: {e}\n")
    yield


# ---------------- FastAPI instance ----------------
app = FastAPI(title="FYP Project API", lifespan=lifespan)


app.mount("/images", StaticFiles(directory="Assets/Images/CameraMonitoring"), name="images")
app.mount("/combinedAudios", StaticFiles(directory="Assets/Audio/CombinedAudios"), name="combinedAudios")

# allows the request from frontEnd or Postman
origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(user_route.router)
app.include_router(student_route.router)
app.include_router(admin_route.router)
app.include_router(exam_route.router)
app.include_router(proctoring_route.router)
app.include_router(teacher_route.router)
#app.include_router(voice_route.router)

