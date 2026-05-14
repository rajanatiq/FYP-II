from typing import List
from API.Schemas.ExamMcqCreate import ExamMCQCreate
from API.Schemas.ExamCreate import ExamCreate
from API.Schemas.SaveMcqAns import SaveMcqAns
from fastapi import APIRouter, File, Request, Depends, UploadFile
from sqlalchemy.orm import Session
from API.db import get_db
from API.Controllers.ExamController import ExamController
from API.Controllers.StudentController import StudentController
from API.Schemas.AttemptedExam import AttemptedExam
router = APIRouter()

session = Depends(get_db)

@router.get('/fetchExams/{courseID}')
# def fetch_exams(courseID:int, db:Session=Depends(get_db)):
def fetch_exams(courseID:int, db:Session=session):
    return StudentController.fetch_exams(db, courseID)
    
@router.post('/createExam')
def add_exam(exam: ExamCreate, db: Session = session):
    return ExamController.create_exam(exam, db)

@router.post('/addMcq')
def add_mcq_endpoint(mcq: List[ExamMCQCreate], db: Session = session):
    return ExamController.add_mcqs(mcq, db)

@router.delete('/deleteExam/{id}')
def delete_exam(id: int, db: Session = session):
    return ExamController.remove_exam(id, db)

@router.get('/fetchMcqs/{exam_id}')
def fetch_mcqs(exam_id: int, db:Session= session):
    return ExamController.fetch_mcqs(db, exam_id)

@router.get('/fetchDescQuestions/{exam_id}')
def fetch_desc_questions(exam_id: int, db:Session = session):
    return ExamController.fetch_desc_questions(db, exam_id)

@router.post("/checkExamAttemptRecord")
def ifExamAlreadyAttempt(data: AttemptedExam, db:Session = session):
    return ExamController.ifExamAlreadyAttempt(data, db)

@router.post('/addStudentExamAttempt')
def addStudentExamRecord(data: AttemptedExam, db:Session= session):
    return ExamController.addStudentExamEntry(data, db)

@router.get('/updateExamStatus/{exam_id}')
def setExamStatusToComplete(exam_id: int, db: Session=session):
    return ExamController.setExamStatusToComplete(exam_id, db)

@router.get('/checkBackCamera/{attempt_id}')
def checkBackCamera(attempt_id: int, db: Session = session):
    return ExamController.checkBackCamera(attempt_id, db)

@router.get('/setBackCameraStatus/{attempt_id}')
def setBackCameraStatus(attempt_id: int, db: Session = session):
    return ExamController.setBackCameraStatus(attempt_id, db)

# MARK: POST METHODS
@router.post('/saveMcqAnswers')
def save_mcq_answers(data: List[SaveMcqAns], attempt_id: int, db: Session = session):
    return ExamController.save_mcq_answers(data,attempt_id, db)


