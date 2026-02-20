import sys
from pathlib import Path


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



# ---------------- FastAPI instance ----------------
app = FastAPI(title="FYP Project API")



# allows the request from frontEnd or Postman
origins = ["*"] 

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,       
    allow_credentials=True,
    allow_methods=["*"],         
    allow_headers=["*"],         
)

# app.include_router(user_route.router)
# app.include_router(student_route.router)
# app.include_router(admin_route.router)
# app.include_router(exam_route.router)
# app.include_router(proctoring_route.router)
# app.include_router(teacher_route.router)
#app.include_router(voice_route.router)



@app.on_event("startup")
def startup_event():
    """
    Ye function server ke start hone par DB connection check karega
    """
    try:
        db = SessionLocal()
        db.execute(text("SELECT 1"))  # simple query to test DB connection
        print("SUCCESS: Successfully connected to database 'FYP_PROJECT_3'.\n")
        db.close()
    except Exception as e:
        print(f"\nERROR: Connection failed.\nDetails: {e}\n")

#  This is testing to check the connection.