from fastapi import APIRouter, File, Request, Depends, UploadFile
from sqlalchemy.orm import Session
from API.db import get_db
from API.Controllers.UserController import UserController
from API.Controllers.StudentController import StudentController
from API.Schemas.StudentAnswer import StudentAnswer

router = APIRouter()

@router.get('/getStudents')
def all_students(db: Session = Depends(get_db)):
    return StudentController.get_all_student(db)

@router.get('/enrolledCourses/{id}')
def get_enrolled_courses(id:int, db:Session = Depends(get_db)):
    return StudentController.get_enrolled_courses(db, id)

@router.get('/exam/{id}')
def fetch_exams(id: int, db: Session = Depends(get_db)):
    return StudentController.fetch_exams(db, id)   

@router.post('/AddMcqAnswer')
def Add_McqAnswer(data: StudentAnswer, db: Session=Depends(get_db)):
    return StudentController.Add_McqAnswer (data, db)

@router.get('/fetchAttemptId/{s_id}/{e_id}')
def fetchExamAttemptID(s_id: int, e_id: int, db: Session = Depends(get_db)):
    return StudentController.fetchExamAttemptID(s_id, e_id, db)

@router.get('/fetchStudentExams/{s_id}')
def fetchStudentExams(s_id: int, db: Session = Depends (get_db)):
    return StudentController.fetch_student_exams(s_id, db)