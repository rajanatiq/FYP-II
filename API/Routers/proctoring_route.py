
from Controllers.ProctoringController import ProctoringController
# from Controllers.AIModelsController import AIModelsController


from fastapi import APIRouter, File, Request, Depends, UploadFile, Form
from sqlalchemy.orm import Session
from db import get_db
router = APIRouter()


@router.post('/FaceMonitoring')
# async def CameraMonitoring(file: UploadFile = File(...), EX_ID: int = Form(...), S_ID: int = Form(...), db: Session=Depends(get_db)):
async def CameraMonitoring(file: UploadFile = File(...),db: Session=Depends(get_db)):
    return await ProctoringController.FaceProctoring(file)

@router.post('/AddProctoringEvent')
async def proctoring_event(file: UploadFile = File(...), EX_ID: int = Form(...),
    S_ID: int = Form(...), db: Session=Depends(get_db)):
    return await ProctoringController.proctoring_event(file, EX_ID, S_ID, db)

@router.get("/studentViolationCount/{std_id}")
def get_student_violation_count(std_id: int, db: Session = Depends(get_db)):
    return ProctoringController.get_student_cheating_count(std_id, db)
