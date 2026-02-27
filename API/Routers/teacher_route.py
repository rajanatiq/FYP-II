from Controllers.TeacherController import TeacherController
from fastapi import APIRouter, File, Request, Depends, UploadFile, Form
from sqlalchemy.orm import Session
from db import get_db

router = APIRouter()

@router.get("/course-allocation/{course_id}/{teacher_id}")
def course_allocation(course_id: int, teacher_id: int, db: Session = Depends(get_db)):
    
    return TeacherController.course_allocation_id(course_id, teacher_id, db)


@router.get('/teacherCourses/{teacherID}/{session}')
def teacherCourses(teacherID: int, session: str, db: Session = Depends(get_db)):
    return TeacherController.teacherAllocatedCourses(teacherID, session, db)

@router.get('/teacherExams/{teacherID}')
def teacherExams(teacherID: int, db: Session = Depends(get_db)):
    return TeacherController.fetch_allocated_courses_exams(teacherID, db)

@router.get('/studentsAppearedInExam/{exam_id}')
def studentsInExam(exam_id: int, db:Session = Depends(get_db)):
    return TeacherController.appearedStudentsinExam(exam_id, db)

@router.get('/getStudentExamLog/{s_id}/{e_id}')
def getStudentExamLog(s_id: int, e_id: int, db:Session = Depends(get_db)):
    return TeacherController.getStudentLogs(s_id, e_id, db)