from typing import List
from Schemas.ExamMcqCreate import ExamMCQCreate
from Schemas.ExamCreate import ExamCreate
from fastapi import APIRouter, File, Request, Depends, UploadFile
from sqlalchemy.orm import Session
from db import get_db
from Controllers.ExamController import ExamController
from Controllers.StudentController import StudentController
from Schemas.AttemptedExam import AttemptedExam
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

# @router.get('/fetchMcqs/{exam_id}')
# def fetch_mcqs(exam_id:int, db:Session=Depends(get_db)):
#     return StudentController.fetch_mcqs(db, exam_id) 

@router.get('/fetchMcqs/{exam_id}')
def fetch_mcqs(exam_id: int, db:Session= session):
    return ExamController.fetch_mcqs(db, exam_id)


@router.post("/checkExamAttemptRecord")
def ifExamAlreadyAttempt(data: AttemptedExam, db:Session = session):
    return ExamController.ifExamAlreadyAttempt(data, db)

@router.post('/addStudentExamAttempt')
def addStudentExamRecord(data: AttemptedExam, db:Session= session):
    return ExamController.addStudentExamEntry(data, db)


