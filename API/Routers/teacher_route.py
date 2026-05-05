from Controllers.TeacherController import TeacherController
from fastapi import APIRouter, File, Request, Depends, UploadFile, Form
from sqlalchemy.orm import Session
from db import get_db
from Schemas.StudentLog import StudentLog
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

@router.post('/getStudentExamLog')
def getStudentExamLog(data: StudentLog, db:Session = Depends(get_db)):
    return TeacherController.getStudentLogs(data, db)

@router.post('/getStudentLogsWithImages')
def getImages(data: StudentLog, db:Session = Depends(get_db)):
    return TeacherController.getStudentLogsWithImages(data, db)

@router.get('/deleteStudentLogRecord/{logId}')
def deleteStudentLogRecord(logId: int, db: Session = Depends(get_db)):
    return TeacherController.deleteStudentLogRecord(logId, db)

@router.get('/fetchStudentAudioLogs/{attempt_id}')
def fetchStudentAudioLogs(attempt_id: int, db: Session = Depends(get_db)):
    return TeacherController.fetchStudentAudioLogs(attempt_id, db)

@router.get('/fetchStudentRecording/{std_id}/{exam_id}')
def fetchStudentRecording(std_id: int, exam_id: int, db: Session = Depends(get_db)):
    return TeacherController.fetchStudentRecording(std_id, exam_id, db)