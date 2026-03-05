from sqlalchemy.orm import Session
from sqlalchemy import extract, func, distinct, case, cast, Time
from datetime import datetime
from fastapi.responses import JSONResponse
from Schemas.StudentLog import StudentLog
# import Models
from Models import (Exam,CourseAllocation,CourseOffering, Course, Teacher, Users, Section, Department, ExamAttempt, Student, StudentExamLog)
image_base_url = 'http://192.168.100.54:8000/images/'

class TeacherController:
    @staticmethod
    def teacherAllocatedCourses(t_id: int, session: str ,db:Session):
        current_year = datetime.now().year
        try:
            result = db.query(
                CourseAllocation.ID.label('allocationID'), 
                CourseOffering.ID.label('offeringID'),
                Course.ID.label('courseID'),
                Section.ID.label('sectionID'),
                Section.name.label('section'),
                Department.name.label('depName'),
                Course.COURSE_CODE.label('courseCode'),
                Course.Title.label('courseTitle'),
                CourseOffering.Semester.label('semester'),
                func.year(CourseAllocation.AllocationDate)
            ).join(
                CourseOffering, CourseOffering.ID == CourseAllocation.ID
            ).join(
                Course, Course.ID == CourseOffering.CourseID
            ).join(
                Section, Section.ID == CourseAllocation.SECTION
            ).join(
                Teacher, Teacher.ID == CourseAllocation.TeacherID
            ).join(
                Department, Department.ID == CourseOffering.DEPARTMENT
            ).join(
                Users, Users.ID == Teacher.userID
            ).filter(
                Teacher.ID == t_id, 
                extract('year', CourseAllocation.AllocationDate) == current_year, 
                CourseOffering.SESSION == session
            ).all()
            
            if not result:
                return {'error': 'no courses found'}
            else:
                courses = [
                    {
                        'allocationID': row.allocationID,
                        'offeringID': row.offeringID,
                        'courseID': row.courseID, 
                        'sectionID': row.sectionID,
                        'department': row.depName,
                        'section': row.section,
                        'semester': row.semester,
                        'courseCode': row.courseCode,
                        'courseTitle': row.courseTitle
                    }
                for row in result   
                ]
                return JSONResponse(content={"courses": courses})
        except Exception as e:
            return {'error': f"Database Error: {str(e)}"}
    
    @staticmethod
    def course_allocation_id(course_id: int, teacher_id: int, db: Session):
        try:
            allocation = db.query(
                CourseAllocation.ID.label("ID")
            ).join(CourseOffering, CourseOffering.ID == CourseAllocation.OfferingID).\
                join(Course, Course.ID == CourseOffering.CourseID).\
                join(Teacher, Teacher.ID == CourseAllocation.TeacherID).\
                join(Users, Users.ID == Teacher.userID).\
                filter(Course.ID == course_id, Teacher.ID == teacher_id).first()

            if allocation:
                return {"CourseAllocationID": allocation[0]}
            else:
                return {"message": "No allocation found for this course and teacher"}

        except Exception as e:
            db.rollback()
            return {"error": f"Database error: {str(e)}"}, 500

    @staticmethod
    def fetch_allocated_courses_exams(teacher_id: int , db:Session):
        result=db.query( 
                    CourseAllocation.ID.label('allocationID'), 
                    Exam.ID.label("examID"),
                    Exam.TITLE.label('examTitle'),
                    Exam.STATUS.label('examStatus'),
                    Exam.E_DATE.label('examDate'),
                    Exam.timeInMinutes.label('timeInMinutes'),
                    func.count(distinct(ExamAttempt.studentID)).label('appearedStudents')
                 ).join(CourseAllocation, CourseAllocation.ID==Exam.A_ID
                 ).join(Teacher, Teacher.ID==CourseAllocation.TeacherID
                 ).outerjoin(ExamAttempt, ExamAttempt.examID == Exam.ID
                 ).filter(
                    Teacher.ID == teacher_id,
                    CourseAllocation.status == 'allocated'
                ).group_by(
                    CourseAllocation.ID,
                    Exam.ID,
                    Exam.TITLE,
                    Exam.STATUS, 
                    Exam.E_DATE,
                    Exam.timeInMinutes
                ).all()
                 
        if not result:
            return {'error': 'no exams  found'}
        else:
            return [
                {
                    "allocationID": exam.allocationID,
                    "examID": exam.examID,
                    "examDate": exam.examDate,
                    "examTitle": exam.examTitle,
                    "examStatus": exam.examStatus,
                    "appearedStudents": exam.appearedStudents,
                    "timeInMinutes": exam.timeInMinutes
                    
                }
                for exam in result
            ]
            
    @staticmethod 
    def appearedStudentsinExam(exam_id: int, db: Session):
        try:
            result = (
                db.query(
                    Student.StudentID.label("studentID"),
                    Users.Name.label("studentName"),
                    Users.identity_no.label("identityNo"),
                    func.concat(Department.name, "-", Section.name).label("section")
                )
                .select_from(ExamAttempt)
                .join(Exam, Exam.ID == ExamAttempt.examID)
                .join(Student, Student.StudentID == ExamAttempt.studentID)
                .join(Users, Users.ID == Student.userID)
                .join(Section, Section.ID == Student.Section)
                .join(Department, Department.ID == Section.department)
                .filter(ExamAttempt.examID == exam_id)
                .all()
            )
            
            if not result:
                return {'error': 'no student found'}
            else:
                students = [
                    {
                        "studentID": std.studentID,
                        "studentName": std.studentName,
                        "identityNo": std.identityNo,
                        "section": std.section
                    }
                    for std in result
                ]
                return {"success": students}
            
        except Exception as e:
            db.rollback()
            return {"error": f"Database error: {str(e)}"}, 500


    @staticmethod
    def getStudentLogs(data: StudentLog, db:Session):
        """Gets only the count of logs."""
        # SELECT
        #     count(*) as total_entry,
        #     SUM(CASE WHEN position = 'right' THEN 1 ELSE 0 END) AS right_count,
        #     SUM(CASE WHEN position = 'left' THEN 1 ELSE 0 END) AS left_count,
        #     SUM(CASE WHEN position = 'up' THEN 1 ELSE 0 END) AS up_count,
        #     SUM(CASE WHEN position = 'down' THEN 1 ELSE 0 END) AS down_count,
        #     SUM(CASE WHEN position = 'straight' THEN 1 ELSE 0 END) AS straight_count,
        #     SUM(CASE WHEN position = 'multiple face detected' THEN 1 ELSE 0 END) AS multiple_faces,
        #     SUM(CASE WHEN isPresent = 1 THEN 1 ELSE 0 END) AS total_present,
        #     SUM(CASE WHEN isPresent = 0 THEN 1 ELSE 0 END) AS total_absent
        # FROM studentExamlog sl 
        # JOIN examAttempt ea on ea.id = sl.attempt_id
        # JOIN Student s on s.StudentID = ea.studentID

        # WHERE ea.studentID = 1 and ea.examID = 2
        try:
            result = db.query( 
                func.count().label('total'),
                func.sum(case((StudentExamLog.position == 'straight', 1), else_= 0)).label('straight'),
                func.sum(case((StudentExamLog.position == 'left', 1), else_= 0)).label('left'),
                func.sum(case((StudentExamLog.position == 'right', 1), else_= 0)).label('right'),
                func.sum(case((StudentExamLog.position == 'up', 1), else_= 0)).label('up'),
                func.sum(case((StudentExamLog.position == 'down', 1), else_= 0)).label('down'),
                func.sum(case((StudentExamLog.position == 'multiple faces', 1), else_= 0)).label('multiple_faces'),
                func.sum(case((StudentExamLog.isPresent == True, 1), else_= 0)).label('total_presence'),
                func.sum(case((StudentExamLog.isPresent == False, 1), else_= 0)).label('total_absence'),
            ).select_from(StudentExamLog).join(
                ExamAttempt, ExamAttempt.ID == StudentExamLog.attempt_id
            ).join(
                Student, Student.StudentID == ExamAttempt.studentID
            ).join(
                Exam, Exam.ID == ExamAttempt.examID
            ).filter(
                ExamAttempt.studentID == data.std_id,
                ExamAttempt.examID == data.exam_id, 
                # cast(StudentExamLog.TIMESTAMP, Time).between(data.startTime, data.endTime)
            ).first()
            
            if result: 
                record = {
                    'total': result.total,
                    'straight': result.straight,
                    'left': result.left,
                    'right': result.right,
                    'up': result.up,
                    'down': result.down,
                    'multiple_faces': result.multiple_faces,
                    'total_presence': result.total_presence,
                    'total_absence': result.total_absence
                }
                return {'content': record}
            else:
                return {"error": "no record found"}
        except Exception as e:
            return {"error": f"Database error: {str(e)}"}, 500
        
        
