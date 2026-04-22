
from Controllers.ProctoringController import ProctoringController
# from Controllers.AIModelsController import AIModelsController


from fastapi import APIRouter, File, Request, Depends, UploadFile, Form
from sqlalchemy.orm import Session
from db import get_db
router = APIRouter()

@router.post('/FaceMonitoring')
async def FaceMonitoring(file: UploadFile = File(...), attempt_id: int = Form(...), identity_no: str = Form(...) ,db: Session=Depends(get_db)):
    return await ProctoringController.FaceProctoring(file, attempt_id, identity_no, db)

@router.post('/voiceMonitoring')
async def voiceProctoring(file: UploadFile = File(...), attempt_id: int = Form(...), identity_no: str = Form(...), question_id: int = Form(...), exam_type: str = Form(...), db: Session=Depends(get_db)):
    return await ProctoringController.VoiceProctoring(file, attempt_id, identity_no, question_id, exam_type, db)

@router.post('/AddProctoringEvent')
async def proctoring_event(file: UploadFile = File(...), EX_ID: int = Form(...),
    S_ID: int = Form(...), db: Session=Depends(get_db)):
    return await ProctoringController.proctoring_event(file, EX_ID, S_ID, db)

@router.get("/studentViolationCount/{std_id}")
def get_student_violation_count(std_id: int, db: Session = Depends(get_db)):
    return ProctoringController.get_student_cheating_count(std_id, db)

@router.post('/verifyVoice')
async def verify_voice(file: UploadFile = File(...), identity_no: str = Form(...)):
    return await ProctoringController.verifyVoice(file, identity_no)
