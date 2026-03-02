from fastapi import UploadFile
from fastapi.responses import JSONResponse

from sqlalchemy.orm import Session
# import Models
from Models import (CourseAllocation, CourseEnrollment, CourseOffering, Student, Teacher, Users, Course, Exam, ExamMCQ,MCQOption,MCQAns, ExamAttempt)

from Schemas.StudentAnswer import StudentAnswer
from Schemas.McqAnswer import McqAnswer
from Schemas.AttemptedExam import AttemptedExam


class StudentController:

    @staticmethod
    def get_all_student(db: Session):
        result = db.query(Student).all()
        return [item.to_dict() for item in result]
    
    @staticmethod
    def get_enrolled_courses(db: Session, student_id: int):
        result = db.query(
            CourseOffering.ID.label('offeringID'),
            CourseEnrollment.ID.label('enrollmentID'),
            CourseOffering.CourseID.label('courseID'),
            Course.Title.label('courseTitle'),
            Teacher.ID.label('teacherID'),
            Users.Name.label('teacherName')
        ).join(
            CourseEnrollment, CourseEnrollment.OfferingID == CourseOffering.ID
        ).join(
            CourseAllocation, CourseAllocation.OfferingID == CourseOffering.ID
        ).join(
            Course, Course.ID == CourseOffering.CourseID
        ).join(
            Teacher, Teacher.ID == CourseAllocation.TeacherID
        ).join(
            Users, Users.ID == Teacher.userID   # get teacher name correctly
        ).join(
            Student, Student.StudentID == CourseEnrollment.StudentID
        ).filter(
            Student.StudentID == student_id, 
            CourseEnrollment.Status == 'enrolled'
        ).all()
        if not result:
            return {
                'content': 'null'
            }
        
        courses = [
                    {
                        "offeringID": row.offeringID,
                        "enrollmentID": row.enrollmentID,
                        "courseID": row.courseID,
                        "courseTitle": row.courseTitle,
                        "teacherID": row.teacherID,
                        "teacherName": row.teacherName
                    } 
                for row in result
            ]
        return courses
 
# Raw Query ------->
# select cf.ID as [OfferingID], CE.ID as [EnrollmentID], CF.CourseID as [CourseID],
# S.StudentID, C.Title
# ,T.ID as [TeacherID], U.Name as [TeacherName]
# from CourseOffering CF 
# JOIN CourseEnrollment CE on CF.ID = CE.OfferingID
# JOIN CourseAllocation CA on CA.OfferingID = CF.ID
# JOIN Course C on CF.CourseID = C.ID
# JOIN Teacher T on t.ID = CA.TeacherID
# JOIN Users U on U.ID = T.userID
# JOIN Student S on s.StudentID = CE.StudentID where s.StudentID = 1 and CE.status = 'enrolled'

    @staticmethod
    def fetch_exams(db: Session, course_id: int):
        """get pending exams of a particular course"""
        result = db.query(
            Exam.ID.label("examID"),
            Exam.TITLE.label('examTitle'),
            Exam.E_DATE.label('examDate'),
            Exam.timeInMinutes.label("timeInMinutes"),
            Exam.STATUS.label('status'),
            Exam.E_TYPE.label('examType')
        ).join(
            CourseAllocation, CourseAllocation.ID == Exam.A_ID
        ).join(
            CourseOffering, CourseOffering.ID == CourseAllocation.OfferingID
        ).join(
            Course, Course.ID == CourseOffering.CourseID
        ).filter(
            Course.ID == course_id, 
            Exam.STATUS == "pending"
        )
        if result:
            exams = [
                    {
                        'examID': row.examID,
                        'examTitle': row.examTitle,
                        'examDate': row.examDate,
                        'timeInMinutes': row.timeInMinutes,
                        'status': row.status,
                        'examType': row.examType
                    }
                    for row in result
                ]
            return exams
        else:
           return JSONResponse(content={"content": "null"}, status_code=404)
        
    # def fetch_mcqs(db: Session, exam_id: int):
    #     result = db.query(
    #         ExamMCQ.ID.label("mcqID"),
    #         MCQOption.ID.label('optionID'),
    #         ExamMCQ.DESCRIPTION.label("question"),
    #         MCQOption.OPTION_TEXT.label("options"),
    #         MCQOption.IS_CORRECT.label('isCorrect')

    #     ).join(
    #         ExamMCQ,ExamMCQ.ID==MCQOption.M_ID
    #     ).filter(ExamMCQ.E_ID==exam_id)
        
    #     if result:
    #         return {
    #             'content':
    #             [
    #                 {
    #                     'mcqID': row.mcqID,
    #                     'optionID':row.optionID,
    #                     'question':row.question,
    #                     'options':row.options,
    #                     'isCorrect': row.isCorrect
    #                 }
    #                 for row in result
    #             ]
    #         }
    #     else:
    #        return JSONResponse(content={"content": "null"}, status_code=404)
           
    @staticmethod

    def Add_McqAnswer(data: StudentAnswer, db: Session):
        try:
            for ans in data.answers:
                record = MCQAns(
                    M_ID=ans.M_ID,
                    S_ID=data.S_ID,
                    O_ID=ans.O_ID
                )
                db.add(record)
            db.commit()
            return {"message": "Data inserted successfully"}
        except Exception as e:
            db.rollback()
            print(f"DB insert error: {e}")
            return {"message": f"DB insert error: {e}"}
        
# select 
# E.TITLE, 
# E.START_TIME, 
# e.END_TIME,
# e.E_DATE
# from 
# CourseAllocation CA 
# JOIN Exam E on CA.ID = E.A_ID
# JOIN CourseOffering CF on CF.ID = CA.OfferingID
# JOIN Course C on c.ID = CF.C.ourseID

# where C.ID = 1

    @staticmethod
    def fetchExamAttemptID(sid: int, eid: int, db: Session):
        """Function to fetch the student exam attempt id of a student exam which he has attempted, against student id and exam id """
        try:
            result = db.query(
                ExamAttempt.ID.label('attemptID')
            ).filter(
                ExamAttempt.examID == eid, 
                ExamAttempt.studentID == sid
            ).first()
            
            if not result:
                return {'error': 'Attempt ID not found.'}
            return {'id': result.attemptID}
        except Exception as e:
            return {'error': f'Database error {e}'}
        