# select CA.ID from CourseOffering CF
# JOIN CourseAllocation CA on CA.OfferingID = Cf.ID
# JOIN Course C on c.ID = CF.CourseID
# JOIN Teacher T on T.ID = CA.TeacherID
# JOIN Users U on T.userID = U.ID
# where C.ID = 1 and T.ID = 1

    @staticmethod
    def getStudentLogsWithImages(s_id: int, e_id: int, db: Session):
        """get the logs with image evidences4"""
        try:
            result = db.query(
                StudentExamLog.id.label('id'),
                StudentExamLog.position.label('position'),
                StudentExamLog.isPresent.label('isPresent'),
                StudentExamLog.image_path.label('image_url')            
            ).join(
                ExamAttempt, ExamAttempt.ID == StudentExamLog.attempt_id
            ).filter(
                ExamAttempt.studentID == s_id, 
                ExamAttempt.examID == e_id,
                StudentExamLog.position != 'straight',
            ).all()
            
            if not result:
                return {'error', 'no record found.'}
            
            content = [
                {
                    'id': data.id,
                    'position': data.position,
                    'isPresent': data.isPresent,
                    'image_url': image_base_url + data.image_url
                }
                for data in result
            ]
            
            return {'content': content}
        except Exception as e:
            return {'error': f'database error {e}'}